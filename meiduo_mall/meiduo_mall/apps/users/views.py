from django.shortcuts import render, redirect, reverse
from django.views import View
from django import http
import re, json
from django.contrib.auth import login, authenticate, logout, mixins
from django.db import DatabaseError
from django_redis import get_redis_connection
from django.conf import settings
from django.contrib.auth.decorators import login_required

from .models import User, Address
import logging
from meiduo_mall.utils.response_code import RETCODE
from celery_tasks.email.tasks import send_verify_email
from .utils import generate_verify_email_url, check_token_to_user
from meiduo_mall.utils.views import LoginRequiredView
from goods.models import SKU
from carts.utils import merge_cart_cookie_to_redis


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

        # 登录成功那一刻合并购物车
        merge_cart_cookie_to_redis(request, user, response)
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
        # 获取当前用户的所有收货地址
        user = request.user
        # address = user.addresses.filter(is_deleted=False)  # 获取当前用户的所有收货地址
        address_qs = Address.objects.filter(is_deleted=False, user=user)  # 获取当前用户的所有收货地址

        address_list = []
        for address in address_qs:
            address_dict = {
                'id': address.id,
                'title': address.title,
                'receiver': address.receiver,
                'province_id': address.province_id,
                'province': address.province.name,
                'city_id': address.city_id,
                'city': address.city.name,
                'district_id': address.district_id,
                'district': address.district.name,
                'place': address.place,
                'mobile': address.mobile,
                'tel': address.tel,
                'email': address.email,
            }
            address_list.append(address_dict)

        context = {
            'addresses': address_list,
            'default_address_id': user.default_address_id
        }
        return render(request, 'user_center_site.html', context)


class CreateAddressView(LoginRequiredView):
    """新增收货地址"""

    def post(self, request):
        """新增收货地址逻辑"""
        user = request.user
        # 判断用户的收货地址数据,如果超过20个提前响应
        count = Address.objects.filter(user=user, is_deleted=False).count()
        # count = user.addresses.count()
        if count >= 20:
            return http.HttpResponseForbidden('用户收货地址上限')
        # 接收请求数据
        json_dict = json.loads(request.body.decode())
        """
            title: '',
            receiver: '',
            province_id: '',
            city_id: '',
            district_id: '',
            place: '',
            mobile: '',
            tel: '',
            email: '',
        """
        title = json_dict.get('title')
        receiver = json_dict.get('receiver')
        province_id = json_dict.get('province_id')
        city_id = json_dict.get('city_id')
        district_id = json_dict.get('district_id')
        place = json_dict.get('place')
        mobile = json_dict.get('mobile')
        tel = json_dict.get('tel')
        email = json_dict.get('email')

        # 校验
        if all([title, receiver, province_id, city_id, district_id, place, mobile]) is False:
            return http.HttpResponseForbidden('缺少必传参数')

        if not re.match(r'^1[3-9]\d{9}$', mobile):
            return http.HttpResponseForbidden('参数mobile有误')
        if tel:
            if not re.match(r'^(0[0-9]{2,3}-)?([2-9][0-9]{6,7})+(-[0-9]{1,4})?$', tel):
                return http.HttpResponseForbidden('参数tel有误')
        if email:
            if not re.match(r'^[a-z0-9][\w\.\-]*@[a-z0-9\-]+(\.[a-z]{2,5}){1,2}$', email):
                return http.HttpResponseForbidden('参数email有误')

        # 新增
        try:
            address = Address.objects.create(
                user=user,
                title=title,
                receiver=receiver,
                province_id=province_id,
                city_id=city_id,
                district_id=district_id,
                place=place,
                mobile=mobile,
                tel=tel,
                email=email
            )
            if user.default_address is None:  # 判断当前用户是否有默认收货地址
                user.default_address = address  # 就把当前的收货地址设置为它的默认值
                user.save()
        except Exception:
            return http.HttpResponseForbidden('新增地址出错')

        # 把新增的地址数据响应回去
        address_dict = {
            'id': address.id,
            'title': address.title,
            'receiver': address.receiver,
            'province_id': address.province_id,
            'province': address.province.name,
            'city_id': address.city_id,
            'city': address.city.name,
            'district_id': address.district_id,
            'district': address.district.name,
            'place': address.place,
            'mobile': address.mobile,
            'tel': address.tel,
            'email': address.email,
        }
        return http.JsonResponse({'code': RETCODE.OK, 'errmsg': 'OK', 'address': address_dict})


