from django.shortcuts import render
from django.views import View
import json, pickle, base64
from django import http
from django_redis import get_redis_connection

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
        response = http.JsonResponse({'code': RETCODE.OK, 'errmsg': '添加购物车成功'})

        if user.is_authenticated:
            # 如果是登录用户存储购物车数据到redis
            # 创建redis连接对象
            redis_conn = get_redis_connection('carts')
            # 创建管道
            pl = redis_conn.pipeline()
            """
            hash: {sku_id_1: count, sku_id2: count}
            set: {sku_id_1, sku_id_2}
            
            """
            # hincrby()
            pl.hincrby('carts_%s' % user.id, sku_id, count)
            # pl.expire('carts_%s' % user.id, 30)

            # sadd()
            if selected:  # 只有勾选的才向set集合中添加
                pl.sadd('selected_%s' % user.id, sku_id)
            # pl.expire('selected_%s' % user.id, 30)
            # 执行管道
            pl.execute()
            # 响应
            # return http.JsonResponse({'code': RETCODE.OK, 'errmsg': '添加购物车成功'})

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
            response.set_cookie('carts', cart_str)
        return response

    def get(self, request):
        """购物车数据展示"""

        user = request.user
        if user.is_authenticated:
            """登录用户获取redis购物车数据
            hash: {sku_id_1: count, sku_id2: count}
            set: {sku_id_1, sku_id_2}
            """
            # 创建redis连接对象
            redis_conn = get_redis_connection('carts')
            # 获取hash数据
            redis_cart = redis_conn.hgetall('carts_%s' % user.id)

            # 获取set数据{b'1', b'2'}
            selected_ids = redis_conn.smembers('selected_%s' % user.id)
            # 将redis购物车数据格式转换成和cookie购物车数据格式一致  目的为了后续数据查询转换代码和cookie共用一套代码
            cart_dict = {}
            for sku_id_bytes, count_bytes in redis_cart.items():
                cart_dict[int(sku_id_bytes)] = {
                    'count': int(count_bytes),
                    'selected': sku_id_bytes in selected_ids
                }

        else:
            """未登录用户获取cookie购物车数据"""
            """
            {
                sku_id_1: {'count': 2, 'selected': True},
                sku_id_2: {'count': 2, 'selected': True}
            }
            """
            # 获取cookie购物车数据
            cart_str = request.COOKIES.get('carts')
            # 判断有没有cookie购物车数据
            if cart_str:
                # 将字符串转换成字典
                cart_dict = pickle.loads(base64.b64decode(cart_str.encode()))
            else:
                return render(request, 'cart.html')

        """
       {
           sku_id_1: {'count': 2, 'selected': True},
           sku_id_2: {'count': 2, 'selected': True}
       }
       """
        # 查询到购物车中所有sku_id对应的sku模型
        sku_qs = SKU.objects.filter(id__in=cart_dict.keys())
        cart_skus = []  # 用来装每个转换好的sku字典
        for sku in sku_qs:
            sku_dict = {
                'id': sku.id,
                'name': sku.name,
                'price': str(sku.price),
                'default_image_url': sku.default_image.url,
                'count': int(cart_dict[sku.id]['count']),  # 方便js中的json对数据渲染
                'selected': str(cart_dict[sku.id]['selected']),
                'amount': str(sku.price * int(cart_dict[sku.id]['count']))
            }
            cart_skus.append(sku_dict)

        context = {
            'cart_skus': cart_skus
        }

        return render(request, 'cart.html', context)

    def put(self, request):
        """修改购物车数据"""
        # 接收前端传入 sku_id, count, selected
        json_dict = json.loads(request.body.decode())
        sku_id = json_dict.get('sku_id')
        count = json_dict.get('count')
        selected = json_dict.get('selected')
        # 校验
        if all([sku_id, count]) is False:
            return http.HttpResponseForbidden('缺少必传参数')

        try:
            sku = SKU.objects.get(id=sku_id)
        except SKU.DoesNotExist:
            return http.HttpResponseForbidden('sku不存在')

        user = request.user
        # 响应给前端修改后的sku数据
        cart_sku = {
            'id': sku.id,
            'name': sku.name,
            'price': sku.price,
            'default_image_url': sku.default_image.url,
            'count': int(count),
            'selected': selected,
            'amount': sku.price * int(count)  # 注意count类型问题
        }
        # count 2
        # sku_id2    {2}
        response = http.JsonResponse({'code': RETCODE.OK, 'errmsg': '修改购物车数据成功', 'cart_sku': cart_sku})
        if user.is_authenticated:

            # 登录用户修改redis购物车数据
            # 创建redis连接对象
            redis_conn = get_redis_connection('carts')
            pl = redis_conn.pipeline()

            # hset  # 覆盖hash中的数据
            pl.hset('carts_%s' % user.id, sku_id, count)
            # 判断selected是True还是False
            if selected:
                # 将勾选的sku_id存储到set集合
                pl.sadd('selected_%s' % user.id, sku_id)
            else:
                # 不勾选时,将sku_id从set集合中移除
                pl.srem('selected_%s' % user.id, sku_id)

            pl.execute()

            # 响应
            # return http.JsonResponse({'code': RETCODE.OK, 'errmsg': '修改购物车数据成功', 'cart_sku': cart_sku})


        else:
            # 未登录用户修改cookie购物车数据

            # 查询cookie购物车数据
            cart_str = request.COOKIES.get('carts')
            # 判断cookie有没有值
            if cart_str:
                # 把字符串转换成字典
                cart_dict = pickle.loads(base64.b64decode(cart_str.encode()))
            else:
                # 如果cookie购物车没有数据
                return http.JsonResponse({'code': RETCODE.DBERR, 'errmsg': 'cookie数据没有获取'})

            # 修改购物车大字典数据,新值覆盖旧值
            cart_dict[sku_id] = {
                'count': count,
                'selected': selected
            }
            # 将字典转换成字符串
            cart_str = base64.b64encode(pickle.dumps(cart_dict)).decode()

            # cart_sku = {
            #     'id': sku.id,
            #     'name': sku.name,
            #     'price': sku.price,
            #     'default_image_url': sku.default_image.url,
            #     'count': count,
            #     'selected': selected,
            #     'amount': sku.price * int(count)  # 注意count类型问题
            # }

            # 设置cookie
            # response = http.JsonResponse({'code': RETCODE.OK, 'errmsg': '修改购物车数据成功', 'cart_sku': cart_sku})
            response.set_cookie('carts', cart_str)
        # 响应
        return response

    def delete(self, request):
        """删除购物车数据"""
        # 接收sku_id
        json_dict = json.loads(request.body.decode())
        sku_id = json_dict.get('sku_id')
        # 校验
        try:
            sku = SKU.objects.get(id=sku_id)
        except SKU.DoesNotExist:
            return http.HttpResponseForbidden('sku不存在')

        # 判断是否登录
        user = request.user
        response = http.JsonResponse({'code': RETCODE.OK, 'errmsg': 'OK'})

        if user.is_authenticated:
            # 登录操作redis数据
            # 创建redis连接对象
            redis_conn = get_redis_connection('carts')
            # 创建管道
            pl = redis_conn.pipeline()

            # 删除hash中的sku_id及count
            pl.hdel('carts_%s' % user.id, sku_id)
            # 删除set集合中的勾选
            pl.srem('selected_%s' % user.id, sku_id)
            pl.execute()

        else:
            # 未登录操作cookie数据
            # 获取cookie数据
            cart_str = request.COOKIES.get('carts')

            # 判断cookie是否获取到
            if cart_str:
                # 把字符串转换成字典
                cart_dict = pickle.loads(base64.b64decode(cart_str.encode()))
            else:
                # 没有获取cookie数据 直接返回
                return http.JsonResponse({'code': RETCODE.DBERR, 'errmsg': 'cookie没有获取到'})
            # 判断当前要删除的sku_id在字典中是否存在
            if sku_id in cart_dict:
                # del cart_dict[sku_id]
                del cart_dict[sku_id]

            if len(cart_dict.keys()) == 0:  # 如果cookie中的购物车数据已经删除完了
                response.delete_cookie('carts')  # 删除cookie
                return response


            # 将字典转换成字符串 {}  # fsdf=
            cart_str = base64.b64encode(pickle.dumps(cart_dict)).decode()
            # 设置cookie
            response.set_cookie('carts', cart_str)
        # 响应
        return response


