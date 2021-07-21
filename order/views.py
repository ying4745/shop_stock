import json
import string
import random
import datetime

from django.urls import reverse
from django.db import transaction
from django.http import JsonResponse
from django.db.models import F, Q, Count
from django.views.generic.base import View
from django.shortcuts import render, redirect

from goods.models import GoodsSKU
from spider.goods_spider import country_type_dict
from order.models import OrderInfo, PurchaseOrder, PurchaseGoods
from action_logging.action_log import logger


class IndexView(View):
    """主页 订单管理 发货"""

    def get(self, request):
        """获取待出货订单 待出货订单和已完成订单总数"""
        orders = OrderInfo.objects.filter(Q(order_status=1) | Q(order_status=4)).order_by('-order_id')

        unfinished_orders = orders.count()
        bale_orders = OrderInfo.objects.filter(Q(order_status=2) | Q(order_status=5)).count()
        shipping_orders = OrderInfo.objects.filter(order_status=10).count()
        no_check_orders = OrderInfo.objects.filter(order_status=9).count()
        finished_orders = OrderInfo.objects.filter(Q(order_status=3) | Q(order_status=6) |
                                                   Q(order_status=7) | Q(order_status=8)).count()

        my_order = orders.filter(order_country='MYR')
        my_orders, dw_my_orders = orders_num_or_dealwith(my_order)

        ph_order = orders.filter(order_country='PHP')
        ph_orders, dw_ph_orders = orders_num_or_dealwith(ph_order)

        th_order = orders.filter(order_country='THB')
        th_orders, dw_th_orders = orders_num_or_dealwith(th_order)

        id_order = orders.filter(order_country='IDR')
        id_orders, dw_id_orders = orders_num_or_dealwith(id_order)

        sg_order = orders.filter(order_country='SGD')
        sg_orders, dw_sg_orders = orders_num_or_dealwith(sg_order)

        br_order = orders.filter(order_country='BRL')
        br_orders, dw_br_orders = orders_num_or_dealwith(br_order)

        tw_order = orders.filter(order_country='TWD')
        tw_orders, dw_tw_orders = orders_num_or_dealwith(tw_order)

        vn_order = orders.filter(order_country='VND')
        vn_orders, dw_vn_orders = orders_num_or_dealwith(vn_order)

        out_of_stock = out_of_stock_good_list(stats_ordergood_count(orders))

        return render(request, 'index.html', locals())

    # 开启事务提交
    @transaction.atomic
    def post(self, request):
        """发货：更改订单状态 库存"""
        orders_list = json.loads(request.POST.get('data_list', ''))

        if not orders_list:
            return JsonResponse({'status': 3, 'msg': '无订单参数'})

        orders_obj = OrderInfo.objects.filter(order_id__in=orders_list)

        # 判断要发货订单  是否已发货   检测订单状态是否为待打包 防止页面没刷新 重复提交
        if orders_obj.filter(order_status=2).exists():
            return JsonResponse({'status': 4, 'msg': '有订单已发货，请稍后查看'})

        # 根据订单 计算是否有缺货商品
        orders_goods = stats_ordergood_count(orders_obj)
        out_of_stock = out_of_stock_good_list(orders_goods)
        out_of_num = len(out_of_stock)
        if out_of_num > 0:
            return JsonResponse({'status': 1, 'msg': str(out_of_num) + ' 件商品缺货'})

        un_orders = orders_obj.filter(order_status=1)
        orders_dict = waybill_order_dict(un_orders)
        # 未处理的订单 提交到平台生成运单号
        msg = make_waybill(orders_dict)
        if msg:
            return JsonResponse({'status': 5, 'msg': msg})

        # 事务保存点
        save_id = transaction.savepoint()

        # 无缺货商品 更新库存 销量
        for good_sku in orders_goods.keys():
            try:
                GoodsSKU.objects.filter(sku_id=good_sku).update(
                    stock=F('stock') - orders_goods[good_sku],
                    sales=F('sales') + orders_goods[good_sku])
            except:
                # 更新有错误 则事务回滚到保存点
                transaction.savepoint_rollback(save_id)
                logger.warning('发货错误：%s 发货异常 前面数据回滚', good_sku)
                return JsonResponse({'status': 2, 'msg': '库存错误'})
            else:
                logger.info('发货操作：%s 库存减少了 %s', good_sku, orders_goods[good_sku])

        # 提交事务
        transaction.savepoint_commit(save_id)
        order_num = orders_obj.update(order_status=2)

        return JsonResponse({'status': 0, 'msg': str(order_num) + ' 个订单发货成功'})


