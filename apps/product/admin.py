# admin.py - نسخه نهایی کاملاً تصحیح شده

from django.contrib import admin
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _
from . import models


# ==========================================
# Custom Admin Actions
# ==========================================
@admin.action(description='فعال کردن موارد انتخاب شده')
def make_active(modeladmin, request, queryset):
    queryset.update(status=True)


@admin.action(description='غیرفعال کردن موارد انتخاب شده')
def make_inactive(modeladmin, request, queryset):
    queryset.update(status=False)


# ==========================================
# 1. SalesUnit Admin
# ==========================================
@admin.register(models.SalesUnit)
class SalesUnitAdmin(admin.ModelAdmin):
    list_display = ['name', 'name_en', 'symbol', 'status', 'sort_order']
    list_display_links = ['name']
    list_editable = ['status', 'sort_order']
    list_filter = ['status']
    search_fields = ['name', 'name_en', 'symbol']
    readonly_fields = ['created_at', 'updated_at']
    actions = [make_active, make_inactive]

    fieldsets = (
        ('اطلاعات واحد فروش', {
            'fields': ('name', 'name_en', 'symbol')
        }),
        ('تنظیمات نمایش', {
            'fields': ('status', 'sort_order')
        }),
        ('اطلاعات سیستمی', {
            'fields': ('created_at', 'updated_at', 'created_by', 'updated_by'),
            'classes': ('collapse',)
        }),
    )

    def save_model(self, request, obj, form, change):
        if not change:
            obj.created_by = request.user
        obj.updated_by = request.user
        super().save_model(request, obj, form, change)


# ==========================================
# 2. PackageUnit Admin
# ==========================================
@admin.register(models.PackageUnit)
class PackageUnitAdmin(admin.ModelAdmin):
    list_display = ['name', 'name_en', 'symbol', 'icon_display', 'status', 'sort_order']
    list_display_links = ['name']
    list_editable = ['status', 'sort_order']
    list_filter = ['status']
    search_fields = ['name', 'name_en', 'symbol']
    readonly_fields = ['created_at', 'updated_at']
    actions = [make_active, make_inactive]

    fieldsets = (
        ('اطلاعات واحد بسته‌بندی', {
            'fields': ('name', 'name_en', 'symbol', 'icon')
        }),
        ('تنظیمات نمایش', {
            'fields': ('status', 'sort_order')
        }),
        ('اطلاعات سیستمی', {
            'fields': ('created_at', 'updated_at', 'created_by', 'updated_by'),
            'classes': ('collapse',)
        }),
    )

    def icon_display(self, obj):
        if obj.icon:
            return format_html('<i class="{}" style="font-size:18px;"></i>', obj.icon)
        return '📦'
    icon_display.short_description = 'آیکون'

    def save_model(self, request, obj, form, change):
        if not change:
            obj.created_by = request.user
        obj.updated_by = request.user
        super().save_model(request, obj, form, change)


# ==========================================
# 3. Brand Admin
# ==========================================
@admin.register(models.Brand)
class BrandAdmin(admin.ModelAdmin):
    list_display = ['title', 'slug', 'image_preview', 'status', 'sort_order', 'created_at']
    list_display_links = ['title']
    list_editable = ['status', 'sort_order']
    list_filter = ['status', 'created_at']
    search_fields = ['title', 'slug', 'description']
    readonly_fields = ['created_at', 'updated_at']
    actions = [make_active, make_inactive]

    fieldsets = (
        ('اطلاعات اصلی', {
            'fields': ('title','isCatalog','slug', 'image', 'description')
        }),
        ('تنظیمات نمایش', {
            'fields': ('status', 'sort_order')
        }),
        ('اطلاعات سیستمی', {
            'fields': ('created_at', 'updated_at', 'created_by', 'updated_by'),
            'classes': ('collapse',)
        }),
    )

    def image_preview(self, obj):
        if obj.image:
            return format_html('<img src="{}" style="width:40px; height:40px; object-fit:cover; border-radius:8px;" />', obj.image.url)
        return '-'
    image_preview.short_description = 'تصویر'

    def save_model(self, request, obj, form, change):
        if not change:
            obj.created_by = request.user
        obj.updated_by = request.user
        super().save_model(request, obj, form, change)


