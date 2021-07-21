# Generated by Django 2.0.12 on 2021-07-16 23:43

from django.db import migrations, models
import goods.models


class Migration(migrations.Migration):

    dependencies = [
        ('goods', '0006_goodssku_status'),
    ]

    operations = [
        migrations.AddField(
            model_name='goods',
            name='image',
            field=models.ImageField(blank=True, default='default.jpg', null=True, upload_to=goods.models.good_spu_path, verbose_name='商品主图'),
        ),
        migrations.AlterField(
            model_name='goodssku',
            name='image',
            field=models.ImageField(blank=True, default='default.jpg', null=True, upload_to=goods.models.good_sku_path, verbose_name='商品图片'),
        ),
    ]