class BaleOrderView(View):
    """待打包订单"""

    def get(self, request):
        """待打包列表"""
        bale_orders = OrderInfo.objects.filter(Q(order_status=2) | Q(order_status=5)).order_by('-order_id')
        bale_orders_count = bale_orders.count()
        return render(request, 'bale_order.html', {'orders': bale_orders,
                                                   'bale_orders_count': bale_orders_count})

    def post(self, request):
        """处理下载、打印请求"""
        orders_dict = json.loads(request.POST.get('data_dict', ''))
        if not orders_dict:
            return JsonResponse({'status': 1, 'msg': '参数错误'})

        # 参数里 国家没在这些国家里 则提示出错
        if not set(orders_dict.keys()).issubset({'MYR','PHP','THB','IDR','SGD','BRL','TWD','VND'}):
            return JsonResponse({'status': 2, 'msg': '国家参数错误'})

        # print("结束", orders_dict)
        # 结果消息
        result_msg = ''
        for k in orders_dict.keys():
            shopee = country_type_dict[k]()
            # order_list_str = list(map(lambda x: int(x), orders_dict[k]))
            msg = shopee.down_order_waybill(orders_dict[k])
            if msg:
                result_msg += k + ' >> ' + msg + '<br>'
                continue
                # return JsonResponse({'status': 2, 'msg': msg})

            OrderInfo.objects.filter(order_country=k,
                                     order_shopeeid__in=orders_dict[k],
                                     order_status=2).update(order_status=5)
        if result_msg:
            return JsonResponse({'status': 0, 'msg': result_msg})

        return JsonResponse({'status': 0, 'msg': '打单完成'})


class PackingListView(View):
    """ 打包清单 点货清单"""

    def get(self, request):
        shopeeid_lists = json.loads(request.GET.get('shopeeid_lists', ''))

        order_obj = OrderInfo.objects.filter(order_shopeeid__in=shopeeid_lists)
        ordergood_dict = stats_ordergood_count(order_obj)
        goods_obj = GoodsSKU.objects.filter(sku_id__in=ordergood_dict.keys()).values('sku_id', 'desc', 'image', 'stock')
        for good in goods_obj:
            good['count'] = ordergood_dict[good['sku_id']]

        return render(request, 'pack_list.html', {'goods_dict': goods_obj})


class OrderShipStatusView(View):
    """
        订单的出货状态
    """
    def post(self, request):
        """订单出货 未出货状态转变"""
        data = json.loads(request.POST.get('data_dict'))
        # print(data)

        if not data.get('order_id', '') or not data.get('request_type', ''):
            return JsonResponse({'status': 1, 'msg': '参数不全'})

        if data['request_type'] == 'bale':
            order_ship_status = 1
        elif data['request_type'] == 'cal':
            order_ship_status = 0
        else:
            return JsonResponse({'status': 2, 'msg': '请求类型参数错误'})

        update_result = OrderInfo.objects.filter(order_id=data['order_id']).update(order_send_status=order_ship_status)
        if update_result:
            return JsonResponse({'status': 0, 'msg': '更新成功'})

        return JsonResponse({'status': 3, 'msg': '出货状态改变出错'})


