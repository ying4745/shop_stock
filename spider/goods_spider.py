import os
import re
import time
import json
import requests
import datetime
from decimal import Decimal

from django.db.models import F
from selenium import webdriver
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from django.db import transaction

from shop_stock.settings import MEDIA_ROOT
from spider import sp_config, add_config
from spider.print_waybill import print_PDF, OldCropPDF
from goods.models import Goods, GoodsSKU
from order.models import OrderInfo, OrderGoods


class PhGoodsSpider():

    def __init__(self):

        self.name = add_config.PH_USERNAME
        self.password = add_config.PH_PASSWORD

        self.headers = {'user-agent': add_config.USER_AGENT}
        self.cookies = get_cookies_from_file(sp_config.PH_COOKIES_SAVE)

        self.login_url = sp_config.LOGIN_URL.format(sp_config.PH_LOGO)
        self.product_list_url = sp_config.PRODUCT_LIST_URL.format(sp_config.PH_LOGO)
        self.product_url = sp_config.PRODUCT_URL.format(sp_config.PH_LOGO)
        self.product_detail_url = sp_config.PRODUCT_DETAIL_URL.format(sp_config.PH_LOGO)

        self.get_order_ids_url = sp_config.GET_ORDER_IDS_URL.format(sp_config.PH_LOGO)
        self.order_list_by_order_ids_url = sp_config.ORDER_LIST_BY_ORDER_IDS_URL.format(sp_config.PH_LOGO)

        self.one_order_url = sp_config.ORDER_SEARCH_URL.format(sp_config.PH_LOGO)
        self.order_income_url = sp_config.ORDER_INCOME_URL.format(sp_config.PH_LOGO)

        self.bind_order_url = sp_config.BIND_ORDER_URL.format(sp_config.PH_LOGO)
        self.query_bind_order_url = sp_config.QUERY_BIND_URL.format(sp_config.PH_LOGO)

        self.forderid_url = sp_config.FORDERID_URL.format(sp_config.PH_LOGO)
        self.job_id_url = sp_config.GET_JOBID_URL.format(sp_config.PH_LOGO)
        self.check_income_url = sp_config.CHECK_INCOME_URL.format(sp_config.PH_LOGO)

        self.make_waybill_url = sp_config.MAKE_WAYBILL_URL.format(sp_config.PH_LOGO)
        self.waybill_url = sp_config.WAYBILL_URL.format(sp_config.PH_LOGO)

        self.cookies_path = sp_config.PH_COOKIES_SAVE
        self.error_path = sp_config.PH_ERROR_LOG
        self.update_path = sp_config.PH_UPDATE_LOG
        self.order_path = sp_config.PH_ORDER_LOG

        # 兑换汇率
        self.exchange_rate = add_config.PHP_CONVERT_RMB
        # 每个订单附加费用
        self.order_add_fee = add_config.ORDER_ADD_FEE
        # 每件商品附加费用
        self.product_add_fee = add_config.PRODUCT_ADD_FEE
        # 国家标示
        self.country = 'PHP'
        self.shop_id = add_config.PH_SHOP_ID

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
        # time.sleep(5)
        WebDriverWait(driver, 15, 0.5).until(EC.presence_of_element_located(
            (By.XPATH, '//*[@id="shop-login"]/div[1]/div/div/div/div/input'))).send_keys(self.name)
        WebDriverWait(driver, 15, 0.5).until(EC.presence_of_element_located(
            (By.XPATH, '//*[@id="shop-login"]/div[2]/div/div/div/div/input'))).send_keys(self.password)

        WebDriverWait(driver, 10, 0.5).until(EC.presence_of_element_located(
            (By.XPATH, '//*[@id="shop-login"]/div[4]/div/div/button'))).click()
        # driver.find_element_by_xpath('//*[@id="shop-login"]/div[1]/div/div/div/div/input').send_keys(self.name)
        # time.sleep(1)
        # driver.find_element_by_xpath('//*[@id="shop-login"]/div[2]/div/div/div/div/input').send_keys(self.password)
        # time.sleep(2)
        # driver.find_element_by_xpath(
        #     '//*[@id="shop-login"]/div[4]/div/div/button').click()
        time.sleep(3)
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
                    return 0, json.loads(response.content.decode())

                # print(response.status_code)  # 403
                # 验证出错，重新登录，再请求
                if i == 0:
                    self.login()

            # save_log(self.error_path, '验证出错，超出请求次数')
            return 1, '验证出错：超出请求次数'

        except TimeoutException:
            return 2, '页面加载出错'

        except :
            return 3, '请求出错'

    # 商品抓取
    def parse_goods_url(self, page):
        """发送请求，获取商品数据字典
        获取商品id信息 按一页48显示 销量升序排列"""
        data = {
            'SPC_CDS': self.cookies['SPC_CDS'],
            'SPC_CDS_VER': 2,
            'page_number': page,
            'page_size': 48,
            'source': 'seller_center',
            'list_type': 'live',
            'list_order_type': 'sales_asc',
        }
        return self.parse_url(self.product_list_url, data)

    def save_goods_data(self, goods_data):
        """解析商品数据，保存到数据库
        马来西亚 则保存马来价格，菲律宾 则保存菲律宾价格"""
        j = 1 # 记录spu数量
        for goods in goods_data['data']['list']:
            # 获取商品的id信息  再去请求商品的详情
            product_id = goods['id']

            data = {
                'SPC_CDS': self.cookies['SPC_CDS'],
                'SPC_CDS_VER': 2,
                'product_id': product_id,
            }
            msg_num, good_detail_data = self.parse_url(self.product_detail_url, data)

            product_data = good_detail_data['data']
            parent_sku = product_data['parent_sku']
            print(parent_sku, j)
            self.parse_create_goodsku(parent_sku, product_data)
            j += 1

    def get_goods(self, page=1, is_all=False):
        """获取商品信息 保存到数据库"""
        self.is_cookies()

        msg_num, goods_data = self.parse_goods_url(page)
        # TODO: 错误消息传出1
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
        # 下载图片 所需header
        m_headers = {
            'user-agent': 'Mozilla/5.0 (Windows NT 6.1; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/95.0.4638.54 Safari/537.36',
            'accept': 'image/avif,image/webp,image/apng,image/svg+xml,image/*,*/*;q=0.8',
            'accept-encoding': 'gzip, deflate, br',
            'referer': 'https://seller.my.shopee.cn/'
        }

        # 创建spu
        g_spu, is_c = Goods.objects.get_or_create(spu_id=parent_sku)

        # 保存主图片 每次都更新当前的主图
        main_image = product_data['images'][0] + '_tn'
        g_spu.image = parent_sku + '/' + main_image + '.jpg'
        g_spu.save()

        # 变体的图片信息数据
        image_data_dict = product_data['tier_variation'][0]

        # 事务保存点
        save_id = transaction.savepoint()

        # 图片名 列表  用于下载图片
        image_name_lists = [main_image]

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
            if self.country == 'PHP':
                defaults['ph_sale_price'] = good['price']
            elif self.country == 'MYR':
                defaults['my_sale_price'] = good['price']
            elif self.country == 'THB':
                defaults['th_sale_price'] = good['price']

            # 如果有变体  则添加变体图片
            if image_data_dict['images']:
                # 添加sku图片
                option_name = good['name'].split(',')[0]
                # 根据变体名字 找他在变体属性列表的位置 根据位置信息去找图片名  依据是变体名排列和图片名排列一一对应
                image_index = image_data_dict['options'].index(option_name)
                # 图片名 后面加_tn 为压缩图片
                sku_image = image_data_dict['images'][image_index] + '_tn'
            # 如果没变体 则为主图
            else:
                sku_image = main_image

            defaults['image'] = parent_sku + '/' + sku_image + '.jpg'
            if sku_image not in image_name_lists:
                image_name_lists.append(sku_image)
            # 抓取的商品sku 添加到列表
            skugood_id_list.append(good['sku'])

            # 子sku创建时 异常处理
            try:
                GoodsSKU.objects.update_or_create(sku_id=good['sku'], defaults=defaults)
            except Exception as e:
                save_log(self.update_path, parent_sku, err_type='——同步未成功商品：')
                save_log(self.error_path, str(e.args))
                # 更新有错误 则事务回滚到保存点
                transaction.savepoint_rollback(save_id)
                is_success_c = False
                break

        # 商品不出错 则执行
        if is_success_c:
            # 提交事务
            transaction.savepoint_commit(save_id)

            # 下载图片 先创建目录文件
            dir_path = os.path.join(MEDIA_ROOT, parent_sku)
            if not os.path.exists(dir_path):
                os.mkdir(dir_path)

            b_count = 1 # 记录变体的数量
            for image_name in image_name_lists:
                url = sp_config.PRODUCT_IMAGE_URL.format(image_name)
                # 文件路径
                file_name = image_name + '.jpg'
                file_path = os.path.join(dir_path, file_name)

                t_num = 0  # 一个图片的下载循环次数
                down_img(url, file_path, m_headers, t_num)
                print(file_name,b_count) # 打印当前下载的图片名

                time.sleep(1.5)
                b_count += 1

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
        """发送请求，获取商品的简化信息 需要里面的商品id信息 没有变体的图片信息"""
        data = {
            'SPC_CDS': self.cookies['SPC_CDS'],
            'SPC_CDS_VER': 2,
            'page_number': 1,
            'page_size': 24,
            'search_type': 'sku',
            'keyword': goodspu,
        }
        return self.parse_url(self.product_url, data)

    def save_single_good(self, good_data):
        try:
            if good_data['data']['page_info']['total'] == 1:
                # 获取商品的id信息  再去请求商品的详情
                product_id = good_data['data']['list'][0]['id']

                data = {
                    'SPC_CDS': self.cookies['SPC_CDS'],
                    'SPC_CDS_VER': 2,
                    'product_id': product_id,
                }
                msg_num, good_detail_data = self.parse_url(self.product_detail_url, data)

                product_data = good_detail_data['data']
                parent_sku = product_data['parent_sku']

                self.parse_create_goodsku(parent_sku, product_data)

                return '商品同步成功'
            else:
                return '没找到商品'
        except Exception as e:
            save_log(self.error_path, str(e.args))
            return '获取商品ID 请求商品详情出错'


    def get_single_good(self, goodsku):
        self.is_cookies()

        msg_num, good_data = self.parse_single_good_url(goodsku)
        # TODO: 错误消息传出2
        return self.save_single_good(good_data)

    # 订单抓取 （待出货 处理中的订单列表中抓取）
    def parse_order_ids_url(self, type, page):
        """发送请求，获取订单id列表"""
        data = {
            'SPC_CDS': self.cookies['SPC_CDS'],
            'SPC_CDS_VER': 2,
            'page_size': 40,
            'page_number': page,
            'source': type,
            'total': 0,
            'sort_by': 'ship_by_date_asc',
        }
        return self.parse_url(self.get_order_ids_url, data)

    def parse_order_list_url(self, order_ids):
        """根据id列表 请求订单数据
            2021/7/23 更新请求订单信息url  POST请求
        """
        url = self.order_list_by_order_ids_url.format(self.cookies['SPC_CDS'])
        order_info_list = []
        for orderid in order_ids:
            order_info_list.append({'order_id': int(orderid), 'shop_id': self.shop_id, 'region_id': self.country[:2]})

        data = {
            'orders': order_info_list
            }

        try:
            response = requests.post(url, json=data, cookies=self.cookies, headers=self.headers)
            if response.status_code == 200:
                return 0, json.loads(response.content.decode())
            try:
                msg = json.loads(response.content.decode())['message']
            except:
                msg = '请求出错 返回代码403'
            return 2, msg
        except:
            return 1, "根据ids 请求订单信息报错"

    def save_order_data(self, order_data):
        """解析订单信息 保存到数据库"""
        for order_info in order_data:
            # 解析订单 用户数据  生成订单详情
            self.parse_create_order(order_info)

    def get_order(self, type='to_process', page=1, is_all=True):
        """获取订单信息 保存到数据库
            :type   'to_process'  待处理订单
                    'shipping' 运输中订单
                    'completed' 已完成订单
            只抓取 待出货列表， 运输中的通过id单个发送请求
        """
        self.is_cookies()
        ids_msg_num, order_ids_data = self.parse_order_ids_url(type, page)
        if ids_msg_num:
            return 1, order_ids_data
        try:
            order_ids = []
            order_lists = order_ids_data['data']['package_list']
            for order in order_lists:
                order_ids.append(str(order['order_id']))
        except:
            return 2, '返回 订单id列表 数据错误'
        if not order_ids:
            return 3, '没有新的处理中订单'

        # 每次请求10个id  2021/1/27
        pages = (len(order_ids) + 9) // 10
        for i in range(pages):
            orderids = order_ids[i * 10:(i + 1) * 10]
            list_msg_num, order_list_data = self.parse_order_list_url(orderids)
            if list_msg_num:
                return 4, order_list_data
            try:
                order_data = order_list_data['data']['orders']
            except:
                return 5, '返回 订单数据 错误'

            self.save_order_data(order_data)

        if is_all:
            try:
                total = order_ids_data['data']['total']
            except:
                return 6, '返回数据错误'

            pages = (total + 39) // 40
            for i in range(page + 1, pages + 1):
                self.get_order(type='to_process', page=i, is_all=False)

        if self.num == 0:
            return 0, '没有订单更新'
        else:
            return 0, str(self.num) + ' 条订单更新'

    # def list_filter_data(self, params, list_data):
    #     """过滤数据列表中符合的数据字典"""
    #     return list(filter(lambda x: x['id'] == params, list_data))[0]

    def parse_create_order(self, order_info):
        """解析创建订单，创建订单同时创建订单商品，更新订单不更新订单商品"""

        # 如果订单状态为取消，不创建，如已有订单 则删除
        # 订单状态：待出货和已运送 为1，已取消为5，已完成为4
        order_obj = OrderInfo.objects.filter(order_id=order_info['order_sn'])
        if order_obj:
            # 订单的状态为 5  则已被取消
            if order_info['status'] == 5:
                order_obj[0].delete()
                return 1, '订单已取消'
            elif order_obj[0].order_status == 1:
                return 2, '订单已同步，且待发货'
            # 已打单 已打包发出订单 单独请求这个订单数据 更新收入
            elif order_obj[0].order_status == 5 and order_obj[0].order_send_status == 1:
                msg_num, order_obj_or_err_msg = self.parse_order_income(order_obj[0])
                if msg_num:
                    return 4, order_obj_or_err_msg
                self.compute_order_profit(order_obj_or_err_msg)
                return 5, '订单已完成，统计订单利润完成'
            else:
                return 3, '订单已存在，且没取消，没出货，没在待发货列表'

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
        # for order_good_info in order_info['order_items']:
        #     total_price += float(order_good_info['order_price']) * order_good_info['amount']

        o_data = {
            'order_time': order_info['order_sn'][:6],
            'order_shopeeid': order_info['order_id'],
            'customer': order_info['buyer_user']['user_name'],
            'customer_remark': order_info['remark'][:200],
            'receiver': order_info['buyer_address_name'],
            'customer_info': customer_info,
            'total_price': total_price,
            'order_country': self.country
        }
        order_obj, is_c = OrderInfo.objects.update_or_create(order_id=order_info['order_sn'], defaults=o_data)

        if is_c:
            self.parse_create_ordergood(order_obj, order_info)
            self.num += 1

        return 0, order_obj

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

                # 查找该订单中 商品是否存在
                order_good = OrderGoods.objects.filter(order=order_obj, sku_good=good_obj)
                # 如订单中已有该商品，则累加数量
                if order_good:
                    order_good.update(count=F('count') + order_item['amount'])
                # 没有，则创建该订单商品
                else:
                    try:
                        # 同一个订单 同种商品 记录只能有一条 唯一确认标志
                        OrderGoods.objects.create(order=order_obj, sku_good=good_obj,
                                                  count=order_item['amount'],
                                                  price=order_item['order_price'])
                    except Exception as e:
                        save_log(self.error_path, str(e.args))
            else:
                if order_item['bundle_deal_model']:
                    # 套装可以为 不同商品 但是同种折扣
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
                        # 套装中价格 暂时记录为原价
                        price = order_bundle_item['price']

                        order_good = OrderGoods.objects.filter(order=order_obj, sku_good=good_obj)
                        # 如订单中已有该商品，则累加数量
                        if order_good:
                            order_good.update(count=F('count') + count)
                        # 没有，则创建该订单商品
                        else:
                            try:
                                # 同一个订单 同种商品 记录只能有一条 唯一确认标志
                                OrderGoods.objects.create(order=order_obj, sku_good=good_obj, count=count, price=price)
                            except Exception as e:
                                save_log(self.error_path, str(e.args))
                else:
                    # 订单备注中 记录错误
                    order_obj.order_desc = order_obj.order_desc + '（订单商品有错误！）'
                    order_obj.save()

    def check_order_status(self):
        """
            订单状态必须为已打单、出货状态必须为已发出
            然后检查这些订单是否在运输中，是则将订单状态转变为快递揽收运输中
        """
        orders = OrderInfo.objects.filter(order_country=self.country, order_status=5, order_send_status=1).values_list('order_shopeeid', flat=True)
        order_ids = list(orders)
        shipping_order_ids = []
        # 每次请求10个id  获取订单状态
        pages = (len(order_ids) + 9) // 10
        for i in range(pages):
            orderids = order_ids[i * 10:(i + 1) * 10]
            list_msg_num, order_list_data = self.parse_order_list_url(orderids)
            if list_msg_num:
                return 1, order_list_data
            try:
                order_data = order_list_data['data']['orders']
            except:
                return 2, '返回 订单数据 错误'

            for order in order_data:
                if order['list_type'] == 8:
                    shipping_order_ids.append(order['order_id'])

        if len(shipping_order_ids) > 0 :
            order_num = OrderInfo.objects.filter(order_shopeeid__in=shipping_order_ids).update(order_status=10)
            return 0, '{} 个订单运送中'.format(order_num)

        return 0, '没有订单更新'

    def update_order(self):
        """已发货订单 更新实际运费 统计利润"""
        orders = OrderInfo.objects.filter(order_country=self.country, order_status=10)
        # print(orders.count())
        for order in orders:
            msg_num, order_obj = self.parse_order_income(order)
            if msg_num:
                continue

            self.compute_order_profit(order_obj)
            self.num += 1

        if self.num == 0:
            return 0, '没有订单更新'
        else:
            return 0, str(self.num) + ' 条订单更新'

    def parse_order_income(self, order_obj):
        """已打单 发货了的订单 单独请求这个订单数据 更新收入
            根据有无实际运费判断 是否发出"""
        req_data = {
            'SPC_CDS': self.cookies['SPC_CDS'],
            'SPC_CDS_VER': 2,
            'order_id': order_obj.order_shopeeid
            }
        msg_num, order_data = self.parse_url(self.order_income_url, req_data)
        if msg_num:
            return 1, order_data
        # TODO: 待定
        order_payment_info = order_data['data']['payment_info']

        # 实际运费 没有实际运费 代表订单没有扫描
        actual_shipping_fee = order_payment_info['shipping_subtotal']['shipping_fee_paid_by_shopee_on_your_behalf']
        if actual_shipping_fee == 0.00:
            return 2, '没有实际运费'

        # 商品总价
        total_price = order_payment_info['merchant_subtotal']['product_price']

        # 判断是否是卖家的优惠卷
        # voucher_price = one_order_data['voucher_price'] if one_order_data['voucher_absorbed_by_seller'] else '0.00'
        voucher_price = order_payment_info['rebate_and_voucher']['voucher_code']

        # 买家支付运费
        shipping_fee = order_payment_info['shipping_subtotal']['shipping_fee_paid_by_buyer']
        # 平台运费回扣
        shipping_rebate = order_payment_info['rebate_and_voucher']['shipping_rebate_from_shopee']

        # 商品折扣 shopee回扣     ？不清楚是什么回扣
        product_rebate = order_payment_info['rebate_and_voucher']['product_discount_rebate_from_shopee']

        # 优惠券  百分比返给买家虾币
        coin_rebate = order_payment_info['rebate_and_voucher']['seller_absorbed_coin_cash_back']

        # 平台佣金
        comm_fee = order_payment_info['fees_and_charges']['commission_fee']
        # 平台服务费
        seller_service_fee = order_payment_info['fees_and_charges']['service_fee']
        # 手续费
        card_txn_fee = order_payment_info['fees_and_charges']['transaction_fee']
        # 税收
        tax_fee = order_payment_info['buyer_paid_tax_amount']

        # 核算订单收入
        # float 先转成str 因为float本身就有误差
        order_income = Decimal(str(total_price)) + Decimal(str(voucher_price)) \
                       + Decimal(str(shipping_fee)) + Decimal(str(shipping_rebate)) \
                       + Decimal(str(actual_shipping_fee)) + Decimal(str(card_txn_fee)) \
                       + Decimal(str(comm_fee)) + Decimal(str(seller_service_fee)) \
                       + Decimal(str(tax_fee)) + Decimal(str(product_rebate)) \
                       + Decimal(str(coin_rebate))

        # 订单收入核对  和平台显示不一样  备注里加提示
        if order_income != Decimal(str(order_data['data']['amount'])):
            order_obj.order_desc=order_obj.order_desc + ' >*>*> 收入异常 <*<*<'
        # 菲律宾 实际运费 舍去0.5 小数
        if order_obj.order_country == 'PHP':
            order_income = order_income.quantize(Decimal(0.0), rounding='ROUND_UP')
        order_obj.order_income=order_income
        order_obj.total_price=total_price
        order_obj.save()

        return 0, order_obj

    def compute_order_profit(self, order_obj):
        """计算订单利润"""
        order_cost = 0  # 订单成本(人民币）

        for good_obj in order_obj.ordergoods_set.all():
            good_buy_price = good_obj.sku_good.buy_price
            # 进价低于6元的商品  不附加国内运杂费
            if good_buy_price < 6:
                order_cost += good_buy_price * good_obj.count
            # 商品的成本  每件商品进价上 国内运杂费
            else:
                order_cost += (good_buy_price + Decimal(self.product_add_fee)) * good_obj.count

        order_profit = order_obj.order_income * Decimal(self.exchange_rate) \
                       - Decimal(order_cost) - Decimal(self.order_add_fee)
        order_obj.order_profit = order_profit
        # 更新订单状态(待确认)
        order_obj.order_status = 9
        order_obj.save()

    # 单个订单
    def parse_single_order_url(self, order_id):
        data = {
            'SPC_CDS': self.cookies['SPC_CDS'],
            'SPC_CDS_VER': 2,
            'keyword': order_id,
            'query': order_id
        }
        return self.parse_url(self.one_order_url, data)

    def save_single_order(self, order_data):
        try:
            single_order_data = order_data['data']['orders']
        except:
            return '返回数据错误'
        if single_order_data:
            order_status_num, order_obj = self.parse_create_order(single_order_data[0])

            # order_obj 为报错消息 或是实例对象
            if order_status_num:
                return order_obj

            # 订单为已发货，且有订单收入 计算利润
            # if order_obj.order_status == 10 and str(order_obj.order_income) != '0.00':
            #     self.compute_order_profit(order_obj)
            #     return '订单收入，利润计算完成'

            return '订单同步完成'
        else:
            return '没找到该订单'

    def get_single_order(self, order_id):
        self.is_cookies()
        msg_num, order_data = self.parse_single_order_url(order_id)
        if msg_num:
            return order_data
        return self.save_single_order(order_data)

    # 生成运单号
    def make_order_waybill(self, orderid):
        self.is_cookies()
        # 组成URL 平台订单号
        url = self.make_waybill_url.format(self.cookies['SPC_CDS'])

        # request payload 参数
        data = {"channel_id": 28016, "order_id": int(orderid), "forder_id": orderid}

        try:
            for i in range(2):
                response = requests.post(url, data=data, cookies=self.cookies, headers=self.headers)

                if response.status_code == 200:
                    res_msg = json.loads(response.text)
                    if res_msg['code'] == 0:
                        return ''
                    if i != 0:
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

    # 获取订单package_number，保存到数据库，后续下载运送单，绑定快递需要
    def get_order_forderid(self, orderids):
        """forderid 与 package_number 相同"""
        url = self.forderid_url.format(self.cookies['SPC_CDS'])
        order_info_list = []
        for orderid in orderids:
            order_info_list.append({'order_id': int(orderid), 'shop_id': self.shop_id, 'region_id': self.country[:2]})

        data = {
            'orders': order_info_list
        }

        # 调用方做异常处理
        response = requests.post(url, json=data, cookies=self.cookies, headers=self.headers)
        res_dict = json.loads(response.content.decode())

        package_list = []
        for ordermodel in res_dict['data']['list']:
            order_package_data = ordermodel['package_list'][0]
            # 把package_number, 运单号 更新到数据库中保存
            OrderInfo.objects.filter(order_shopeeid=str(ordermodel['order_id'])).update(
                order_package_num=order_package_data['package_number'], order_waybill_num=order_package_data['consignment_no'])
            # 组成需要的数据列表
            package_list.append({'order_id': ordermodel['order_id'], 'shop_id': self.shop_id,
                                 'region_id': self.country[:2], 'package_number': order_package_data['package_number']})
        return package_list

    # 2021/7/1 更新下载运单号URL
    def down_order_waybill(self, order_ids):
        """下载运单号
        order_ids: 订单号列表 ['2224060720','2221118585','2222123945']
        列表长度最长为50
        """
        job_id_url = self.job_id_url.format(self.cookies['SPC_CDS'])
        pages = (len(order_ids) + 49) // 50
        for i in range(pages):
            orderids = order_ids[i*50:(i+1)*50]
            try:
                package_list = self.get_order_forderid(orderids)
            except:
                return '请求package number 出错'
            # 组合参数 请求一个job_id 用于下载运单号
            data = {
                'generate_file_details': [{'file_contents': [3],
                                          'file_name': '运单',
                                          'file_type': 'THERMAL_PDF'}],
                'package_list': package_list,
                'record_generate_schema': True
            }

            try:
                un_print = True
                for i in range(2):
                    # 请求jobid
                    response = requests.post(job_id_url, json=data, cookies=self.cookies, headers=self.headers)

                    if response.status_code == 200:
                        res_dict = json.loads(response.content.decode())
                        try:
                            job_id = res_dict['data']['list'][0]['job_id']
                        except:
                            return '返回数据中 无job id，状态码：{}'.format(response.status_code)

                        # 根据jobid 下载运单号
                        g_data = {
                            'SPC_CDS': self.cookies['SPC_CDS'],
                            'SPC_CDS_VER': 2,
                            'job_id': job_id
                        }
                        # 等待一会  系统生成PDF
                        time.sleep(3)
                        g_response = requests.get(self.waybill_url, params=g_data,
                                                cookies=self.cookies, headers=self.headers)
                        if g_response.status_code == 200:
                            pdf_data = g_response.content
                            if not pdf_data.startswith(b'%PDF-1.'):
                                return '下载的PDF格式错误, 打单失败！'
                            # 文件名
                            file_name = self.country + '-0-(' +str(i) +').pdf'
                            file_path = os.path.join(add_config.PRINT_WAYBILL_PATH, file_name)

                            with open(file_path, 'wb') as f:
                                f.write(pdf_data)

                            if os.path.isfile(file_path):
                                # 调用打印类  打印运单号
                                print_PDF(file_path)
                                # print('打单成功')

                                # os.remove(file_path)
                                un_print = False
                                break

                    # print(response.status_code)  # 403
                    # 验证出错，重新登录，再请求
                    if i == 0:
                        self.login()

                if un_print:
                    return '验证出错：超出请求次数'

            except Exception as e:
                save_log(self.error_path, str(e.args))
                return '下载PDF请求出错'

        return ''

    # 绑定订单  首公里
    def bind_order(self, express, waybill_num, package_list):
        bind_url = self.bind_order_url.format(self.cookies['SPC_CDS'])
        data = {
            'carrier_id': int(express),
            'fm_tn': waybill_num,
            'package_list': list(package_list)
        }

        response = requests.post(bind_url, json=data, cookies=self.cookies, headers=self.headers)

        if response.status_code == 200:
            res_dict = json.loads(response.content.decode())
            msg = res_dict.get('message', '')
            if not msg:
                return '绑定失败'
            if msg == 'success':
                return ''
        return '绑定请求返回出错'


    def query_bind_order(self, waybill, page=1, is_all=True):
        """按快递运单号 查询绑定成功的订单
            action_status 2 为绑定成功
        """
        # 当前时间戳 和过去十天的时间戳
        end_time = int(time.time())
        create_time = end_time - 864000
        data = {
            'SPC_CDS': self.cookies['SPC_CDS'],
            'SPC_CDS_VER': 2,
            'create_time': create_time,
            'end_time': end_time,
            'fm_tn': waybill,
            'action_status': 2,
            'is_only_contain_alarm': 'false',
            'page_number': page,
            'page_size': 100
            }
        msg_num, request_data = self.parse_url(self.query_bind_order_url, data)

        if msg_num:
            return request_data

        order_sn_list = []
        try:
            for sing_data in request_data['data']['list']:
                order_sn_list.append(sing_data['order_sn'])
        except:
            return '返回数据错误'

        if order_sn_list:
            OrderInfo.objects.filter(order_id__in=order_sn_list).update(order_bind_status=1)

        # 是否翻页
        if is_all:
            # 计算共有多少页
            total = request_data['data']['page_info']['total']
            pages = (total + 99) // 100

            for i in range(page + 1, pages + 1):
                self.query_bind_order(waybill, i, is_all=False)

        return ''

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
        msg_num, order_data = self.parse_check_income_url(page, start_date, end_date)
        # TODO: 错误消息传出3
        self.check_order_income(order_data)

        if is_all:
            total = order_data['data']['page_info']['total']
            # TODO: 后期修改 待调整
            pages = (total + 49) // 50
            for i in range(page + 1, pages + 1):
                self.get_income_order(i, start_date, end_date, is_all=False)


