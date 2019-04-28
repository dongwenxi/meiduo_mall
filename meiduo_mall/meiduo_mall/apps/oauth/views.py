from django.shortcuts import render, redirect
from django.views import View
from django import http
from QQLoginTool.QQtool import OAuthQQ
from django.conf import settings
from django.contrib.auth import login
import re
from django_redis import get_redis_connection

from meiduo_mall.utils.response_code import RETCODE
import logging
from .models import OAuthQQUser
from .utils import generate_openid_signature, check_openid_sign
from users.models import User
from .models import OAuthQQUser


logger = logging.getLogger('django')



# Create your views here.
class OAuthURLView(View):
    """提供QQ登录界面链接"""

    def get(self, request):
        # 提取前端用查询参数传入的next参数:记录用户从哪里去到login界面
        next = request.GET.get('next', '/')
        # QQ_CLIENT_ID = '101518219'
        # QQ_CLIENT_SECRET = '418d84ebdc7241efb79536886ae95224'
        # QQ_REDIRECT_URI = 'http://www.meiduo.site:8000/oauth_callback'
        # oauth = OAuthQQ(client_id='appid', client_secret='appkey', redirect_uri='授权成功回调url', state='记录来源')
        oauth = OAuthQQ(client_id=settings.QQ_CLIENT_ID,
                        client_secret=settings.QQ_CLIENT_SECRET,
                        redirect_uri=settings.QQ_REDIRECT_URI,
                        state=next)
        # 拼接QQ登录连接
        # https://graph.qq.com/oauth2.0/authorize?response_type=code&client_id=123&redirect_uri=xxx&state=next
        login_url = oauth.get_qq_url()

        return http.JsonResponse({'login_url': login_url, 'code': RETCODE.OK, 'errmsg': 'OK'})


class OAuthUserView(View):
    """QQ登录后回调处理"""

    def get(self, request):


        # 获取查询字符串中的code
        code = request.GET.get('code')
        state = request.GET.get('state', '/')


        # 创建QQ登录SDK对象
        oauth = OAuthQQ(client_id=settings.QQ_CLIENT_ID,
                        client_secret=settings.QQ_CLIENT_SECRET,
                        redirect_uri=settings.QQ_REDIRECT_URI,
                        )

        try:
            # 调用SDK中的get_access_token(code) 得到access_token
            access_token = oauth.get_access_token(code)
            # 调用SDK中的get_openid(access_token) 得到openid
            openid = oauth.get_open_id(access_token)
        except Exception as e:
            logger.error(e)
            return http.JsonResponse({'code': RETCODE.SERVERERR, 'errmsg': 'QQ服务器不可用'})

        # 在OAuthQQUser表中查询openid
        try:
            oauth_model = OAuthQQUser.objects.get(openid=openid)
        except OAuthQQUser.DoesNotExist:
            # 如果在OAuthQQUser表中没有查询到openid, 没绑定说明第一个QQ登录
            # 先对openid进行加密
            openid = generate_openid_signature(openid)
            # 创建一个新的美多用户和QQ的openid绑定
            return render(request, 'oauth_callback.html', {'openid': openid})
        else:
            # 如果在OAuthQQUser表中查询到openid,说明是已绑定过美多用户的QQ号
            user = oauth_model.user
            login(request, user)
            # 直接登录成功:  状态操持,
            response = redirect(state)
            response.set_cookie('username', user.username, max_age=settings.SESSSION_COOKIE_AGE)
            return response


        # return http.JsonResponse({'openid': openid})

    def post(self, request):
        """实现openid绑定用户逻辑"""
        # 接收数据
        mobile = request.POST.get('mobile')
        password = request.POST.get('password')
        sms_code = request.POST.get('sms_code')
        openid = request.POST.get('openid')

        if all([mobile, password, sms_code, openid]) is False:
            return http.HttpResponseForbidden('缺少必传参数')


        # 校验
        if not re.match(r'^1[3-9]\d{9}$', mobile):
            return http.HttpResponseForbidden('您输入的手机号格式不正确')

        if not re.match(r'^[0-9A-Za-z]{8,20}$', password):
            return http.HttpResponseForbidden('请输入8-20位的密码')

        # 短信验证码校验后期再补充
        redis_coon = get_redis_connection('verify_code')
        sms_code_server = redis_coon.get('sms_%s' % mobile)  # 获取redis中的短信验证码

        if sms_code_server is None or sms_code != sms_code_server.decode():
            return http.HttpResponseForbidden('短信验证码有误')

        # 校验openid
        openid = check_openid_sign(openid)
        if openid is None:
            return http.HttpResponseForbidden('openid无效')

        # 绑定用户
        try:
            user = User.objects.get(mobile=mobile)
        except User.DoesNotExist:
            # 当前要绑定的用户是一个新用户
            user = User.objects.create_user(
                username=mobile,
                password=password,
                mobile=mobile,
            )
        else:
            # 当前要绑定的用户是已存在
            if user.check_password(password) is False:
                return http.HttpResponseForbidden('账号或密码错误')

        # 如果代码能执行到这里,用户user绝对已经有了
        # 用户openid和user绑定
        OAuthQQUser.objects.create(
            user=user,
            openid=openid
        )

        # 重定向
        login(request, user)
        response = redirect(request.GET.get('state'))
        response.set_cookie('username', user.username, max_age=settings.SESSION_COOKIE_AGE)
        return response