# Generated by Django 2.0.12 on 2019-07-13 14:04

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('order', '0014_auto_20190708_1746'),
    ]

    operations = [
        migrations.AlterField(
            model_name='orderinfo',
            name='order_desc',
            field=models.CharField(default='', max_length=128, verbose_name='订单备注'),
        ),
        migrations.AlterField(
            model_name='purchaseorder',
            name='desc',
            field=models.CharField(default='', max_length=128, verbose_name='备注'),
        ),
    ]
