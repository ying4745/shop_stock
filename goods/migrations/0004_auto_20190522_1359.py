# Generated by Django 2.0.12 on 2019-05-22 13:59

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('goods', '0003_auto_20190516_2226'),
    ]

    operations = [
        migrations.AlterField(
            model_name='goodssku',
            name='desc',
            field=models.CharField(max_length=64, verbose_name='商品规格'),
        ),
        migrations.AlterField(
            model_name='goodssku',
            name='shelf',
            field=models.CharField(default='001', max_length=64, verbose_name='货架号'),
        ),
    ]
