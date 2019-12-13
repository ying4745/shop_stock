# Generated by Django 2.0.12 on 2019-12-14 00:13

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('order', '0019_auto_20191129_0057'),
    ]

    operations = [
        migrations.AlterField(
            model_name='orderinfo',
            name='order_status',
            field=models.SmallIntegerField(choices=[(1, '待发货'), (2, '待打包'), (3, '已完成'), (4, '已处理'), (5, '已打单'), (6, '已拨款'), (7, '异常款'), (8, '丢失件'), (9, '待核对')], default=1, verbose_name='订单状态'),
        ),
    ]
