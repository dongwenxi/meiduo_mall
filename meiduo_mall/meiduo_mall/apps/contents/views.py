from django.shortcuts import render
from django.views import View

# Create your views here.
class IndexView(View):
    """首页"""

    def get(self, request):
        """
        商品分类及广告数据展示
        """
        categories = {}  # 用来包装所有商品类别数据
        """
        { 
            1: {
                'channels': [cat1-1, cat1-2,...]  第一组里面的所有一级数据
                'sub_cats': [cat2-1, cat2-2]   用来装所有二级数据, 在二级中再包含三级数据cat2-1.sub_cats = cat3
                },
                
            2: {
                'channels': [cat1-1...],
                'sub_cats': [...]
                }
                
        
        }
        """



        context = {
            'categories': ''
        }


        return render(request, 'index.html', context)