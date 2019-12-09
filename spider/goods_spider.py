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
from spider.print_waybill import CropPDF, OldCropPDF
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
        self.forderid_url = sp_config.PH_FORDERID_URL
        self.check_income_url = sp_config.PH_CHECK_INCOME_URL

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
        self.check_msg = {'shopee_order': 0,
                          'shopee_count': 0,
                          'shopee_pay_time': [],
                          'success_order': 0,
                          'not_found_order_list': [],
                          'error_order_list': [],
                          'order_count': 0
                          }

    def login(self):
        """登录获取cookies"""
        driver = webdriver.Chrome()
        driver.get(self.login_url)
        time.sleep(3)
        driver.find_element_by_xpath('//input[@type="text"]').send_keys(self.name)
        time.sleep(1)
        driver.find_element_by_xpath('//input[@type="password"]').send_keys(self.password)
        time.sleep(2)
        driver.find_element_by_xpath(
            '//*[@id="app"]/div[2]/div/div[1]/div/div/div[3]/div/div/div/div[2]/button').click()
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
            # print(self.cookies)

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
            if re.match(r'^[+\w #,)(_/\-.*]+$', good['name']):
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
            'list_type': type,
            'order_by_create_date': 'desc'
        }
        return self.parse_url(self.order_url, data)

    def save_order_data(self, order_data):
        """解析订单信息 保存到数据库"""
        for order_info in order_data['data']['orders']:
            # 订单用户信息
            # user_info = self.list_filter_data(order_info['userid'], order_data['users'])

            # 解析订单 用户数据  生成订单详情
            order_obj = self.parse_create_order(order_info)

            if not order_obj:
                # save_log(self.order_path, order_info['ordersn'], err_type='$已取消的订单：')
                continue

            if order_obj.order_status == 5 and str(order_obj.order_income) != '0.00':
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

        total = order_data['data']['meta']['total']
        total_page = total // 40
        if total_page > 0 and is_all:
            for i in range(1, total_page + 1):
                self.get_order(type, page=i * 40, is_all=False)

    # def list_filter_data(self, params, list_data):
    #     """过滤数据列表中符合的数据字典"""
    #     return list(filter(lambda x: x['id'] == params, list_data))[0]

    def parse_create_order(self, order_info):
        """解析创建订单，创建订单同时创建订单商品，更新订单不更新订单商品"""

        # 如果订单状态为取消，不创建，如已有订单 则删除
        # 订单状态：待出货和已运送 为1，已取消为5，已完成为4
        # 已完成的订单，不再更新
        order_obj = OrderInfo.objects.filter(order_id=order_info['order_sn'])
        if order_obj:
            if order_info['status'] == 5:
                order_obj[0].delete()
                return None
            if order_obj[0].order_status == 3:
                return None

        # 订单用户收货率
        delivery_order = order_info['buyer_user']['delivery_order_count']
        # 考虑订单用户第一次购物
        if delivery_order == 0:
            customer_info = '100%&0'
        else:
            customer_info = str(order_info['buyer_user']['delivery_succ_count'] * 100 // delivery_order) + '%&' + str(
                delivery_order)
        # 商品总价
        total_price = 0
        for order_good_info in order_info['order_items']:
            total_price += float(order_good_info['order_price']) * order_good_info['amount']

        # 判断是否是卖家的优惠卷
        voucher_price = order_info['voucher_price'] if order_info['voucher_absorbed_by_seller'] else '0.00'

        if order_info['currency'] == 'PHP':
            # 菲律宾 实际运费 0.5向上进1
            actual_shipping_fee = Decimal(order_info['actual_shipping_fee']).quantize(Decimal(0.0))
        else:
            actual_shipping_fee = Decimal(order_info['actual_shipping_fee'])
        # 买家支付运费
        shipping_fee = order_info['shipping_fee']
        # 平台运费回扣
        shipping_rebate = order_info['shipping_rebate']

        # 平台佣金
        comm_fee = order_info['comm_fee']
        # 平台服务费
        seller_service_fee = order_info['seller_service_fee']
        # 手续费
        card_txn_fee = order_info['card_txn_fee_info']['card_txn_fee']

        # 买家或平台支付的运费
        our_shipping_fee = Decimal(shipping_rebate) + Decimal(shipping_fee)
        if shipping_fee == '0.00' and shipping_rebate == '0.00':
            our_shipping_fee = Decimal(order_info['origin_shipping_fee'])

        # 没出货，无实际运费时 不计算订单收入
        order_income = '0.00'
        if actual_shipping_fee != 0.00:
            # 订单收入
            order_income = Decimal(total_price) + our_shipping_fee \
                           - actual_shipping_fee - Decimal(card_txn_fee) - Decimal(voucher_price) \
                           - Decimal(comm_fee) - Decimal(seller_service_fee)

        o_data = {
            'order_time': order_info['order_sn'][:6],
            'order_shopeeid': order_info['order_id'],
            'customer': order_info['buyer_user']['user_name'],
            'customer_remark': order_info['remark'],
            'receiver': order_info['buyer_address_name'],
            'customer_info': customer_info,
            'total_price': total_price,
            'order_income': order_income,
            'order_country': order_info['currency']
        }
        order_obj, is_c = OrderInfo.objects.update_or_create(order_id=order_info['order_sn'], defaults=o_data)

        if is_c:
            self.parse_create_ordergood(order_obj, order_info)
            self.num += 1

        return order_obj

    def parse_create_ordergood(self, order_obj, order_info):
        """
        解析数据 创建订单商品 统计订单进货成本
        :param order_obj: 订单对象
        :param order_info: 订单数据
        """

        # 订单下的商品，商品对象为唯一的
        for order_item in order_info['order_items']:
            good_sku = order_item['item_model']['sku']

            # 有sku 则为普通商品，没有 则为套装商品
            if good_sku:
                try:
                    good_obj = GoodsSKU.objects.get(sku_id=good_sku)
                except Exception as e:
                    save_log(self.error_path, str(e.args))
                    msg = '(' + order_info['order_sn'] + ') 缺失商品： ' + good_sku + '\t'
                    save_log(self.order_path, msg, err_type='@订单商品错误：')
                    # 订单备注中 记录缺失的商品
                    order_obj.order_desc = order_obj.order_desc + good_sku + ' , '
                    order_obj.save()
                    # 跳过该商品， 记录下 手动修复
                    continue

                g_data = {
                    'count': order_item['amount'],
                    'price': order_item['order_price'],
                }
                try:
                    # 同一个订单 同种商品 记录只能有一条 唯一确认标志
                    OrderGoods.objects.update_or_create(order=order_obj, sku_good=good_obj, defaults=g_data)
                except Exception as e:
                    save_log(self.error_path, str(e.args))
            else:
                if order_item['bundle_deal_model']:
                    # 套装一共包含多少件商品
                    bundle_count = 0
                    for item in order_item['item_list']:
                        bundle_count += int(item['amount'])
                    # 循环每个套装中的商品
                    for order_bundle_item in order_item['bundle_deal_model']:
                        sku = order_bundle_item['sku']
                        try:
                            good_obj = GoodsSKU.objects.get(sku_id=sku)
                        except Exception as e:
                            save_log(self.error_path, str(e.args))
                            msg = '(' + order_info['order_sn'] + ') 缺失商品： ' + sku + '\t'
                            save_log(self.order_path, msg, err_type='@订单套装商品错误：')
                            # 订单备注中 记录缺失的商品
                            order_obj.order_desc = order_obj.order_desc + sku + '; '
                            order_obj.save()
                            # 跳过该商品， 记录下 手动修复
                            continue

                        # 套装中该商品的数量
                        count = list(filter(lambda x: x['model_id'] == order_bundle_item['model_id'],
                                            order_item['item_list']))[0]['amount']
                        # 套装中每件商品的平均价格
                        price = Decimal(order_item['order_price']) / bundle_count
                        g_data = {
                            'count': count,
                            'price': price,
                        }
                        try:
                            # 同一个订单 同种商品 记录只能有一条 唯一确认标志
                            OrderGoods.objects.update_or_create(order=order_obj, sku_good=good_obj, defaults=g_data)
                        except Exception as e:
                            save_log(self.error_path, str(e.args))
                else:
                    # 订单备注中 记录错误
                    order_obj.order_desc = order_obj.order_desc + '（订单商品有错误！）'
                    order_obj.save()

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
        if order_data['data']['orders']:
            # order = order_data['orders'][0]
            # user_info = order_data['users'][0]

            order_obj = self.parse_create_order(order_data['data']['orders'][0])

            if not order_obj:
                return '订单已取消/已完成'

            if order_obj.order_status == 5 and str(order_obj.order_income) != '0.00':
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
        url = self.make_waybill_url.format(self.cookies['SPC_CDS'])

        headers = {'content-type': 'application/json; charset=UTF-8'}
        headers.update(self.headers)

        # request payload 参数
        # data = {"orderLogistic": {"userid": 0, "orderid": None, "type": 0, "status": 0, "channelid": 0,
        #                           "channel_status": "", "consignment_no": "", "booking_no": "",
        #                           "pickup_time": 0, "actual_pickup_time": 0, "deliver_time": 0,
        #                           "actual_deliver_time": 0, "ctime": 0, "mtime": 0, "seller_realname": "",
        #                           "branchid": 0, "slug": "", "shipping_carrier": "",
        #                           "logistic_command": "generate_tracking_no", "extra_data": "{}"}}
        data = {"channel_id": 28016, "order_id": int(orderid), "forder_id": orderid}

        try:
            for i in range(2):
                response = requests.post(url, data=json.dumps(data), cookies=self.cookies, headers=headers)

                if response.status_code == 200:
                    res_msg = json.loads(response.text)
                    if res_msg['code'] == 0:
                        return ''
                    else:
                        save_log(self.error_path, res_msg['user_message'])
                        return res_msg['user_message']
                # print(response.status_code)
                if i == 0:
                    self.login()

            save_log(self.error_path, '验证出错，超出请求次数')
            return '验证出错：超出请求次数'

        except Exception as e:
            save_log(self.error_path, str(e.args))
            return '发送请求出错'

    # 获取订单forderid，下载运送单需要
    def get_order_forderid(self, orderids):
        orderids = ','.join(orderids)
        data = {
            'SPC_CDS': self.cookies['SPC_CDS'],
            'SPC_CDS_VER': 2,
            'order_ids': orderids
        }

        response = requests.get(self.forderid_url, params=data,
                                cookies=self.cookies, headers=self.headers)
        res_dict = json.loads(response.content.decode())

        forder_map = {}
        for ordermodel in res_dict['data']['list']:
            forder_map[str(ordermodel['order_id'])] = {"forder_ids": [ordermodel['forders'][0]['forder_id']]}
        return forder_map

    def down_order_waybill(self, orderids):
        """下载运单号
        orderids: 订单号列表 ['2224060720','2221118585','2222123945']"""
        forderid_dict = self.get_order_forderid(orderids)
        data = {
            'order_ids': orderids,
            'order_forder_map': forderid_dict
        }

        self.is_cookies()

        try:
            for i in range(2):
                response = requests.post(self.waybill_url, json=data, cookies=self.cookies, headers=self.headers)

                if response.status_code == 200:
                    # 文件名
                    file_name = 'WorkPDF001.pdf'
                    file_path = os.path.join(sp_config.PRINT_WAYBILL_PATH, file_name)

                    with open(file_path, 'wb') as f:
                        f.write(response.content)

                    if os.path.isfile(file_path):
                        # 调用打印类  打印运单号
                        crop_pdf = CropPDF(file_dir=sp_config.PRINT_WAYBILL_PATH)
                        crop_pdf.run()

                        # os.remove(file_path)
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

    # 订单收入 核对（按打款日期周期 获取订单信息）
    def parse_check_income_url(self, page, start_date, end_date):
        data = {
            'SPC_CDS': self.cookies['SPC_CDS'],
            'SPC_CDS_VER': 2,
            'start_date': start_date,
            'end_date': end_date,
            'tran_type': 0,
            'page_number': page,
            'page_size': 50
        }
        return self.parse_url(self.check_income_url, data)

    def check_order_income(self, order_data):
        for order_info in order_data['data']['list']:
            # 平台订单收入保留两位小数 累加
            shopee_order_income = Decimal(order_info['amount']).quantize(Decimal('0.00'))
            self.check_msg['shopee_count'] += shopee_order_income
            self.check_msg['shopee_order'] += 1
            if order_info['release_time_str'] not in self.check_msg['shopee_pay_time']:
                self.check_msg['shopee_pay_time'].append(order_info['release_time_str'])

            order_obj = OrderInfo.objects.filter(order_shopeeid=order_info['order_id'])
            if not order_obj:
                self.check_msg['not_found_order_list'].append(order_info['order_id'])
                continue

            order_income = order_obj[0].order_income

            # 如果平台收入 等于 则更新订单状态、打款时间
            if order_income == shopee_order_income:
                order_obj.update(order_status=6, order_pay_time=order_info['release_time_str'])
                self.check_msg['order_count'] += order_income
                self.check_msg['success_order'] += 1
            # 不等于 则订单状态为异常，打款时间 记录平台收入
            else:
                order_obj.update(order_status=7, order_pay_time=shopee_order_income)
                self.check_msg['error_order_list'].append(order_info['order_id'])

    def get_income_order(self, page, start_date, end_date, is_all=True):
        """根据打款时间 获取订单打款信息"""
        self.is_cookies()
        order_data = self.parse_check_income_url(page, start_date, end_date)
        self.check_order_income(order_data)

        if is_all:
            total = order_data['data']['page_info']['total']
            total_page = total // 50
            for i in range(2, total_page + 2):
                self.get_income_order(i, start_date, end_date, is_all=False)


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
        self.forderid_url = sp_config.MY_FORDERID_URL
        self.check_income_url = sp_config.MY_CHECK_INCOME_URL

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
        self.check_msg = {'shopee_order': 0,
                          'shopee_count': 0,
                          'shopee_pay_time': [],
                          'success_order': 0,
                          'not_found_order_list': [],
                          'error_order_list': [],
                          'order_count': 0
                          }


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
        self.check_income_url = sp_config.TH_CHECK_INCOME_URL
        self.forderid_url = sp_config.TH_FORDERID_URL

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
        self.check_msg = {'shopee_order': 0,
                          'shopee_count': 0,
                          'shopee_pay_time': [],
                          'success_order': 0,
                          'not_found_order_list': [],
                          'error_order_list': [],
                          'order_count': 0
                          }


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
        self.check_income_url = sp_config.ID_CHECK_INCOME_URL
        self.forderid_url = sp_config.ID_FORDERID_URL

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
        self.check_msg = {'shopee_order': 0,
                          'shopee_count': 0,
                          'shopee_pay_time': [],
                          'success_order': 0,
                          'not_found_order_list': [],
                          'error_order_list': [],
                          'order_count': 0
                          }

    def down_order_waybill(self, orderids):
        """下载运单号
        orderids: 订单号列表 ['2224060720','2221118585','2222123945']"""

        # 订单号由字符串转成整数  列表转成字符串 如'[2349952432]'
        orderids = str(list(map(lambda x: int(x), orderids)))
        data = {
            'orderids': orderids,
        }

        self.is_cookies()

        try:
            for i in range(2):
                response = requests.get(self.waybill_url, params=data, cookies=self.cookies, headers=self.headers)

                if response.status_code == 200:
                    # 提取header中隐藏的文件名
                    file_name = response.headers._store['content-disposition'][1][-20:-1]
                    file_path = os.path.join(sp_config.PRINT_WAYBILL_PATH, file_name)

                    with open(file_path, 'wb') as f:
                        f.write(response.content)

                    if os.path.isfile(file_path):
                        # 调用旧打印类 切割pdf 打印运单
                        crop_pdf = OldCropPDF(file_dir=sp_config.PRINT_WAYBILL_PATH)
                        crop_pdf.run()

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


