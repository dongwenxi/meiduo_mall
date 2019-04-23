from django.shortcuts import render
from django.views import View
from django_redis import get_redis_connection
from django import http

from meiduo_mall.libs.captcha.captcha import captcha


class ImageCodeView(View):
    """生成图形验证码"""

    def get(self, request, uuid):
        """
        :param uuid: 唯一标识,用来区分当前的图形验证码属于那个用户
        :return: image
        """

        # 利用SDK 生成图形验证码 (唯一标识字符串, 图形验证内容字符串, 二进制图片数据)
        name, text, image = captcha.generate_captcha()

        # 创建redis连接对象
        redis_conn = get_redis_connection('verify_code')
        # 将图形验证码字符串存入到reids
        redis_conn.setex('img_%s' % uuid, 300, text)
        # 把生成好的图片响应给前端
        return http.HttpResponse(image, content_type='image/png')


class SMSCodeView(View):
    """短信验证码"""

    def get(self, request, mobile):
        """
        :param mobile: 要接收短信验证码的手号
        """

        # 接收到前端 传入的 mobile, image_code, uuid

        # 创建redis连接对象 根据uuid作为key 获取到reids中当前用户的图形验证值
        # 判断用户写的图形验证码和我们redis存的是否一致

        # 发送短信
        # 将生成好的短信验证码也存储到redis,以备后期校验
        # 响应

        pass