class CartsSelectView(View):
    """购物车全选"""

    def put(self, request):

        json_dict = json.loads(request.body.decode())
        selected = json_dict.get('selected')

        if isinstance(selected, bool) is False:
            return http.HttpResponseForbidden('参数有误')

        user = request.user
        response = http.JsonResponse({'code': RETCODE.OK, 'errmsg': 'OK'})
        if user.is_authenticated:
            """登录用户操作redis数据"""
            # 创建redis连接对象
            redis_conn = get_redis_connection('carts')
            # 获取到hash购物车数据{sku_id: count}
            redis_cart = redis_conn.hgetall('carts_%s' % user.id)
            # 判断当前是全选还是全不选
            if selected:
                # 如果是全选把hash中的所有sku_id添加到set集合中
                redis_conn.sadd('selected_%s' % user.id, *redis_cart.keys())
            else:
                # 如果取消全选,把hash中的所有sku_id 从set集合中删除
                # redis_conn.srem('selected_%s' % user.id, *redis_cart.keys())
                redis_conn.delete('selected_%s' % user.id)  # 将指定key对应的数据直接删除

        else:
            """未登录用户操作cookie数据"""
            # 获取cookie购物车数据
            cart_str = request.COOKIES.get('carts')
            # 判断有没有获取到cookie购物车数据
            if cart_str:
                # 如果获取到把字符串转换成字典
                cart_dict = pickle.loads(base64.b64decode(cart_str.encode()))
            else:
                # 如果没有获取到直接响应
                return http.JsonResponse({'code': RETCODE.DBERR, 'errmsg': 'cookie数据没有获取到'})
            """
            {
                sku_id: {'count': 1, 'selected': True}
            }
            """
            # 遍历cookie购物车大字典,把里面的selected改为True或False
            for sku_id in cart_dict:
                cart_dict[sku_id]['selected'] = selected
            # 把字典转换成字符串
            cart_str = base64.b64encode(pickle.dumps(cart_dict)).decode()
            # 设置cookie
            response.set_cookie('carts', cart_str)

        return response




