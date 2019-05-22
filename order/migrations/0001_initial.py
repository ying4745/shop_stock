# Generated by Django 2.0.12 on 2019-05-06 10:21

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('goods', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='OrderGoods',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('create_time', models.DateTimeField(auto_now_add=True, verbose_name='创建事件')),
                ('update_time', models.DateTimeField(auto_now=True, verbose_name='更新时间')),
                ('count', models.IntegerField(default=1, verbose_name='商品数量')),
                ('price', models.DecimalField(decimal_places=2, default=0, max_digits=10, verbose_name='商品售价')),
            ],
            options={
                'verbose_name': '订单商品',
                'verbose_name_plural': '订单商品',
                'db_table': 'order_goods',
            },
        ),
        migrations.CreateModel(
            name='OrderInfo',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('create_time', models.DateTimeField(auto_now_add=True, verbose_name='创建事件')),
                ('update_time', models.DateTimeField(auto_now=True, verbose_name='更新时间')),
                ('order_id', models.CharField(max_length=16, unique=True, verbose_name='订单编号')),
                ('order_time', models.CharField(max_length=16, verbose_name='订单时间')),
                ('customer', models.CharField(max_length=32, verbose_name='客户名字')),
                ('total_price', models.DecimalField(decimal_places=2, max_digits=10, verbose_name='应付总额')),
                ('order_income', models.DecimalField(decimal_places=2, default=0, max_digits=10, verbose_name='订单收入')),
                ('order_profit', models.DecimalField(decimal_places=2, default=0, max_digits=10, verbose_name='订单利润')),
                ('order_status', models.SmallIntegerField(choices=[(1, '待发货'), (2, '待打单'), (3, '已发货'), (4, '已完成')], default=1, verbose_name='订单状态')),
                ('order_country', models.CharField(choices=[('my', '马来西亚'), ('ph', '菲律宾'), ('th', '泰国')], default='my', max_length=5, verbose_name='订单国家')),
            ],
            options={
                'verbose_name': '订单详情',
                'verbose_name_plural': '订单详情',
                'db_table': 'order_info',
            },
        ),
        migrations.AddField(
            model_name='ordergoods',
            name='order',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='order.OrderInfo', verbose_name='订单'),
        ),
        migrations.AddField(
            model_name='ordergoods',
            name='sku_good',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='goods.GoodsSKU', verbose_name='商品SKU'),
        ),
    ]
