import xadmin
from xadmin import views

from goods.models import Goods, GoodsSKU
from order.models import OrderGoods, OrderInfo, PurchaseOrder, PurchaseGoods


class GoodsXadmin(object):
    list_display = ['spu_id', 'get_image', 'get_link', 'get_sku_url', 'max_weight']
    search_fields = ['goodssku__sku_id', 'spu_id']
    list_filter = ['spu_id']

    list_editable = ['max_weight']
    # def get_goodssku(self, obj):
    #     sku_query = obj.goodssku_set.all()
    #     return str(['%s:%s:%s'%(i.sku_id, i.buy_price, i.stock) for i in sku_query])

    # get_goodssku.short_description = '子SKU'
    #
    # class GoodsSKUInline:
    #     model = GoodsSKU
    #     extra = 0
    #
    # inlines = [GoodsSKUInline]


class GoodsSKUXadmin(object):
    list_display = ['sku_id', 'goods', 'desc', 'get_image', 'buy_price', 'stock', 'sales', 'status']
    search_fields = ['sku_id']
    list_filter = ['sales', 'status']
    ordering = ('-create_time',)

    # show_detail_fields = ['sku_id']
    list_editable = ['buy_price', 'stock', 'status']


class BaseSetting(object):
    """主题配置"""
    enable_themes = True
    use_bootswatch = True


class GlobalSetting(object):
    #页头
    site_title = 'Shopee后台管理'
    #页脚
    site_footer = '跨境电商'
    # 左侧样式
    # menu_style = 'accordion'

    # 设置models的全局图标
    global_search_models = [Goods, GoodsSKU]
    global_models_icon = {
        Goods: "glyphicon glyphicon-gift", GoodsSKU: "fa fa-cloud"
    }

    # 设置导航栏顺序
    def get_site_menu(self):
        return ({'title': '商品管理', 'menus': (
                {'title': '商品spu信息', 'url': self.get_model_url(Goods, 'changelist')},
                {'title': '商品sku信息', 'url': self.get_model_url(GoodsSKU, 'changelist')},
                {'title': '订单信息', 'url': self.get_model_url(OrderInfo, 'changelist')},
                {'title': '订单商品', 'url': self.get_model_url(OrderGoods, 'changelist')},
                {'title': '采购信息', 'url': self.get_model_url(PurchaseOrder, 'changelist')},
                {'title': '采购商品', 'url': self.get_model_url(PurchaseGoods, 'changelist')},
            )},)

xadmin.site.register(Goods, GoodsXadmin)
xadmin.site.register(GoodsSKU, GoodsSKUXadmin)

xadmin.site.register(views.BaseAdminView, BaseSetting)
xadmin.site.register(views.CommAdminView, GlobalSetting)
