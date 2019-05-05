from django.shortcuts import render
from django.views import View

from goods.models import GoodsChannel, GoodsCategory


class IndexView(View):
    """首页"""

    def get(self, request):
        """
        商品分类及广告数据展示
        """
        """
               { 
                   1: {
                       'channels': [cat1-1, cat1-2,...]  第一组里面的所有一级数据
                       'cat_subs': [cat2-1, cat2-2]   用来装所有二级数据, 在二级中再包含三级数据cat2-1.cat_subs = cat3
                       },

                   2: {
                       'channels': [cat1-1...],
                       'cat_subs': [...]
                       }


               }
               """
        categories = {}  # 用来包装所有商品类别数据
        # 获取所有一级类别分组数据
        goods_channels_qs = GoodsChannel.objects.order_by('group_id', 'sequence')
        for channel in goods_channels_qs:

            group_id = channel.group_id  # 获取组号

            # 判断当前的组号在字典中是否存在
            if group_id not in categories:
                # 不存在,包装一个当前组的准备数据
                categories[group_id] = {'channels': [], 'cat_subs': []}

            cat1 = channel.category  # 获取一级类别数据
            cat1.url = channel.url  # 将频道中的url绑定给一级类型对象

            categories[group_id]['channels'].append(cat1)





        context = {
            'categories': categories
        }



        return render(request, 'index.html', context)