# apps/pro/urls.py

from django.urls import path
from .views import dashboard
from .views import orders
from .views import peyment
from .views import pro
from .views import slider
from .views import postuser
from .views import users
from .views import products
from .views import role
from .views import photoshop
from .views import checkview

app_name = 'panel'

urlpatterns = [

    path('',dashboard.main,name='index'),
    path('user-offline/', dashboard.user_offline, name='user_offline'),
    path('update-activity/', dashboard.update_activity, name='update_activity'),
    path('api/dashboard/', dashboard.dashboard_api, name='dashboard_api'),
    # ================start order=======
    path('admin/orders/', orders.admin_orders_panel, name='admin_orders_panel'),

    # APIها
    path('api/orders/list/', orders.api_orders_list, name='api_orders_list'),
    path('api/orders/change-status/', orders.api_change_order_status, name='api_change_order_status'),
    path('api/orders/<uuid:order_id>/', orders.api_order_detail, name='api_order_detail'),
    path('api/orders/chart-data/', orders.api_orders_chart_data, name='api_orders_chart_data'),
    path('api/orders/update-tracking/', orders.api_update_tracking_code, name='api_update_tracking_code'),
    path('api/orders/verify-receipt/', orders.api_verify_receipt, name='api_verify_receipt'),

    path('panel/api/orders/verify-receipt/', orders.api_verify_receipt, name='api_verify_receipt'),
    # ==============
    path('admin/payments/', peyment.admin_payments_panel, name='admin_payments_panel'),
    path('api/payments/list/', peyment.api_payments_list, name='api_payments_list'),
    path('api/payments/chart-data/', peyment.api_payments_chart_data, name='api_payments_chart_data'),
    path('api/payments/<int:payment_id>/', peyment.api_payment_detail, name='api_payment_detail'),
    path('api/payments/update-status/', peyment.api_update_payment_status, name='api_update_payment_status'),
    #========================
    path('admin/print-orders/', pro.admin_print_orders_panel, name='admin_print_orders_panel'),
    path('api/print-orders/list/', pro.api_print_orders_list, name='api_print_orders_list'),
    path('api/print-orders/chart-data/', pro.api_print_orders_chart_data, name='api_print_orders_chart_data'),
    path('api/print-orders/<uuid:order_id>/', pro.api_print_order_detail, name='api_print_order_detail'),
    path('api/print-orders/update-status/', pro.api_update_print_order_status, name='api_update_print_order_status'),
    # ===================
    path('admin/slider/', slider.admin_slider_panel, name='admin_slider_panel'),
    path('api/slider/list/', slider.api_slider_list, name='api_slider_list'),
    path('api/slider/<int:slider_id>/', slider.api_slider_detail, name='api_slider_detail'),
    path('api/slider/create/', slider.api_slider_create, name='api_slider_create'),
    path('api/slider/update/<int:slider_id>/', slider.api_slider_update, name='api_slider_update'),
    path('api/slider/delete/<int:slider_id>/', slider.api_slider_delete, name='api_slider_delete'),
    path('api/slider/toggle/<int:slider_id>/', slider.api_slider_toggle_status, name='api_slider_toggle'),
    path('api/slider/reorder/', slider.api_slider_reorder, name='api_slider_reorder'),
    path('api/add-user/', postuser.api_add_user, name='api_add_user'),
    path('api/admin-login-check/', postuser.api_admin_login_check, name='api_admin_login_check'),
    # ================
    path('spi/userspanel', users.admin_panel_index, name='userindex'),

    # ============= API های داشبورد =============
    path('api/dashboard/stats/', users.api_dashboard_stats, name='api_dashboard_stats'),

    # ============= API های مدیریت کاربران =============
    # لیست کاربران با فیلتر و جستجو
    path('api/users/', users.api_users_list, name='api_users_list'),

    # دریافت جزئیات کامل یک کاربر
    path('api/users/<uuid:user_id>/', users.api_user_detail, name='api_user_detail'),

    # ایجاد کاربر جدید
    path('api/users/create/', users.api_user_create, name='api_user_create'),

    # ویرایش کاربر
    path('api/users/<uuid:user_id>/update/', users.api_user_update, name='api_user_update'),

    # حذف کاربر (سافت یا هارد دیلیت)
    path('api/users/<uuid:user_id>/delete/', users.api_user_delete, name='api_user_delete'),

    # بن/آنبان کردن کاربر
    path('api/users/<uuid:user_id>/toggle-ban/', users.api_user_toggle_ban, name='api_user_toggle_ban'),

    # تغییر وضعیت آنلاین/آفلاین کاربر
    path('api/users/<uuid:user_id>/toggle-online/', users.api_user_toggle_online_status, name='api_user_toggle_online'),

    # افزایش/کاهش موجودی کیف پول
    path('api/users/<uuid:user_id>/update-wallet/', users.api_user_update_wallet, name='api_user_update_wallet'),

    # افزایش/کاهش امتیازات کاربر
    path('api/users/<uuid:user_id>/update-points/', users.api_user_update_points, name='api_user_update_points'),
    path('api/users/<uuid:user_id>/toggle-verified/', users.api_user_toggle_verified, name='api_user_toggle_verified'),
    path('api/users/<uuid:user_id>/toggle-payment/', users.api_user_toggle_payment, name='api_user_toggle_payment'),
        path('api/users/<str:user_id>/get-roles/', users.api_user_get_roles, name='api_user_get_roles'),
    path('api/users/<str:user_id>/update-roles/', users.api_user_update_roles, name='api_user_update_roles'),


    # ============================

    path('product_panel', products.product_admin_index, name='productindex'),

     path('api/products/', products.ProductAPIView.as_view(), name='product_list'),
    path('api/products/<int:product_id>/', products.ProductAPIView.as_view(), name='product_detail'),
    path('api/products/<int:product_id>/update/', products.ProductAPIView.as_view(), name='product_update'),
    path('api/products/<int:product_id>/delete/', products.ProductAPIView.as_view(), name='product_delete'),
    path('api/products/bulk-create/', products.BulkProductCreateView.as_view(), name='bulk_create'),
    path('api/products/bulk-price-update/', products.BulkPriceUpdateView.as_view(), name='bulk_price'),

    # آمار
    path('api/stats/', products.StatsAPIView.as_view(), name='stats'),

    # برندها
    path('api/brands/', products.BrandAPIView.as_view(), name='brand_list'),
    path('api/brands/create/', products.BrandAPIView.as_view(), name='brand_create'),
    path('api/brands/<int:brand_id>/delete/', products.BrandAPIView.as_view(), name='brand_delete'),

    # دسته‌بندی‌ها
    path('api/categories/', products.CategoryAPIView.as_view(), name='category_list'),
    path('api/categories/create/', products.CategoryAPIView.as_view(), name='category_create'),
    path('api/categories/<int:category_id>/delete/', products.CategoryAPIView.as_view(), name='category_delete'),

    # کاتالوگ‌ها
    path('api/catalogs/', products.CatalogAPIView.as_view(), name='catalog_list'),
    path('api/catalogs/create/', products.CatalogAPIView.as_view(), name='catalog_create'),
    path('api/catalogs/<int:catalog_id>/delete/', products.CatalogAPIView.as_view(), name='catalog_delete'),

    # واحدها
    path('api/sales-units/', products.SalesUnitAPIView.as_view(), name='sales_unit_list'),
    path('api/sales-units/create/', products.SalesUnitAPIView.as_view(), name='sales_unit_create'),
    path('api/package-units/', products.PackageUnitAPIView.as_view(), name='package_unit_list'),

    # ویژگی‌ها
    path('api/attributes/', products.AttributeAPIView.as_view(), name='attribute_list'),
    path('api/attributes/create/', products.AttributeAPIView.as_view(), name='attribute_create'),
    path('api/attributes/<int:attr_id>/delete/', products.AttributeAPIView.as_view(), name='attribute_delete'),

    # تخفیف‌ها
    path('api/discounts/', products.DiscountAPIView.as_view(), name='discount_list'),
    path('api/discounts/create/', products.DiscountAPIView.as_view(), name='discount_create'),
    path('api/discounts/<int:discount_id>/delete/', products.DiscountAPIView.as_view(), name='discount_delete'),
    path('api/discounts/<int:discount_id>/toggle/', products.DiscountAPIView.as_view(), {'action': 'toggle'}, name='discount_toggle'),
    # =========
           path('roles/', role.role_panel_view, name='role_panel'),

    # API ها - مسیرهای ثابت باید قبل از مسیرهای متغیر بیایند
    path('api/roles/create/', role.role_create_api, name='role_create_api'),
    path('api/roles/', role.roles_api, name='roles_api'),

    # مسیرهای دارای پارامتر (بعد از مسیرهای ثابت)
    path('api/roles/<str:role_id>/', role.role_detail_api, name='role_detail_api'),
    path('api/roles/<str:role_id>/update/', role.role_update_api, name='role_update_api'),
    path('api/roles/<str:role_id>/delete/', role.role_delete_api, name='role_delete_api'),
    path('api/roles/<str:role_id>/ban-urls/create/', role.ban_url_create_api, name='ban_url_create_api'),

    # مسیرهای ban-urls
    path('api/ban-urls/<str:ban_url_id>/update/', role.ban_url_update_api, name='ban_url_update_api'),
    path('api/ban-urls/<str:ban_url_id>/delete/', role.ban_url_delete_api, name='ban_url_delete_api'),

    # مسیرهای اختصاص کاربران
    path('api/roles/<str:role_id>/assign-users/', role.assign_users_to_role_api, name='assign_users_to_role_api'),
    path('api/roles/<str:role_id>/remove-user/<str:user_id>/', role.remove_user_from_role_api, name='remove_user_from_role_api'),
    # ==============
    path('operator/dashboard/', photoshop.operator_dashboard, name='operator_dashboard'),
    path('operator/order/<uuid:order_id>/', photoshop.order_detail, name='order_detail'),
    path('operator/order/<uuid:order_id>/upload/', photoshop.upload_design, name='upload_design'),
    path('operator/order/<uuid:order_id>/send-to-customer/', photoshop.send_to_customer, name='send_to_customer'),
    path('operator/order/<uuid:order_id>/complete/', photoshop.complete_order, name='complete_order'),
    path('operator/api/orders/list/', photoshop.api_orders_list, name='api_orders_list'),
    path('operator/api/orders/<uuid:order_id>/', photoshop.api_order_detail, name='api_order_detail'),
    path('customer/order/<uuid:order_id>/review/', photoshop.customer_review_page, name='customer_review'),
    path('api/order/<uuid:order_id>/approve/', photoshop.api_approve_design, name='api_approve'),
    path('api/order/<uuid:order_id>/reject/', photoshop.api_reject_design, name='api_reject'),
    # ==============

   path('admin/checks/', checkview.admin_check_list, name='admin_check_list'),
path('admin/api/check/list/', checkview.api_check_list, name='api_check_list'),
path('admin/api/check/<uuid:check_id>/', checkview.admin_check_detail, name='admin_check_detail'),
path('admin/check/verify/<uuid:check_id>/', checkview.admin_check_verify, name='admin_check_verify'),
path('admin/check/reject/<uuid:check_id>/', checkview.admin_check_reject, name='admin_check_reject'),
path('admin/check/finalize/<uuid:check_id>/', checkview.admin_check_finalize, name='admin_check_finalize'),
path('admin/check/bulk-action/', checkview.admin_check_bulk_action, name='admin_check_bulk_action'),
path('admin/check/export-csv/', checkview.admin_check_export_csv, name='admin_check_export_csv'),

]