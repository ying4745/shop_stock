# Generated by Django 2.0.12 on 2019-06-05 01:57

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('order', '0007_auto_20190527_1414'),
    ]

    operations = [
        migrations.AlterField(
            model_name='orderinfo',
            name='customer',
            field=models.CharField(max_length=64, verbose_name='客户名字'),
        ),
        migrations.AlterField(
            model_name='orderinfo',
            name='receiver',
            field=models.CharField(default='默认', max_length=64, verbose_name='收件人'),
        ),
    ]