class MYGoodsSpider(PhGoodsSpider):

    def __init__(self):
        self.name = add_config.MY_USERNAME
        self.password = add_config.MY_PASSWORD

        self.headers = {'user-agent': add_config.USER_AGENT}
        self.cookies = get_cookies_from_file(sp_config.MY_COOKIES_SAVE)

        self.login_url = sp_config.LOGIN_URL.format(sp_config.MY_LOGO)
        self.product_list_url = sp_config.PRODUCT_LIST_URL.format(sp_config.MY_LOGO)
        self.product_url = sp_config.PRODUCT_URL.format(sp_config.MY_LOGO)
        self.product_detail_url = sp_config.PRODUCT_DETAIL_URL.format(sp_config.MY_LOGO)

        self.get_order_ids_url = sp_config.GET_ORDER_IDS_URL.format(sp_config.MY_LOGO)
        self.order_list_by_order_ids_url = sp_config.ORDER_LIST_BY_ORDER_IDS_URL.format(sp_config.MY_LOGO)

        self.one_order_url = sp_config.ORDER_SEARCH_URL.format(sp_config.MY_LOGO)
        self.order_income_url = sp_config.ORDER_INCOME_URL.format(sp_config.MY_LOGO)

        self.bind_order_url = sp_config.BIND_ORDER_URL.format(sp_config.MY_LOGO)
        self.query_bind_order_url = sp_config.QUERY_BIND_URL.format(sp_config.MY_LOGO)

        self.forderid_url = sp_config.FORDERID_URL.format(sp_config.MY_LOGO)
        self.job_id_url = sp_config.GET_JOBID_URL.format(sp_config.MY_LOGO)
        self.check_income_url = sp_config.CHECK_INCOME_URL.format(sp_config.MY_LOGO)

        self.make_waybill_url = sp_config.MAKE_WAYBILL_URL.format(sp_config.MY_LOGO)
        self.waybill_url = sp_config.WAYBILL_URL.format(sp_config.MY_LOGO)

        self.cookies_path = sp_config.MY_COOKIES_SAVE
        self.error_path = sp_config.MY_ERROR_LOG
        self.update_path = sp_config.MY_UPDATE_LOG
        self.order_path = sp_config.MY_ORDER_LOG

        # 兑换汇率
        self.exchange_rate = add_config.MYR_CONVERT_RMB
        # 每个订单附加费用
        self.order_add_fee = add_config.ORDER_ADD_FEE
        self.product_add_fee = add_config.PRODUCT_ADD_FEE

        self.country = 'MYR'
        self.shop_id = add_config.MY_SHOP_ID

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
        self.name = add_config.TH_USERNAME
        self.password = add_config.TH_PASSWORD

        self.headers = {'user-agent': add_config.USER_AGENT}
        self.cookies = get_cookies_from_file(sp_config.TH_COOKIES_SAVE)

        self.login_url = sp_config.LOGIN_URL.format(sp_config.TH_LOGO)
        self.product_list_url = sp_config.PRODUCT_LIST_URL.format(sp_config.TH_LOGO)
        self.product_url = sp_config.PRODUCT_URL.format(sp_config.TH_LOGO)
        self.product_detail_url = sp_config.PRODUCT_DETAIL_URL.format(sp_config.TH_LOGO)

        self.get_order_ids_url = sp_config.GET_ORDER_IDS_URL.format(sp_config.TH_LOGO)
        self.order_list_by_order_ids_url = sp_config.ORDER_LIST_BY_ORDER_IDS_URL.format(sp_config.TH_LOGO)

        self.one_order_url = sp_config.ORDER_SEARCH_URL.format(sp_config.TH_LOGO)
        self.order_income_url = sp_config.ORDER_INCOME_URL.format(sp_config.TH_LOGO)

        self.bind_order_url = sp_config.BIND_ORDER_URL.format(sp_config.TH_LOGO)
        self.query_bind_order_url = sp_config.QUERY_BIND_URL.format(sp_config.TH_LOGO)

        self.forderid_url = sp_config.FORDERID_URL.format(sp_config.TH_LOGO)
        self.job_id_url = sp_config.GET_JOBID_URL.format(sp_config.TH_LOGO)
        self.check_income_url = sp_config.CHECK_INCOME_URL.format(sp_config.TH_LOGO)

        self.make_waybill_url = sp_config.MAKE_WAYBILL_URL.format(sp_config.TH_LOGO)
        self.waybill_url = sp_config.WAYBILL_URL.format(sp_config.TH_LOGO)

        self.cookies_path = sp_config.TH_COOKIES_SAVE
        self.error_path = sp_config.TH_ERROR_LOG
        self.update_path = sp_config.TH_UPDATE_LOG
        self.order_path = sp_config.TH_ORDER_LOG

        # 兑换汇率
        self.exchange_rate = add_config.THB_CONVERT_RMB
        # 每个订单附加费用
        self.order_add_fee = add_config.ORDER_ADD_FEE
        self.product_add_fee = add_config.PRODUCT_ADD_FEE

        self.country = 'THB'
        self.shop_id = add_config.TH_SHOP_ID

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
        self.name = add_config.ID_USERNAME
        self.password = add_config.ID_PASSWORD

        self.headers = {'user-agent': add_config.USER_AGENT}
        self.cookies = get_cookies_from_file(sp_config.ID_COOKIES_SAVE)

        self.login_url = sp_config.LOGIN_URL.format(sp_config.ID_LOGO)
        self.product_list_url = sp_config.PRODUCT_LIST_URL.format(sp_config.ID_LOGO)
        self.product_url = sp_config.PRODUCT_URL.format(sp_config.ID_LOGO)
        self.product_detail_url = sp_config.PRODUCT_DETAIL_URL.format(sp_config.ID_LOGO)

        self.get_order_ids_url = sp_config.GET_ORDER_IDS_URL.format(sp_config.ID_LOGO)
        self.order_list_by_order_ids_url = sp_config.ORDER_LIST_BY_ORDER_IDS_URL.format(sp_config.ID_LOGO)

        self.one_order_url = sp_config.ORDER_SEARCH_URL.format(sp_config.ID_LOGO)
        self.order_income_url = sp_config.ORDER_INCOME_URL.format(sp_config.ID_LOGO)

        self.bind_order_url = sp_config.BIND_ORDER_URL.format(sp_config.ID_LOGO)
        self.query_bind_order_url = sp_config.QUERY_BIND_URL.format(sp_config.ID_LOGO)

        self.forderid_url = sp_config.FORDERID_URL.format(sp_config.ID_LOGO)
        self.job_id_url = sp_config.GET_JOBID_URL.format(sp_config.ID_LOGO)
        self.check_income_url = sp_config.CHECK_INCOME_URL.format(sp_config.ID_LOGO)

        self.make_waybill_url = sp_config.MAKE_WAYBILL_URL.format(sp_config.ID_LOGO)
        self.waybill_url = sp_config.WAYBILL_URL.format(sp_config.ID_LOGO)

        self.cookies_path = sp_config.ID_COOKIES_SAVE
        self.error_path = sp_config.ID_ERROR_LOG
        self.update_path = sp_config.ID_UPDATE_LOG
        self.order_path = sp_config.ID_ORDER_LOG

        # 兑换汇率
        self.exchange_rate = add_config.IDR_CONVERT_RMB
        # 每个订单附加费用
        self.order_add_fee = add_config.ORDER_ADD_FEE
        self.product_add_fee = add_config.PRODUCT_ADD_FEE

        self.country = 'IDR'
        self.shop_id = add_config.ID_SHOP_ID

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

        data = {
            'order_ids': orderids,
        }

        self.is_cookies()

        try:
            for i in range(2):
                response = requests.post(self.waybill_url, json=data, cookies=self.cookies, headers=self.headers)

                if response.status_code == 200:
                    pdf_data = response.content
                    if not pdf_data.startswith(b'%PDF-1.'):
                        return '下载的PDF格式错误, 打单失败！'
                    # 文件名
                    file_name = 'WorkPDF00ID.pdf'
                    file_path = os.path.join(add_config.PRINT_WAYBILL_PATH, file_name)

                    with open(file_path, 'wb') as f:
                        f.write(pdf_data)

                    if os.path.isfile(file_path):
                        # 调用旧打印类 切割pdf 打印运单
                        print_PDF(file_path)

                    return ''

                # print(response.status_code)  # 403
                # 验证出错，重新登录，再请求
                if i == 0:
                    self.login()

            save_log(self.error_path, '验证出错，超出请求次数')
            return '验证出错：超出请求次数'

        except Exception as e:
            save_log(self.error_path, str(e.args))
            return '发送请求出错'


