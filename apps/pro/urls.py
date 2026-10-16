# apps/pro/urls.py

from django.urls import path
from . import views
from . import panel

app_name = 'pro'

urlpatterns = [
    # صفحه اصلی
    path('', views.proorder_page, name='proorder_page'),

    # ==================== API ها ====================
    # مرحله ۱: نصبیات + PDFها
    path('api/installations/', views.get_installations, name='get_installations'),

    # مرحله ۲: جنس‌ها
    path('api/installations/<int:installation_id>/materials/',
         views.get_materials_by_installation,
         name='get_materials_by_installation'),

    # مرحله ۳: طرح‌های آماده
    path('api/installations/<int:installation_id>/templates/',
         views.get_templates_by_installation,
         name='get_templates_by_installation'),

    # محاسبه قیمت
    path('api/calculate-price/', views.calculate_price, name='calculate_price'),

    # ثبت نهایی
    path('api/create-order/', views.create_pro_order, name='create_pro_order'),

    # ==================== پنل کاربر ====================
    path('panel/user/pro-orders/',
         panel.ProUserOrdersPanelView.as_view(),
         name='user_pro_orders_panel'),

    path('panel/api/user/pro-orders/list/',
         panel.UserProOrdersListAPIView.as_view(),
         name='user_api_pro_orders_list'),

    path('panel/api/user/pro-orders/<uuid:order_id>/',
         panel.UserProOrderDetailAPIView.as_view(),
         name='user_api_pro_order_detail'),

    path('panel/api/user/pro-orders/approve-design/',
         panel.UserApproveDesignAPIView.as_view(),
         name='user_api_pro_approve_design'),

    path('panel/api/user/pro-orders/reject-design/',
         panel.UserRejectDesignAPIView.as_view(),
         name='user_api_pro_reject_design'),

    path('panel/api/user/pro-orders/cancel/',
         panel.UserCancelOrderAPIView.as_view(),
         name='user_api_pro_cancel_order'),
]