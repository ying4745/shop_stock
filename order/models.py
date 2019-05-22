from django.db import models

from db.base_model import BaseModel


class OrderInfo(BaseModel):
    """订单详情"""
    ORDER_STATUS_CHOICES = (
        (1, '待发货'),
        (2, '已发货'),
        (3, '已完成'),
    )
    ORDER_COUNTRY_CHOICES = (
        ('MYR', '马来西亚'),
        ('PHP', '菲律宾'),
        ('THB', '泰国'),
    )

    order_id = models.CharField(max_length=16, unique=True, verbose_name='订单编号')
    order_time = models.CharField(max_length=16, verbose_name='订单时间')
    customer = models.CharField(max_length=32, verbose_name='客户名字')
    receiver = models.CharField(max_length=32, default='默认', verbose_name='收件人')
    customer_info = models.CharField(max_length=32, default='100%/0', verbose_name='客户收货率')
    total_price = models.DecimalField(max_digits=10, decimal_places=2, verbose_name='商品总额')
    order_income = models.DecimalField(max_digits=10, decimal_places=2,
                                       default=0, verbose_name='订单收入')
    order_profit = models.DecimalField(max_digits=10, decimal_places=2,
                                       default=0, verbose_name='订单利润')
    order_status = models.SmallIntegerField(choices=ORDER_STATUS_CHOICES,
                                            default=1, verbose_name='订单状态')
    order_country = models.CharField(max_length=5, choices=ORDER_COUNTRY_CHOICES,
                                     default='MYR', verbose_name='订单国家')

    @property
    def customer_grade(self):
        return int(self.customer_info.split('%')[0])

    class Meta:
        db_table = 'order_info'
        verbose_name = '订单详情'
        verbose_name_plural = verbose_name

    def __str__(self):
        return self.order_id


class OrderGoods(BaseModel):
    """订单商品"""
    order = models.ForeignKey('OrderInfo', on_delete=models.CASCADE,
                              verbose_name='订单')
    sku_good = models.ForeignKey('goods.GoodsSKU', on_delete=models.CASCADE,
                                 verbose_name='商品SKU')
    count = models.IntegerField(default=1, verbose_name='商品数量')
    price = models.DecimalField(max_digits=10, decimal_places=2,
                                default=0, verbose_name='商品售价')

    def get_image(self):
        from django.utils.safestring import mark_safe
        # mark_safe后就不会转义
        return mark_safe("<img src='/media/%s' width=80 height=80>" % self.sku_good.image)

    get_image.short_description = "图片"

    class Meta:
        db_table = 'order_goods'
        verbose_name = '订单商品'
        verbose_name_plural = verbose_name


class PurchaseOrder(BaseModel):
    """采购单
    单号使用时间戳表示"""
    PURCHASE_STATUS = (
        (1, '采购中'),
        (2, '已入库'),
    )
    purchase_id = models.CharField(max_length=16, unique=True, verbose_name='采购单号')
    total_price = models.DecimalField(max_digits=10, decimal_places=2,
                                      default=0, verbose_name='采购总额')
    desc = models.CharField(max_length=128, null=False, blank=False, verbose_name='备注')
    pur_status = models.SmallIntegerField(choices=PURCHASE_STATUS,
                                          default=1, verbose_name='采购状态')

    class Meta:
        db_table = 'purchase_order'
        verbose_name = '采购单'
        verbose_name_plural = verbose_name

    def __str__(self):
        return self.purchase_id


class PurchaseGoods(BaseModel):
    """采购单商品"""
    purchase = models.ForeignKey('PurchaseOrder', on_delete=models.CASCADE,
                                 verbose_name='采购单')
    sku_good = models.ForeignKey('goods.GoodsSKU', on_delete=models.CASCADE,
                                 verbose_name='商品SKU')
    count = models.IntegerField(default=1, verbose_name='商品数量')
    price = models.DecimalField(max_digits=10, decimal_places=2,
                                default=0, verbose_name='采购价格')

    class Meta:
        db_table = 'purchase_goods'
        verbose_name = '采购单商品'
        verbose_name_plural = verbose_name