class SgGoodsSpider(PhGoodsSpider):

    def __init__(self):
        self.name = add_config.SG_USERNAME
        self.password = add_config.SG_PASSWORD

        self.headers = {'user-agent': add_config.USER_AGENT}
        self.cookies = get_cookies_from_file(sp_config.SG_COOKIES_SAVE)

        self.login_url = sp_config.LOGIN_URL.format(sp_config.SG_LOGO)
        self.product_list_url = sp_config.PRODUCT_LIST_URL.format(sp_config.SG_LOGO)
        self.product_url = sp_config.PRODUCT_URL.format(sp_config.SG_LOGO)
        self.product_detail_url = sp_config.PRODUCT_DETAIL_URL.format(sp_config.SG_LOGO)

        self.get_order_ids_url = sp_config.GET_ORDER_IDS_URL.format(sp_config.SG_LOGO)
        self.order_list_by_order_ids_url = sp_config.ORDER_LIST_BY_ORDER_IDS_URL.format(sp_config.SG_LOGO)

        self.one_order_url = sp_config.ORDER_SEARCH_URL.format(sp_config.SG_LOGO)
        self.order_income_url = sp_config.ORDER_INCOME_URL.format(sp_config.SG_LOGO)

        self.bind_order_url = sp_config.BIND_ORDER_URL.format(sp_config.SG_LOGO)
        self.query_bind_order_url = sp_config.QUERY_BIND_URL.format(sp_config.SG_LOGO)

        self.forderid_url = sp_config.FORDERID_URL.format(sp_config.SG_LOGO)
        self.job_id_url = sp_config.GET_JOBID_URL.format(sp_config.SG_LOGO)
        self.check_income_url = sp_config.CHECK_INCOME_URL.format(sp_config.SG_LOGO)

        self.make_waybill_url = sp_config.MAKE_WAYBILL_URL.format(sp_config.SG_LOGO)
        self.waybill_url = sp_config.WAYBILL_URL.format(sp_config.SG_LOGO)

        self.cookies_path = sp_config.SG_COOKIES_SAVE
        self.error_path = sp_config.SG_ERROR_LOG
        self.update_path = sp_config.SG_UPDATE_LOG
        self.order_path = sp_config.SG_ORDER_LOG

        # 兑换汇率
        self.exchange_rate = add_config.SGD_CONVERT_RMB
        # 每个订单附加费用
        self.order_add_fee = add_config.ORDER_ADD_FEE
        self.product_add_fee = add_config.PRODUCT_ADD_FEE

        self.country = 'SGD'
        self.shop_id = add_config.SG_SHOP_ID

        self.num = 0
        self.check_msg = {'shopee_order': 0,
                          'shopee_count': 0,
                          'shopee_pay_time': [],
                          'success_order': 0,
                          'not_found_order_list': [],
                          'error_order_list': [],
                          'order_count': 0
                          }

    # 生成运单号
    def make_order_waybill(self, orderid):
        self.is_cookies()
        # 组成URL 平台订单号
        url = self.make_waybill_url.format(self.cookies['SPC_CDS'])

        # request payload 参数
        data = {"channel_id": 18028, "order_id": int(orderid), "forder_id": orderid}

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
                # print(response.status_code)
                if i == 0:
                    self.login()

            save_log(self.error_path, '验证出错，超出请求次数')
            return '验证出错：超出请求次数'

        except Exception as e:
            save_log(self.error_path, str(e.args))
            return '发送请求出错'


