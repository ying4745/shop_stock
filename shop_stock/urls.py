"""shop_stock URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/2.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
# from django.contrib import admin
import xadmin
from django.urls import path
from django.conf import settings
from django.conf.urls.static import static

from goods.views import AutoFollowView
from goods.views import GoodsListView, GoodsSpiderView, ModifyGoodsView, SingleGoodsListView
from order.views import OrderListView, IndexView, OrderSpiderView, BuyGoodsView, ModifyPurchaseView
from order.views import StockView, StockListView, OrderChartsView, OrderInfoView, OrderWaybillView
from order.views import BaleOrderView, CheckIncomeView, CheckOrderView, ShippingOrderView
from order.views import OrderShipStatusView, BindOrderView, PackingListView

urlpatterns = [
    # path('admin/', admin.site.urls),
    path('xadmin/', xadmin.site.urls),

    path('goods/list/', GoodsListView.as_view(), name='goods_list'),                # 商品列表 get页面 post数据
    path('modify/good/', ModifyGoodsView.as_view(), name='modify_good'),            # 修改商品数据
    path('goodsku/list/', SingleGoodsListView.as_view(), name='goodsku_list'),      # 单个spu商品 sku列表

    path('order/list/', OrderListView.as_view(), name='order_list'),                # 已完成订单列表 get页面 post数据
    path('order/info/', OrderInfoView.as_view(), name='order_info'),                # 已完成订单详情 修改订单备注信息
    path('order/charts/data', OrderChartsView.as_view(), name='charts_data'),       # 订单统计 图表数据

    path('buy/product/', BuyGoodsView.as_view(), name='buy_product'),               # 采购单列表 创建
    path('modify/purchase/', ModifyPurchaseView.as_view(), name='modify_purchase'), # 采购单修改

    path('finished/purchase/', StockView.as_view(), name='finished_purchase'),      # 入库操作
    path('purchase/list/', StockListView.as_view(), name='purchase_list'),          # 入库单列表 get页面 post数据

    path('get/product/', GoodsSpiderView.as_view(), name='get_product'),            # 抓取商品信息
    path('get/order/', OrderSpiderView.as_view(), name='get_order'),                # 抓取订单信息

    path('order/waybill/', OrderWaybillView.as_view(), name='order_waybill'),       # 生成运单号

    path('bale/order/', BaleOrderView.as_view(), name='bale_order'),                # 打包订单 打印运单号
    path('check/order/', CheckOrderView.as_view(), name='check_order'),             # 每天送货订单确认
    path('shipping/order/', ShippingOrderView.as_view(), name='shipping_order'),    # 快递发往仓库中订单列表
    path('order/status/', OrderShipStatusView.as_view(), name='order_ship_status'), # 订单的出货状态转变
    path('bind/order/', BindOrderView.as_view(), name='bind_order'),                # 首公里 绑定订单
    path('packing/order/list/', PackingListView.as_view(), name='pack_list'),       # 打包清单

    path('check/income/', CheckIncomeView.as_view(), name='check_income'),          # 核对收款

    # path('auto/follow/', auto_follow, name='auto_follow'),                          # 刷粉操作
    # path('eachshop/autofollow/', each_auto_follow, name='each_auto_follow'),        # 每个站点 自动刷粉操作
    path('auto/follow/', AutoFollowView.as_view(), name='auto_follow'),             # 刷粉操作

    # path('import/excel/', ImportExcelView.as_view(), name='import_excel'),         # 填充数据

    path('', IndexView.as_view(), name='index')                                     # 主页 发货管理

] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

