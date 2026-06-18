from django.contrib import admin
from django.urls import reverse
from django.utils.html import format_html
from .models import Order, OrderItem, OrderStatusHistory, ShippingMethod, OrderStatus, PaymentReceipt, Wishlist
from django.db import transaction


@admin.register(ShippingMethod)
class ShippingMethodAdmin(admin.ModelAdmin):
    list_display = ['name', 'base_cost', 'delivery_time', 'is_active', 'sort_order']
    list_editable = ['base_cost', 'is_active', 'sort_order']
    list_filter = ['is_active']
    search_fields = ['name']


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    readonly_fields = ['product_title', 'quantity', 'unit_price', 'total']
    can_delete = False


class OrderStatusHistoryInline(admin.TabularInline):
    model = OrderStatusHistory
    extra = 0
    readonly_fields = ['status', 'note', 'created_at']
    can_delete = False


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ['order_number', 'user_info', 'total_display', 'status_badge', 'order_date']
    list_filter = ['status', 'created_at']
    search_fields = ['order_number', 'user__mobileNumber']
    readonly_fields = ['order_number', 'subtotal', 'total', 'created_at', 'paid_at', 'cancelled_at', 'earned_points']
    inlines = [OrderItemInline, OrderStatusHistoryInline]

    fieldsets = (
        ('اطلاعات اصلی', {'fields': ('order_number', 'user', 'status', 'description','receipt_verified','used_from_wallet')}),
        ('اطلاعات ارسال', {'fields': ('address', 'shipping_method', 'tracking_code')}),
        ('مبالغ', {'fields': ('subtotal', 'discount_amount', 'coupon_discount', 'shipping_cost', 'total')}),
        ('زمان‌بندی', {'fields': ('created_at', 'paid_at', 'shipped_date', 'delivered_date', 'cancelled_at')}),
        ('امتیازات', {'fields': ('earned_points', 'used_points')}),
        ('یادداشت‌ها', {'fields': ('admin_note',)}),
    )

    def user_info(self, obj):
        if obj.user:
            return f"{obj.user.mobileNumber} - {obj.user.name or ''}"
        return 'مهمان'
    user_info.short_description = 'کاربر'

    def total_display(self, obj):
        return f"{int(obj.total):,} تومان" if obj.total else '0 تومان'
    total_display.short_description = 'مبلغ نهایی'

    def order_date(self, obj):
        return obj.created_at.strftime('%Y/%m/%d %H:%M')
    order_date.short_description = 'تاریخ ثبت'

    def status_badge(self, obj):
        colors = {
            'pending': '#f59e0b',
            'paid': '#10b981',
            'processing': '#3b82f6',
            'packaging': '#8b5cf6',
            'shipped': '#06b6d4',
            'delivered': '#059669',
            'cancelled': '#ef4444',
        }
        names = dict(OrderStatus.choices)
        color = colors.get(obj.status, '#6b7280')
        name = names.get(obj.status, obj.status)
        return format_html('<span style="background:{}; color:white; padding:4px 12px; border-radius:20px;">{}</span>', color, name)
    status_badge.short_description = 'وضعیت'


@admin.register(PaymentReceipt)
class PaymentReceiptAdmin(admin.ModelAdmin):
    list_display = ['id', 'order_number', 'user_mobile', 'payment_amount_display', 'status_badge', 'verified_at']
    list_filter = ['status']
    search_fields = ['order__order_number', 'order__user__mobileNumber', 'receipt_number']
    readonly_fields = ['uploaded_at']

    fieldsets = (
        ('اطلاعات سفارش', {'fields': ('order',)}),
        ('فایل رسید', {'fields': ('receipt_file',)}),
        ('اطلاعات رسید', {'fields': ('receipt_number', 'bank_name', 'tracking_code', 'payment_date', 'payment_amount')}),
        ('وضعیت', {'fields': ('status', 'admin_note', 'rejection_reason', 'verified_by', 'verified_at')}),
    )

    def order_number(self, obj):
        return obj.order.order_number
    order_number.short_description = 'شماره سفارش'
    order_number.admin_order_field = 'order__order_number'

    def user_mobile(self, obj):
        if obj.order and obj.order.user:
            return obj.order.user.mobileNumber
        return '-'
    user_mobile.short_description = 'شماره موبایل'

    def payment_amount_display(self, obj):
        if obj.payment_amount:
            return f"{int(obj.payment_amount):,} تومان"
        return '-'
    payment_amount_display.short_description = 'مبلغ'

    def status_badge(self, obj):
        if obj.status == 0:
            return format_html('<span style="background:#f39c12; color:white; padding:3px 12px; border-radius:20px;">⏳ در انتظار</span>')
        elif obj.status == 1:
            return format_html('<span style="background:#27ae60; color:white; padding:3px 12px; border-radius:20px;">✓ تایید شده</span>')
        else:
            return format_html('<span style="background:#e74c3c; color:white; padding:3px 12px; border-radius:20px;">✗ رد شده</span>')
    status_badge.short_description = 'وضعیت'


@admin.register(OrderItem)
class OrderItemAdmin(admin.ModelAdmin):
    list_display = ['product_title', 'order_number', 'quantity', 'unit_price_display', 'total_display']
    search_fields = ['product_title', 'order__order_number']

    def order_number(self, obj):
        return obj.order.order_number
    order_number.short_description = 'شماره سفارش'

    def unit_price_display(self, obj):
        return f"{int(obj.unit_price):,} تومان" if obj.unit_price else '0'
    unit_price_display.short_description = 'قیمت واحد'

    def total_display(self, obj):
        return f"{int(obj.total):,} تومان" if obj.total else '0'
    total_display.short_description = 'جمع'


@admin.register(OrderStatusHistory)
class OrderStatusHistoryAdmin(admin.ModelAdmin):
    list_display = ['order_number', 'status', 'note_short', 'created_at']
    list_filter = ['status']

    def order_number(self, obj):
        return obj.order.order_number
    order_number.short_description = 'شماره سفارش'

    def note_short(self, obj):
        return obj.note[:50] if obj.note else '-'
    note_short.short_description = 'توضیحات'


@admin.register(Wishlist)
class WishlistAdmin(admin.ModelAdmin):
    list_display = ['user_mobile', 'product_title', 'added_at']
    search_fields = ['user__mobileNumber', 'product__title']

    def user_mobile(self, obj):
        return obj.user.mobileNumber
    user_mobile.short_description = 'کاربر'