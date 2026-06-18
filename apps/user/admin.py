# apps/user/admin.py
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils.translation import gettext_lazy as _
from django.utils.html import format_html
from django.urls import reverse

from .models.user import CustomUser
from .models.security import UserSecurity
from .models.device import UserDevice
from .models.profile import Province, City, UserAddress, Wallet, WalletTransaction, CustomerLoyalty, LoyaltyTransaction

@admin.register(CustomUser)
class CustomUserAdmin(BaseUserAdmin):
    list_display = ("mobileNumber", "name", "family", "email", "gender", "get_roles", "is_active", "is_staff", "is_superuser",)
    list_filter = ("is_active", "is_superuser", "gender", "roles")
    search_fields = ("mobileNumber", "name", "family", "email")
    ordering = ("-id",)
    filter_horizontal = ("roles",)

    fieldsets = (
        (None, {"fields": ("mobileNumber", "password")}),
        (_("اطلاعات شخصی"), {"fields": ("name", "family", "email", "gender", "shop_name", "avatar")}),
        (_("نقش‌ها"), {"fields": ("roles",)}),
        (_("سطوح دسترسی"), {"fields": ("is_active", "is_staff", "is_superuser", "groups", "user_permissions")}),
        (_("تاریخ‌ها"), {"fields": ("last_login", "createAt", "last_activity")}),
    )

    add_fieldsets = (
        (None, {
            "classes": ("wide",),
            "fields": ("mobileNumber", "password1", "password2", "name", "family", "email", "gender", "roles", "is_active", "is_staff", "is_superuser"),
        }),
    )

    readonly_fields = ("createAt", "last_activity")

    def get_roles(self, obj):
        return ", ".join([role.title for role in obj.roles.all()])
    get_roles.short_description = "نقش‌ها"


# =========================
# User Security Admin
# =========================
@admin.register(UserSecurity)
class UserSecurityAdmin(admin.ModelAdmin):
    list_display = ("user", "activeCode", "expireCode", "isBan", "isInfoFiled", "createdAt",'isVerfiyByManager','isPeymentuser')
    list_filter = ("isBan", "isInfoFiled")
    search_fields = ("user__mobileNumber", "activeCode")
    ordering = ("-createdAt",)


# =========================
# User Device Admin
# =========================
@admin.register(UserDevice)
class UserDeviceAdmin(admin.ModelAdmin):
    list_display = ("user", "deviceInfo", "ipAddress", "createdAt")
    search_fields = ("user__mobileNumber", "deviceInfo", "ipAddress")
    list_filter = ("createdAt",)
    ordering = ("-createdAt",)


# =========================
# Province and City Admin
# =========================
class CityInline(admin.TabularInline):
    model = City
    extra = 1
    fields = ['name', 'is_active']
    show_change_link = True
    verbose_name = "شهر"
    verbose_name_plural = "شهرها"


@admin.register(Province)
class ProvinceAdmin(admin.ModelAdmin):
    list_display = ['name', 'is_active', 'cities_count']
    list_editable = ['is_active']
    list_filter = ['is_active']
    search_fields = ['name']
    ordering = ['name']
    inlines = [CityInline]

    def cities_count(self, obj):
        count = obj.cities.count()
        return format_html(
            '<span style="background-color: #4CAF50; color: white; padding: 2px 8px; border-radius: 12px; font-size: 12px;">{}</span>',
            count
        )
    cities_count.short_description = "تعداد شهرها"


@admin.register(City)
class CityAdmin(admin.ModelAdmin):
    list_display = ['name', 'province_link', 'is_active']
    list_editable = ['is_active']
    list_filter = ['is_active', 'province']
    search_fields = ['name', 'province__name']
    autocomplete_fields = ['province']
    ordering = ['province__name', 'name']

    def province_link(self, obj):
        url = reverse('admin:app_province_change', args=[obj.province.id])
        return format_html('<a href="{}" style="font-weight: bold;">{}</a>', url, obj.province.name)
    province_link.short_description = "استان"


