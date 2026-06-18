# admin.py - یه کم قشنگتر اما بازم ساده
from django.contrib import admin
from django.utils.html import format_html
from .models import Discount, Coupon


@admin.register(Discount)
class DiscountAdmin(admin.ModelAdmin):
    list_display = ('title', 'amount_display', 'scope', 'is_active', 'date_range')
    list_filter = ('is_active', 'discount_type', 'scope')
    search_fields = ('title',)
    list_editable = ('is_active',)

    def amount_display(self, obj):
        if obj.discount_type == 'percent':
            return f"{obj.amount}%"
        return f"{obj.amount:,.0f} تومان"
    amount_display.short_description = 'مقدار'

    def date_range(self, obj):
        if obj.start_date and obj.end_date:
            return f"{obj.start_date.date()} → {obj.end_date.date()}"
        return '-'
    date_range.short_description = 'بازه'


@admin.register(Coupon)
class CouponAdmin(admin.ModelAdmin):
    list_display = ('code', 'title', 'amount_display', 'is_active', 'date_range')
    list_filter = ('is_active', 'discount_type')
    search_fields = ('code', 'title')
    list_editable = ('is_active',)

    def amount_display(self, obj):
        if obj.discount_type == 'percent':
            return f"{obj.amount}%"
        return f"{obj.amount:,.0f} تومان"
    amount_display.short_description = 'مقدار'

    def date_range(self, obj):
        if obj.start_date and obj.end_date:
            return f"{obj.start_date.date()} → {obj.end_date.date()}"
        return '-'
    date_range.short_description = 'بازه'