# ==========================================
# 4. Category Admin
# ==========================================
@admin.register(models.Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ['title', 'slug', 'parent_display', 'image_preview', 'status', 'sort_order']
    list_display_links = ['title']
    list_editable = ['status', 'sort_order']
    list_filter = ['status', 'parent']
    search_fields = ['title', 'slug', 'parent__title']
    readonly_fields = ['created_at', 'updated_at']
    actions = [make_active, make_inactive]

    fieldsets = (
        ('اطلاعات اصلی', {
            'fields': ('title', 'slug', 'parent', 'image')
        }),
        ('برندهای مرتبط', {
            'fields': ('brands',),
            'classes': ('collapse',)
        }),
        ('تنظیمات نمایش', {
            'fields': ('status', 'sort_order')
        }),
        ('اطلاعات سیستمی', {
            'fields': ('created_at', 'updated_at', 'created_by', 'updated_by'),
            'classes': ('collapse',)
        }),
    )
    filter_horizontal = ['brands']

    def image_preview(self, obj):
        if obj.image:
            return format_html('<img src="{}" style="width:40px; height:40px; border-radius:8px; object-fit:cover;" />', obj.image.url)
        return '-'
    image_preview.short_description = 'تصویر'

    def parent_display(self, obj):
        if obj.parent:
            return obj.parent.title
        return 'دسته اصلی'
    parent_display.short_description = 'دسته والد'

    def save_model(self, request, obj, form, change):
        if not change:
            obj.created_by = request.user
        obj.updated_by = request.user
        super().save_model(request, obj, form, change)


# ==========================================
# 5. Catalog Admin
# ==========================================
@admin.register(models.Catalog)
class CatalogAdmin(admin.ModelAdmin):
    list_display = ['title', 'slug', 'brand_display', 'file_link', 'image_preview', 'status', 'sort_order']
    list_display_links = ['title']
    list_editable = ['status', 'sort_order']
    list_filter = ['status', 'brand']
    search_fields = ['title', 'slug', 'brand__title']
    readonly_fields = ['created_at', 'updated_at']
    actions = [make_active, make_inactive]

    fieldsets = (
        ('اطلاعات اصلی', {
            'fields': ('title', 'slug', 'brand', 'categories', 'image')
        }),
        ('فایل کاتالوگ', {
            'fields': ('files',)
        }),
        ('تنظیمات نمایش', {
            'fields': ('status', 'sort_order')
        }),
        ('اطلاعات سیستمی', {
            'fields': ('created_at', 'updated_at', 'created_by', 'updated_by'),
            'classes': ('collapse',)
        }),
    )
    filter_horizontal = ['categories']

    def image_preview(self, obj):
        if obj.image:
            return format_html('<img src="{}" style="width:40px; height:40px; object-fit:cover; border-radius:8px;" />', obj.image.url)
        return '-'
    image_preview.short_description = 'تصویر'

    def file_link(self, obj):
        if obj.files:
            return format_html('<a href="{}" target="_blank" style="background:#e96500; color:white; padding:2px 8px; border-radius:12px; text-decoration:none;">📄 PDF</a>', obj.files.url)
        return '-'
    file_link.short_description = 'فایل'

    def brand_display(self, obj):
        return obj.brand.title if obj.brand else '-'
    brand_display.short_description = 'برند'

    def save_model(self, request, obj, form, change):
        if not change:
            obj.created_by = request.user
        obj.updated_by = request.user
        super().save_model(request, obj, form, change)


# ==========================================
# 6. Product Gallery Inline
# ==========================================
class ProductGalleryInline(admin.TabularInline):
    model = models.ProductGallery
    fields = ['image', 'image_preview', 'alt_text', 'sort_order']
    readonly_fields = ['image_preview']
    extra = 1

    def image_preview(self, obj):
        if obj.image:
            return format_html('<img src="{}" style="width:50px; height:50px; object-fit:cover; border-radius:8px;" />', obj.image.url)
        return '-'
    image_preview.short_description = 'پیش‌نمایش'


# ==========================================
# 7. Product Attribute Inline
# ==========================================
class ProductAttributeInline(admin.TabularInline):
    model = models.ProductAttributeValue
    fields = ['attribute', 'value']
    extra = 1


# ==========================================
# 8. Product Admin (نسخه نهایی بدون خطا)
# ==========================================
@admin.register(models.Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = [
        'title', 'code', 'brand_display', 'price_display', 'sales_unit_display',
        'stock_display', 'stock_status', 'package_info', 'image_preview', 'status'
    ]
    list_display_links = ['title']
    list_editable = ['status']
    list_filter = ['status', 'brand', 'categories', 'use_packaging', 'sales_unit', 'package_unit']
    search_fields = ['title', 'slug', 'code', 'brand__title', 'description']
    readonly_fields = ['created_at', 'updated_at', 'package_info_readonly']
    filter_horizontal = ['categories']
    actions = [make_active, make_inactive]

    fieldsets = (
        ('اطلاعات اصلی محصول', {
            'fields': ('title', 'slug', 'code', 'brand', 'categories', 'catalog')
        }),
        ('تصاویر و فایل‌ها', {
            'fields': ('image', 'product_pdf')
        }),
        ('💰 قیمت و موجودی', {
            'fields': ('price', 'stock')
        }),
        ('📐 واحد فروش', {
            'fields': ('sales_unit',),
        }),
        ('⚙️ سیستم بسته‌بندی', {
            'fields': ('use_packaging', 'package_unit', 'package_size', 'min_order', 'step'),
        }),
        ('توضیحات', {
            'fields': ('description',)
        }),
        ('تنظیمات نمایش', {
            'fields': ('status', 'sort_order')
        }),
        ('اطلاعات سیستمی', {
            'fields': ('created_at', 'updated_at', 'created_by', 'updated_by'),
            'classes': ('collapse',)
        }),
    )

    inlines = [ProductGalleryInline, ProductAttributeInline]

    def image_preview(self, obj):
        if obj.image:
            return format_html('<img src="{}" style="width:40px; height:40px; object-fit:cover; border-radius:8px;" />', obj.image.url)
        return '-'
    image_preview.short_description = 'تصویر'

    def price_display(self, obj):
        if obj.price:
            return f"{obj.price:,.0f} تومان"
        return 'تماس بگیرید'
    price_display.short_description = 'قیمت'

    def stock_display(self, obj):
        """نمایش موجودی به صورت ساده"""
        if obj.stock:
            return str(obj.stock)
        return '۰'
    stock_display.short_description = 'موجودی'

    def sales_unit_display(self, obj):
        if obj.sales_unit and obj.sales_unit.name:
            return obj.sales_unit.name
        return '-'
    sales_unit_display.short_description = 'واحد فروش'

    def stock_status(self, obj):
        """وضعیت موجودی - بدون استفاده از format با فرمت f"""
        try:
            stock_val = float(obj.stock) if obj.stock else 0
        except (TypeError, ValueError):
            stock_val = 0

        if stock_val > 0:
            if stock_val > 10:
                color = '#10b981'
                status = 'موجود'
            else:
                color = '#f59e0b'
                status = 'موجودی محدود'
            # استفاده از concatenation ساده به جای format
            return format_html(
                '<span style="color: {}; font-weight: bold;">' + status + ' (' + str(stock_val) + ' ' + (obj.sales_unit.name if obj.sales_unit and obj.sales_unit.name else 'واحد') + ')</span>',
                color
            )
        return format_html('<span style="color: #ef4444; font-weight: bold;">ناموجود</span>')
    stock_status.short_description = 'وضعیت موجودی'

    def brand_display(self, obj):
        return obj.brand.title if obj.brand else '-'
    brand_display.short_description = 'برند'

    def package_info(self, obj):
        if obj.use_packaging and obj.package_size and obj.package_unit:
            sales_unit_symbol = obj.sales_unit.symbol if obj.sales_unit and obj.sales_unit.symbol else 'واحد'
            return format_html(
                '<span style="background:#fef3c7; color:#d97706; padding:2px 8px; border-radius:12px; font-size:11px;">📦 هر {}: {} {}</span>',
                obj.package_unit.name, str(obj.package_size), sales_unit_symbol
            )
        return format_html('<span style="background:#e5e7eb; color:#6b7280; padding:2px 8px; border-radius:12px; font-size:11px;">📏 فروش تکی</span>')
    package_info.short_description = 'نوع فروش'

    def package_info_readonly(self, obj):
        sales_unit_symbol = obj.sales_unit.symbol if obj.sales_unit and obj.sales_unit.symbol else 'واحد'
        sales_unit_name = obj.sales_unit.name if obj.sales_unit and obj.sales_unit.name else 'واحد'

        if obj.use_packaging and obj.package_size and obj.package_unit:
            package_unit_name = obj.package_unit.name
            package_unit_symbol = obj.package_unit.symbol or ''

            return format_html(
                '<div style="background:#fef3c7; padding:12px; border-radius:8px; border-right:3px solid #d97706;">'
                '<div style="font-weight:bold; margin-bottom:10px;">📦 جزئیات بسته‌بندی</div>'
                '<div style="display:grid; grid-template-columns:1fr 1fr; gap:8px;">'
                '<div><strong>واحد بسته‌بندی:</strong> {} {}</div>'
                '<div><strong>اندازه هر بسته:</strong> {} {}</div>'
                '<div><strong>حداقل سفارش:</strong> {} {}</div>'
                '<div><strong>گام افزایش:</strong> {} {}</div>'
                '</div>'
                '<div style="margin-top:10px; background:white; padding:8px; border-radius:6px; font-size:12px;">'
                '<strong>🔢 نحوه محاسبه:</strong> مقدار درخواستی ÷ {} = تعداد {} (گرد به بالا)'
                '</div>'
                '</div>',
                package_unit_name, package_unit_symbol,
                str(obj.package_size), sales_unit_symbol,
                str(obj.min_order), sales_unit_symbol,
                str(obj.step), sales_unit_symbol,
                str(obj.package_size), package_unit_name
            )
        return format_html(
            '<div style="background:#e5e7eb; padding:12px; border-radius:8px;">'
            '<div style="font-weight:bold;">📏 فروش تکی</div>'
            '<div>این محصول به صورت {} ({}) فروخته می‌شود</div>'
            '<div style="margin-top:8px; font-size:12px; color:#666;">حداقل سفارش: {} {}</div>'
            '<div style="font-size:12px; color:#666;">گام افزایش: {} {}</div>'
            '</div>',
            sales_unit_name, sales_unit_symbol,
            str(obj.min_order), sales_unit_symbol,
            str(obj.step), sales_unit_symbol
        )
    package_info_readonly.short_description = 'جزئیات سیستم فروش'

    def save_model(self, request, obj, form, change):
        if not change:
            obj.created_by = request.user
        obj.updated_by = request.user
        super().save_model(request, obj, form, change)


# ==========================================
# 9. Product Gallery Admin
# ==========================================
@admin.register(models.ProductGallery)
class ProductGalleryAdmin(admin.ModelAdmin):
    list_display = ['product', 'image_preview', 'alt_text', 'sort_order']
    list_editable = ['sort_order']
    list_filter = ['product']
    search_fields = ['product__title', 'alt_text']

    def image_preview(self, obj):
        if obj.image:
            return format_html('<img src="{}" style="width:50px; height:50px; object-fit:cover; border-radius:8px;" />', obj.image.url)
        return '-'
    image_preview.short_description = 'تصویر'


# ==========================================
# 10. Attribute Admin
# ==========================================
@admin.register(models.Attribute)
class AttributeAdmin(admin.ModelAdmin):
    list_display = ['name', 'code', 'icon', 'usage_count']
    list_filter = []
    search_fields = ['name', 'code']

    fieldsets = (
        ('اطلاعات اصلی', {
            'fields': ('name', 'code', 'icon')
        }),
    )

    def usage_count(self, obj):
        count = models.ProductAttributeValue.objects.filter(attribute=obj).count()
        return format_html('<span style="font-weight:bold;">{} محصول</span>', count)
    usage_count.short_description = 'تعداد استفاده'

    def save_model(self, request, obj, form, change):
        if not obj.code and obj.name:
            import re
            obj.code = re.sub(r'[\s\u200c]+', '_', obj.name.strip())
        super().save_model(request, obj, form, change)


# ==========================================
# 11. ProductAttributeValue Admin
# ==========================================
@admin.register(models.ProductAttributeValue)
class ProductAttributeValueAdmin(admin.ModelAdmin):
    list_display = ['product', 'attribute', 'value']
    list_filter = ['attribute']
    search_fields = ['product__title', 'attribute__name', 'value']
    raw_id_fields = ['product', 'attribute']


# ==========================================
# Custom Admin Site Configuration
# ==========================================
admin.site.site_header = 'دکو - پنل مدیریت'
admin.site.site_title = 'پنل مدیریت دکو'
admin.site.index_title = 'داشبورد مدیریت'