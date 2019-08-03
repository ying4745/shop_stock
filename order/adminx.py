import xadmin

from order.models import OrderInfo, OrderGoods, PurchaseOrder, PurchaseGoods


class OrderGoodsInline():
    model = OrderGoods
    extra = 0
    style = 'table'


class OrderInfoXadmin(object):
    list_display = ['order_id', 'customer', 'customer_info',
                    'receiver', 'order_income', 'order_profit',
                    'order_status', 'order_country', 'create_time']
    search_fields = ['order_id', 'order_country']
    list_filter = ['order_status', 'order_country','create_time']
    # 点击排序
    date_hierarchy = ('create_time',)
    ordering = ('-order_id',)
    list_editable = ['order_profit', 'order_status']

    inlines = [OrderGoodsInline]


class OrderGoodsXadmin(object):
    list_display = ['order', 'sku_good', 'get_good_desc',
                    'get_image', 'count', 'price',
                    'get_good_stock', 'create_time']
    search_fields = ['order__order_id', 'sku_good__sku_id']
    list_filter = ['order__order_id', 'sku_good__sku_id']
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
