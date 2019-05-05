from django.shortcuts import render
from django.views import View


class ListView(View):
    """商品列表界面"""

    def get(self, request, category_id, page_num):
        return render(request, 'list.html')