class BindOrderView(View):
    """首公里  绑定订单"""

    def get(self, request):
        waybill_num = request.GET.get('waybill_num', '')
        if not waybill_num:
            return JsonResponse({'status': 1, 'msg': '无查询快递运单号'})
        # 查找已打单 未绑定的订单 是哪几个国家的
        all_country = OrderInfo.objects.filter(order_status=5, order_bind_status=0) \
            .values_list('order_country', flat=True).distinct()
        # 循环 每个国家去查询一下
        result_msg = ''
        for country_d in all_country:
            shopee = country_type_dict[country_d]()
            msg = shopee.query_bind_order(waybill_num)
            if msg:
                result_msg += country_d + ' >> ' + msg + '<br>'
                continue

        if result_msg:
            return JsonResponse({'status': 0, 'msg': result_msg})

        return JsonResponse({'status': 0, 'msg': '查询完成'})

    def post(self, request):
        """绑定订单"""
        request_data = json.loads(request.POST.get('data_dict'))

        if not request_data.get('waybill_num', ''):
            return JsonResponse({'status': 1, 'msg': '快递运单号参数缺失'})

        if not request_data.get('express', ''):
            return JsonResponse({'status': 2, 'msg': '快递公司参数缺失'})

        request_country_params = []
        if request_data['bind_type'] == 'send_order':
            all_country = OrderInfo.objects.filter(order_status=5, order_bind_status=0, order_send_status=1)\
                .values_list('order_country', flat=True).distinct()
            for country_d in all_country:
                all_order_params = OrderInfo.objects.filter(order_status=5, order_country=country_d,
                                                            order_bind_status=0, order_send_status=1) \
                    .values(as_order_id=F('order_shopeeid'), package_number=F('order_package_num'),
                            sls_tn=F('order_waybill_num'))
                # order_id 存在与模型中  所以取别名后 再来修改回去
                for x in all_order_params:
                    x['order_id'] = int(x.pop('as_order_id'))
                request_country_params.append({
                    'bind_country': country_d,
                    'package_list': all_order_params
                })
        elif request_data['bind_type'] == 'all_order':
            all_country = OrderInfo.objects.filter(order_status=5, order_bind_status=0).values_list(
                'order_country', flat=True).distinct()
            for country_d in all_country:
                all_order_params = OrderInfo.objects.filter(order_status=5, order_country=country_d, order_bind_status=0) \
                    .values(as_order_id=F('order_shopeeid'), package_number=F('order_package_num'),
                            sls_tn=F('order_waybill_num'))
                # order_id 存在与模型中  所以取别名后 再来修改回去
                for x in all_order_params:
                    x['order_id'] = int(x.pop('as_order_id'))
                request_country_params.append({
                    'bind_country': country_d,
                    'package_list': all_order_params
                })
        elif request_data['bind_type'] == 'check_order':
            if not request_data['check_order']:
                return JsonResponse({'status': 3, 'msg': '选中订单参数错误'})
            for country_d in request_data['check_order'].keys():
                all_order_params = OrderInfo.objects.filter(
                    order_shopeeid__in=request_data['check_order'][country_d], order_bind_status=0).values(
                    as_order_id=F('order_shopeeid'), package_number=F('order_package_num'),
                            sls_tn=F('order_waybill_num'))
                # order_id 存在与模型中  所以取别名后 再来修改回去
                for x in all_order_params:
                    x['order_id'] = int(x.pop('as_order_id'))
                request_country_params.append({
                    'bind_country': country_d,
                    'package_list': all_order_params
                })
        else:
            return JsonResponse({'status': 2, 'msg': '绑定类型参数错误'})

        result_msg = ''
        for sing_country in request_country_params:
            shopee = country_type_dict[sing_country['bind_country']]()
            msg = shopee.bind_order(request_data['express'], request_data['waybill_num'], sing_country['package_list'])
            if msg:
                result_msg += sing_country['bind_country'] + ' >> ' + msg + '<br>'
                continue

        if result_msg:
            return JsonResponse({'status': 0, 'msg': result_msg})

        return JsonResponse({'status': 0, 'msg': '绑定成功'})


class ShippingOrderView(View):
    """已被快递揽收订单"""

    def get(self, request):
        """快递揽收订单列表"""
        shipping_orders = OrderInfo.objects.filter(order_status=10).order_by('-order_id')
        shipping_orders_count = shipping_orders.count()
        return render(request, 'shipping_order.html', {'orders': shipping_orders,
                                                   'shipping_orders_count': shipping_orders_count})


class CheckOrderView(View):
    """每天送货订单 确认页"""

    def get(self, request):
        """待确认列表"""
        check_orders = OrderInfo.objects.filter(order_status=9).order_by('-order_id')
        check_orders_count = check_orders.count()
        return render(request, 'check_order.html', {'orders': check_orders,
                                                   'check_orders_count': check_orders_count})

    def post(self, request):
        order_num = OrderInfo.objects.filter(order_status=9).update(order_status=3)
        return JsonResponse({'status': 0, 'msg': '{} 个订单确认'.format(order_num)})