# =========================
# User Address Admin
# =========================
@admin.register(UserAddress)
class UserAddressAdmin(admin.ModelAdmin):
    list_display = [
        'user_info', 'address_type_badge', 'province', 'city',
        'is_default_badge', 'is_active', 'created_at'
    ]
    list_filter = ['address_type', 'is_default', 'is_active', 'province', 'created_at']
    search_fields = ['user__mobileNumber', 'user__name', 'user__family', 'address_text', 'postal_code']
    autocomplete_fields = ['user', 'province', 'city']
    readonly_fields = ['created_at', 'updated_at']
    actions = ['set_as_default', 'set_as_active', 'set_as_inactive']

    fieldsets = (
        ('اطلاعات کاربر', {
            'fields': ('user', 'address_type')
        }),
        ('آدرس', {
            'fields': ('province', 'city', 'address_text', 'postal_code')
        }),
        ('موقعیت جغرافیایی', {
            'fields': ('latitude', 'longitude'),
            'classes': ('collapse',)
        }),
        ('وضعیت', {
            'fields': ('is_default', 'is_active')
        }),
        ('تاریخچه', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )

    def user_info(self, obj):
        return format_html(
            '<strong>{}</strong><br><span style="color:#666;">{}</span>',
            obj.user.mobileNumber,
            f"{obj.user.name or ''} {obj.user.family or ''}"
        )
    user_info.short_description = "کاربر"

    def address_type_badge(self, obj):
        colors = {
            'home': '#4CAF50',
            'work': '#2196F3',
            'other': '#9E9E9E'
        }
        return format_html(
            '<span style="background-color:{}; color:white; padding:2px 8px; border-radius:12px; font-size:11px;">{}</span>',
            colors.get(obj.address_type, '#9E9E9E'),
            obj.get_address_type_display()
        )
    address_type_badge.short_description = "نوع آدرس"

    def is_default_badge(self, obj):
        if obj.is_default:
            return format_html('<span style="color:#4CAF50; font-weight:bold;">✓ پیش‌فرض</span>')
        return format_html('<span style="color:#999;">-</span>')
    is_default_badge.short_description = "پیش‌فرض"

    def set_as_default(self, request, queryset):
        for address in queryset:
            address.is_default = True
            address.save()
        self.message_user(request, "آدرس‌های انتخاب شده به عنوان پیش‌فرض تنظیم شدند.")
    set_as_default.short_description = "تنظیم به عنوان آدرس پیش‌فرض"

    def set_as_active(self, request, queryset):
        queryset.update(is_active=True)
        self.message_user(request, "آدرس‌های انتخاب شده فعال شدند.")
    set_as_active.short_description = "فعال کردن آدرس‌ها"

    def set_as_inactive(self, request, queryset):
        queryset.update(is_active=False)
        self.message_user(request, "آدرس‌های انتخاب شده غیرفعال شدند.")
    set_as_inactive.short_description = "غیرفعال کردن آدرس‌ها"


# =========================
# Wallet Admin
# =========================
class WalletTransactionInline(admin.TabularInline):
    model = WalletTransaction
    extra = 0
    readonly_fields = ['created_at']
    fields = ['amount', 'transaction_type', 'status', 'reference_id', 'description', 'created_at']
    can_delete = False
    show_change_link = True


@admin.register(Wallet)
class WalletAdmin(admin.ModelAdmin):
    list_display = ['user_info', 'balance_display', 'frozen_balance_display', 'total_transactions', 'created_at']
    readonly_fields = ['balance', 'frozen_balance', 'created_at', 'updated_at']
    search_fields = ['user__mobileNumber', 'user__name', 'user__family']
    inlines = [WalletTransactionInline]
    actions = ['deposit_to_wallet']

    fieldsets = (
        ('اطلاعات کاربر', {
            'fields': ('user',)
        }),
        ('موجودی کیف پول', {
            'fields': ('balance', 'frozen_balance')
        }),
        ('تاریخچه', {
            'fields': ('created_at', 'updated_at')
        })
    )

    def user_info(self, obj):
        return format_html(
            '<strong>{}</strong><br>{} {}',
            obj.user.mobileNumber,
            obj.user.name or '',
            obj.user.family or ''
        )
    user_info.short_description = "کاربر"

    def balance_display(self, obj):
        return format_html(
            '<span style="color:#4CAF50; font-weight:bold;">{} تومان</span>',
            f"{obj.balance:,}"
        )
    balance_display.short_description = "موجودی"

    def frozen_balance_display(self, obj):
        if obj.frozen_balance > 0:
            return format_html(
                '<span style="color:#FF9800;">{} تومان</span>',
                f"{obj.frozen_balance:,}"
            )
        return f"{obj.frozen_balance:,} تومان"
    frozen_balance_display.short_description = "موجودی مسدود شده"

    def total_transactions(self, obj):
        return obj.transactions.count()
    total_transactions.short_description = "تعداد تراکنش‌ها"

    def deposit_to_wallet(self, request, queryset):
        self.message_user(request, "لطفاً از بخش تراکنش‌ها برای واریز استفاده کنید.")
    deposit_to_wallet.short_description = "واریز به کیف پول‌های انتخاب شده"


@admin.register(WalletTransaction)
class WalletTransactionAdmin(admin.ModelAdmin):
    list_display = [
        'id', 'wallet_info', 'amount_display', 'transaction_type_badge',
        'status_badge', 'reference_id', 'created_at'
    ]
    list_filter = ['transaction_type', 'status', 'created_at']
    search_fields = ['wallet__user__mobileNumber', 'reference_id', 'description']
    readonly_fields = ['created_at']
    autocomplete_fields = ['wallet']

    def wallet_info(self, obj):
        return obj.wallet.user.mobileNumber
    wallet_info.short_description = "کاربر"

    def amount_display(self, obj):
        color = '#4CAF50' if obj.transaction_type in ['deposit', 'refund', 'bonus'] else '#F44336'
        sign = '+' if obj.transaction_type in ['deposit', 'refund', 'bonus'] else '-'
        return format_html(
            '<span style="color:{}; font-weight:bold;">{} {} تومان</span>',
            color, sign, f"{obj.amount:,}"
        )
    amount_display.short_description = "مبلغ"

    def transaction_type_badge(self, obj):
        colors = {
            'deposit': '#4CAF50',
            'withdraw': '#F44336',
            'payment': '#FF9800',
            'refund': '#2196F3',
            'bonus': '#9C27B0'
        }
        return format_html(
            '<span style="background-color:{}; color:white; padding:2px 8px; border-radius:12px; font-size:11px;">{}</span>',
            colors.get(obj.transaction_type, '#9E9E9E'),
            obj.get_transaction_type_display()
        )
    transaction_type_badge.short_description = "نوع تراکنش"

    def status_badge(self, obj):
        colors = {
            'pending': '#FF9800',
            'completed': '#4CAF50',
            'failed': '#F44336',
            'cancelled': '#9E9E9E'
        }
        return format_html(
            '<span style="color:{}; font-weight:bold;">{}</span>',
            colors.get(obj.status, '#9E9E9E'),
            obj.get_status_display()
        )
    status_badge.short_description = "وضعیت"


# =========================
# Customer Loyalty Admin
# =========================
class LoyaltyTransactionInline(admin.TabularInline):
    model = LoyaltyTransaction
    extra = 0
    readonly_fields = ['created_at']
    fields = ['points', 'transaction_type', 'order_id', 'description', 'created_at']
    can_delete = False
    show_change_link = True


@admin.register(CustomerLoyalty)
class CustomerLoyaltyAdmin(admin.ModelAdmin):
    list_display = [
        'user_info', 'total_points_display', 'current_tier_badge',
        'lifetime_purchase_display', 'redeemable_value_display', 'updated_at'
    ]

    readonly_fields = ['total_points', 'lifetime_purchase', 'created_at', 'updated_at']
    search_fields = ['user__mobileNumber', 'user__name', 'user__family']
    list_filter = ['current_tier']
    inlines = [LoyaltyTransactionInline]
    actions = ['add_points_action']

    fieldsets = (
        ('اطلاعات کاربر', {
            'fields': ('user',)
        }),

        ('امتیازات', {
            'fields': ('total_points', 'current_tier','total_coins')
        }),
        ('خریدها', {
            'fields': ('lifetime_purchase',)
        }),
        ('تاریخچه', {
            'fields': ('created_at', 'updated_at')
        })
    )

    def user_info(self, obj):
        return format_html(
            '<strong>{}</strong><br>{} {}',
            obj.user.mobileNumber,
            obj.user.name or '',
            obj.user.family or ''
        )
    user_info.short_description = "کاربر"

    def total_points_display(self, obj):
        return format_html(
            '<span style="color:#2196F3; font-weight:bold; font-size:14px;">{}</span>',
            f"{obj.total_points:,}"
        )
    total_points_display.short_description = "مجموع امتیازات"

    def current_tier_badge(self, obj):
        colors = {
            'bronze': '#CD7F32',
            'silver': '#C0C0C0',
            'gold': '#FFD700',
            'platinum': '#E5E4E2'
        }
        return format_html(
            '<span style="background-color:{}; color:#333; padding:3px 10px; border-radius:15px; font-weight:bold;">{}</span>',
            colors.get(obj.current_tier, '#9E9E9E'),
            obj.get_current_tier_display()
        )
    current_tier_badge.short_description = "سطح عضویت"

    def lifetime_purchase_display(self, obj):
        return format_html(
            '<span style="color:#9C27B0;">{} تومان</span>',
            f"{obj.lifetime_purchase:,}"
        )
    lifetime_purchase_display.short_description = "مجموع خرید"

    def redeemable_value_display(self, obj):
        try:
            value = obj.redeemable_value
            return format_html(
                '<span style="color:#4CAF50;">{} تومان</span>',
                f"{value:,}"
            )
        except:
            return "-"
    redeemable_value_display.short_description = "قیمت قابل تبدیل"

    def add_points_action(self, request, queryset):
        for loyalty in queryset:
            loyalty.add_points(1000, description="امتیاز تشویقی توسط ادمین")
        self.message_user(request, f"{queryset.count()} کاربر {1000} امتیاز دریافت کردند.")
    add_points_action.short_description = "اضافه کردن ۱۰۰۰ امتیاز به کاربران انتخاب شده"


@admin.register(LoyaltyTransaction)
class LoyaltyTransactionAdmin(admin.ModelAdmin):
    list_display = [
        'id', 'user_info', 'points_display', 'transaction_type_badge',
        'order_id', 'created_at'
    ]
    list_filter = ['transaction_type', 'created_at']
    search_fields = ['loyalty__user__mobileNumber', 'order_id', 'description']
    readonly_fields = ['created_at']
    autocomplete_fields = ['loyalty']

    def user_info(self, obj):
        return obj.loyalty.user.mobileNumber
    user_info.short_description = "کاربر"

    def points_display(self, obj):
        color = '#4CAF50' if obj.transaction_type == 'earn' else '#F44336'
        sign = '+' if obj.transaction_type == 'earn' else ''
        return format_html(
            '<span style="color:{}; font-weight:bold;">{} {}</span>',
            color, sign, f"{obj.points:,}"
        )
    points_display.short_description = "امتیاز"

    def transaction_type_badge(self, obj):
        colors = {
            'earn': '#4CAF50',
            'redeem': '#FF9800',
            'expire': '#F44336',
            'adjust': '#2196F3'
        }
        return format_html(
            '<span style="background-color:{}; color:white; padding:2px 8px; border-radius:12px; font-size:11px;">{}</span>',
            colors.get(obj.transaction_type, '#9E9E9E'),
            obj.get_transaction_type_display()
        )
    transaction_type_badge.short_description = "نوع تراکنش"


# ==================== فایل apps/user/admin.py ====================
# ==================== فایل apps/user/admin.py ====================

from django.urls import reverse
from .models.role import Role, RoleBanUrl, UserBan


@admin.register(Role)
class RoleAdmin(admin.ModelAdmin):
    """مدیریت نقش‌ها"""

    list_display = ['title', 'users_count', 'ban_urls_count', 'isActive', 'createAt','slug']
    list_filter = ['isActive', 'createAt','slug']
    search_fields = ['title','slug']
    list_editable = ['isActive','slug']
    list_per_page = 20

    fieldsets = (
        ('اطلاعات نقش', {
            'fields': ('title', 'isActive')
        }),
    )

    def users_count(self, obj):
        count = obj.users.count()
        return format_html('<span style="font-weight: bold;">{}</span>', count)
    users_count.short_description = 'تعداد کاربران'

    def ban_urls_count(self, obj):
        count = obj.ban_urls.count()
        return format_html('<span style="color: #dc3545;">{}</span>', count)
    ban_urls_count.short_description = 'URL ممنوع'


@admin.register(RoleBanUrl)
class RoleBanUrlAdmin(admin.ModelAdmin):
    """مدیریت URL های ممنوع"""

    list_display = ['role', 'url_pattern', 'description_short', 'isActive', 'created_at']
    list_filter = ['isActive', 'role']
    search_fields = ['url_pattern', 'description', 'role__title']
    list_editable = ['isActive']
    list_per_page = 20

    fieldsets = (
        ('اطلاعات URL ممنوع', {
            'fields': ('role', 'url_pattern', 'description')
        }),
        ('وضعیت', {
            'fields': ('isActive',)
        }),
    )

    def description_short(self, obj):
        if obj.description:
            return obj.description[:40] + '...' if len(obj.description) > 40 else obj.description
        return '-'
    description_short.short_description = 'توضیحات'


@admin.register(UserBan)
class UserBanAdmin(admin.ModelAdmin):
    """مدیریت بن کاربران"""

    list_display = ['user_link', 'reason_badge', 'started_at', 'expires_at_status', 'is_active_badge', 'banned_by']
    list_filter = ['is_active', 'reason', 'is_permanent']
    search_fields = ['user__mobileNumber', 'user__name', 'user__family', 'description']
    list_per_page = 20

    fieldsets = (
        ('کاربر', {
            'fields': ('user',)
        }),
        ('دلیل بن', {
            'fields': ('reason', 'description')
        }),
        ('زمان', {
            'fields': ('started_at', 'expires_at', 'is_permanent')
        }),
        ('وضعیت', {
            'fields': ('is_active', 'banned_by')
        }),
    )

    readonly_fields = ['started_at']

    def user_link(self, obj):
        url = reverse('admin:user_customuser_change', args=[obj.user.id])
        return format_html('<a href="{}" style="font-weight: bold;">{}</a>', url, obj.user.mobileNumber)
    user_link.short_description = 'کاربر'

    def reason_badge(self, obj):
        colors = {
            'spam': '#ffc107',
            'abuse': '#dc3545',
            'fraud': '#dc3545',
            'violation': '#fd7e14',
            'security': '#6f42c1',
            'other': '#6c757d',
        }
        color = colors.get(obj.reason, '#6c757d')
        return format_html('<span style="background: {}; color: white; padding: 2px 8px; border-radius: 12px; font-size: 11px;">{}</span>',
                          color, obj.get_reason_display())
    reason_badge.short_description = 'دلیل'

    def expires_at_status(self, obj):
        if obj.is_permanent:
            return format_html('<span style="color: #dc3545;">♾️ دائمی</span>')
        if obj.expires_at:
            if obj.is_expired:
                return format_html('<span style="color: #6c757d;">✅ منقضی شده</span>')
            return format_html('<span style="color: #ffc107;">⏳ {}</span>', obj.expires_at.strftime('%Y-%m-%d %H:%M'))
        return '-'
    expires_at_status.short_description = 'زمان انقضا'

    def is_active_badge(self, obj):
        if obj.is_active and not obj.is_expired:
            return format_html('<span style="color: #dc3545;">🔒 فعال</span>')
        return format_html('<span style="color: #28a745;">✓ غیرفعال</span>')
    is_active_badge.short_description = 'وضعیت'

    def banned_by(self, obj):
        if obj.banned_by:
            return obj.banned_by.mobileNumber
        return 'سیستم'
    banned_by.short_description = 'بن کننده'