class SgGoodsSpider(IdGoodsSpider):

    def __init__(self):
        self.name = sp_config.SG_USERNAME
        self.password = sp_config.SG_PASSWORD

        self.headers = {'user-agent': sp_config.USER_AGENT}
        self.cookies = get_cookies_from_file(sp_config.SG_COOKIES_SAVE)

        self.login_url = sp_config.SG_LOGIN_URL
        self.product_url = sp_config.SG_PRODUCT_URL

        self.order_url = sp_config.SG_ORDER_URL
        self.search_order_url = sp_config.SG_ORDER_SEARCH_URL
        self.check_income_url = sp_config.SG_CHECK_INCOME_URL
        self.forderid_url = sp_config.SG_FORDERID_URL

        self.make_waybill_url = sp_config.SG_MAKE_WAYBILL_URL
        self.waybill_url = sp_config.SG_WAYBILL_URL

        self.cookies_path = sp_config.SG_COOKIES_SAVE
        self.error_path = sp_config.SG_ERROR_LOG
        self.update_path = sp_config.SG_UPDATE_LOG
        self.order_path = sp_config.SG_ORDER_LOG

        # 兑换汇率
        self.exchange_rate = sp_config.SGD_CONVERT_RMB
        # 每个订单附加费用
        self.order_add_fee = sp_config.ORDER_ADD_FEE
        self.product_add_fee = sp_config.PRODUCT_ADD_FEE
        self.country = 'sg'

        self.num = 0
        self.check_msg = {'shopee_order': 0,
                          'shopee_count': 0,
                          'shopee_pay_time': [],
                          'success_order': 0,
                          'not_found_order_list': [],
                          'error_order_list': [],
                          'order_count': 0
                          }


