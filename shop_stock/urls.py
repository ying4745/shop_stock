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

from goods.views import GoodsListView, GoodsSpiderView
from order.views import OrderListView, IndexView, OrderSpiderView, \
    BuyGoodsView, ModifyPurchaseView, StockView

urlpatterns = [
    # path('admin/', admin.site.urls),
    path('xadmin/', xadmin.site.urls),
    path('goods/list/', GoodsListView.as_view(), name='goods_list'),  # 所有商品列表
    path('order/list/', OrderListView.as_view(), name='order_list'),  # 完成订单列表

    path('get/product/', GoodsSpiderView.as_view(), name='get_product'),  # 抓取商品信息
    path('get/order/', OrderSpiderView.as_view(), name='get_order'),  # 抓取订单信息

    path('buy/product/', BuyGoodsView.as_view(), name='buy_product'),  # 生成, 获取采购单
    path('modify/purchase/', ModifyPurchaseView.as_view(), name='modify_purchase'),  # 采购单修改
    path('finished/purchase/', StockView.as_view(), name='finished_purchase'),  # 入库

    path('', IndexView.as_view())  # 主页 出货管理

] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
