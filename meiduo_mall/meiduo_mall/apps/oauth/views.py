from django.shortcuts import render
from django.views import View
from django import http
from QQLoginTool.QQtool import OAuthQQ
from django.conf import settings

from meiduo_mall.utils.response_code import RETCODE
import logging

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



        return http.JsonResponse({'openid': openid})