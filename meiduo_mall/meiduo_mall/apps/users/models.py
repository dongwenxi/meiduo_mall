from django.db import models
from django.contrib.auth.models import AbstractUser

class User(AbstractUser):
    """自定义用户模型"""

    mobile = models.CharField(max_length=11, unique=True, verbose_name='手机号')
    # 如果模型对应的表已经存在,并且表中已有数据,那么新追加的字段必须给默认值,或可以为None,不然迁移就报错
    email_active = models.BooleanField(default=False, verbose_name='邮箱激活状态')

    class Meta:  # 元类
        db_table = 'tb_users'
        verbose_name = '用户'
        verbose_name_plural = verbose_name

    def __str__(self):
        return self.username