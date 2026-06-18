from django.contrib import admin
from django.utils.html import format_html
from .models import (
    Installation, InstallationMaterial, MaterialPDF,
    ReadyTemplate, TemplateGallery, OrderMaterial
)

# ==================== تنظیمات ظاهری ====================
admin.site.site_header = "مدیریت نصبیات"
admin.site.site_title = "پنل مدیریت"
admin.site.index_title = "داشبورد"

# ==================== 1. نصبیات ====================
@admin.register(Installation)
class InstallationAdmin(admin.ModelAdmin):
    list_display = ['title', 'order', 'is_active', 'image_preview', 'created_at']
    list_editable = ['order', 'is_active']
    list_filter = ['is_active']
    search_fields = ['title', 'description']
    list_per_page = 20

    def image_preview(self, obj):
        if obj.main_image:
            return format_html('<img src="{}" width="50" height="50" style="border-radius:8px; object-fit:cover"/>', obj.main_image.url)
        return "-"
    image_preview.short_description = "عکس"

# ==================== 2. جنس نصبیات ====================
@admin.register(InstallationMaterial)
class InstallationMaterialAdmin(admin.ModelAdmin):
    list_display = ['title', 'installation', 'price_multiplier', 'is_active', 'order']
    list_editable = ['price_multiplier', 'is_active', 'order']
    list_filter = ['installation', 'is_active']
    search_fields = ['title']

    def image_preview(self, obj):
        if obj.image:
            return format_html('<img src="{}" width="40" height="40" style="border-radius:6px"/>', obj.image.url)
        return "-"
    image_preview.short_description = "عکس"

# ==================== 3. PDFهای جنس ====================
@admin.register(MaterialPDF)
class MaterialPDFAdmin(admin.ModelAdmin):
    list_display = ['title', 'material', 'code', 'download_count', 'created_at']
    list_filter = ['material__installation', 'material']
    search_fields = ['title', 'code']
    readonly_fields = ['code', 'download_count']

    actions = ['reset_download']

    def reset_download(self, request, queryset):
        queryset.update(download_count=0)
        self.message_user(request, "تعداد دانلودها بازنشانی شد")
    reset_download.short_description = "بازنشانی تعداد دانلود"

# ==================== 4. طرح‌های آماده ====================
@admin.register(ReadyTemplate)
class ReadyTemplateAdmin(admin.ModelAdmin):
    list_display = ['title', 'installation', 'width', 'height', 'is_active', 'order']
    list_editable = ['is_active', 'order']
    list_filter = ['installation', 'is_active']
    search_fields = ['title']

    def image_preview(self, obj):
        if obj.image:
            return format_html('<img src="{}" width="40" height="40" style="border-radius:6px"/>', obj.image.url)
        return "-"
    image_preview.short_description = "عکس"

# ==================== 5. گالری طرح‌ها ====================
@admin.register(TemplateGallery)
class TemplateGalleryAdmin(admin.ModelAdmin):
    list_display = ['template', 'order', 'image_preview']
    list_editable = ['order']
    list_filter = ['template']

    def image_preview(self, obj):
        if obj.image:
            return format_html('<img src="{}" width="50" height="50" style="border-radius:6px; object-fit:cover"/>', obj.image.url)
        return "-"
    image_preview.short_description = "عکس"