class OrderListView(View):
    """订单列表页"""
    COUNTRY = {
        '马来西亚': 'MYR',
        '菲律宾': 'PHP',
        '泰国': 'THB',
        '印尼': 'IDR',
        '新加坡': 'SGD',
        '巴西': 'BRL',
        '台湾': 'TWD',
        '越南': 'VND'
    }

    def get(self, request):
        """提供订单静态页面"""
        return render(request, 'order_list.html')

    def post(self, request):
        """ajax 请求订单数据"""

        # 第一条数据的起始位置
        start = int(request.POST.get('start', 0))
        # 每页显示的长度，默认为10
        length = int(request.POST.get('length', 10))
        # 计数器，确保ajax从服务器返回是对应的
        draw = int(request.POST.get('draw', 1))

        # 全局搜索条件
        new_search = request.POST.get('search[value]', '')
        # 特定列搜索条件 第三列
        col_search = request.POST.get('columns[2][search][value]', '')

        # 排序列的序号
        order_id_f = request.POST.get('order[0][column]', '')
        # 排序列名
        order_name_f = request.POST.get('columns[{0}][data]'.format(order_id_f), '')
        # 排序类型
        order_type_f = '-' if request.POST.get('order[0][dir]', '') == 'desc' else ''

        # 日期范围参数
        min_date = request.POST.get('min_date', '')
        max_date = request.POST.get('max_date', '')

        all_orders = OrderInfo.objects.filter(Q(order_status=3) | Q(order_status=6) |
                                              Q(order_status=7) | Q(order_status=8))
        # 总订单数
        recordsTotal = all_orders.count()

        # 模糊查询，包含内容就查询
        if new_search:
            all_orders = all_orders.filter(Q(order_id__contains=new_search) |
                                           Q(order_time__contains=new_search) |
                                           Q(order_shopeeid__contains=new_search) |
                                           Q(order_pay_time__contains=new_search))

        # 单独列参数 查询
        if col_search:
            all_orders = all_orders.filter(order_country__contains=self.COUNTRY[col_search])

        # 日期范围 查询
        if min_date and max_date:
            all_orders = all_orders.filter(order_time__gte=min_date,
                                           order_time__lte=max_date)

        # 过滤后 商品数
        recordsFiltered = all_orders.count()

        # 单列排序
        if order_name_f:
            all_orders = all_orders.order_by(order_type_f + order_name_f)

        # 第一页数据
        page_obj = all_orders[start:(start + length)]
        # 转成字典
        page_data = [order.order_dict() for order in page_obj]

        result = {
            'draw': draw,
            'recordsTotal': recordsTotal,
            'recordsFiltered': recordsFiltered,
            'data': page_data
        }

        return JsonResponse(result)


class OrderInfoView(View):
    """订单详情视图，订单备注修改"""

    def get(self, request):
        order_id = request.GET.get('order_id', '')

        order_obj = OrderInfo.objects.filter(order_id=order_id)

        if order_obj:
            order_obj = order_obj[0]

        return render(request, 'order_info.html', {'order_obj': order_obj})

    def post(self, request):
        data = json.loads(request.POST.get('update_data', ''))

        if not data.get('order_id', ''):
            return JsonResponse({'status': 1, 'msg': '参数错误'})

        try:
            OrderInfo.objects.filter(order_id=data['order_id']).update(order_desc=data['order_desc'])
        except:
            return JsonResponse({'status': 2, 'msg': '修改失败'})

        logger.info('备注修改：%s 的备注更新为 %s', data['order_id'], data['order_desc'])

        return JsonResponse({'status': 0, 'msg': '修改成功'})


