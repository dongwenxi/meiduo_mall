from django.shortcuts import render
from django.views import View
from django import http
from django.core.paginator import Paginator

from contents.utils import get_categories
from .models import GoodsCategory
from .utils import get_breadcrumb


class ListView(View):
    """商品列表界面"""

    def get(self, request, category_id, page_num):
        """
        :param category_id: 当前选择的三级类别id
        :param page_num: 第几页
        """
        try:
            category = GoodsCategory.objects.get(id=category_id)
        except GoodsCategory.DoesNotExist:
            return http.HttpResponseNotFound('商品类别不存在')

        # 获取查询参数中的sort 排序规则
        sort = request.GET.get('sort', 'default')

        if sort == 'price':
            sort_fields = 'price'
        elif sort == 'hot':
            sort_fields = '-sales'
        else:
            sort_fields = 'create_time'

        # 面包屑导航数据
        # a = (page_num - 1) * 5
        # b = a + 5
        # 查询当前三级类别下面的所有sku
        sku_qs = category.sku_set.filter(is_launched=True).order_by(sort_fields)

        # 创建分页对象
        paginator = Paginator(sku_qs, 5)  # Paginator(要进行分页的所有数据, 每页显示多少条数据)
        page_skus = paginator.page(page_num)  # 获取指定界面的sku数据
        total_page = paginator.num_pages  # 获取当前的总页数

        context = {
            'categories': get_categories(),  # 频道分类
            'breadcrumb': get_breadcrumb(category),  # 面包屑导航
            'sort': sort,  # 排序字段
            'category': category,  # 第三级分类
            'page_skus': page_skus,  # 分页后数据
            'total_page': total_page,  # 总页数
            'page_num': page_num,  # 当前页码
        }

        return render(request, 'list.html', context)
