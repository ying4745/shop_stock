#!/usr/bin/python3
# DateTime: 2019/7/14 11:00

import sys
import os

# 将项目根目录加入到系统搜索路径中
# 根据当前文件夹位置拼接路径
sys.path.append(os.path.dirname(os.path.realpath(__file__))+"../")

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "shop_stock.settings")

import django
django.setup()

from order.models import OrderInfo, OrderGoods
from goods.models import GoodsSKU, Goods
from decimal import Decimal



# 手动计算 马来 利润
def compute_profit():
    all_order = OrderInfo.objects.filter(order_country='MYR', order_time__gt='190615')
    for order_info in all_order:
        if str(order_info.order_income) != '0.00':
            order_cost = 0  # 订单成本(人民币）
            for order_good in order_info.ordergoods_set.all():
                # 商品的成本  每件商品进价上加一元 国内运杂费
                order_cost += (order_good.sku_good.buy_price + Decimal(1)) * order_good.count

            order_profit = order_info.order_income * Decimal(1.65) - Decimal(order_cost) - Decimal(2)
            order_info.order_profit = order_profit
            order_info.save()

if __name__ == '__main__':
    compute_profit()