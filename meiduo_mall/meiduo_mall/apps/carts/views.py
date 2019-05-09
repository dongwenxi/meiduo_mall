from django.shortcuts import render
from django.views import View
import json
from django import http

from goods.models import SKU


# Create your views here.
class CartsView(View):
    """购物车"""

    def post(self, request):

        # 获取请求体中的sku_id, count
        json_dict = json.loads(request.body.decode())
        sku_id = json_dict.get('sku_id')
        count = json_dict.get('count')
        selected = json_dict.get('selected', True)

        # 校验
        if all([sku_id, count]) is False:
            return http.HttpResponseForbidden('缺少必传参数')

        try:
            sku = SKU.objects.get(id=sku_id)
        except SKU.DoesNotExist:
            return http.HttpResponseForbidden('sku不存在')

        # 判断当用户是否登录还是未登录
        user = request.user
        if user.is_authenticated:
            # 如果是登录用户存储购物车数据到redis
            pass
        else:
            # 如果未登录存储购物车数据到cookie
            pass
        pass