from django.shortcuts import render
from django.views import View


# Create your views here.
class RegisterView(View):
    """注册"""

    def get(self, request):
        """提供注册界面"""
        return render(request, 'register.html')