class UpdateDestroyAddressView(LoginRequiredView):
    """修改和删除"""

    def put(self, request, address_id):
        """修改地址逻辑"""
        # 查询要修改的地址对象
        try:
            address = Address.objects.get(id=address_id)
        except Address.DoesNotExist:
            return http.HttpResponseForbidden('要修改的地址不存在')


        # 接收
        json_dict = json.loads(request.body.decode())
        title = json_dict.get('title')
        receiver = json_dict.get('receiver')
        province_id = json_dict.get('province_id')
        city_id = json_dict.get('city_id')
        district_id = json_dict.get('district_id')
        place = json_dict.get('place')
        mobile = json_dict.get('mobile')
        tel = json_dict.get('tel')
        email = json_dict.get('email')

        # 校验
        if all([title, receiver, province_id, city_id, district_id, place, mobile]) is False:
            return http.HttpResponseForbidden('缺少必传参数')

        if not re.match(r'^1[3-9]\d{9}$', mobile):
            return http.HttpResponseForbidden('参数mobile有误')
        if tel:
            if not re.match(r'^(0[0-9]{2,3}-)?([2-9][0-9]{6,7})+(-[0-9]{1,4})?$', tel):
                return http.HttpResponseForbidden('参数tel有误')
        if email:
            if not re.match(r'^[a-z0-9][\w\.\-]*@[a-z0-9\-]+(\.[a-z]{2,5}){1,2}$', email):
                return http.HttpResponseForbidden('参数email有误')


        # 修改
        Address.objects.filter(id=address_id).update(
            title=title,
            receiver=receiver,
            province_id=province_id,
            city_id=city_id,
            district_id=district_id,
            place=place,
            mobile=mobile,
            tel=tel,
            email=email
        )
        address = Address.objects.get(id=address_id)  # 要重新查询一次新数据
        # 把新增的地址数据响应回去
        address_dict = {
            'id': address.id,
            'title': address.title,
            'receiver': address.receiver,
            'province_id': address.province_id,
            'province': address.province.name,
            'city_id': address.city_id,
            'city': address.city.name,
            'district_id': address.district_id,
            'district': address.district.name,
            'place': address.place,
            'mobile': address.mobile,
            'tel': address.tel,
            'email': address.email,
        }
        return http.JsonResponse({'code': RETCODE.OK, 'errmsg': 'OK', 'address': address_dict})
        # 响应

    def delete(self, request, address_id):
        """对收货地址逻辑删除"""
        try:
            address = Address.objects.get(id=address_id)
        except Address.DoesNotExist:
            return http.HttpResponseForbidden('要删除的地址不存在')

        address.is_deleted = True
        # address.delete()
        address.save()

        return http.JsonResponse({'code': RETCODE.OK, 'errmsg': 'OK'})



class DefaultAddressView(LoginRequiredView):
    """设置默认地址"""

    def put(self, request, address_id):
        """实现默认地址"""
        try:
            address = Address.objects.get(id=address_id)
        except Address.DoesNotExist:
            return http.HttpResponseForbidden('要修改的地址不存在')

        user = request.user
        user.default_address = address
        user.save()

        return http.JsonResponse({'code': RETCODE.OK, 'errmsg': 'OK'})


class UpdateTitleAddressView(LoginRequiredView):
    """修改用户收货地址标题"""
    def put(self, request, address_id):
        try:
            address = Address.objects.get(id=address_id)
        except Address.DoesNotExist:
            return http.HttpResponseForbidden('要修改的地址不存在')

        json_dict = json.loads(request.body.decode())
        title = json_dict.get('title')
        address.title = title
        address.save()

        return http.JsonResponse({'code': RETCODE.OK, 'errmsg': 'OK'})


class ChangePasswordView(LoginRequiredView):
    """修改密码"""

    def get(self, request):
        return render(request, 'user_center_pass.html')


    def post(self, request):
        """实现修改密码逻辑"""

        # 接收参数
        old_password = request.POST.get('old_pwd')
        password = request.POST.get('new_pwd')
        password2 = request.POST.get('new_cpwd')

        # 校验
        if all([old_password, password, password2]) is False:
            return http.HttpResponseForbidden("缺少必传参数")

        user = request.user
        if user.check_password(old_password) is False:
            return render(request, 'user_center_pass.html', {'origin_pwd_errmsg': '原始密码错误'})

        if not re.match(r'^[0-9A-Za-z]{8,20}$', password):
            return http.HttpResponseForbidden('密码最少8位，最长20位')
        if password != password2:
            return http.HttpResponseForbidden('两次输入的密码不一致')

        # 修改密码
        user.set_password(password)
        user.save()

        # 响应重定向到登录界面
        logout(request)
        response = redirect('/login/')
        response.delete_cookie('username')

        return response


class UserBrowseHistory(View):
    """用户商品浏览记录"""

    def post(self, request):

        # 判断当前用户是否登录
        user = request.user
        if not user.is_authenticated:
            return http.JsonResponse({'code': RETCODE.SESSIONERR, 'errmsg': '用户未登录'})

        # 获取请求体中的sku_id
        json_dict = json.loads(request.body.decode())
        sku_id = json_dict.get('sku_id')

        # 校验sku_id
        try:
            sku = SKU.objects.get(id=sku_id)
        except SKU.DoesNotExist:
            return http.HttpResponseForbidden('sku_id不存在')

        # 创建redis连接对象
        redis_conn = get_redis_connection('history')
        pl = redis_conn.pipeline()

        key = 'history_%s' % user.id
        # 先去重
        pl.lrem(key, 0, sku_id)

        # 存储到列表的开头
        pl.lpush(key, sku_id)

        # 截取前5个
        pl.ltrim(key, 0, 4)
        # 执行管道
        pl.execute()

        # 响应
        return http.JsonResponse({'code': RETCODE.OK, 'errmsg': 'OK'})

    def get(self, request):
        """浏览记录查询"""

        # 创建redis连接对象
        redis_conn = get_redis_connection('history')
        sku_id_list = redis_conn.lrange('history_%s' % request.user.id, 0, -1)
        # 获取当前登录用户的浏览记录列表数据 [sku_id1, sku_id2]

        # 通过sku_id查询sku,再将sku模型转换成字典
        # sku_qs = SKU.objects.filter(id__in=sku_id_list)  [b'3', b'2', b'5'] [2, 3, 5]
        skus = []  # 用来装每一个sku字典
        for sku_id in sku_id_list:
            sku = SKU.objects.get(id=sku_id)
            sku_dict = {
                'id': sku.id,
                'name': sku.name,
                'default_image_url': sku.default_image.url,
                'price': sku.price
            }
            skus.append(sku_dict)
        # 响应
        return http.JsonResponse({'code': RETCODE.OK, 'errmsg': 'OK', 'skus': skus})