class TwGoodsSpider(PhGoodsSpider):

    def __init__(self):
        self.name = add_config.TW_USERNAME
        self.password = add_config.TW_PASSWORD

        self.headers = {'user-agent': add_config.USER_AGENT}
        self.cookies = get_cookies_from_file(sp_config.TW_COOKIES_SAVE)

        self.login_url = sp_config.LOGIN_URL.format(sp_config.TW_LOGO)
        self.product_list_url = sp_config.PRODUCT_LIST_URL.format(sp_config.TW_LOGO)
        self.product_url = sp_config.PRODUCT_URL.format(sp_config.TW_LOGO)
        self.product_detail_url = sp_config.PRODUCT_DETAIL_URL.format(sp_config.TW_LOGO)

        self.get_order_ids_url = sp_config.GET_ORDER_IDS_URL.format(sp_config.TW_LOGO)
        self.order_list_by_order_ids_url = sp_config.ORDER_LIST_BY_ORDER_IDS_URL.format(sp_config.TW_LOGO)

        self.one_order_url = sp_config.ORDER_SEARCH_URL.format(sp_config.TW_LOGO)
        self.order_income_url = sp_config.ORDER_INCOME_URL.format(sp_config.TW_LOGO)

        self.bind_order_url = sp_config.BIND_ORDER_URL.format(sp_config.TW_LOGO)
        self.query_bind_order_url = sp_config.QUERY_BIND_URL.format(sp_config.TW_LOGO)

        self.forderid_url = sp_config.FORDERID_URL.format(sp_config.TW_LOGO)
        self.job_id_url = sp_config.GET_JOBID_URL.format(sp_config.TW_LOGO)
        self.check_income_url = sp_config.CHECK_INCOME_URL.format(sp_config.TW_LOGO)

        self.make_waybill_url = sp_config.MAKE_WAYBILL_URL.format(sp_config.TW_LOGO)
        self.waybill_url = sp_config.WAYBILL_URL.format(sp_config.TW_LOGO)

        self.cookies_path = sp_config.TW_COOKIES_SAVE
        self.error_path = sp_config.TW_ERROR_LOG
        self.update_path = sp_config.TW_UPDATE_LOG
        self.order_path = sp_config.TW_ORDER_LOG

        # 兑换汇率
        self.exchange_rate = add_config.TWD_CONVERT_RMB
        # 每个订单附加费用
        self.order_add_fee = add_config.ORDER_ADD_FEE
        self.product_add_fee = add_config.PRODUCT_ADD_FEE

        self.country = 'TWD'
        self.shop_id = sp_config.TW_SHOP_ID

        self.num = 0
        self.check_msg = {'shopee_order': 0,
                          'shopee_count': 0,
                          'shopee_pay_time': [],
                          'success_order': 0,
                          'not_found_order_list': [],
                          'error_order_list': [],
                          'order_count': 0
                          }