class OrderChartsView(View):
    """订单图表数据"""

    def get(self, request):
        # 默认过去30天的订单
        default_start_date = (datetime.date.today() - datetime.timedelta(days=30)).strftime('%y%m%d')
        default_end_date = datetime.date.today().strftime('%y%m%d')

        start_date_str = request.GET.get('start_date', default_start_date)
        end_date_str = request.GET.get('end_date', default_end_date)

        date_list = order_date_list(start_date_str, end_date_str)

        all_orders = OrderInfo.objects.filter(order_time__gte=start_date_str, order_time__lte=end_date_str)

        my_value_list = []
        ph_value_list = []
        th_value_list = []
        id_value_list = []
        sg_value_list = []
        br_value_list = []
        tw_value_list = []
        vn_value_list = []
        if all_orders:
            my_orders = all_orders.filter(Q(order_status=3) | Q(order_status=6) | Q(order_status=7) |
                                          Q(order_status=8), order_country='MYR').order_by('order_time')
            ph_orders = all_orders.filter(Q(order_status=3) | Q(order_status=6) | Q(order_status=7) |
                                          Q(order_status=8), order_country='PHP').order_by('order_time')
            th_orders = all_orders.filter(Q(order_status=3) | Q(order_status=6) | Q(order_status=7) |
                                          Q(order_status=8), order_country='THB').order_by('order_time')
            id_orders = all_orders.filter(Q(order_status=3) | Q(order_status=6) | Q(order_status=7) |
                                          Q(order_status=8), order_country='IDR').order_by('order_time')
            sg_orders = all_orders.filter(Q(order_status=3) | Q(order_status=6) | Q(order_status=7) |
                                          Q(order_status=8), order_country='SGD').order_by('order_time')
            br_orders = all_orders.filter(Q(order_status=3) | Q(order_status=6) | Q(order_status=7) |
                                          Q(order_status=8), order_country='BRL').order_by('order_time')
            tw_orders = all_orders.filter(Q(order_status=3) | Q(order_status=6) | Q(order_status=7) |
                                          Q(order_status=8), order_country='TWD').order_by('order_time')
            vn_orders = all_orders.filter(Q(order_status=3) | Q(order_status=6) | Q(order_status=7) |
                                          Q(order_status=8), order_country='VND').order_by('order_time')

            my_value_list = order_value_list(date_list, my_orders)
            ph_value_list = order_value_list(date_list, ph_orders)
            th_value_list = order_value_list(date_list, th_orders)
            id_value_list = order_value_list(date_list, id_orders)
            sg_value_list = order_value_list(date_list, sg_orders)
            br_value_list = order_value_list(date_list, br_orders)
            tw_value_list = order_value_list(date_list, tw_orders)
            vn_value_list = order_value_list(date_list, vn_orders)

        # 日期 去掉年份
        date_list = list(map(lambda x: x[2:], date_list))

        charts_data = {
            'my_value_list': my_value_list,
            'ph_value_list': ph_value_list,
            'th_value_list': th_value_list,
            'id_value_list': id_value_list,
            'sg_value_list': sg_value_list,
            'br_value_list': br_value_list,
            'tw_value_list': tw_value_list,
            'vn_value_list': vn_value_list,
            'date_list': date_list
        }

        return JsonResponse(charts_data)


class BuyGoodsView(View):
    """采购单列表，创建采购单"""

    def get(self, request):

        purchase_orders = PurchaseOrder.objects.filter(pur_status=1).order_by('-create_time')
        stock_orders_num = PurchaseOrder.objects.filter(pur_status=2).count()
        # 采购中商品
        pur_goods_list = purchase_orders.values_list('purchasegoods__sku_good__sku_id', flat=True)

        orders = OrderInfo.objects.filter(Q(order_status=1) | Q(order_status=4))
        orders_goods = stats_ordergood_count(orders)
        out_of_stock = out_of_stock_good_list(orders_goods)

        # 还未采购的缺货商品
        un_pur_goods_list = list(set(out_of_stock).difference(set(pur_goods_list)))
        un_pur_goods = GoodsSKU.objects.filter(sku_id__in=un_pur_goods_list).order_by('sku_id')

        return render(request, 'purchase_list.html', {'purchase_orders': purchase_orders,
                                                      'stock_orders_num': stock_orders_num,
                                                      'orders_goods': orders_goods,
                                                      'un_pur_goods': un_pur_goods})

    @transaction.atomic
    def post(self, request):
        """生成采购单"""
        goods_list = json.loads(request.POST.get('data_list'))

        if not goods_list:
            return JsonResponse({'status': 3, 'msg': '无商品参数'})

        # 采购单号 当前时间加四位随机字母
        purchase_id = datetime.datetime.now().strftime('%y%m%d%H%M%S') + \
                      ''.join(random.sample(string.ascii_letters, 4))

        c_save = transaction.savepoint()

        purchase_obj = PurchaseOrder.objects.create(purchase_id=purchase_id)
        for good in goods_list:
            try:
                good_obj = GoodsSKU.objects.get(sku_id=good)
                PurchaseGoods.objects.create(purchase=purchase_obj,
                                             sku_good=good_obj,
                                             price=good_obj.buy_price)
            except:
                transaction.savepoint_rollback(c_save)
                JsonResponse({'status': 1, 'msg': '采购单创建失败'})

        transaction.savepoint_commit(c_save)

        return JsonResponse({'status': 0, 'msg': '采购单创建成功'})


