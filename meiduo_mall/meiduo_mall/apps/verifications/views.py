from django.shortcuts import render
from django.views import View


class ImageCodeView(View):
    """生成图形验证码"""

    def get(self, request, uuid):
        pass