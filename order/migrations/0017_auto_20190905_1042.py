# Generated by Django 2.0.12 on 2019-09-05 10:42

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('order', '0016_auto_20190719_2220'),
    ]

    operations = [
        migrations.AlterField(
            model_name='orderinfo',
            name='order_country',
            field=models.CharField(choices=[('MYR', '马来西亚'), ('PHP', '菲律宾'), ('THB', '泰国'), ('IDR', '印尼')], default='MYR', max_length=5, verbose_name='订单国家'),
        ),
    ]
