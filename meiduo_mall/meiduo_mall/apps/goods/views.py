from django.shortcuts import render
from django.views import View
from django import http
from django.core.paginator import Paginator

from contents.utils import get_categories
from .models import GoodsCategory, SKU
from .utils import get_breadcrumb
from meiduo_mall.utils.response_code import RETCODE


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
        # order_by(只能放当前查询集中每个模型中的字段)
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


class HotGoodsView(View):
    """热销排行数据"""

    def get(self, request, category_id):

        try:
            category = GoodsCategory.objects.get(id=category_id)
        except GoodsCategory.DoesNotExist:
            return http.HttpResponseNotFound('商品类别不存在')

        # 获取当前三级类别下面销量最高的前两个sku
        skus_qs = category.sku_set.filter(is_launched=True).order_by('-sales')[0:2]

        hot_skus = []  # 包装两个热销商品字典
        for sku in skus_qs:
            hot_skus.append({
                'id': sku.id,
                'name': sku.name,
                'price': sku.price,
                'default_image_url': sku.default_image.url
            })

        return http.JsonResponse({'code': RETCODE.OK, 'errmsg': 'OK', 'hot_skus': hot_skus})


class DetailView(View):
    """商品详情界面"""

    def get(self, request, sku_id):

        try:
            sku = SKU.objects.get(id=sku_id)
        except SKU.DoesNotExist:
            return render(request, '404.html')

        category = sku.category  # 获取当前sku所对应的三级分类

        # 查询当前sku所对应的spu
        spu = sku.spu

        spu_spec_qs = spu.specs.order_by('id')  # 获取当前spu中的所有规格
        for spec in spu_spec_qs:  # 遍历当前所有的规格
            spec.spec_options = spec.options.all() # 把规格下的所有选项绑定到规格对象的spec_options属性上




        context = {
            'categories': get_categories(), # 商品分类
            'breadcrumb': get_breadcrumb(category),  # 面包屑导航
            'sku': sku,  # 当前要显示的sku模型对象
            'category': category,  # 当前的显示sku所属的三级类别
            'spu': spu,  # sku所属的spu
            'spec_qs': spu_spec_qs,   # 当前商品的所有规格数据
        }
        return render(request, 'detail.html', context)
        pass