# ==================== 6. سفارشات (مهم) ====================
@admin.register(OrderMaterial)
class OrderMaterialAdmin(admin.ModelAdmin):
    list_display = ['id_short', 'installation', 'material', 'dimensions', 'status_badge', 'created_at']
    list_filter = ['status', 'installation', 'created_at']
    search_fields = ['id', 'notes', 'user__username']
    readonly_fields = ['id', 'created_at', 'updated_at']
    list_per_page = 25


    fieldsets = (
        ('اطلاعات سفارش', {
            'fields': ('id', 'user', 'status', 'design_type', 'notes')
        }),
        ('محصولات', {
            'fields': ('installation', 'material', 'pdf_document', 'ready_template')
        }),
        ('ابعاد', {
            'fields': ('length', 'width')
        }),
        ('عکس و قیمت', {
            'fields': ('plan_image', 'total_price'),
            'classes': ('collapse',)
        }),
        ('تاریخ', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    def id_short(self, obj):
        return str(obj.id)[:8]
    id_short.short_description = "شماره"

    def dimensions(self, obj):
        return f"{obj.length}×{obj.width} متر"
    dimensions.short_description = "ابعاد"

    def status_badge(self, obj):
        colors = {
            'pending': '#f39c12',
            'confirmed': '#3498db',
            'processing': '#9b59b6',
            'ready': '#1abc9c',
            'delivered': '#27ae60',
            'cancelled': '#e74c3c'
        }
        status_text = dict(OrderMaterial.STATUS_CHOICES).get(obj.status, obj.status)
        return format_html(
            '<span style="background:{}; color:white; padding:3px 10px; border-radius:20px; font-size:11px">{}</span>',
            colors.get(obj.status, '#95a5a6'),
            status_text
        )
    status_badge.short_description = "وضعیت"

    # اکشن‌های گروهی
    actions = ['mark_confirmed', 'mark_processing', 'mark_delivered', 'mark_cancelled']

    def mark_confirmed(self, request, queryset):
        queryset.update(status='confirmed')
        self.message_user(request, "✅ تأیید شد")
    mark_confirmed.short_description = "تأیید سفارش"

    def mark_processing(self, request, queryset):
        queryset.update(status='processing')
        self.message_user(request, "⚙️ در حال ساخت")
    mark_processing.short_description = "در حال ساخت"

    def mark_delivered(self, request, queryset):
        queryset.update(status='delivered')
        self.message_user(request, "🚚 تحویل شد")
    mark_delivered.short_description = "تحویل شد"

    def mark_cancelled(self, request, queryset):
        queryset.update(status='cancelled')
        self.message_user(request, "❌ لغو شد")
    mark_cancelled.short_description = "لغو سفارش"



# admin.py
from django.contrib import admin
from django.utils.html import format_html
from django.utils.safestring import mark_safe
from .models import OrderDesignStatus, OrderReviewHistory


@admin.register(OrderDesignStatus)
class OrderDesignStatusAdmin(admin.ModelAdmin):
    list_display = ['order_link', 'status_badge', 'operator_message_preview', 'delivered_at', 'updated_at']
    list_filter = ['status', 'created_at']
    search_fields = ['order__id', 'order__user__username', 'operator_message']
    readonly_fields = ['created_at', 'updated_at', 'image_preview', 'psd_link']
    list_per_page = 20
    raw_id_fields = ['order']

    fieldsets = (
        ('اطلاعات سفارش', {
            'fields': ('order', 'status')
        }),
        ('فایل‌های طراحی', {
            'fields': ('final_design_image', 'image_preview', 'final_design_psd', 'psd_link')
        }),
        ('پیام و تاریخ', {
            'fields': ('operator_message', 'delivered_at', 'created_at', 'updated_at')
        }),
    )

    def order_link(self, obj):
        url = f"/admin/pro/ordermaterial/{obj.order.id}/change/"
        return format_html('<a href="{}" target="_blank">{}</a>', url, str(obj.order.id)[:8])
    order_link.short_description = "شماره سفارش"

    def status_badge(self, obj):
        colors = {
            'pending_design': 'gray',
            'designing': 'orange',
            'ready_for_review': 'blue',
            'approved': 'green',
            'rejected': 'red',
            'finalized': 'darkgreen',
        }
        color = colors.get(obj.status, 'gray')
        return format_html('<span style="background:{}; color:white; padding:3px 8px; border-radius:12px;">{}</span>',
                          color, obj.get_status_display())
    status_badge.short_description = "وضعیت"

    def operator_message_preview(self, obj):
        if obj.operator_message:
            return obj.operator_message[:50] + ('...' if len(obj.operator_message) > 50 else '')
        return "-"
    operator_message_preview.short_description = "پیام اپراتور"

    def image_preview(self, obj):
        if obj.final_design_image:
            return format_html('<img src="{}" style="max-width:150px; max-height:100px; border-radius:8px;" />', obj.final_design_image.url)
        return "-"
    image_preview.short_description = "پیش‌نمایش تصویر"

    def psd_link(self, obj):
        if obj.final_design_psd:
            return format_html('<a href="{}" target="_blank">📎 دانلود فایل PSD</a>', obj.final_design_psd.url)
        return "-"
    psd_link.short_description = "فایل PSD"


@admin.register(OrderReviewHistory)
class OrderReviewHistoryAdmin(admin.ModelAdmin):
    list_display = ['order_link', 'action_badge', 'message_preview', 'reject_round_display', 'created_by_name', 'created_at']
    list_filter = ['action', 'reject_round', 'created_at']
    search_fields = ['order__id', 'message', 'created_by__username']
    readonly_fields = ['created_at', 'attached_image_preview']
    list_per_page = 20
    raw_id_fields = ['order', 'created_by']

    fieldsets = (
        ('اطلاعات اصلی', {
            'fields': ('order', 'action', 'message')
        }),
        ('مرحله رد', {
            'fields': ('reject_round',)
        }),
        ('فایل پیوست', {
            'fields': ('attached_image', 'attached_image_preview')
        }),
        ('اطلاعات تکمیلی', {
            'fields': ('created_by', 'created_at')
        }),
    )

    def order_link(self, obj):
        url = f"/admin/pro/ordermaterial/{obj.order.id}/change/"
        return format_html('<a href="{}" target="_blank">{}</a>', url, str(obj.order.id)[:8])
    order_link.short_description = "شماره سفارش"

    def action_badge(self, obj):
        colors = {
            'operator_submit': '#667eea',
            'user_approve': '#10b981',
            'user_reject': '#ef4444',
        }
        icons = {
            'operator_submit': '📤',
            'user_approve': '✅',
            'user_reject': '❌',
        }
        color = colors.get(obj.action, 'gray')
        icon = icons.get(obj.action, '')
        return format_html('<span style="background:{}; color:white; padding:3px 8px; border-radius:12px;">{} {}</span>',
                          color, icon, obj.get_action_display())
    action_badge.short_description = "نوع اقدام"

    def message_preview(self, obj):
        if obj.message:
            return obj.message[:50] + ('...' if len(obj.message) > 50 else '')
        return "-"
    message_preview.short_description = "پیام"

    def reject_round_display(self, obj):
        if obj.reject_round:
            return format_html('<span style="background:#ef4444; color:white; padding:2px 8px; border-radius:12px;">{} از ۳</span>', obj.reject_round)
        return "-"
    reject_round_display.short_description = "مرحله رد"

    def created_by_name(self, obj):
        if obj.created_by:
            return obj.created_by.username
        return "-"
    created_by_name.short_description = "انجام دهنده"

    def attached_image_preview(self, obj):
        if obj.attached_image:
            return format_html('<img src="{}" style="max-width:100px; max-height:80px; border-radius:8px;" />', obj.attached_image.url)
        return "-"
    attached_image_preview.short_description = "پیش‌نمایش تصویر پیوست"