class VnGoodsSpider(PhGoodsSpider):

    def __init__(self):
        self.name = add_config.VN_USERNAME
        self.password = add_config.VN_PASSWORD

        self.headers = {'user-agent': add_config.USER_AGENT}
        self.cookies = get_cookies_from_file(sp_config.VN_COOKIES_SAVE)

        self.login_url = sp_config.LOGIN_URL.format(sp_config.VN_LOGO)
        self.product_list_url = sp_config.PRODUCT_LIST_URL.format(sp_config.VN_LOGO)
        self.product_url = sp_config.PRODUCT_URL.format(sp_config.VN_LOGO)
        self.product_detail_url = sp_config.PRODUCT_DETAIL_URL.format(sp_config.VN_LOGO)

        self.get_order_ids_url = sp_config.GET_ORDER_IDS_URL.format(sp_config.VN_LOGO)
        self.order_list_by_order_ids_url = sp_config.ORDER_LIST_BY_ORDER_IDS_URL.format(sp_config.VN_LOGO)

        self.one_order_url = sp_config.ORDER_SEARCH_URL.format(sp_config.VN_LOGO)
        self.order_income_url = sp_config.ORDER_INCOME_URL.format(sp_config.VN_LOGO)

        self.bind_order_url = sp_config.BIND_ORDER_URL.format(sp_config.VN_LOGO)
        self.query_bind_order_url = sp_config.QUERY_BIND_URL.format(sp_config.VN_LOGO)

        self.forderid_url = sp_config.FORDERID_URL.format(sp_config.VN_LOGO)
        self.job_id_url = sp_config.GET_JOBID_URL.format(sp_config.VN_LOGO)
        self.check_income_url = sp_config.CHECK_INCOME_URL.format(sp_config.VN_LOGO)

        self.make_waybill_url = sp_config.MAKE_WAYBILL_URL.format(sp_config.VN_LOGO)
        self.waybill_url = sp_config.WAYBILL_URL.format(sp_config.VN_LOGO)

        self.cookies_path = sp_config.VN_COOKIES_SAVE
        self.error_path = sp_config.VN_ERROR_LOG
        self.update_path = sp_config.VN_UPDATE_LOG
        self.order_path = sp_config.VN_ORDER_LOG

        # 兑换汇率
        self.exchange_rate = add_config.VND_CONVERT_RMB
        # 每个订单附加费用
        self.order_add_fee = add_config.ORDER_ADD_FEE
        self.product_add_fee = add_config.PRODUCT_ADD_FEE

        self.country = 'VND'
        self.shop_id = add_config.VN_SHOP_ID

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
        self.name = add_config.BR_USERNAME
        self.password = add_config.BR_PASSWORD

        self.headers = {'user-agent': add_config.USER_AGENT}
        self.cookies = get_cookies_from_file(sp_config.BR_COOKIES_SAVE)

        self.login_url = sp_config.LOGIN_URL.format(sp_config.BR_LOGO)
        self.product_list_url = sp_config.PRODUCT_LIST_URL.format(sp_config.BR_LOGO)
        self.product_url = sp_config.PRODUCT_URL.format(sp_config.BR_LOGO)
        self.product_detail_url = sp_config.PRODUCT_DETAIL_URL.format(sp_config.BR_LOGO)

        self.get_order_ids_url = sp_config.GET_ORDER_IDS_URL.format(sp_config.BR_LOGO)
        self.order_list_by_order_ids_url = sp_config.ORDER_LIST_BY_ORDER_IDS_URL.format(sp_config.BR_LOGO)

        self.one_order_url = sp_config.ORDER_SEARCH_URL.format(sp_config.BR_LOGO)
        self.order_income_url = sp_config.ORDER_INCOME_URL.format(sp_config.BR_LOGO)

        self.bind_order_url = sp_config.BIND_ORDER_URL.format(sp_config.BR_LOGO)
        self.query_bind_order_url = sp_config.QUERY_BIND_URL.format(sp_config.BR_LOGO)

        self.forderid_url = sp_config.FORDERID_URL.format(sp_config.BR_LOGO)
        self.job_id_url = sp_config.GET_JOBID_URL.format(sp_config.BR_LOGO)
        self.check_income_url = sp_config.CHECK_INCOME_URL.format(sp_config.BR_LOGO)

        self.make_waybill_url = sp_config.MAKE_WAYBILL_URL.format(sp_config.BR_LOGO)
        self.waybill_url = sp_config.WAYBILL_URL.format(sp_config.BR_LOGO)

        self.cookies_path = sp_config.BR_COOKIES_SAVE
        self.error_path = sp_config.BR_ERROR_LOG
        self.update_path = sp_config.BR_UPDATE_LOG
        self.order_path = sp_config.BR_ORDER_LOG

        # 兑换汇率
        self.exchange_rate = add_config.BRL_CONVERT_RMB
        # 每个订单附加费用
        self.order_add_fee = add_config.ORDER_ADD_FEE
        self.product_add_fee = add_config.PRODUCT_ADD_FEE

        self.country = 'BRL'
        self.shop_id = add_config.BR_SHOP_ID

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