class BrGoodsSpider(PhGoodsSpider):

    def __init__(self):
        self.name = sp_config.MY_USERNAME
        self.password = sp_config.MY_PASSWORD

        self.headers = {'user-agent': sp_config.USER_AGENT}
        self.cookies = get_cookies_from_file(sp_config.MY_COOKIES_SAVE)

        self.login_url = sp_config.MY_LOGIN_URL
        self.product_url = sp_config.MY_PRODUCT_URL

        self.order_url = sp_config.MY_ORDER_URL
        # 巴西
        self.order_detail_url = sp_config.BR_ORDER_DETAIL_URL
        self.one_order_url = 'https://seller.my.shopee.cn/api/v3/order/get_one_order'

        self.forderid_url = sp_config.MY_FORDERID_URL
        self.check_income_url = sp_config.MY_CHECK_INCOME_URL

        # 巴西
        self.make_waybill_url = sp_config.BR_MAKE_WAYBILL_URL
        self.waybill_url = sp_config.BR_WAYBILL_URL

        self.cookies_path = sp_config.MY_COOKIES_SAVE
        self.error_path = sp_config.MY_ERROR_LOG
        self.update_path = sp_config.MY_UPDATE_LOG
        self.order_path = sp_config.MY_ORDER_LOG

        # 兑换汇率
        self.exchange_rate = sp_config.MYR_CONVERT_RMB
        # 每个订单附加费用
        self.order_add_fee = sp_config.ORDER_ADD_FEE
        self.product_add_fee = sp_config.PRODUCT_ADD_FEE
        self.country = 'br'

        self.num = 0
        self.add_orderid_dict = {}
        self.check_msg = {'shopee_order': 0,
                          'shopee_count': 0,
                          'shopee_pay_time': [],
                          'success_order': 0,
                          'not_found_order_list': [],
                          'error_order_list': [],
                          'order_count': 0
                          }

    # 订单抓取
    def parse_order_url(self, type, page):
        """发送请求，获取订单数据字典"""
        data = {
            'SPC_CDS': self.cookies['SPC_CDS'],
            'SPC_CDS_VER': 2,
            'is_massship': 'false',
            'offset': page,
            'limit': 40,
            'list_type': type,
            'order_by_create_date': 'desc',
            'sip_shopid': 191538284,
            'sip_region': 'br'
        }
        return self.parse_url(self.order_url, data)

    def save_order_data(self, order_data):
        """解析订单信息 保存到数据库"""
        for order_info in order_data['data']['orders']:

            # 解析订单 用户数据  生成订单详情
            order_obj = self.parse_create_order(order_info)

            if not order_obj:
                continue

        if self.num > 0:
            # add_orderid_dict 字典的键为orderid 值为order_obj对象
            orderid_list = str(list(self.add_orderid_dict.keys()))
            data = {
                'orderid_list': orderid_list,
            }
            order_detail_list = self.parse_url(self.order_detail_url, data)
            # 循环 每一个订单 根据shopid找到 订单
            for order_detail in order_detail_list['data']['list']:
                order_obj = self.add_orderid_dict[order_detail['orderid']]
                self.parse_ordergood(order_detail, order_obj)

    def get_order(self, type='toship', page=0, is_all=True):
        """获取订单信息 保存到数据库
            :type   'toship'  待出货订单
                    'shipping' 运输中订单
                    'completed' 已完成订单
        """
        self.is_cookies()
        order_data = self.parse_order_url(type, page)
        self.save_order_data(order_data)

        if is_all:
            total = order_data['data']['meta']['total']
            total_page = total // 40
            for i in range(1, total_page + 1):
                self.get_order(type, page=i * 40, is_all=False)

    def parse_create_order(self, order_info):
        """解析创建订单，创建订单同时创建订单商品，更新订单不更新订单商品"""

        # 如果订单状态为取消，不创建，如已有订单 则删除
        # 订单状态：待出货和已运送为 2，已取消为5，已完成为4
        # 订单类型：待出货 7；已运送 8；已完成 3；已取消 4
        # 已完成的订单，不再更新
        order_obj = OrderInfo.objects.filter(order_id=order_info['order_sn'])
        if order_obj:
            # 自己系统状态为完成时，不再同步信息
            if order_obj[0].order_status == 3:
                return None
            # 订单为取消状态时  删除订单
            if order_info['status'] == 5:
                order_obj[0].delete()
                return None
            # 订单状态 在运输中时，更新自己系统订单状态为 已完成
            if order_info['list_type'] == 8:
                order_obj.update(order_status=3)
                self.num += 1
                return None     

        # 订单用户收货率
        delivery_order = order_info['buyer_user']['delivery_order_count']
        # 考虑订单用户第一次购物
        if delivery_order == 0:
            customer_info = '100%&0'
        else:
            customer_info = str(order_info['buyer_user']['delivery_succ_count'] * 100 // delivery_order) + '%&' + str(
                delivery_order)
        # 商品总价
        total_price = 0

        o_data = {
            'order_time': order_info['order_sn'][:6],
            'order_shopeeid': order_info['order_id'],
            'customer': order_info['buyer_user']['user_name'],
            'customer_remark': order_info['remark'],
            'customer_info': customer_info,
            'total_price': total_price,
            'order_country': order_info['currency']
        }
        order_obj, is_c = OrderInfo.objects.update_or_create(order_id=order_info['order_sn'], defaults=o_data)

        if is_c:
            self.num += 1
            self.add_orderid_dict[order_info['order_id']] = order_obj

        return order_obj

    def parse_ordergood(self, order_detail, order_obj):
        """解析数据 创建订单商品"""

        order_cost = 0  # 订单成本(人民币）
        # 循环订单中的每一项商品，添加订单商品
        for order_item in order_detail['order_items']:
            good_sku = order_item['model_sku']
            try:
                good_obj = GoodsSKU.objects.get(sku_id=good_sku)
            except Exception as e:
                save_log(self.error_path, str(e.args))
                msg = '(' + order_obj.order_id + ') 缺失商品： ' + good_sku + '\t'
                save_log(self.order_path, msg, err_type='@订单商品错误：')
                # 订单备注中 记录缺失的商品
                order_obj.order_desc = order_obj.order_desc + good_sku + ', '
                order_obj.save()
                # 跳过该商品， 记录下 手动修复
                continue

            g_data = {
                'count': order_item['quantity'],
                'price': order_item['settlement_price'],
            }
            try:
                # 同一个订单 同种商品 记录只能有一条 唯一确认标志
                OrderGoods.objects.update_or_create(order=order_obj, sku_good=good_obj, defaults=g_data)
            except Exception as e:
                save_log(self.error_path, str(e.args))

            # 商品的成本  每件商品进价上加一元国内运杂费
            order_cost += (good_obj.buy_price + Decimal(self.product_add_fee)) \
                          * Decimal(order_item['quantity'])

        order_profit = Decimal(order_detail['net_settlement_amount']) * Decimal(self.exchange_rate) \
                       - Decimal(order_cost) - Decimal(self.order_add_fee)

        order_obj.total_price=order_detail['settlement_amount']
        order_obj.order_income=order_detail['net_settlement_amount']
        order_obj.order_profit=order_profit
        order_obj.save()

    # 单个订单
    def parse_single_order_url(self, order_id):
        """
        :param order_id: shopee平台 订单号
        """
        data = {
            'SPC_CDS': self.cookies['SPC_CDS'],
            'SPC_CDS_VER': 2,
            'sip_region': 'br',
            'sip_shopid': 191538284,
            'order_id': order_id
        }
        return self.parse_url(self.one_order_url, data)

    def get_single_order(self, order_id):
        order_id = int(order_id)
        self.is_cookies()
        order_data = self.parse_single_order_url(order_id)
        if order_data['data']:
            order_obj = self.parse_create_order(order_data['data'])

            if not order_obj:
                return '订单已取消/已完成'

            data = {
                'orderid_list': str([order_id]),
            }
            order_detail_list = self.parse_url(self.order_detail_url, data)
            self.parse_ordergood(order_detail_list['data']['list'][0], order_obj)

            return '订单同步完成'

        return '没找到订单'

    # 生成运单号
    def make_order_waybill(self, orderid):
        self.is_cookies()
        # 组成URL 平台订单号
        url = self.make_waybill_url.format(self.cookies['SPC_CDS'])

        data = {"channel_id": 90001, "order_id": int(orderid)}

        try:
            for i in range(2):
                response = requests.post(url, data=data, cookies=self.cookies, headers=self.headers)

                if response.status_code == 200:
                    res_msg = json.loads(response.text)
                    if res_msg['code'] == 0:
                        return ''
                    else:
                        save_log(self.error_path, res_msg['user_message'])
                        return res_msg['user_message']
                if i == 0:
                    self.login()

            save_log(self.error_path, '验证出错，超出请求次数')
            return '验证出错：超出请求次数'

        except Exception as e:
            save_log(self.error_path, str(e.args))
            return '发送请求出错'

    def down_order_waybill(self, orderids):
        """下载运单号
        orderids: 订单号列表 ['2224060720','2221118585','2222123945']
        订单号由字符串转成整数  列表转成字符串 如'[2349952432]'
        """

        orderids = str(list(map(lambda x: int(x), orderids)))
        data = {
            'sip_region': 'br',
            'sip_shopid': 191538284,
            'orderids': orderids,
        }

        self.is_cookies()

        try:
            for i in range(2):
                response = requests.get(self.waybill_url, params=data, cookies=self.cookies, headers=self.headers)

                if response.status_code == 200:
                    # 提取header中隐藏的文件名
                    file_name = response.headers._store['content-disposition'][1][-20:-1]
                    file_path = os.path.join(sp_config.PRINT_WAYBILL_PATH, file_name)

                    with open(file_path, 'wb') as f:
                        f.write(response.content)

                    if os.path.isfile(file_path):
                        # 调用旧打印类 切割pdf 打印运单
                        crop_pdf = OldCropPDF(file_dir=sp_config.PRINT_WAYBILL_PATH)
                        crop_pdf.run()

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



    # 订单收入 核对（按打款日期周期 获取订单信息）
    def parse_check_income_url(self, page, start_date, end_date):
        data = {
            'SPC_CDS': self.cookies['SPC_CDS'],
            'SPC_CDS_VER': 2,
            'start_date': start_date,
            'end_date': end_date,
            'tran_type': 0,
            'page_number': page,
            'page_size': 50
        }
        return self.parse_url(self.check_income_url, data)

    def check_order_income(self, order_data):
        for order_info in order_data['data']['list']:
            # 平台订单收入保留两位小数 累加
            shopee_order_income = Decimal(order_info['amount']).quantize(Decimal('0.00'))
            self.check_msg['shopee_count'] += shopee_order_income
            self.check_msg['shopee_order'] += 1
            if order_info['release_time_str'] not in self.check_msg['shopee_pay_time']:
                self.check_msg['shopee_pay_time'].append(order_info['release_time_str'])

            order_obj = OrderInfo.objects.filter(order_shopeeid=order_info['order_id'])
            if not order_obj:
                self.check_msg['not_found_order_list'].append(order_info['order_id'])
                continue

            order_income = order_obj[0].order_income

            # 如果平台收入 等于 则更新订单状态、打款时间
            if order_income == shopee_order_income:
                order_obj.update(order_status=6, order_pay_time=order_info['release_time_str'])
                self.check_msg['order_count'] += order_income
                self.check_msg['success_order'] += 1
            # 不等于 则订单状态为异常，打款时间 记录平台收入
            else:
                order_obj.update(order_status=7, order_pay_time=shopee_order_income)
                self.check_msg['error_order_list'].append(order_info['order_id'])

    def get_income_order(self, page, start_date, end_date, is_all=True):
        """根据打款时间 获取订单打款信息"""
        self.is_cookies()
        order_data = self.parse_check_income_url(page, start_date, end_date)
        self.check_order_income(order_data)

        if is_all:
            total = order_data['data']['page_info']['total']
            total_page = total // 50
            for i in range(2, total_page + 2):
                self.get_income_order(i, start_date, end_date, is_all=False)

