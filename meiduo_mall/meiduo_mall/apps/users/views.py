from django.shortcuts import render, redirect
from django.views import View
from django import http
import re
from django.contrib.auth import login
from django.db import DatabaseError

from .models import User
import logging
from meiduo_mall.utils.response_code import RETCODE

logger = logging.getLogger('django')  # 创建日志输出器对象

# Create your views here.
class RegisterView(View):
    """注册"""

    def get(self, request):
        """提供注册界面"""
        # http://127.0.0.1/register/
        # http://127.0.0.1:8000/register/index/

        return render(request, 'register.html')

    def post(self, request):
        """用户注册功能"""

        # 接收前端传入的表单数据: username, password, password2, mobile, sms_code, allow
        username = request.POST.get('username')
        password = request.POST.get('password')
        password2 = request.POST.get('password2')
        mobile = request.POST.get('mobile')
        sms_code = request.POST.get('sms_code')
        allow = request.POST.get('allow')  # 单选框如果勾选就是 'on',如果没有勾选 None

        #  all None, False, ''
        # 校验前端传入的参数是否齐全
        if all([username, password, password2, mobile, sms_code, allow]) is False:
            return http.HttpResponseForbidden('缺少必传参数')

        # 校验数据前端传入数据是否符合要求
        if not re.match(r'^[a-zA-Z0-9_-]{5,20}$', username):
            return http.HttpResponseForbidden('请输入5-20个字符的用户名')

        if not re.match(r'^[0-9A-Za-z]{8,20}$', password):
            return http.HttpResponseForbidden('请输入8-20位的密码')

        if password != password2:
            return http.HttpResponseForbidden('输入的密码两次不一致')

        if not re.match(r'^1[3-9]\d{9}$', mobile):
            return http.HttpResponseForbidden('您输入的手机号格式不正确')

        # TODO 短信验证码校验后期再补充


        # 创建一个user
        try:
            user = User.objects.create_user(
                username=username,
                password=password,  # 密码在存储时需要加密后再存到表中
                mobile=mobile
            )
        except DatabaseError as e:
            logger.error(e)
            return render(request, 'register.html', {'register_errmsg': '用户注册失败'})


        # 状态保持
        login(request, user)  # 存储用户的id到session中记录它的登录状态

        # 注册成功重定向到首页
        return redirect('/')


class UsernameCountView(View):
    """判断用户名是否已注册"""

    def get(self, request, username):

        # 查询当前用户名的个数要么0要么1 1代表重复
        count = User.objects.filter(username=username).count()

        return http.JsonResponse({'count': count, 'code': RETCODE.OK, 'errmsg': 'OK'})


class MobileCountView(View):
    """判断手机号是否已注册"""

    def get(self, request, mobile):

        # 查询当前手机号的个数要么0要么1 1代表重复
        count = User.objects.filter(mobile=mobile).count()

        return http.JsonResponse({'count': count, 'code': RETCODE.OK, 'errmsg': 'OK'})