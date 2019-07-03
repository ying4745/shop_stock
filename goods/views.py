import json

from django.db.models import Q
from django.db import transaction
from django.shortcuts import render
from django.http import JsonResponse
from django.views.generic.base import View

from spider.goods_spider import country_type_dict
from goods.models import GoodsSKU, Goods
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
            if 'shelf' in update_data:
                GoodsSKU.objects.filter(goods=good_spu).update(shelf=update_data['shelf'])

            return JsonResponse({'status': 0, 'msg': '更新成功'})

        elif 'sku_id' in update_data:

            try:
                goodsku_obj = GoodsSKU.objects.get(sku_id=update_data['sku_id'])
            except:
                return JsonResponse({'status': 5, 'msg': '商品sku不存在'})

            del update_data['sku_id']

            try:
                goodsku_obj.set_attr(update_data)
                goodsku_obj.save()
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
            good_obj = GoodsSKU.objects.filter(goods=good_obj[0].goods, status=1)

        res_data = {}
        for good in good_obj:
            res_data[good.sku_id] = [good.stock, good.image.url]

        return JsonResponse({'status': 0, 'msg': res_data})


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


# class ImportExcelView(View):
#     def get(self, request):
#         excel_obj = ImportExcel()
#         excel_obj.save_data()
#         return JsonResponse({'msg': 'ok'})