class TwGoodsSpider(PhGoodsSpider):

    def __init__(self):
        self.name = sp_config.TW_USERNAME
        self.password = sp_config.TW_PASSWORD

        self.headers = {'user-agent': sp_config.USER_AGENT}
        self.cookies = get_cookies_from_file(sp_config.TW_COOKIES_SAVE)

        self.login_url = sp_config.TW_LOGIN_URL
        self.product_url = sp_config.TW_PRODUCT_URL

        self.order_url = sp_config.TW_ORDER_URL
        self.search_order_url = sp_config.TW_ORDER_SEARCH_URL
        self.check_income_url = sp_config.TW_CHECK_INCOME_URL
        self.forderid_url = sp_config.TW_FORDERID_URL

        self.make_waybill_url = sp_config.TW_MAKE_WAYBILL_URL
        self.waybill_url = sp_config.TW_WAYBILL_URL

        self.cookies_path = sp_config.TW_COOKIES_SAVE
        self.error_path = sp_config.TW_ERROR_LOG
        self.update_path = sp_config.TW_UPDATE_LOG
        self.order_path = sp_config.TW_ORDER_LOG

        # 兑换汇率
        self.exchange_rate = sp_config.TWD_CONVERT_RMB
        # 每个订单附加费用
        self.order_add_fee = sp_config.ORDER_ADD_FEE
        self.product_add_fee = sp_config.PRODUCT_ADD_FEE
        self.country = 'tw'

        self.num = 0
        self.check_msg = {'shopee_order': 0,
                          'shopee_count': 0,
                          'shopee_pay_time': [],
                          'success_order': 0,
                          'not_found_order_list': [],
                          'error_order_list': [],
                          'order_count': 0
                          }


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
    'IDR': IdGoodsSpider,
    'SGD': SgGoodsSpider,
    'BRL': BrGoodsSpider,
    'TWD': TwGoodsSpider,
}

if __name__ == '__main__':
    ss = PhGoodsSpider()
    # ss.get_goods()
    ss.get_order()
