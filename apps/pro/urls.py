# apps/pro/urls.py

from django.urls import path
from . import views
from . import panel

app_name = 'pro'

urlpatterns = [
    # صفحه اصلی
    path('', views.proorder_page, name='proorder_page'),

    # API ها با نام‌های سازگار با فرانت‌اند
    path('api/installations/', views.get_installations, name='get_installations'),
    path('api/installations/<int:installation_id>/materials/', views.get_materials_by_installation, name='get_materials_by_installation'),
    path('api/materials/<int:material_id>/pdfs/', views.get_pdfs_by_material, name='get_pdfs_by_material'),
    path('api/verify-pdf/', views.verify_pdf_code, name='verify_pdf_code'),
    path('api/installations/<int:installation_id>/templates/', views.get_templates_by_installation, name='get_templates_by_installation'),
    path('api/calculate-price/', views.calculate_price, name='calculate_price'),
    path('api/submit-order/', views.submit_order, name='submit_order'),
    path('api/create-order/', views.create_pro_order, name='create_pro_order'),
    path('panel/user/pro-orders/', panel.ProUserOrdersPanelView.as_view(), name='user_pro_orders_panel'),

    # API ها
    path('panel/api/user/pro-orders/list22/', panel.UserProOrdersListAPIView.as_view(), name='user_api_pro_orders_list'),
    path('panel/api/user/pro-orders/<uuid:order_id>/', panel.UserProOrderDetailAPIView.as_view(), name='user_api_pro_order_detail'),
    path('panel/api/user/pro-orders/approve-design/', panel.UserApproveDesignAPIView.as_view(), name='user_api_pro_approve_design'),
    path('panel/api/user/pro-orders/reject-design/', panel.UserRejectDesignAPIView.as_view(), name='user_api_pro_reject_design'),
    path('panel/api/user/pro-orders/cancel/', panel.UserCancelOrderAPIView.as_view(), name='user_api_pro_cancel_order'),
]