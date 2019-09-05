import os
import re
import time
import json
import requests
import datetime
from decimal import Decimal

from selenium import webdriver
from django.db import transaction

from spider import sp_config
from spider.print_waybill import CropPDF
from goods.models import Goods, GoodsSKU
from order.models import OrderInfo, OrderGoods


class PhGoodsSpider():

    def __init__(self):

        self.name = sp_config.PH_USERNAME
        self.password = sp_config.PH_PASSWORD

        self.headers = {'user-agent': sp_config.USER_AGENT}
        self.cookies = get_cookies_from_file(sp_config.PH_COOKIES_SAVE)

        self.login_url = sp_config.PH_LOGIN_URL
        self.product_url = sp_config.PH_PRODUCT_URL
        self.order_url = sp_config.PH_ORDER_URL
        self.search_order_url = sp_config.PH_ORDER_SEARCH_URL
        self.make_waybill_url = sp_config.PH_MAKE_WAYBILL_URL
        self.waybill_url = sp_config.PH_WAYBILL_URL

        self.cookies_path = sp_config.PH_COOKIES_SAVE
        self.error_path = sp_config.PH_ERROR_LOG
        self.update_path = sp_config.PH_UPDATE_LOG
        self.order_path = sp_config.PH_ORDER_LOG

        # 兑换汇率
        self.exchange_rate = sp_config.PHP_CONVERT_RMB
        # 每个订单附加费用
        self.order_add_fee = sp_config.ORDER_ADD_FEE
        # 每件商品附加费用
        self.product_add_fee = sp_config.PRODUCT_ADD_FEE
        # 国家标示
        self.country = 'ph'

        self.num = 0

    def login(self):
        """登录获取cookies"""
        driver = webdriver.Chrome()
        driver.get(self.login_url)
        time.sleep(3)
        driver.find_element_by_xpath('//input[@type="text"]').send_keys(self.name)
        time.sleep(1)
        driver.find_element_by_xpath('//input[@type="password"]').send_keys(self.password)
        time.sleep(2)
        driver.find_element_by_xpath('//button[@class="shopee-button shopee-button--primary '
                                     'shopee-button--normal shopee-button--block shopee-button--round"]').click()
        time.sleep(5)
        for cook in driver.get_cookies():
            self.cookies[cook['name']] = cook['value']

        # 保存cookies到文件中
        save_cookies_to_file(self.cookies_path, self.cookies)

        driver.quit()

    def is_cookies(self):
        # 判断是否有cookies，没有则登录获取
        if not self.cookies:
            self.login()
            print(self.cookies)

    def parse_url(self, url, data):
        """处理请求, 出错 记录错误 抛出异常"""

        try:
            for i in range(2):
                response = requests.get(url, params=data,
                                        cookies=self.cookies, headers=self.headers)

                if response.status_code == 200:
                    return json.loads(response.content.decode())

                print(response.status_code)  # 403
                # 验证出错，重新登录，再请求
                if i == 0:
                    self.login()

            save_log(self.error_path, '验证出错，超出请求次数')
            raise Exception('验证出错：超出请求次数')

        except Exception as e:
            save_log(self.error_path, '请求出错')
            raise e

    # 商品抓取
    def parse_goods_url(self, page):
        """发送请求，获取商品数据字典"""
        data = {
            'SPC_CDS': self.cookies['SPC_CDS'],
            'SPC_CDS_VER': 2,
            'page_number': page,
            'page_size': 24,
            'list_order_type': 'list_time_dsc'
            }
        return self.parse_url(self.product_url, data)

    def save_goods_data(self, goods_data):
        """解析商品数据，保存到数据库
        马来西亚 则保存马来价格，菲律宾 则保存菲律宾价格"""
        for goods in goods_data['data']['list']:
            parent_sku = goods['parent_sku']
            # print('spu信息：', parent_sku)
            self.parse_create_goodsku(parent_sku, goods)

    def get_goods(self, page=1, is_all=False):
        """获取商品信息 保存到数据库"""
        self.is_cookies()

        goods_data = self.parse_goods_url(page)
        self.save_goods_data(goods_data)

        # 是否请求全部数据
        if is_all:
            # 计算共有多少页
            total = goods_data['data']['page_info']['total']
            pages = (total + 23) // 24

            for i in range(page + 1, pages + 1):
                self.get_goods(i, is_all=False)

    @transaction.atomic
    def parse_create_goodsku(self, parent_sku, product_data):
        g_spu, is_c = Goods.objects.get_or_create(spu_id=parent_sku)

        # 事务保存点
        save_id = transaction.savepoint()

        skugood_id_list = []
        is_success_c = True
        for good in product_data['model_list']:
            # 判断sku与spu是否一样 相同则抛出异常
            if parent_sku == good['sku']:
                err_msg = 'SPU与SKU号相同，异常SPU为：' + parent_sku
                save_log(self.update_path, err_msg, err_type='**异常商品：')
                continue

            defaults = {'goods': g_spu, }

            # 非英文数字加字符的商品规格 不添加 （排除小语种语言）
            if re.match(r'^[+\w #,)(_/\-.]+$', good['name']):
                defaults['desc'] = good['name']

            # 判断国家  添加到不同价格
            if self.country == 'ph':
                defaults['ph_sale_price'] = good['price']
            elif self.country == 'my':
                defaults['my_sale_price'] = good['price']
            elif self.country == 'th':
                defaults['th_sale_price'] = good['price']

            # 抓取的商品sku 添加到列表
            skugood_id_list.append(good['sku'])

            # 子sku创建时 异常处理
            try:
                goodsku_obj, is_create = GoodsSKU.objects.update_or_create(sku_id=good['sku'], defaults=defaults)
            except Exception as e:
                save_log(self.update_path, parent_sku, err_type='——同步未成功商品：')
                save_log(self.error_path, str(e.args))
                # 更新有错误 则事务回滚到保存点
                transaction.savepoint_rollback(save_id)
                is_success_c = False
                break
            else:
                # 创建sku 则设置默认图片地址
                if is_create:
                    file_path = format_file_path(good['sku'])
                    goodsku_obj.image = parent_sku + '/' + file_path + '.jpg'
                    goodsku_obj.save()

        # 商品不出错 则执行
        if is_success_c:
            # 提交事务
            transaction.savepoint_commit(save_id)

            # 创建 则为新增记录
            if is_c:
                save_log(self.update_path, parent_sku, err_type='新增单个商品：')
                self.num += 1
            # 本地数据库 与 网上 商品同步
            else:
                # 查找这个spu的所有sku_id
                spu_skugood_list = Goods.objects.filter(spu_id=parent_sku).values_list('goodssku__sku_id', flat=True)
                # 数据库中有，同步时没有的sku_id
                wait_del_skugood_list = list(set(spu_skugood_list).difference(set(skugood_id_list)))

                # 查找同步时没有的商品
                not_have_skugood = GoodsSKU.objects.filter(sku_id__in=wait_del_skugood_list)

                # 并且 没订单关联的商品
                wait_del_skugoods = not_have_skugood.filter(ordergoods__isnull=True)

                # 如果这个商品 库存为0 则删除这个商品
                for sku_good in wait_del_skugoods:
                    if sku_good.stock == 0:
                        sku_good.delete()

                # 有订单关联的商品 且库存为0 下架操作
                wait_down_skugoods = not_have_skugood.filter(ordergoods__isnull=False)
                for sku_good in wait_down_skugoods:
                    if sku_good.stock == 0:
                        sku_good.status = 0
                        sku_good.save()

    # 单个商品抓取
    def parse_single_good_url(self, goodspu):
        """发送请求，获取单个商品信息"""
        data = {
            'SPC_CDS': self.cookies['SPC_CDS'],
            'SPC_CDS_VER': 2,
            'page_number': 1,
            'page_size': 24,
            'search': goodspu
            }
        return self.parse_url(self.product_url, data)

    def save_single_good(self, good_data):
        if good_data['data']['page_info']['total'] == 1:
            product_data = good_data['data']['list'][0]
            parent_sku = product_data['parent_sku']
            # print('spu信息：', parent_sku)

            self.parse_create_goodsku(parent_sku, product_data)

            return '商品同步成功'
        else:
            return '没找到商品'

    def get_single_good(self, goodsku):
        self.is_cookies()

        good_data = self.parse_single_good_url(goodsku)
        return self.save_single_good(good_data)

    # 订单抓取
    def parse_order_url(self, type, page):
        """发送请求，获取订单数据字典"""
        data = {
            'SPC_CDS': self.cookies['SPC_CDS'],
            'SPC_CDS_VER': 2,
            'is_massship': 'false',
            'offset': page,
            'limit': 40,
            'type': type,
            'sort_type': 'sort_desc'
            }
        return self.parse_url(self.order_url, data)

    def save_order_data(self, order_data):
        """解析订单信息 保存到数据库"""
        for order_info in order_data['orders']:
            # 订单用户信息
            user_info = self.list_filter_data(order_info['userid'], order_data['users'])

            # 解析订单 用户数据  生成订单详情
            order_obj = self.parse_create_order(user_info, order_info, order_data)

            if not order_obj:
                # save_log(self.order_path, order_info['ordersn'], err_type='$已取消的订单：')
                continue

            if order_obj.order_status != 3 and str(order_obj.order_income) != '0.00':
                self.compute_order_profit(order_obj)

                self.num += 1

    def get_order(self, type='toship', page=0, is_all=True):
        """获取订单信息 保存到数据库
            :type   'toship'  待出货订单
                    'shipping' 运输中订单
                    'completed' 已完成订单
        """
        self.is_cookies()
        order_data = self.parse_order_url(type, page)
        self.save_order_data(order_data)

        total = order_data['meta']['total']
        total_page = total // 40
        if total_page > 0 and is_all:
            for i in range(1, total_page + 1):
                self.get_order(type, page=i * 40, is_all=False)

    def list_filter_data(self, params, list_data):
        """过滤数据列表中符合的数据字典"""
        return list(filter(lambda x: x['id'] == params, list_data))[0]

    def parse_create_order(self, user_info, order_info, order_data):
        """解析创建订单，创建订单同时创建订单商品，更新订单不更新订单商品"""

        # 如果订单状态为取消，不创建，如已有订单 则删除
        # 订单状态：待出货和已运送 为1，已取消为5，已完成为4
        # 已完成的订单，不再更新
        order_obj = OrderInfo.objects.filter(order_id=order_info['ordersn'])
        if order_obj:
            if order_info['status'] == 5:
                order_obj[0].delete()
                return None
            if order_obj[0].order_status == 3:
                return None

        # 订单用户收货率
        delivery_order = user_info['delivery_order_count']
        # 考虑订单用户第一次购物
        if delivery_order == 0:
            customer_info = '100%&0'
        else:
            customer_info = str(user_info['delivery_succ_count'] * 100 // delivery_order) + '%&' + str(delivery_order)
        # 商品总价
        total_price = order_info['buyer_paid_amount']

        # 判断是否是卖家的优惠卷
        voucher_price = order_info['voucher_price'] if order_info['voucher_absorbed_by_seller'] else '0.00'
        # 实际运费
        actual_shipping_fee = order_info['actual_shipping_fee']
        # 买家支付运费
        shipping_fee = order_info['shipping_fee']
        # 手续费
        card_txn_fee = order_info['card_txn_fee_info']['card_txn_fee']
        # 平台运费回扣
        shipping_rebate = order_info['shipping_rebate']
        # 平台佣金
        comm_fee = order_info['comm_fee']

        # 买家或平台支付的运费
        our_shipping_fee = Decimal(shipping_rebate) + Decimal(shipping_fee)
        if shipping_fee == '0.00' and shipping_rebate == '0.00':
            our_shipping_fee = Decimal(order_info['origin_shipping_fee'])

        # 没出货，无实际运费时 不计算订单收入
        order_income = '0.00'
        if actual_shipping_fee != '0.00':
            # 订单收入
            order_income = Decimal(total_price) + our_shipping_fee \
                           - Decimal(actual_shipping_fee) - Decimal(card_txn_fee) - Decimal(voucher_price) - Decimal(comm_fee)

        o_data = {
            'order_time': order_info['ordersn'][:6],
            'order_shopeeid': order_info['id'],
            'customer': user_info['username'],
            'receiver': order_info['buyer_address_name'],
            'customer_info': customer_info,
            'total_price': total_price,
            'order_income': order_income,
            'order_country': order_info['currency']
        }
        order_obj, is_c = OrderInfo.objects.update_or_create(order_id=order_info['ordersn'], defaults=o_data)

        if is_c:
            self.parse_create_ordergood(order_obj, order_info, order_data)
            self.num += 1

        return order_obj

    def parse_create_ordergood(self, order_obj, order_info, order_data):
        """
        解析数据 创建订单商品 统计订单进货成本
        :param order_obj: 订单对象
        :param order_info: 订单数据
        :param order_data: 抓取到的全部数据
        """

        # 订单下的商品，商品对象为唯一的
        for order_item in order_info['order_items']:
            good_info = self.list_filter_data(order_item, order_data['order-items'])

            good_sku = self.list_filter_data(good_info['modelid'], order_data['item-models'])['sku']
            try:
                good_obj = GoodsSKU.objects.get(sku_id=good_sku)
            except Exception as e:
                save_log(self.error_path, str(e.args))
                msg = '(' + order_info['ordersn'] + ') 缺失商品： ' + good_sku + '\t'
                save_log(self.order_path, msg, err_type='@订单商品错误：')
                # 订单备注中 记录缺失的商品
                order_obj.order_desc = order_obj.order_desc + good_sku + ' , '
                order_obj.save()
                # 跳过该商品， 记录下 手动修复
                continue

            g_data = {
                'count': good_info['amount'],
                'price': good_info['order_price'],
                }
            try:
                # 同一个订单 同种商品 记录只能有一条 唯一确认标志
                OrderGoods.objects.update_or_create(order=order_obj, sku_good=good_obj, defaults=g_data)
            except Exception as e:
                save_log(self.error_path, str(e.args))

    def compute_order_profit(self, order_obj):
        """计算订单利润"""
        order_cost = 0  # 订单成本(人民币）

        for good_obj in order_obj.ordergoods_set.all():
            # 商品的成本  每件商品进价上加一元 国内运杂费
            order_cost += (good_obj.sku_good.buy_price + Decimal(self.product_add_fee)) * good_obj.count

        order_profit = order_obj.order_income * Decimal(self.exchange_rate) \
                       - Decimal(order_cost) - Decimal(self.order_add_fee)
        order_obj.order_profit = order_profit
        # 更新订单状态(已完成)
        order_obj.order_status = 3
        order_obj.save()

    # 单个订单
    def parse_single_order_url(self, order_id):
        data = {
            'SPC_CDS': self.cookies['SPC_CDS'],
            'SPC_CDS_VER': 2,
            'keyword': order_id,
            'query': order_id,
            }
        return self.parse_url(self.search_order_url, data)

    def save_single_order(self, order_data):
        if order_data['orders']:
            order = order_data['orders'][0]
            user_info = order_data['users'][0]

            order_obj = self.parse_create_order(user_info, order, order_data)

            if not order_obj:
                return '订单已取消/已完成'

            if order_obj.order_status != 3 and str(order_obj.order_income) != '0.00':
                self.compute_order_profit(order_obj)

            return '订单同步完成'

        return '没找到订单'

    def get_single_order(self, order_id):
        self.is_cookies()
        order_data = self.parse_single_order_url(order_id)
        return self.save_single_order(order_data)

    # 生成运单号
    def make_order_waybill(self, orderid):
        self.is_cookies()
        # 组成URL 平台订单号
        url = self.make_waybill_url.format(orderid, self.cookies['SPC_CDS'])

        headers = {'content-type': 'application/json; charset=UTF-8'}
        headers.update(self.headers)

        # request payload 参数
        data = {"orderLogistic": {"userid": 0, "orderid": None, "type": 0, "status": 0, "channelid": 0,
                                  "channel_status": "", "consignment_no": "", "booking_no": "",
                                  "pickup_time": 0, "actual_pickup_time": 0, "deliver_time": 0,
                                  "actual_deliver_time": 0, "ctime": 0, "mtime": 0, "seller_realname": "",
                                  "branchid": 0, "slug": "", "shipping_carrier": "",
                                  "logistic_command": "generate_tracking_no", "extra_data": "{}"}}

        try:
            for i in range(2):
                response = requests.put(url, data=json.dumps(data), cookies=self.cookies, headers=headers)

                if response.status_code == 200:
                    return ''
                # print(response.status_code)
                if i == 0:
                    self.login()

            save_log(self.error_path, '验证出错，超出请求次数')
            return '验证出错：超出请求次数'

        except Exception as e:
            save_log(self.error_path, str(e.args))
            return '发送请求出错'

    def down_order_waybill(self, orderids):
        """下载运单号
        orderids: 订单号列表的字符串"""
        data = {
            'orderids': orderids,
            'language': 'zh-my',
            'api_from': 'waybill',
            }

        self.is_cookies()
        headers = {'upgrade-insecure-requests': '1'}
        headers.update(self.headers)

        try:
            for i in range(2):
                response = requests.get(self.waybill_url, params=data, cookies=self.cookies, headers=headers)

                if response.status_code == 200:
                    # 文件名
                    file_name = response.headers._store['content-disposition'][1][-20:-1]
                    file_path = os.path.join(sp_config.PRINT_WAYBILL_PATH, file_name)

                    with open(file_path, 'wb') as f:
                        f.write(response.content)

                    if os.path.isfile(file_path):
                        # 调用打印类  打印运单号
                        crop_pdf = CropPDF(file_dir=sp_config.PRINT_WAYBILL_PATH)
                        crop_pdf.run()
                        # print('打单成功')

                    return ''

                print(response.status_code)  # 403
                # 验证出错，重新登录，再请求
                if i == 0:
                    self.login()

            save_log(self.error_path, '验证出错，超出请求次数')
            return '验证出错：超出请求次数'

        except Exception as e:
            save_log(self.error_path, str(e.args))
            return '发送请求出错'


class MYGoodsSpider(PhGoodsSpider):

    def __init__(self):
        self.name = sp_config.MY_USERNAME
        self.password = sp_config.MY_PASSWORD

        self.headers = {'user-agent': sp_config.USER_AGENT}
        self.cookies = get_cookies_from_file(sp_config.MY_COOKIES_SAVE)

        self.login_url = sp_config.MY_LOGIN_URL
        self.product_url = sp_config.MY_PRODUCT_URL
        self.order_url = sp_config.MY_ORDER_URL
        self.search_order_url = sp_config.MY_ORDER_SEARCH_URL
        self.make_waybill_url = sp_config.MY_MAKE_WAYBILL_URL
        self.waybill_url = sp_config.MY_WAYBILL_URL

        self.cookies_path = sp_config.MY_COOKIES_SAVE
        self.error_path = sp_config.MY_ERROR_LOG
        self.update_path = sp_config.MY_UPDATE_LOG
        self.order_path = sp_config.MY_ORDER_LOG

        # 兑换汇率
        self.exchange_rate = sp_config.MYR_CONVERT_RMB
        # 每个订单附加费用
        self.order_add_fee = sp_config.ORDER_ADD_FEE
        self.product_add_fee = sp_config.PRODUCT_ADD_FEE
        self.country = 'my'

        self.num = 0


class ThGoodsSpider(PhGoodsSpider):

    def __init__(self):
        self.name = sp_config.TH_USERNAME
        self.password = sp_config.TH_PASSWORD

        self.headers = {'user-agent': sp_config.USER_AGENT}
        self.cookies = get_cookies_from_file(sp_config.TH_COOKIES_SAVE)

        self.login_url = sp_config.TH_LOGIN_URL
        self.product_url = sp_config.TH_PRODUCT_URL
        self.order_url = sp_config.TH_ORDER_URL
        self.search_order_url = sp_config.TH_ORDER_SEARCH_URL
        self.make_waybill_url = sp_config.TH_MAKE_WAYBILL_URL
        self.waybill_url = sp_config.TH_WAYBILL_URL

        self.cookies_path = sp_config.TH_COOKIES_SAVE
        self.error_path = sp_config.TH_ERROR_LOG
        self.update_path = sp_config.TH_UPDATE_LOG
        self.order_path = sp_config.TH_ORDER_LOG

        # 兑换汇率
        self.exchange_rate = sp_config.THB_CONVERT_RMB
        # 每个订单附加费用
        self.order_add_fee = sp_config.ORDER_ADD_FEE
        self.product_add_fee = sp_config.PRODUCT_ADD_FEE
        self.country = 'th'

        self.num = 0


class IdGoodsSpider(PhGoodsSpider):

    def __init__(self):
        self.name = sp_config.ID_USERNAME
        self.password = sp_config.ID_PASSWORD

        self.headers = {'user-agent': sp_config.USER_AGENT}
        self.cookies = get_cookies_from_file(sp_config.ID_COOKIES_SAVE)

        self.login_url = sp_config.ID_LOGIN_URL
        self.product_url = sp_config.ID_PRODUCT_URL
        self.order_url = sp_config.ID_ORDER_URL
        self.search_order_url = sp_config.ID_ORDER_SEARCH_URL
        self.make_waybill_url = sp_config.ID_MAKE_WAYBILL_URL
        self.waybill_url = sp_config.ID_WAYBILL_URL

        self.cookies_path = sp_config.ID_COOKIES_SAVE
        self.error_path = sp_config.ID_ERROR_LOG
        self.update_path = sp_config.ID_UPDATE_LOG
        self.order_path = sp_config.ID_ORDER_LOG

        # 兑换汇率
        self.exchange_rate = sp_config.IDR_CONVERT_RMB
        # 每个订单附加费用
        self.order_add_fee = sp_config.ORDER_ADD_FEE
        self.product_add_fee = sp_config.PRODUCT_ADD_FEE
        self.country = 'id'

        self.num = 0

def save_log(filename, msg, err_type='Error'):
    # 写入错误日志
    now_time = datetime.datetime.now().strftime('%y-%m-%d %H:%M')
    msg = '\t'.join([err_type, now_time, msg]) + '\n'
    with open(filename, 'a+', encoding='utf-8') as f:
        f.write(msg)


def save_cookies_to_file(filename, cookies):
    with open(filename, 'w', encoding='utf-8') as f:
        f.write(json.dumps(cookies))


def get_cookies_from_file(filename):
    try:
        with open(filename, encoding='utf-8') as f:
            cookies_dict = json.loads(f.read())
    except:
        return {}
    return cookies_dict


def format_file_path(goodsku):
    """根据商品sku，设置默认图片名"""

    # 替换sku中的+号
    good_sku = goodsku.replace('+', '_')
    # 根据sku_id中的'#','_'，设置默认图片路径
    if '#' in good_sku:
        # 提取编号 '主spu号_#03' 去除'#' 保存默认图片路径为'主spu号_03.jpg
        file_path = re.match(r'(.*#[^._]*)', good_sku).group(0).replace('#', '')
    elif '_' in good_sku:
        # 除去最后一个'_'和它之后的字符
        file_path = re.match(r'(.*)_', good_sku).group(1)
    else:
        file_path = good_sku[:-1]

    return file_path


country_type_dict = {
    'MYR': MYGoodsSpider,
    'PHP': PhGoodsSpider,
    'THB': ThGoodsSpider,
    'IDR': IdGoodsSpider
    }

if __name__ == '__main__':
    ss = PhGoodsSpider()
    # ss.get_goods()
    ss.get_order()
