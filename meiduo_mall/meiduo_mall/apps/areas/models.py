from django.db import models

# Create your models here.
class Area(models.Model):
    """省市区"""
    name = models.CharField(max_length=20, verbose_name='名称')
    parent = models.ForeignKey('self', on_delete=models.SET_NULL, related_name='subs', null=True, blank=True, verbose_name='上级行政区划')


    class Meta:
        db_table = 'tb_areas'
        verbose_name = '省市区'
        verbose_name_plural = '省市区'

    def __str__(self):
        return self.name


"""
area: 广东省
area.id
area.name
area.parent =None
aras.sbus.all() 广东省下面的所有市




area: 市
area.id  市的id
area.name  市的名字
area.parent = 省


book: 一方  hero_set 起了个别名 叫subs
hero: 多方  hbook外键

book.hero_set.all()
"""