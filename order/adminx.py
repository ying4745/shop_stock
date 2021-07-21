import xadmin

from order.models import OrderInfo, OrderGoods, PurchaseOrder, PurchaseGoods


class OrderGoodsInline():
    model = OrderGoods
    extra = 0
    style = 'table'

# 自定义Action
from xadmin.plugins.actions import BaseActionView

class MyAction(BaseActionView):

     # 这里需要填写三个属性
     # 1. 相当于这个 Action 的唯一标示, 尽量用比较针对性的名字
     action_name = "修改状态"
     # 2. 描述, 出现在 Action 菜单中,
     description = ('更改状态为已打单')
     # 3. 该 Action 所需权限
     model_perm = 'change'

     # 而后实现 do_action 方法
     def do_action(self, queryset):
         # queryset 是包含了已经选择的数据的 queryset
         queryset.update(order_status=5)
         return

class OrderInfoXadmin(object):
    # 制定action
    actions = [MyAction, ]

    list_display = ['order_id', 'order_income', 'order_profit','order_status',
                    'order_bind_status', 'order_country', 'order_shopeeid',
                    'order_package_num', 'order_waybill_num']
    search_fields = ['order_id', 'order_country']
    list_filter = ['order_status', 'order_country','order_bind_status']
    # 点击排序
    date_hierarchy = ('create_time',)
    ordering = ('-order_id',)
    list_editable = ['order_profit', 'order_status', 'order_bind_status']

    inlines = [OrderGoodsInline]


class OrderGoodsXadmin(object):
    list_display = ['order', 'sku_good', 'get_good_desc',
                    'get_image', 'count', 'price',
                    'get_good_stock', 'create_time']
    search_fields = ['order__order_id', 'sku_good__sku_id']
    list_filter = ['order__order_country', 'sku_good__sku_id']
    date_hierarchy = ('create_time', 'order__order_id')
    ordering = ('order__order_id',)

    relfield_style = 'fk_ajax'  # fk-外键 显示样式

    def get_good_stock(self, obj):
        return obj.sku_good.stock

    def get_good_desc(self, obj):
        return obj.sku_good.desc

    get_good_stock.short_description = '库存'
    get_good_desc.short_description = '规格'


class PurchaseOrderXadmin(object):
    list_display = ['purchase_id', 'total_price', 'desc', 'pur_status']
    search_fields = ['purchase_id']
    # 点击排序
    date_hierarchy = ('create_time',)
    ordering = ('-purchase_id',)
    list_editable = ['total_price', 'desc']

    class PurchaseGoodsInline:
        model = PurchaseGoods
        extra = 0
        style = 'table'

    inlines = [PurchaseGoodsInline]


class PurchaseGoodsXadmin(object):
    list_display = ['purchase', 'sku_good', 'count', 'price']
    search_fields = ['purchase__purchase_id', 'sku_good__sku_id']
    list_filter = ['purchase__purchase_id', 'sku_good__sku_id']
    date_hierarchy = ('create_time', 'purchase__purchase_id')
    ordering = ('purchase__purchase_id',)


xadmin.site.register(OrderInfo, OrderInfoXadmin)
xadmin.site.register(OrderGoods, OrderGoodsXadmin)
xadmin.site.register(PurchaseOrder, PurchaseOrderXadmin)
xadmin.site.register(PurchaseGoods, PurchaseGoodsXadmin)
