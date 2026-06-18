# peyment/urls.py

from django.urls import path
from .views import *
from .panel_view import PaymentListView, PaymentDetailView

app_name = 'peyment'

urlpatterns = [
    # مسیرهای قبلی برای پرداخت سفارش
    path('request/<uuid:order_id>/', send_request, name='request'),
    path('verify/', Zarin_pal_view_verfiy.as_view(), name='verify'),
    path('show_sucess/<str:message>/', show_verfiy_message, name='show_sucess'),
    path('show_verfiy_unmessage/<str:message>/', show_verfiy_unmessage, name='show_verfiy_unmessage'),

    # مسیرهای پنل مدیریت برای مشاهده پرداخت‌ها
    path('payments/', PaymentListView.as_view(), name='payment_list'),
    path('payments/<int:payment_id>/', PaymentDetailView.as_view(), name='payment_detail'),

    # =========== APIهای جدید برای پرداخت حق عضویت (5,000,000 تومان) ===========
    # API برای شروع پرداخت حق عضویت (برای استفاده در فرانت‌اند با fetch/ajax)
    path('api/membership/pay/', MembershipPaymentAPIView.as_view(), name='membership_payment_api'),

    # API برای بررسی وضعیت عضویت کاربر (برای استفاده در فرانت‌اند)
    path('api/membership/status/', check_membership_status, name='check_membership_status'),

    # مسیر کمکی برای پرداخت مستقیم حق عضویت (برای استفاده در لینک‌های ساده)
    path('membership/pay/', membership_payment_redirect, name='membership_payment_redirect'),

    # صفحه نمایش پرداخت حق عضویت (برای استفاده در قالب‌ها)
    path('membership/pay/page/', MembershipPaymentView.as_view(), name='membership_payment_page'),
]