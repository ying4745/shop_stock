import re

from django.db import models

from db.base_model import BaseModel


class Goods(BaseModel):
    """主商品信息"""
    name = models.CharField(max_length=64, default='未填写', verbose_name='商品名称')
    spu_id = models.CharField(max_length=64, unique=True, verbose_name='主SPU号')
    g_url = models.CharField(max_length=400, default='', verbose_name='商品链接')
    max_weight = models.IntegerField(default=0, verbose_name='最大实重')

    class Meta:
        ordering = ['spu_id']
        db_table = 'goods_spu'
        verbose_name = '主商品SPU'
        verbose_name_plural = verbose_name

    def __str__(self):
        return self.spu_id


def good_spu_path(instance, filename):
    """默认上传文件路径"""
    file_suffix = filename.split('.')[1]
    # 处理文件名
    if '#' in instance.sku_id:
        if re.match(r'(.*#[^.]{2})', instance.sku_id):
            filename = re.match(r'(.*#[^.]{2})', instance.sku_id).group() + '.' + file_suffix
    elif '_' in instance.sku_id:
        filename = re.match(r'(.*)_', instance.sku_id).group(1) + '.' + file_suffix
    return '{0}/{1}'.format(instance.goods.spu_id, filename)


class GoodsSKU(BaseModel):
    """商品SKU 子变体"""
    goods = models.ForeignKey('Goods', on_delete=models.CASCADE, verbose_name='主商品SPU')
    sku_id = models.CharField(max_length=64, unique=True, verbose_name='子商品SKU')
    desc = models.CharField(max_length=64, verbose_name='商品规格')
    buy_price = models.DecimalField(max_digits=10, decimal_places=2,
                                    default=0, verbose_name='进货价')
    my_sale_price = models.DecimalField(max_digits=10, decimal_places=2,
                                        default=0, verbose_name='马来西亚售价')
    ph_sale_price = models.DecimalField(max_digits=10, decimal_places=2,
                                        default=0, verbose_name='菲律宾售价')
    th_sale_price = models.DecimalField(max_digits=10, decimal_places=2,
                                        default=0, verbose_name='泰国售价')
    stock = models.IntegerField(default=0, verbose_name='库存')
    sales = models.IntegerField(default=0, verbose_name='销量')
    shelf = models.CharField(max_length=64, default='001', verbose_name='货架号')
    image = models.ImageField(upload_to=good_spu_path, null=True,
                              blank=True, verbose_name='商品图片')

    class Meta:
        db_table = 'goods_sku'
        verbose_name = '子商品SKU'
        verbose_name_plural = verbose_name

    def __str__(self):
        return self.sku_id

    def get_image(self):
        from django.utils.safestring import mark_safe
        # mark_safe后就不会转义
        return mark_safe("<img src='/media/%s' width=60 height=60>" % self.image)
    get_image.short_description = "图片"

    def good_dict(self):
        good_data = {
            'goods': self.goods.spu_id,
            'max_weight': self.goods.max_weight,
            'g_url': self.goods.g_url,
            'sku_id': self.sku_id,
            'desc': self.desc,
            'image': str(self.image),
            'buy_price': self.buy_price,
            'stock': self.stock,
            'sales': self.sales,
            'my_sale_price': self.my_sale_price,
            'ph_sale_price': self.ph_sale_price,
            'th_sale_price': self.th_sale_price,
            'shelf': self.shelf
        }
        return good_data
