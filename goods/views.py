import json
import time


from django.db.models import Q
from django.db import transaction
from django.shortcuts import render
from django.http import JsonResponse
from django.views.generic.base import View
from dwebsocket.decorators import accept_websocket, require_websocket

from goods.models import GoodsSKU, Goods
from action_logging.action_log import logger
from spider.goods_spider import country_type_dict
from spider.auto_follow.shopfuns import country_shop_dict

# from order.models import OrderInfo
# from spider.goods_spider import get_cookies_from_file
# from spider import sp_config
# from decimal import Decimal
# import requests


# from spider.import_excel import ImportExcel

class GoodsListView(View):
    """商品列表页"""

    def get(self, request):
        """ 渲染商品列表页 提供静态页面
            各国商品数量
        """
        my_goods = Goods.objects.filter(goodssku__my_sale_price__gt=0).distinct().count()
        ph_goods = Goods.objects.filter(goodssku__ph_sale_price__gt=0).distinct().count()
        th_goods = Goods.objects.filter(goodssku__th_sale_price__gt=0).distinct().count()
        return render(request, 'goods_list.html', locals())

    def post(self, request):
        """ajax 请求数据"""

        # 第一条数据的起始位置
        start = int(request.POST.get('start', 0))
        # 每页显示的长度，默认为10
        length = int(request.POST.get('length', 10))
        # 计数器，确保ajax从服务器返回是对应的
        draw = int(request.POST.get('draw', 1))
        # 全局搜索条件
        new_search = request.POST.get('search[value]', '')

        # 排序列的序号 默认开启两列排序 肯定有值
        order_id_f = request.POST.get('order[0][column]', '')
        # 排序列名
        order_name_f = request.POST.get('columns[{0}][data]'.format(order_id_f), '')
        # 排序类型
        order_type_f = '-' if request.POST.get('order[0][dir]', '') == 'desc' else ''

        # 取第二个排序列 取列名、排序类型
        order_id_s = request.POST.get('order[1][column]', '')
        order_name_s = request.POST.get('columns[{0}][data]'.format(order_id_s), '')
        order_type_s = '-' if request.POST.get('order[1][dir]', '') == 'desc' else ''

        all_goods = GoodsSKU.objects.filter(status=1)
        # 总商品数
        recordsTotal = all_goods.count()

        # 模糊查询，包含内容就查询
        if new_search:
            all_goods = all_goods.filter(Q(sku_id__contains=new_search) |
                                         Q(goods__spu_id__contains=new_search))
        # 过滤后 商品数
        recordsFiltered = all_goods.count()

        # 两列排序
        if order_name_f and order_name_s:
            all_goods = all_goods.order_by(order_type_f + order_name_f,
                                           order_type_s + order_name_s)
        # 单列排序
        elif order_name_f:
            all_goods = all_goods.order_by(order_type_f + order_name_f)

        # 第一页数据
        page_obj = all_goods[start:(start + length)]
        # 转成字典
        page_data = [good.good_dict() for good in page_obj]

        result = {
            'draw': draw,
            'recordsTotal': recordsTotal,
            'recordsFiltered': recordsFiltered,
            'data': page_data
        }

        return JsonResponse(result)


class ModifyGoodsView(View):

    def get(self, request):
        """商品上下架修改"""
        sku_id = request.GET.get('sku_id', '')
        res_type = request.GET.get('res_type', '')

        if not all([sku_id, res_type]):
            return JsonResponse({'status': 1, 'msg': '参数不完整'})

        if res_type == 'down':
            good_status = 0
            msg = '下架成功'
        elif res_type == 'up':
            good_status = 1
            msg = '成功上架'
        else:
            return JsonResponse({'status': 2, 'msg': '参数错误'})

        try:
            good_obj = GoodsSKU.objects.get(sku_id=sku_id)
        except:
            return JsonResponse({'status': 3, 'msg': '没找到这个商品'})

        good_obj.status = good_status
        good_obj.save()

        logger.info('状态操作：%s > %s', sku_id, msg)

        return JsonResponse({'status': 0, 'msg': msg})

    def post(self, request):
        """商品URL、重量、进价、货架号修改"""
        update_data = json.loads(request.POST.get('update_data', ''))

        if 'spu_id' in update_data:
            try:
                good_spu = Goods.objects.get(spu_id=update_data['spu_id'])
            except Goods.DoesNotExist:
                return JsonResponse({'status': 2, 'msg': '商品SPU错误'})

            del update_data['spu_id']
            try:
                good_spu.set_attr(update_data)
                good_spu.save()
            except:
                return JsonResponse({'status': 3, 'msg': '商品更新错误'})

            if 'buy_price' in update_data:
                GoodsSKU.objects.filter(goods=good_spu).update(buy_price=update_data['buy_price'])

                logger.info('进价修改：%s 进货价更新为 %s', good_spu, update_data['buy_price'])

            if 'shelf' in update_data:
                GoodsSKU.objects.filter(goods=good_spu).update(shelf=update_data['shelf'])

            return JsonResponse({'status': 0, 'msg': '更新成功'})

        elif 'sku_id' in update_data:
            skuId = update_data['sku_id']
            try:
                goodsku_obj = GoodsSKU.objects.get(sku_id=skuId)
            except:
                return JsonResponse({'status': 5, 'msg': '商品sku不存在'})

            del update_data['sku_id']

            try:
                old_value = getattr(goodsku_obj, list(update_data)[0])
                goodsku_obj.set_attr(update_data)
                goodsku_obj.save()
                # 单个字典取值 key list(dict)[0] value list(dict.values())[0]
                logger.info('单品修改：%s < %s > 从 %s 变更为 %s', skuId, list(update_data)[0],
                            old_value, list(update_data.values())[0])
            except:
                return JsonResponse({'status': 3, 'msg': '商品更新错误'})

            return JsonResponse({'status': 0, 'msg': '更新成功'})

        return JsonResponse({'status': 1, 'msg': '无更新参数'})