class ModifyPurchaseView(View):
    """采购单修改"""

    def get(self, request):
        """渲染模态框中 修改页面"""
        purchase_id = request.GET.get('pur_id', '')

        pur_obj = PurchaseOrder.objects.filter(purchase_id=purchase_id)

        if pur_obj:
            pur_obj = pur_obj[0]

        orders = OrderInfo.objects.filter(Q(order_status=1) | Q(order_status=4))
        orders_goods = stats_ordergood_count(orders)

        return render(request, 'purchase_form.html', {'pur_obj': pur_obj,
                                                      'pur_goods_dict': orders_goods})

    @transaction.atomic
    def post(self, request):
        pur_dict = json.loads(request.POST.get('data_dict'))

        pur_order = PurchaseOrder.objects.filter(purchase_id=pur_dict['purchase_id'])
        if len(pur_order) == 0:
            return JsonResponse({'status': 1, 'msg': '采购单号错误'})
        try:
            pur_order.update(total_price=pur_dict['purchase_price'],
                             desc=pur_dict['purchase_desc'])
        except:
            return JsonResponse({'status': 2, 'msg': '采购单参数错误'})

        if not pur_dict.get('purchase_goods', ''):
            return JsonResponse({'status': 3, 'msg': '采购单商品错误'})

        # 新增或更新商品
        pur_obj = pur_order[0]
        pur_good_list = []

        p_save = transaction.savepoint()

        for good in pur_dict['purchase_goods']:
            pur_good_list.append(good['sku_id'])
            try:
                sku_good = GoodsSKU.objects.get(sku_id=good['sku_id'])
                PurchaseGoods.objects.update_or_create(purchase=pur_obj,
                                                       sku_good=sku_good,
                                                       defaults={'count': good['count'],
                                                                 'price': sku_good.buy_price})
            except Exception as e:
                # print(e)
                transaction.savepoint_rollback(p_save)
                return JsonResponse({'status': 4, 'msg': '失败：' + str(e)})

        transaction.savepoint_commit(p_save)

        # 删除新商品里没有的商品
        for pur_good in pur_obj.purchasegoods_set.all():
            if pur_good.sku_good.sku_id not in pur_good_list:
                pur_good.delete()

        return JsonResponse({'status': 0, 'msg': '采购单更新成功'})


class StockView(View):
    """入库"""

    @transaction.atomic
    def get(self, request):
        """采购单 入库"""
        purchase_id = request.GET.get('purchase_id', '')

        if not purchase_id:
            return JsonResponse({'status': 1, 'msg': 'id参数错误'})

        pur_order = PurchaseOrder.objects.filter(purchase_id=purchase_id)
        if not pur_order:
            return JsonResponse({'status': 2, 'msg': '没找到该订单'})

        s_save = transaction.savepoint()

        pur_obj = pur_order[0]
        for pur_good in pur_obj.purchasegoods_set.all():
            # 已入库的商品 不操作
            if pur_good.status:
                continue
            skuId = pur_good.sku_good.sku_id
            try:
                GoodsSKU.objects.filter(sku_id=skuId).update(stock=F('stock') + pur_good.count)
                pur_good.status = 1
                pur_good.save()
            except:
                transaction.savepoint_rollback(s_save)
                logger.warning('入库错误：%s 入库异常 前面数据回滚', skuId)
                return JsonResponse({'status': 3, 'msg': '更新失败'})
            else:
                logger.info('商品入库：入库单<%s>中 %s 库存增加了 %s', purchase_id, skuId, pur_good.count)

        transaction.savepoint_commit(s_save)
        pur_order.update(pur_status=2)

        return JsonResponse({'status': 0, 'msg': '更新成功'})

    def post(self, request):
        """采购商品单项 入库"""
        data = json.loads(request.POST.get('data_dict'))
        # print(data)

        if not data.get('pur_id', '') or not data.get('sku_id', ''):
            return JsonResponse({'status': 1, 'msg': '参数错误'})

        skugood_obj = GoodsSKU.objects.filter(sku_id=data['sku_id'])
        if not skugood_obj:
            return JsonResponse({'status': 2, 'msg': '没找到该商品信息'})

        pur_good = PurchaseGoods.objects.filter(purchase__purchase_id=data['pur_id'],
                                                sku_good__sku_id=data['sku_id'],
                                                status=0)
        if not pur_good:
            return JsonResponse({'status': 3, 'msg': '没找到这条记录'})

        good_num = pur_good[0].count
        try:
            skugood_obj.update(stock=F('stock') + good_num)
            pur_good.update(status=1)
        except:
            return JsonResponse({'status': 4, 'msg': '更新失败'})
        else:
            logger.info('单品入库：入库单<%s>中 %s 库存增加了 %s', data['pur_id'], data['sku_id'], good_num)

        return JsonResponse({'status': 0, 'msg': '更新成功'})


