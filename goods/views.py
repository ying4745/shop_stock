import json

from django.db import transaction
from django.shortcuts import render
from django.http import JsonResponse
from django.views.generic.base import View

from spider.goods_spider import PhGoodsSpider
from goods.models import GoodsSKU, Goods


class GoodsListView(View):
    """商品列表页"""

    def get(self, request):
        goods = GoodsSKU.objects.all()[:60]

        return render(request, 'goods_list.html', {'goods': goods})

    @transaction.atomic
    def post(self, request):
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
                # 事务操作 如一个更新有错误，其他更新都取消
                save_id = transaction.savepoint()
                for good_sku in good_spu.goodssku_set.all():
                    try:
                        good_sku.buy_price = update_data['buy_price']
                        good_sku.save()
                    except:
                        transaction.savepoint_rollback(save_id)
                        return JsonResponse({'status': 4, 'msg': '商品进价更新错误'})
                transaction.savepoint_commit(save_id)

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

        return JsonResponse({'status': 1, 'msg': '无更新目标'})


class GoodsSpiderView(View):
    """爬取商品信息"""

    def get(self, request):
        # data_type: True 为取全部数据，False 为取第一页数据
        data_type = request.GET.get('data_type', '')
        country_type = request.GET.get('country_type', '')

        if not country_type:
            return JsonResponse({'status': 1, 'msg': '参数错误'})

        # 判断国家
        if country_type == 'MY':
            shopee = MYGoodsSpiper()
        elif country_type == 'PH':
            shopee = PhGoodsSpider()
        else:
            return JsonResponse({'status': 1, 'msg': '参数错误'})

        shopee.get_goods(is_all=bool(data_type))

        return JsonResponse({'status': 0, 'msg': str(shopee.num) + ' 条商品更新'})