class SingleGoodsListView(View):
    """单个spu商品 sku列表"""

    def get(self, request):
        sku_id = request.GET.get('sku_id', '')
        search_type = request.GET.get('search_type', '')

        if not sku_id:
            return JsonResponse({'status': 1, 'msg': '无参数'})

        good_obj = GoodsSKU.objects.filter(sku_id=sku_id, status=1)
        if not good_obj:
            return JsonResponse({'status': 3, 'msg': '没找到这个商品'})

        if search_type == 'all':
            good_obj = GoodsSKU.objects.filter(goods=good_obj[0].goods, status=1).order_by('sku_id')

        res_data = good_obj.values('sku_id', 'desc', 'sales', 'stock', 'image')

        return JsonResponse({'status': 0, 'msg': list(res_data)})


class GoodsSpiderView(View):
    """爬取商品信息"""

    def get(self, request):
        # data_type: True 为取全部数据，False 为取第一页数据
        data_type = request.GET.get('data_type', '')
        good_type = request.GET.get('good_type', '')
        country_type = request.GET.get('country_type', '')
        goodsku = request.GET.get('goodsku', '')

        if not country_type:
            return JsonResponse({'status': 1, 'msg': '无国家参数'})

        # 判断国家 调用不同的类
        if country_type in country_type_dict:
            shopee = country_type_dict[country_type]()
        else:
            return JsonResponse({'status': 2, 'msg': '国家参数错误'})

        # 判断单个还是多个商品
        if good_type == 'many':
            shopee.get_goods(is_all=bool(data_type))
            return JsonResponse({'status': 0, 'msg': str(shopee.num) + ' 条商品更新'})
        elif good_type == 'single' and goodsku:
            msg = shopee.get_single_good(goodsku)
            return JsonResponse({'status': 0, 'msg': msg})
        else:
            return JsonResponse({'status': 3, 'msg': '商品或SKU参数错误'})


class AutoFollowView(View):
    """自动关注、取关"""
    def get(self, request):
        return render(request, 'shopeefans.html')

    def post(self, request):
        request_dict = json.loads(request.POST.get('request_dict', ''))
        # print(request_dict)
        if not request_dict:
            return JsonResponse({'status': 1, 'msg': '参数错误'})

        if request_dict['shop_country'] in country_shop_dict:
            shopeefans = country_shop_dict[request_dict['shop_country']]()
        else:
            return JsonResponse({'status': 2, 'msg': '国家类型参数错误'})

        if request_dict['follow_type'] == 'unfollow':
            res_msg = shopeefans.batch_unfollow(request_dict['people_num'])
            return JsonResponse({'status': 0, 'msg': res_msg})

        elif request_dict['follow_type'] == 'follow':
            # 没有店铺ID 或 店铺ID不全部是数字组成
            if not request_dict['shop_id'] or not request_dict['shop_id'].isdigit():
                return JsonResponse({'status': 3, 'msg': '店铺ID错误'})
            res_msg = shopeefans.batch_follow(request_dict['shop_id'], request_dict['people_num'])
            return JsonResponse({'status': 0, 'msg': res_msg})
        else:
            return JsonResponse({'status': 4, 'msg': '关注or取关参数错误'})


