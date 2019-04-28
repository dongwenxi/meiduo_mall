from django.shortcuts import render, redirect, reverse
from django.views import View
from django import http
import re, json
from django.contrib.auth import login, authenticate, logout, mixins
from django.db import DatabaseError
from django_redis import get_redis_connection
from django.conf import settings
from django.contrib.auth.decorators import login_required

from .models import User
import logging
from meiduo_mall.utils.response_code import RETCODE
from celery_tasks.email.tasks import send_verify_email
from .utils import generate_verify_email_url, check_token_to_user
from meiduo_mall.utils.views import LoginRequiredView


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

        # 短信验证码校验后期再补充
        redis_coon = get_redis_connection('verify_code')
        sms_code_server = redis_coon.get('sms_%s' % mobile)  # 获取redis中的短信验证码

        if sms_code_server is None or sms_code != sms_code_server.decode():
            return http.HttpResponseForbidden('短信验证码有误')

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
        response = redirect('/')  # 创建好响应对象
        response.set_cookie('username', user.username, max_age=settings.SESSION_COOKIE_AGE)

        # 响应结果重定向到首页
        return response


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


class LoginView(View):
    """用户账号登录"""

    def get(self, request):
        """提供登录界面"""
        return render(request, 'login.html')

    def post(self, request):
        """账户密码登录实现逻辑"""

        # 接收用户名，密码
        username = request.POST.get('username')
        password = request.POST.get('password')
        remembered = request.POST.get('remembered')

        if all([username, password]) is False:
            return http.HttpResponseForbidden('缺少必传参数')

        # 校验
        # user = User.objects.get(username=username)
        # user.check_password(password)
        # if re.match(r'^1[3-9]\d{9}$', username):
        #     User.USERNAME_FIELD = 'mobile'

        # 登录认证
        user = authenticate(username=username, password=password)
        # User.USERNAME_FIELD = 'username'
        if user is None:
            return render(request, 'login.html', {'account_errmsg': '用户名或密码错误'})

        # if remembered != 'on':  # 没有勾选记住登录
        #     settings.SESSION_COOKIE_AGE = 0  # 修改Django的SESSION缓存时长
        # # 状态保持
        # login(request, user)


        # 实现状态保持
        login(request, user)
        # 设置状态保持的周期
        if remembered != 'on':
            # 没有记住用户：浏览器会话结束就过期, 默认是两周
            request.session.set_expiry(0)

        response = redirect(request.GET.get('next', '/'))  # 创建好响应对象
        response.set_cookie('username', user.username, max_age=settings.SESSION_COOKIE_AGE)

        # 响应结果重定向到首页
        return response


class LogoutView(View):
    """退出登录"""

    def get(self, request):
        # 清除session中的状态保持数据
        logout(request)

        # 清除cookie中的username
        response = redirect(reverse('users:login'))
        response.delete_cookie('username')
        # 重定向到login界面
        return response


class UserInfoView(mixins.LoginRequiredMixin, View):
    """用户个人信息"""

    def get(self, request):
        """提供用户中心界面"""
        # 判断当前用户是否登录,如果登录返回用户中心界面
        # 如果用户没有登录,就重定义到登录
        # user = request.user  # 通过请求对象获取user
        # if user.is_authenticated:
        #     return render(request, 'user_center_info.html')
        # else:
        #     return redirect('/login/?next=/info/')
        # return redirect_to_login(self.request.get_full_path(), self.get_login_url(), self.get_redirect_field_name())

        return render(request, 'user_center_info.html')


class EmailView(mixins.LoginRequiredMixin, View):
    """添加用户邮箱"""

    def put(self, request):

        # 接收请求体email数据
        json_dict = json.loads(request.body.decode())
        email = json_dict.get('email')

        # 校验
        if all([email]) is None:
            return http.HttpResponseForbidden('缺少邮箱数据')

        if not re.match(r'^[a-z0-9][\w\.\-]*@[a-z0-9\-]+(\.[a-z]{2,5}){1,2}$', email):
            return http.HttpResponseForbidden('邮箱格式有误')


        # 获取到user
        user = request.user
        # 设置user.email字段
        user.email = email
        # 调用save保存
        user.save()

        # 在此地还要发送一个邮件到email
        # from django.core.mail import send_mail
        # # send_mail(邮件主题, 普通邮件正文, 发件人邮箱, [收件人邮件], html_message='超文本邮件内容')
        # send_mail('美多', '', '美多商城<itcast99@163.com>', [email], html_message='收钱了')
        # verify_url = 'http://www.meiduo.site:8000/emails/verification/?token=2'
        verify_url = generate_verify_email_url(user)  # 生成邮箱激活url
        send_verify_email.delay(email, verify_url)

        # 响应
        return http.JsonResponse({'code': RETCODE.OK, 'errmsg': 'OK'})


class VerifyEmailView(View):
    """激活邮箱"""

    def get(self, request):
        """实现激活邮箱逻辑"""
        # 获取token
        token = request.GET.get('token')

        # 解密并获取到user
        user = check_token_to_user(token)
        if user is None:
            return http.HttpResponseForbidden('token无效')

        # 修改当前user.email_active=True
        user.email_active = True
        user.save()

        # 响应
        return redirect('/info/')



class AddressView(LoginRequiredView):
    """用户收货地址"""
    def get(self, request):
        """提供用户收货地址界面"""
        return render(request, 'user_center_site.html')