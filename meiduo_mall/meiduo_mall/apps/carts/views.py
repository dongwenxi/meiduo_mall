from django.shortcuts import render
from django.views import View
import json, pickle, base64
from django import http


from goods.models import SKU
from meiduo_mall.utils.response_code import RETCODE


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

            """
            {
                sku_id_1: {'count': 2, 'selected': True},
                sku_id_2: {'count': 2, 'selected': True}
            }
            """
            # 先获取cookie购物车数据
            cart_str = request.COOKIES.get('carts')
            # 如果cookie中已有购物车数据
            if cart_str:
                # 把cookie购物车字符串转回到字典
                cart_str_bytes = cart_str.encode()
                cart_bytes = base64.b64decode(cart_str_bytes)
                cart_dict = pickle.loads(cart_bytes)

                # cart_dict = pickle.loads(base64.b64decode(cart_str.encode()))
            else:
                # 如果cookie中没有购物车数据
                # 准备一个空字典
                cart_dict = {}

            # 判断要添加的sku_id 在字典中是否存在,如果存在,需要对count做增量计算
            if sku_id in cart_dict:
                origin_count = cart_dict[sku_id]['count']  # 获取它原有count
                count += origin_count  # 累加count

            # 添加
            cart_dict[sku_id] = {
                'count': count,
                'selected': selected
            }

            # 把购物车字典转换回字符串 然后重新设置到cookie中
            cart_str = base64.b64encode(pickle.dumps(cart_dict)).decode()


            # 响应
            response = http.JsonResponse({'code': RETCODE.OK, 'errmsg': '添加购物车成功'})
            response.set_cookie('carts', cart_str)
            return response
