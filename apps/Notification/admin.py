# apps/notifications/admin.py

from django.contrib import admin
from .models import OrderStatusNotification


@admin.register(OrderStatusNotification)
class OrderStatusNotificationAdmin(admin.ModelAdmin):
    """پنل ادمین ساده برای اعلان‌ها"""

    # چی نشون بده
    list_display = (
        'id',
        'get_order_number',
        'get_user_mobile',
        'old_status',
        'new_status',
        'is_sent',
        'created_at',
    )

    # فیلترها
    list_filter = ('new_status', 'is_sent')

    # جستجو
    search_fields = ('order__order_number', 'user__mobileNumber', 'message')

    # ویرایش مستقیم
    list_editable = ('is_sent',)

    # فقط خواندنی
    readonly_fields = ('created_at', 'status_changed_at')

    # ترتیب
    ordering = ('-created_at',)

    # تعداد در صفحه
    list_per_page = 20

    def get_order_number(self, obj):
        return obj.order.order_number
    get_order_number.short_description = 'شماره سفارش'

    def get_user_mobile(self, obj):
        return obj.user.mobileNumber if obj.user else '---'
    get_user_mobile.short_description = 'موبایل کاربر'