class CartsSimpleView(View):
    """展示简单的购物车数据"""

    def get(self, request):

        user = request.user
        if user.is_authenticated:
            """登录用户获取redis购物车数据
            hash: {sku_id_1: count, sku_id2: count}
            set: {sku_id_1, sku_id_2}
            """
            # 创建redis连接对象
            redis_conn = get_redis_connection('carts')
            # 获取hash数据
            redis_cart = redis_conn.hgetall('carts_%s' % user.id)

            # 获取set数据{b'1', b'2'}
            selected_ids = redis_conn.smembers('selected_%s' % user.id)
            # 将redis购物车数据格式转换成和cookie购物车数据格式一致  目的为了后续数据查询转换代码和cookie共用一套代码
            cart_dict = {}
            for sku_id_bytes, count_bytes in redis_cart.items():
                cart_dict[int(sku_id_bytes)] = {
                    'count': int(count_bytes),
                    'selected': sku_id_bytes in selected_ids
                }

        else:
            """未登录用户获取cookie购物车数据"""
            """
            {
                sku_id_1: {'count': 2, 'selected': True},
                sku_id_2: {'count': 2, 'selected': True}
            }
            """
            # 获取cookie购物车数据
            cart_str = request.COOKIES.get('carts')
            # 判断有没有cookie购物车数据
            if cart_str:
                # 将字符串转换成字典
                cart_dict = pickle.loads(base64.b64decode(cart_str.encode()))
            else:
                return http.JsonResponse({'code': RETCODE.DBERR, 'errmsg': '没有购物车数据'})

        """
       {
           sku_id_1: {'count': 2, 'selected': True},
           sku_id_2: {'count': 2, 'selected': True}
       }
       """
        # 查询到购物车中所有sku_id对应的sku模型
        sku_qs = SKU.objects.filter(id__in=cart_dict.keys())
        cart_skus = []  # 用来装每个转换好的sku字典
        for sku in sku_qs:
            sku_dict = {
                'id': sku.id,
                'name': sku.name,
                'price': str(sku.price),
                'default_image_url': sku.default_image.url,
                'count': int(cart_dict[sku.id]['count']),  # 方便js中的json对数据渲染
            }
            cart_skus.append(sku_dict)


        return http.JsonResponse({'code': RETCODE.OK, 'errmsg': 'OK', 'cart_skus': cart_skus})