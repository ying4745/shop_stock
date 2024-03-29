import os
import re

from django.db import models
from django.utils.safestring import mark_safe

from db.base_model import BaseModel


def good_spu_path(instance, filename):
    """默认上传文件路径"""
    return os.path.join(instance.spu_id, filename)


class Goods(BaseModel):
    """主商品信息"""
    name = models.CharField(max_length=64, default='未填写', verbose_name='商品名称')
    spu_id = models.CharField(max_length=64, unique=True, verbose_name='主SPU号')
    g_url = models.CharField(max_length=400, default='', verbose_name='商品链接')
    max_weight = models.IntegerField(default=0, verbose_name='最大实重')
    image = models.ImageField(upload_to=good_spu_path, null=True,
                              blank=True, default='default.jpg', verbose_name='商品主图')

    class Meta:
        ordering = ['spu_id']
        db_table = 'goods_spu'
        verbose_name = '主商品SPU'
        verbose_name_plural = verbose_name

    def __str__(self):
        return self.spu_id

    def get_image(self):
        # mark_safe后就不会转义
        return mark_safe("<img src='/media/%s' width=80 height=80>" % self.image)
    get_image.short_description = "图片"

    def get_link(self):
        link_list = self.g_url.split(';;')
        if link_list[0]:
            link_str = ''
            for idx, l in enumerate(link_list):
                link_str += '<a target="_blank" href="{0}">链接{1}</a></br>'.format(l,str(idx + 1))
            return mark_safe(link_str)
        return mark_safe("<p>无</p>")
    get_link.short_description = "商品链接"

    def get_sku_url(self):
        return mark_safe("<a href='/xadmin/goods/goodssku/?_q_={}'>子SKU</a>".format(self.spu_id))
    get_sku_url.short_description = "跳转"

def good_sku_path(instance, filename):
    """默认上传文件路径"""
    return os.path.join(instance.goods.spu_id, filename)

    # file_suffix = filename.split('.')[1]
    # # 处理文件名
    # good_sku = instance.sku_id.replace('+', '_')
    # if '#' in good_sku:
    #     file_name = re.match(r'(.*#[^._]*)', good_sku).group(0).replace('#', '')
    # elif '_' in instance.sku_id:
    #     file_name = re.match(r'(.*)_', good_sku).group(1)
    # else:
    #     file_name = good_sku[:-1]
    # file_name = file_name + '.' + file_suffix
    #
    # return '{0}/{1}'.format(instance.goods.spu_id, file_name)


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
    image = models.ImageField(upload_to=good_sku_path, null=True,
                              blank=True, default='default.jpg', verbose_name='商品图片')
    status = models.BooleanField(default=1, verbose_name='商品状态')

    class Meta:
        db_table = 'goods_sku'
        verbose_name = '子商品SKU'
        verbose_name_plural = verbose_name

    def __str__(self):
        return self.sku_id

    @property
    def img_url(self):
        if self.image and hasattr(self.image, 'url'):
            return self.image.url
        return ''

    def get_image(self):
        return mark_safe("<img src='/media/%s' width=60 height=60>" % self.image)
    get_image.short_description = "图片"

    def good_dict(self):
        good_data = {
            'goods': self.goods.spu_id,
            'max_weight': self.goods.max_weight,
            'g_url': self.goods.g_url,
            'sku_id': self.sku_id,
            'desc': self.desc,
            'image': self.img_url,
            'buy_price': self.buy_price,
            'stock': self.stock,
            'sales': self.sales,
            'my_sale_price': self.my_sale_price,
            'ph_sale_price': self.ph_sale_price,
            'th_sale_price': self.th_sale_price,
            'shelf': self.shelf
        }
        return good_data
