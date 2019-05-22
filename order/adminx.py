import xadmin

from order.models import OrderInfo, OrderGoods


class OrderInfoXadmin(object):
    list_display = ['order_id', 'customer', 'customer_info',
                    'receiver', 'order_income', 'order_profit',
                    'order_status', 'order_country', 'create_time']
    search_fields = ['order_id', 'order_country']
    list_filter = ['order_status', 'order_country','create_time']
    # 点击排序
    date_hierarchy = ('create_time',)
    ordering = ('-order_id',)

    class OrderGoodsInline:
        model = OrderGoods
        extra = 0

    inlines = [OrderGoodsInline]


class OrderGoodsXadmin(object):
    list_display = ['order', 'sku_good', 'get_good_desc',
                    'get_image', 'count', 'price',
                    'get_good_stock', 'create_time']
    search_fields = ['order', 'sku_good']
    list_filter = ['order', 'sku_good']
    date_hierarchy = ('create_time', 'order')
    ordering = ('order',)

    def get_good_stock(self, obj):
        return obj.sku_good.stock

    def get_good_desc(self, obj):
        return obj.sku_good.desc

    get_good_stock.short_description = '库存'
    get_good_desc.short_description = '规格'


xadmin.site.register(OrderInfo, OrderInfoXadmin)
xadmin.site.register(OrderGoods, OrderGoodsXadmin)