class StockListView(View):
    """入库单列表"""

    def get(self, request):
        """入库单列表静态页面"""
        return render(request, 'stock_list.html')

    def post(self, request):
        """ajax 请求入库单数据"""

        # 第一条数据的起始位置
        start = int(request.POST.get('start', 0))
        # 每页显示的长度，默认为10
        length = int(request.POST.get('length', 10))
        # 计数器，确保ajax从服务器返回是对应的
        draw = int(request.POST.get('draw', 1))

        # 全局搜索条件
        new_search = request.POST.get('search[value]', '')

        # 排序列的序号
        order_id_f = request.POST.get('order[0][column]', '')
        # 排序列名
        order_name_f = request.POST.get('columns[{0}][data]'.format(order_id_f), '')
        # 排序类型
        order_type_f = '-' if request.POST.get('order[0][dir]', '') == 'desc' else ''

        pur_orders = PurchaseOrder.objects.filter(pur_status=2)
        all_stock = PurchaseGoods.objects.filter(purchase__in=pur_orders)
        # 总订单数
        recordsTotal = all_stock.count()

        # 模糊查询，包含内容就查询
        if new_search:
            all_stock = all_stock.filter(sku_good__sku_id__contains=new_search)

        # 过滤后 商品数
        recordsFiltered = all_stock.count()

        # 单列排序
        if order_name_f:
            all_stock = all_stock.order_by(order_type_f + order_name_f)

        # 第一页数据
        page_obj = all_stock[start:(start + length)]

        page_data = []
        # 查询后的数据 特殊处理
        if new_search:
            for pur_good in page_obj:
                pur_good_dict = pur_good.stock_dict()
                pur_good_dict['order_good_count'] = 1
                pur_good_dict['row_id'] = 1
                page_data.append(pur_good_dict)

        # 转成字典列表
        # page_data = [pur_good.stock_dict() for pur_good in page_obj]

        # 合并行 处理数据 增加一个订单共多少商品即商品序号
        else:
            pur_good_index = {}
            for pur_good in page_obj:
                pur_good_dict = pur_good.stock_dict()
                if pur_good_dict['purchase'] not in pur_good_index:
                    pur_good_index[pur_good_dict['purchase']] = 1
                    pur_good_dict['row_id'] = 1
                else:
                    pur_good_index[pur_good_dict['purchase']] += 1
                    pur_good_dict['row_id'] = pur_good_index[pur_good_dict['purchase']]
                page_data.append(pur_good_dict)

            for single_data in page_data:
                single_data['order_good_count'] = pur_good_index[single_data['purchase']]

        result = {
            'draw': draw,
            'recordsTotal': recordsTotal,
            'recordsFiltered': recordsFiltered,
            'data': page_data
        }

        return JsonResponse(result)


class OrderWaybillView(View):
    """生成运单号"""

    def post(self, request):
        orders_dict = json.loads(request.POST.get('data_list'))

        if not orders_dict:
            return JsonResponse({'status': 3, 'msg': '无订单ID参数'})
        # print(orders_dict)
        msg = make_waybill(orders_dict)

        return msg if msg else JsonResponse({'status': 0, 'msg': '成功生成运单号'})


class OrderSpiderView(View):
    """爬取订单信息"""

    def get(self, request):
        data_type = request.GET.get('data_type', '')
        country_type = request.GET.get('country_type', '')
        order_type = request.GET.get('order_type', '')
        order_id = request.GET.get('order_id', '')
        if not country_type:
            return JsonResponse({'status': 1, 'msg': '无参数'})

        # 判断国家 调用不同的类
        if country_type in country_type_dict:
            shopee = country_type_dict[country_type]()
        else:
            return JsonResponse({'status': 2, 'msg': '国家参数错误'})

        if order_type == 'many':
            # ['toship', 'shipping', 'completed', 'cancelled']
            # 新物流 URL  类型为to_process
            if data_type in ['toship','to_process']:
                # 请求处理中的列表 获取新的订单
                status_num, msg = shopee.get_order(data_type)
                if status_num:
                    return JsonResponse({'status': 5, 'msg': msg})
                else:
                    return JsonResponse({'status': 0, 'msg': msg})
            elif data_type == 'shipping':
                # 根据shopid 请求订单收入信息 更新订单 根据有无实际运费判断
                status_num, msg = shopee.update_order()
                return JsonResponse({'status': 0, 'msg': msg})
            elif data_type == 'check':
                status_num, msg = shopee.check_order_status()
                return JsonResponse({'status': 0, 'msg': msg})
            else:
                return JsonResponse({'status': 4, 'msg': '订单状态参数错误'})
        elif order_type == 'single' and order_id:
            msg = shopee.get_single_order(order_id)
            return JsonResponse({'status': 0, 'msg': msg})
        else:
            return JsonResponse({'status': 3, 'msg': '订单号参数错误'})


