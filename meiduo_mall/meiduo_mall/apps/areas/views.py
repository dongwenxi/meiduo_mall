from django.shortcuts import render
from django.views import View


# Create your views here.
class AreasView(View):
    """省市区数据查询"""

    def get(self, request):
        """实现省市区查询逻辑"""
        pass