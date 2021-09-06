# Generated by Django 2.0.12 on 2021-07-02 23:53

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('order', '0023_orderinfo_order_package_num'),
    ]

    operations = [
        migrations.AddField(
            model_name='orderinfo',
            name='order_bind_status',
            field=models.BooleanField(default=0, verbose_name='订单绑定状态'),
        ),
        migrations.AddField(
            model_name='orderinfo',
            name='order_send_status',
            field=models.BooleanField(default=0, verbose_name='订单出货状态'),
        ),
    ]