class CheckIncomeView(View):
    """核对收款"""
    def get(self, request):
        return render(request, 'check_income.html')

    def post(self, request):
        request_dict = json.loads(request.POST.get('request_dict', ''))
        # print(request_dict)
        if not request_dict:
            return JsonResponse({'status': 1, 'msg': '参数错误'})

        if request_dict['shop_country'] in country_type_dict:
            shopee = country_type_dict[request_dict['shop_country']]()
        else:
            return JsonResponse({'status': 2, 'msg': '国家类型参数错误'})

        shopee.get_income_order(1, request_dict['date_min'], request_dict['date_max'])
        return JsonResponse({'status': 0, 'msg': shopee.check_msg})


def stats_ordergood_count(orders_obj):
    """ 计算订单中每一种商品的总件数
        返回： 商品sku_id、数量 组成的字典
    """
    # 统计订单商品数量
    orders_goods_list = orders_obj.values_list('ordergoods__sku_good__sku_id', 'ordergoods__count')
    orders_goods = {}
    for g in orders_goods_list:
        if g[0]:
            if g[0] not in orders_goods.keys():
                orders_goods[g[0]] = g[1]
            else:
                orders_goods[g[0]] += g[1]

    return orders_goods


def out_of_stock_good_list(goods_dict):
    """ 根据统计的各订单商品数量  检查缺货商品
        返回： 商品的skuID 列表
    """
    out_of_stock = []
    for skuid in goods_dict.keys():
        if GoodsSKU.objects.filter(sku_id=skuid,stock__lt=goods_dict[skuid]).exists():
            out_of_stock.append(skuid)

    return out_of_stock


def order_date_list(start_date_str, end_date_str):
    """订单日期列表
    :return 每一天日期列表"""
    start_date = datetime.datetime.strptime(start_date_str, '%y%m%d')
    end_date = datetime.datetime.strptime(end_date_str, '%y%m%d')
    date_list = []
    while start_date <= end_date:
        date_str = start_date.strftime('%y%m%d')
        date_list.append(date_str)
        start_date += datetime.timedelta(days=1)
    return date_list


def order_value_list(date_list, orders_obj):
    """
    每日订单数量
    :param date_list: 每天日期列表
    :param order_count: 订单统计列表
    :return: 每日订单数量，无则为0
    """
    order_count = orders_obj.values('order_time').annotate(count=Count('order_id'))

    value_list = []
    k = 0
    for i in date_list:
        if k < len(order_count):
            if order_count[k]['order_time'] == i:
                value_list.append(order_count[k]['count'])
                k += 1
            else:
                value_list.append(0)

        else:
            value_list.append(0)

    return value_list


def waybill_order_dict(orders):
    """根据订单分国家 统计出待处理的订单列表"""
    orders_dict = {}
    for order in orders:
        if order.order_country not in orders_dict:
            orders_dict[order.order_country] = [order.order_shopeeid]
        else:
            orders_dict[order.order_country].append(order.order_shopeeid)

    return orders_dict


def make_waybill(orders_dict):
    # 申请运单号
    res_msg = ''
    for k in orders_dict.keys():
        success_order_list = []
        shopee = country_type_dict[k]()
        for v in orders_dict[k]:
            msg = shopee.make_order_waybill(v)
            if msg:
                res_msg += v + ' >> ' + msg + '<br>'
                # return JsonResponse({'status': 2, 'msg': msg})
            else:
                success_order_list.append(v)

        OrderInfo.objects.filter(order_country=k,
                                 order_shopeeid__in=success_order_list,
                                 order_status=1).update(order_status=4)
    if res_msg:
        return  res_msg
    return ''


def orders_num_or_dealwith(order_obj):
    """返回订单数 和其中已处理的订单数"""
    order_num = order_obj.count()
    dw_order_num = order_obj.filter(order_status=4).count()
    return order_num, dw_order_num
