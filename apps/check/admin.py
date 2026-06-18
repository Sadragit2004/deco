# apps/payment/admin.py

from django.contrib import admin
from django.utils.html import format_html
from .models import CheckPayment, CheckPaymentStatus, CheckPaymentHistory


@admin.register(CheckPayment)
class CheckPaymentAdmin(admin.ModelAdmin):
    list_display = ['tracking_number', 'get_user_mobile', 'get_order_number', 'check_amount', 'status', 'has_image', 'created_at']
    list_filter = ['status', 'is_finalized']
    search_fields = ['tracking_number', 'user__mobileNumber', 'order__order_number', 'check_number']
    readonly_fields = ['tracking_number', 'created_at', 'updated_at']

    fieldsets = (
        ('اطلاعات اصلی', {
            'fields': ('tracking_number', 'user', 'order', 'pro_order', 'status', 'is_finalized')
        }),
        ('اطلاعات چک', {
            'fields': ('check_image', 'check_amount', 'bank_name', 'check_number', 'check_date', 'description')
        }),
        ('اطلاعات اداری', {
            'fields': ('admin_note', 'rejection_reason', 'verified_by', 'verified_at')
        }),
    )

    def get_user_mobile(self, obj):
        if obj.user:
            return obj.user.mobileNumber or obj.user.phone or '-'
        return '-'
    get_user_mobile.short_description = 'موبایل کاربر'

    def get_order_number(self, obj):
        if obj.order:
            return obj.order.order_number
        elif obj.pro_order:
            return str(obj.pro_order.id)[:8]
        return '-'
    get_order_number.short_description = 'شماره سفارش'

    def has_image(self, obj):
        return 'دارد' if obj.check_image else 'ندارد'
    has_image.short_description = 'عکس چک'

    actions = ['make_verified', 'make_rejected']

    def make_verified(self, request, queryset):
        for item in queryset.filter(status='pending'):
            item.status = 'verified'
            item.verified_by = request.user
            item.verified_at = timezone.now()
            item.save()
        self.message_user(request, 'چک‌ها تایید شدند')
    make_verified.short_description = 'تایید چک‌های انتخاب شده'

    def make_rejected(self, request, queryset):
        for item in queryset.filter(status='pending'):
            item.status = 'rejected'
            item.save()
        self.message_user(request, 'چک‌ها رد شدند')
    make_rejected.short_description = 'رد چک‌های انتخاب شده'


@admin.register(CheckPaymentHistory)
class CheckPaymentHistoryAdmin(admin.ModelAdmin):
    list_display = ['check_payment', 'action', 'message', 'created_at']
    list_filter = ['action']
    search_fields = ['check_payment__tracking_number', 'message']
    readonly_fields = ['check_payment', 'action', 'message', 'created_by', 'created_at']

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False