# Generated by Django 2.0.12 on 2019-05-16 22:26

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('order', '0003_auto_20190509_1707'),
    ]

    operations = [
        migrations.AlterField(
            model_name='orderinfo',
            name='order_country',
            field=models.CharField(choices=[('MYR', '马来西亚'), ('PHP', '菲律宾'), ('th', '泰国')], default='my', max_length=5, verbose_name='订单国家'),
        ),
    ]