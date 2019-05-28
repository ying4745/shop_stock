# Generated by Django 2.0.12 on 2019-05-06 10:21

from django.db import migrations, models
import django.db.models.deletion
import goods.models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='Goods',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('create_time', models.DateTimeField(auto_now_add=True, verbose_name='创建事件')),
                ('update_time', models.DateTimeField(auto_now=True, verbose_name='更新时间')),
                ('name', models.CharField(default='未填写', max_length=64, verbose_name='商品名称')),
                ('spu_id', models.CharField(max_length=16, unique=True, verbose_name='主SPU号')),
                ('g_url', models.URLField(blank=True, null=True, verbose_name='商品链接')),
                ('max_weight', models.IntegerField(default=0, verbose_name='最大实重')),
            ],
            options={
                'verbose_name': '商品SPU',
                'verbose_name_plural': '商品SPU',
                'db_table': 'goods_spu',
            },
        ),
        migrations.CreateModel(
            name='GoodsSKU',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('create_time', models.DateTimeField(auto_now_add=True, verbose_name='创建事件')),
                ('update_time', models.DateTimeField(auto_now=True, verbose_name='更新时间')),
                ('sku_id', models.CharField(max_length=16, unique=True, verbose_name='商品SKU号')),
                ('desc', models.CharField(max_length=32, verbose_name='商品规格')),
                ('buy_price', models.DecimalField(decimal_places=2, default=0, max_digits=10, verbose_name='进货价')),
                ('my_sale_price', models.DecimalField(decimal_places=2, default=0, max_digits=10, verbose_name='马来西亚售价')),
                ('ph_sale_price', models.DecimalField(decimal_places=2, default=0, max_digits=10, verbose_name='菲律宾售价')),
                ('stock', models.IntegerField(default=0, verbose_name='库存')),
                ('sales', models.IntegerField(default=0, verbose_name='销量')),
                ('image', models.ImageField(blank=True, null=True, upload_to=goods.models.good_spu_path, verbose_name='商品图片')),
                ('goods', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='goods.Goods', verbose_name='商品SPU')),
            ],
            options={
                'verbose_name': '商品SKU',
                'verbose_name_plural': '商品SKU',
                'db_table': 'goods_sku',
            },
        ),
    ]