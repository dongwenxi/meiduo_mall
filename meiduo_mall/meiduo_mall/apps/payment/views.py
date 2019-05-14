from django.shortcuts import render
from alipay import AliPay
from django import http
from django.conf import settings
import os

from meiduo_mall.utils.views import LoginRequiredView
from orders.models import OrderInfo
from meiduo_mall.utils.response_code import RETCODE


class PaymentView(LoginRequiredView):
    """第一个视图 拼接好支付宝登录链接"""

    def get(self, request, order_id):

        # 校验订单
        try:
            order = OrderInfo.objects.get(order_id=order_id, user=request.user, status=OrderInfo.ORDER_STATUS_ENUM['UNPAID'])
        except OrderInfo.DoesNotExist:
            return http.HttpResponseForbidden('订单有误')

        # 支付宝
        ALIPAY_APPID = '2016091900551154'
        ALIPAY_DEBUG = True  # 表示是沙箱环境还是真实支付环境
        ALIPAY_URL = 'https://openapi.alipaydev.com/gateway.do'
        ALIPAY_RETURN_URL = 'http://www.meiduo.site:8000/payment/status/'
        # 创建AliPay 对象
        alipay = AliPay(
            appid=settings.ALIPAY_APPID,
            app_notify_url=None,  # 默认回调url
            app_private_key_path=os.path.join(os.path.dirname(os.path.abspath(__file__)), 'keys/app_private_key.pem'),
            alipay_public_key_path=os.path.join(os.path.dirname(os.path.abspath(__file__)), 'keys/alipay_public_key.pem'),
            # 支付宝的公钥，验证支付宝回传消息使用，不是你自己的公钥,
            sign_type="RSA2",  # RSA 或者 RSA2
            debug = settings.ALIPAY_DEBUG  # 默认False
        )

        # 调用它的方法api_alipay_trade_page_pay得到支付链接后面的查询参数部分
        order_string = alipay.api_alipay_trade_page_pay(
            subject='美多商城%s' % order_id,
            out_trade_no=order_id,
            total_amount=str(order.total_amount),  # 要注意转换类型
            return_url=settings.ALIPAY_RETURN_URL
        )

        # 支付url 拼接 查询参数
        # 沙箱环境链接: 'https://openapi.alipaydev.com/gateway.do' + '?' + order_string
        # 真实环境链接: 'https://openapi.alipay.com/gateway.do' + '?' + order_string
        alipay_url = settings.ALIPAY_URL + '?' + order_string

        # 响应
        return http.JsonResponse({'code': RETCODE.OK, 'errmsg': 'OK', 'alipay_url': alipay_url})



# 第二个视图 就是校验支付结果,及修改订单状态