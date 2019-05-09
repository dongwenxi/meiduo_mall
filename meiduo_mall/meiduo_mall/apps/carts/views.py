from django.shortcuts import render
from django.views import View

# Create your views here.
class CartsView(View):
    """购物车"""

    def post(self, request):
        pass