# @accept_websocket
# def auto_follow(request):
#     if request.is_websocket():
#         req_dict = request.websocket.wait()
#         req_dict = json.loads(req_dict.decode('utf-8'))
#         # print(req_dict)
#
#         # 判断国家 调用不同的类
#         if req_dict['shop_country'] in country_shop_dict:
#             shopeefans = country_shop_dict[req_dict['shop_country']](request.websocket)
#         else:
#             request.websocket.send('> 国家类型参数错误'.encode('utf-8'))
#             time.sleep(0.5)
#             return
#
#         if req_dict['follow_type'] == 'unfollow':
#             shopeefans.batch_unfollow(req_dict['people_num'])
#         elif req_dict['follow_type'] == 'follow':
#             # 没有店铺ID 或 店铺ID不全部是数字组成
#             if not req_dict['shop_id'] or not req_dict['shop_id'].isdigit():
#                 request.websocket.send('> 店铺ID错误'.encode('utf-8'))
#                 return
#             shopeefans.batch_follow(req_dict['shop_id'], req_dict['people_num'])
#         else:
#             request.websocket.send('> 关注or取关参数错误'.encode('utf-8'))
#             time.sleep(0.5)
#
#     else:
#         return render(request, 'shopeefans.html')
#
#
# @require_websocket  # 只允许websocket连接
# def each_auto_follow(request):
#     req_dict = request.websocket.wait()
#     req_dict = req_dict.decode('utf-8')
#
#     if not req_dict.isdigit():
#         request.websocket.send('> 人数必须是正整数'.encode('utf-8'))
#         time.sleep(0.5)
#         return
#
#     # 循环每个国家 取关操作
#     for shopeefan_obj in country_shop_dict.values():
#         shopeefans = shopeefan_obj(request.websocket)
#         shopeefans.batch_unfollow(req_dict)


# class ImportExcelView(View):
#     """手动更新利润"""
#     def get(self, request):
#         all_order = OrderInfo.objects.filter(order_country='PHP', order_status=3, order_time__gt='191217')
#         url = 'https://seller.ph.shopee.cn/api/v3/order/get_one_order/'
#         headers = {'user-agent': sp_config.USER_AGENT}
#         cookies = get_cookies_from_file(sp_config.PH_COOKIES_SAVE)
#         req_data = {
#             'SPC_CDS': cookies['SPC_CDS'],
#             'SPC_CDS_VER': 2}
#         num = 0
#         for order_info in all_order:
#             req_data['order_id'] = order_info.order_shopeeid
#
#             response = requests.get(url, params=req_data,
#                                     cookies=cookies, headers=headers)
#
#             if response.status_code == 200:
#                 one_order_data = json.loads(response.content.decode())
#             else:
#                 one_order_data = ''
#                 print('*'*50, order_info.order_shopeeid)
#                 continue
#
#             one_order_data = one_order_data['data']
#
#             # 商品总价
#             total_price = 0
#             for order_good_info in one_order_data['order_items']:
#                 total_price += float(order_good_info['order_price']) * order_good_info['amount']
#
#             # 判断是否是卖家的优惠卷
#             voucher_price = one_order_data['voucher_price'] if one_order_data['voucher_absorbed_by_seller'] else '0.00'
#
#             if one_order_data['currency'] == 'PHP':
#                 # 菲律宾 实际运费 舍去0.5 小数
#                 actual_shipping_fee = Decimal(one_order_data['actual_shipping_fee']).quantize(Decimal(0.0),
#                                                                                               rounding='ROUND_DOWN')
#
#             else:
#                 actual_shipping_fee = Decimal(one_order_data['actual_shipping_fee'])
#             # 买家支付运费
#             shipping_fee = one_order_data['shipping_fee']
#             # 平台运费回扣
#             shipping_rebate = one_order_data['shipping_rebate']
#
#             # 平台佣金
#             comm_fee = one_order_data['comm_fee']
#             # 平台服务费
#             seller_service_fee = one_order_data['seller_service_fee']
#             # 手续费
#             card_txn_fee = one_order_data['card_txn_fee_info']['card_txn_fee']
#
#             # 买家或平台支付的运费
#             our_shipping_fee = Decimal(shipping_rebate) + Decimal(shipping_fee)
#             # 如果平台和买家都没有付运费 则判定 平台补贴默认的运费
#             if shipping_fee == '0.00' and shipping_rebate == '0.00':
#                 our_shipping_fee = Decimal(one_order_data['origin_shipping_fee'])
#
#             # 没出货，无实际运费时 不计算订单收入
#             order_income = '0.00'
#             if actual_shipping_fee != 0.00:
#                 # 订单收入
#                 order_income = Decimal(total_price) + our_shipping_fee \
#                                - actual_shipping_fee - Decimal(card_txn_fee) - Decimal(voucher_price) \
#                                - Decimal(comm_fee) - Decimal(seller_service_fee)
#
#             order_cost = 0  # 订单成本(人民币）
#
#             for good_obj in order_info.ordergoods_set.all():
#                 good_buy_price = good_obj.sku_good.buy_price
#                 # 进价低于6元的商品  不附加国内运杂费
#                 if good_buy_price < 6:
#                     order_cost += good_buy_price * good_obj.count
#                 # 商品的成本  每件商品进价上加一元 国内运杂费
#                 else:
#                     order_cost += (good_buy_price + Decimal('1')) * good_obj.count
#             # 汇率要变
#             order_profit = Decimal(order_income) * Decimal('0.127') - Decimal(order_cost) - Decimal('1')
#
#             order_info.order_profit = order_profit
#             order_info.order_income = order_income
#             order_info.save()
#
#             num += 1
#             print(num, order_info.order_shopeeid)
#
#         return JsonResponse({'msg': 'ok'})
