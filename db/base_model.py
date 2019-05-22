from django.db import models


class BaseModel(models.Model):
    """模型基类"""
    create_time = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    update_time = models.DateTimeField(auto_now=True, verbose_name='更新时间')

    # 自动添加属性
    def set_attr(self, arrt_dict):
        for key, value in arrt_dict.items():
            if hasattr(self, key) and key != 'id':
                setattr(self, key, value)

    class Meta:
        abstract = True