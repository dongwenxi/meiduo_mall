from django.shortcuts import render

from meiduo_mall.utils.views import LoginRequiredView


class OrderSettlementView(LoginRequiredView):
    """去结算界面"""

    def get(self, request):
        pass