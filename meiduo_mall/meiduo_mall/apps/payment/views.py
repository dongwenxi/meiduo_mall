from django.shortcuts import render
from alipay import AliPay
from django import http
from django.conf import settings
import os

from meiduo_mall.utils.views import LoginRequiredView
from orders.models import OrderInfo
from meiduo_mall.utils.response_code import RETCODE
from .models import Payment


class PaymentView(LoginRequiredView):
    """第一个视图 拼接好支付宝登录链接"""

    def get(self, request, order_id):

        # 校验订单
        try:
            order = OrderInfo.objects.get(order_id=order_id, user=request.user, status=OrderInfo.ORDER_STATUS_ENUM['UNPAID'])
        except OrderInfo.DoesNotExist:
            return http.HttpResponseForbidden('订单有误')

        # 支付宝
        # ALIPAY_APPID = '2016091900551154'
        # ALIPAY_DEBUG = True  # 表示是沙箱环境还是真实支付环境
        # ALIPAY_URL = 'https://openapi.alipaydev.com/gateway.do'
        # ALIPAY_RETURN_URL = 'http://www.meiduo.site:8000/payment/status/'
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





class PaymentStatusView(LoginRequiredView):
    """第二个视图 就是校验支付结果,及修改订单状态"""
    def get(self, request):
        # 获取查询参数
        query_dict = request.GET
        # 将QueryDict类型转换成字典
        data = query_dict.dict()
        # 将字典中的sign移除
        sign = data.pop('sign')

        # 创建alipay对象
        alipay = AliPay(
            appid=settings.ALIPAY_APPID,
            app_notify_url=None,  # 默认回调url
            app_private_key_path=os.path.join(os.path.dirname(os.path.abspath(__file__)), 'keys/app_private_key.pem'),
            alipay_public_key_path=os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                                'keys/alipay_public_key.pem'),
            # 支付宝的公钥，验证支付宝回传消息使用，不是你自己的公钥,
            sign_type="RSA2",  # RSA 或者 RSA2
            debug=settings.ALIPAY_DEBUG  # 默认False
        )


        # 调用它的verify方法校验支付结果
        success = alipay.verify(data, sign)
        if success:
            # 保存支付宝交易号和美多订单号
            order_id = data.get('out_trade_no')
            trade_id = data.get('trade_no')
            try:
                Payment.objects.get(order_id=order_id, trade_id=trade_id)
            except Payment.DoesNotExist:
                # 保存支付结果
                Payment.objects.create(
                    order_id=order_id,
                    trade_id=trade_id
                )

                # 修改美多订单状态
                OrderInfo.objects.filter(user=request.user, order_id=order_id, status=OrderInfo.ORDER_STATUS_ENUM['UNPAID']).update(
                    status=OrderInfo.ORDER_STATUS_ENUM['UNCOMMENT']
                )
            # 响应
            return render(request, 'pay_success.html', {'trade_id': trade_id})
        else:
            return http.HttpResponseForbidden('非法请求')
