from django.shortcuts import render
from django_redis import get_redis_connection
from decimal import Decimal

from meiduo_mall.utils.views import LoginRequiredView
from users.models import Address
from goods.models import SKU


class OrderSettlementView(LoginRequiredView):
    """去结算界面"""

    def get(self, request):
        user = request.user
        addresses = Address.objects.filter(user=user, is_deleted=False)
        # 如果有收货地址什么也不做,没有收货地址把变量设置为None
        addresses = addresses if addresses.exists() else None

        # 创建redis连接对象
        redis_conn = get_redis_connection('carts')
        # 获取hash所有数据{sku_id: count}
        redis_cart = redis_conn.hgetall('carts_%s' % user.id)
        # 获取set集合数据{sku_id}
        cart_selected = redis_conn.smembers('selected_%s' % user.id)

        cart_dict = {}  # 准备一个字典,用来装勾选商品id及count  {1: 2}
        for sku_id_bytes in cart_selected:  # 遍历set集合
            # 将勾选的商品sku_id 和count装入字典,并都转换为int类型
            cart_dict[int(sku_id_bytes)] = int(redis_cart[sku_id_bytes])


        # 通过set集合中的sku_id查询到对应的所有sku模型
        sku_qs = SKU.objects.filter(id__in=cart_dict.keys())  # 此处bytes类型会自动转换

        total_count = 0  # 记录总数量
        total_amount = Decimal('0.00')  # 商品总价
        # 遍历sku_qs查询集给每个sku模型多定义count和amount属性
        for sku in sku_qs:
            count = cart_dict[sku.id]  # 获取当前商品的购买数量
            sku.count = count  # 把当前商品购物车数据绑定到sku模型对象上
            sku.amount = sku.price * count

            total_count += count  # 累加购买商品总数量
            total_amount += sku.amount  # 累加商品总价

        freight = Decimal('10.00')  # 运费


        context = {
            'addresses': addresses,  # 用户收货地址
            'skus': sku_qs,  # 勾选的购物车商品数据
            'total_count': total_count,  # 勾选商品总数量
            'total_amount': total_amount,  # 勾选商品总价
            'freight': freight,  # 运费
            'payment_amount': total_amount + freight  # 实付款
        }
        return render(request, 'place_order.html', context)