def down_img(url, filepath, headers, t_num):
    """下载图片函数 如报错 回回调两次 还是出错则保存 有图片名的空白文件"""
    try:
        t_num += 1
        print('第 {} 次下载中...'.format(str(t_num)))
        i_request = requests.get(url, headers=headers)
        with open(filepath, 'wb') as f:
            f.write(i_request.content)
    except:
        if t_num < 4:
            time.sleep(2.5)
            down_img(url, filepath, headers, t_num)
        else:
            # raise Exception
            with open(filepath, 'wb') as f:
                f.write(b'')
            print(filepath+' 4 次下载后 还是出错')

# def format_file_path(goodsku):
#     """根据商品sku，设置默认图片名"""
#
#     # 替换sku中的+号
#     good_sku = goodsku.replace('+', '_')
#     # 根据sku_id中的'#','_'，设置默认图片路径
#     if '#' in good_sku:
#         # 提取编号 '主spu号_#03' 去除'#' 保存默认图片路径为'主spu号_03.jpg
#         file_path = re.match(r'(.*#[^._]*)', good_sku).group(0).replace('#', '')
#     elif '_' in good_sku:
#         # 除去最后一个'_'和它之后的字符
#         file_path = re.match(r'(.*)_', good_sku).group(1)
#     else:
#         file_path = good_sku[:-1]
#
#     return file_path


country_type_dict = {
    'MYR': MYGoodsSpider,
    'PHP': PhGoodsSpider,
    'THB': ThGoodsSpider,
    'IDR': IdGoodsSpider,
    'SGD': SgGoodsSpider,
    'BRL': BrGoodsSpider,
    'TWD': TwGoodsSpider,
    'VND': VnGoodsSpider,
}

if __name__ == '__main__':
    ss = PhGoodsSpider()
    # ss.get_goods()
    ss.get_order()
