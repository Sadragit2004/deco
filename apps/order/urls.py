from django.urls import path
from . import viewcar
from . import views

app_name = 'order'

urlpatterns = [
    # APIهای سبد خرید
    path('cart/add/', viewcar.cart_add_api, name='cart_add_api'),
    path('cart/remove/', viewcar.cart_remove_api, name='cart_remove_api'),
    path('cart/update/', viewcar.cart_update_api, name='cart_update_api'),
    path('cart/clear/', viewcar.cart_clear_api, name='cart_clear_api'),
    path('cart/data/', viewcar.cart_data_api, name='cart_data_api'),

    # صفحات اصلی سفارش
    path('create/', views.CreateOrderView.as_view(), name='create_order'),
    path('checkout/<uuid:order_id>/', views.checkout, name='checkout'),
    path('my-orders/', views.user_orders, name='user_orders'),
    path('order-detail/<uuid:order_id>/', views.order_detail, name='order_detail'),

    # APIهای عمومی
    path('api/order/<uuid:order_id>/get-total/', views.get_order_total_api, name='get_order_total_api'),

    # ==================== APIهای سیستم پرداخت با چک ====================
    # ایجاد مدل چک هنگام تیک زدن کاربر
    path('api/check/create/<uuid:order_id>/', views.create_check_payment_api, name='create_check_api'),

    # آپلود عکس چک
    path('api/check/upload/<uuid:order_id>/', views.upload_check_image_api, name='upload_check_api'),

    # لغو پرداخت با چک
    path('api/check/cancel/<uuid:order_id>/', views.cancel_check_payment_api, name='cancel_check_api'),

    # دریافت وضعیت چک سفارش
    path('api/check/status/<uuid:order_id>/', views.get_check_status_api, name='check_status_api'),
]