from django.urls import path
from . import views
app_name = "coupons"

urlpatterns = [
    path("", views.CouponListView.as_view(), name="coupon_list"),
    path("<str:code>/", views.coupon_detail, name="coupon_detail"),
]