import json
import string
import random
import datetime

from django.db.models import F
from django.db import transaction
from django.shortcuts import render
from django.http import JsonResponse
from django.views.generic.base import View

from goods.models import GoodsSKU
from spider.goods_spider import PhGoodsSpider, MYGoodsSpiper
from order.models import OrderInfo, PurchaseOrder, PurchaseGoods


class IndexView(View):
    """主页 订单管理 发货 采购"""

    def get(self, request):
        """获取待出货订单 待出货订单和已完成订单总数"""
        orders = OrderInfo.objects.filter(order_status=1).order_by('-order_time')

        unfinished_orders = orders.count()
        shipping_orders = OrderInfo.objects.filter(order_status=2).count()
        finished_orders = OrderInfo.objects.filter(order_status=3).count()

        out_of_stock, orders_goods = out_of_stock_good_list(orders)

        return render(request, 'index.html', {'orders': orders,
                                              'out_of_stock': out_of_stock,
                                              'unfinished_orders': unfinished_orders,
                                              'shipping_orders': shipping_orders,
                                              'finished_orders': finished_orders})

    # 开启事务提交
    @transaction.atomic
    def post(self, request):
        """发货：更改订单状态 库存"""
        orders_list = json.loads(request.POST.get('data_list', ''))

        if not orders_list:
            return JsonResponse({'status': 3, 'msg': '请选中订单'})

        # 根据订单 计算是否有缺货商品
        orders_obj = OrderInfo.objects.filter(order_id__in=orders_list)

        out_of_stock, orders_goods = out_of_stock_good_list(orders_obj)
        out_of_num = len(out_of_stock)
        if out_of_num > 0:
            return JsonResponse({'status': 1, 'msg': str(out_of_num) + ' 件商品缺货'})

        # 事务保存点
        save_id = transaction.savepoint()

        # 无缺货商品 更新库存
        for good_sku in orders_goods.keys():
            try:
                GoodsSKU.objects.filter(sku_id=good_sku).update(
                    stock=F('stock') - orders_goods[good_sku])
            except:
                # 更新有错误 则事务回滚到保存点
                transaction.savepoint_rollback(save_id)
                return JsonResponse({'status': 2, 'msg': '库存错误'})

        # 提交事务
        transaction.savepoint_commit(save_id)
        order_num = orders_obj.update(order_status=2)

        return JsonResponse({'status': 0, 'msg': str(order_num) + ' 个订单发货成功'})


class OrderListView(View):
    """订单列表页"""

    def get(self, request):
        """获取已发货、已完成清单"""
        order_type = request.GET.get('order_type', '')

        if order_type == 'shipping':
            orders = OrderInfo.objects.filter(order_status=2).order_by('-order_time')
        else:
            orders = OrderInfo.objects.filter(order_status=3).order_by('-order_time')

        for order in orders:
            amount = 0
            for good in order.ordergoods_set.all():
                amount += good.count
            order.goods_num = amount

        return render(request, 'order_list.html', {'orders': orders})


class BuyGoodsView(View):
    """采购单生成、获取"""

    def get(self, request):
        purchase_type = request.GET.get('purchase_type', '')

        if purchase_type == 'buy':
            purchase_orders = PurchaseOrder.objects.filter(pur_status=1).order_by('-create_time')
        else:
            purchase_orders = PurchaseOrder.objects.filter(pur_status=2).order_by('-create_time')

        return render(request, 'purchase_list.html', {'purchase_orders': purchase_orders,
                                                      'purchase_type': purchase_type})

    @transaction.atomic
    def post(self, request):
        """生成采购单"""
        goods_list = json.loads(request.POST.get('data_list'))

        if not goods_list:
            return JsonResponse({'status': 3, 'msg': '请选中商品'})

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
        """渲染 修改页面"""
        purchase_id = request.GET.get('pur_id', '')

        pur_obj = PurchaseOrder.objects.filter(purchase_id=purchase_id)

        if pur_obj:
            pur_obj = pur_obj[0]

        return render(request, 'purchase_form.html', {'pur_obj': pur_obj})

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

        pur_obj = pur_order[0]
        pur_good_list = []

        p_save = transaction.savepoint()

        # 新增或更新商品
        if pur_dict['purchase_goods']:
            for good in pur_dict['purchase_goods']:
                pur_good_list.append(good['sku_id'])
                try:
                    sku_good = GoodsSKU.objects.get(sku_id=good['sku_id'])
                    PurchaseGoods.objects.update_or_create(purchase=pur_obj,
                                                           sku_good=sku_good,
                                                           defaults={'count': good['count']})
                except Exception as e:
                    # print(e)
                    transaction.savepoint_rollback(p_save)
                    return JsonResponse({'status': 3, 'msg': '订单商品更新失败'})

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
        purchase_id = request.GET.get('purchase_id', '')

        if not purchase_id:
            return JsonResponse({'status': 1, 'msg': 'id参数错误'})

        pur_order = PurchaseOrder.objects.filter(purchase_id=purchase_id)
        if not pur_order:
            return JsonResponse({'status': 2, 'msg': '没找到该订单'})

        s_save = transaction.savepoint()

        pur_obj = pur_order[0]
        for pur_good in pur_obj.purchasegoods_set.all():
            try:
                GoodsSKU.objects.filter(sku_id=pur_good.sku_good.sku_id).update(
                    stock=F('stock') + pur_good.count)
            except:
                transaction.savepoint_rollback(s_save)
                return JsonResponse({'status': 3, 'msg': '更新失败'})

        transaction.savepoint_commit(s_save)
        pur_order.update(pur_status=2)

        return JsonResponse({'status': 0, 'msg': '更新成功'})


class OrderSpiderView(View):
    """爬取订单信息"""

    def get(self, request):
        data_type = request.GET.get('data_type', '')
        country_type = request.GET.get('country_type', '')
        if not data_type or not country_type:
            return JsonResponse({'status': 1, 'msg': '参数错误'})

        # 判断国家
        if country_type == 'MY':
            shopee = MYGoodsSpiper()
        elif country_type == 'PH':
            shopee = PhGoodsSpider()
        else:
            return JsonResponse({'status': 1, 'msg': '参数错误'})
        shopee.get_order(data_type)

        return JsonResponse({'status': 0, 'msg': str(shopee.num) + ' 条订单更新'})


def out_of_stock_good_list(orders_obj):
    """ 计算订单中每一种商品的总件数
        返回： 商品数量大于库存的商品sku_id列表
              商品sku_id、数量 组成的字典
    """
    # 统计订单商品数量  粗糙待优化代码
    orders_goods = {}
    for order in orders_obj:
        for order_good in order.ordergoods_set.all():
            if order_good.sku_good.sku_id not in orders_goods.keys():
                orders_goods[order_good.sku_good.sku_id] = order_good.count
            else:
                orders_goods[order_good.sku_good.sku_id] += order_good.count
    # 缺货商品sku列表
    out_of_stock = []
    for orders_good in orders_goods.keys():
        good_stock = GoodsSKU.objects.get(sku_id=orders_good).stock
        if orders_goods[orders_good] > good_stock:
            out_of_stock.append(orders_good)

    return out_of_stock, orders_goods
