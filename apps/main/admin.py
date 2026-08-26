# admin.py

from django.contrib import admin
from django.utils.html import format_html
from .models import Slider, Portfolio, PortfolioGallery, Music


# =========================================================
# ادمین اسلایدر
# =========================================================
@admin.register(Slider)
class SliderAdmin(admin.ModelAdmin):
    list_display = ['title', 'is_active', 'order', 'start_date', 'end_date', 'preview_image']
    list_filter = ['is_active', 'start_date', 'end_date']
    search_fields = ['title', 'description']
    list_editable = ['order', 'is_active']
    readonly_fields = ['created_at', 'updated_at', 'preview_image_large']

    fieldsets = (
        ('اطلاعات اصلی', {
            'fields': ('title', 'description', 'is_active', 'order','isdiscount',)
        }),
        ('عکس‌ها', {
            'fields': ('image_pc', 'image_mobile', 'preview_image_large'),
            'classes': ('wide',),
        }),
        ('تاریخ و زمان', {
            'fields': ('start_date', 'end_date'),
            'classes': ('wide',),
        }),
        ('لینک', {
            'fields': ('link',),
        }),
        ('اطلاعات سیستمی', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',),
        }),
    )

    def preview_image(self, obj):
        """نمایش عکس کوچک در لیست"""
        if obj.image_pc:
            return format_html('<img src="{}" width="50" height="30" style="border-radius: 5px;" />', obj.image_pc.url)
        return "بدون عکس"
    preview_image.short_description = "پیش‌نمایش"

    def preview_image_large(self, obj):
        """نمایش عکس بزرگ در فرم"""
        if obj.image_pc:
            return format_html('<img src="{}" width="300" height="100" style="border-radius: 10px; margin-top: 10px;" />', obj.image_pc.url)
        return "عکسی آپلود نشده است"
    preview_image_large.short_description = "پیش‌نمایش عکس پی‌سی"

    def save_model(self, request, obj, form, change):
        """ذخیره با لاگ"""
        if not change:
            obj.created_by = request.user
        super().save_model(request, obj, form, change)


# =========================================================
# ادمین نمونه کار
# =========================================================
class PortfolioGalleryInline(admin.TabularInline):
    model = PortfolioGallery
    extra = 3


@admin.register(Portfolio)
class PortfolioAdmin(admin.ModelAdmin):
    list_display = ['title', 'user', 'created_at']
    list_filter = ['created_at']
    search_fields = ['title', 'user__mobileNumber']
    inlines = [PortfolioGalleryInline]


@admin.register(PortfolioGallery)
class PortfolioGalleryAdmin(admin.ModelAdmin):
    list_display = ['portfolio', 'image']


# =========================================================
# ادمین آهنگ
# =========================================================
@admin.register(Music)
class MusicAdmin(admin.ModelAdmin):
    list_display = ['title', 'artist', 'preview_cover', 'created_at']
    search_fields = ['title', 'artist']
    list_filter = ['created_at']
    readonly_fields = ['created_at', 'preview_cover_large']

    fieldsets = (
        ('اطلاعات آهنگ', {
            'fields': ('title', 'artist')
        }),
        ('فایل‌ها', {
            'fields': ('audio_file', 'cover', 'preview_cover_large'),
            'classes': ('wide',),
        }),
        ('اطلاعات سیستمی', {
            'fields': ('created_at',),
            'classes': ('collapse',),
        }),
    )

    def preview_cover(self, obj):
        """نمایش کاور کوچک در لیست"""
        if obj.cover:
            return format_html('<img src="{}" width="50" height="50" style="border-radius: 5px;" />', obj.cover.url)
        return "بدون کاور"
    preview_cover.short_description = "کاور"

    def preview_cover_large(self, obj):
        """نمایش کاور بزرگ در فرم"""
        if obj.cover:
            return format_html('<img src="{}" width="200" height="200" style="border-radius: 10px; margin-top: 10px;" />', obj.cover.url)
        return "کاوری آپلود نشده است"
    preview_cover_large.short_description = "پیش‌نمایش کاور"