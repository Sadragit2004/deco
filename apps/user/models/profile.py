from django.db import models
from django.contrib.auth import get_user_model
from decimal import Decimal
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils import timezone
from .user import CustomUser



class Province(models.Model):
    """مدل استان"""
    name = models.CharField(max_length=50, unique=True, verbose_name="نام استان")
    is_active = models.BooleanField(default=True, verbose_name="فعال")

    class Meta:
        verbose_name = "استان"
        verbose_name_plural = "استان‌ها"
        ordering = ['name']

    def __str__(self):
        return self.name


class City(models.Model):
    """مدل شهر با ارتباط به استان"""
    province = models.ForeignKey(Province, on_delete=models.CASCADE, related_name='cities', verbose_name="استان")
    name = models.CharField(max_length=50, verbose_name="نام شهر")
    is_active = models.BooleanField(default=True, verbose_name="فعال")

    class Meta:
        verbose_name = "شهر"
        verbose_name_plural = "شهرها"
        ordering = ['province__name', 'name']
        unique_together = ['province', 'name']

    def __str__(self):
        return f"{self.name} - {self.province.name}"


class UserAddress(models.Model):
    """مدل آدرس کاربر"""
    ADDRESS_TYPES = (
        ('home', 'آدرس منزل'),
        ('work', 'آدرس محل کار'),
        ('other', 'سایر'),
    )

    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='addresses', verbose_name="کاربر")
    address_type = models.CharField(max_length=10, choices=ADDRESS_TYPES, default='home', verbose_name="نوع آدرس")
    province = models.ForeignKey(Province, on_delete=models.PROTECT, related_name='addresses', verbose_name="استان")
    city = models.ForeignKey(City, on_delete=models.PROTECT, related_name='addresses', verbose_name="شهر")
    address_text = models.TextField(verbose_name="آدرس کامل")
    postal_code = models.CharField(max_length=10, blank=True, null=True, verbose_name="کد پستی")
    latitude = models.DecimalField(max_digits=9, decimal_places=6, blank=True, null=True, verbose_name="عرض جغرافیایی")
    longitude = models.DecimalField(max_digits=9, decimal_places=6, blank=True, null=True, verbose_name="طول جغرافیایی")
    is_default = models.BooleanField(default=False, verbose_name="آدرس پیش‌فرض")
    is_active = models.BooleanField(default=True, verbose_name="فعال")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="تاریخ ایجاد")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="تاریخ بروزرسانی")

    class Meta:
        verbose_name = "آدرس کاربر"
        verbose_name_plural = "آدرس‌های کاربران"
        ordering = ['-is_default', '-created_at']

    def save(self, *args, **kwargs):
        if self.is_default:
            UserAddress.objects.filter(user=self.user, is_default=True).update(is_default=False)
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.get_address_type_display()} - {self.user.mobileNumber}"


class Wallet(models.Model):
    """مدل کیف پول کاربر"""
    TRANSACTION_TYPES = (
        ('deposit', 'واریز'),
        ('withdraw', 'برداشت'),
        ('payment', 'پرداخت سفارش'),
        ('refund', 'بازگشت وجه'),
        ('bonus', 'پاداش امتیازی'),
    )

    TRANSACTION_STATUS = (
        ('pending', 'در حال انتظار'),
        ('completed', 'انجام شده'),
        ('failed', 'ناموفق'),
        ('cancelled', 'لغو شده'),
    )

    user = models.OneToOneField(CustomUser, on_delete=models.CASCADE, related_name='wallet', verbose_name="کاربر")
    balance = models.DecimalField(max_digits=12, decimal_places=0, default=0, validators=[MinValueValidator(0)], verbose_name="موجودی (تومان)")
    frozen_balance = models.DecimalField(max_digits=12, decimal_places=0, default=0, validators=[MinValueValidator(0)], verbose_name="موجودی مسدود شده")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="تاریخ ایجاد کیف پول")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="تاریخ بروزرسانی")

    class Meta:
        verbose_name = "کیف پول"
        verbose_name_plural = "کیف پول‌ها"

    def __str__(self):
        return f"کیف پول {self.user.mobileNumber} - موجودی: {self.balance} تومان"


class WalletTransaction(models.Model):
    """مدل تراکنش‌های کیف پول"""
    wallet = models.ForeignKey(Wallet, on_delete=models.CASCADE, related_name='transactions', verbose_name="کیف پول")
    amount = models.DecimalField(max_digits=12, decimal_places=0, verbose_name="مبلغ (تومان)")
    transaction_type = models.CharField(max_length=10, choices=Wallet.TRANSACTION_TYPES, verbose_name="نوع تراکنش")
    status = models.CharField(max_length=10, choices=Wallet.TRANSACTION_STATUS, default='pending', verbose_name="وضعیت")
    reference_id = models.CharField(max_length=100, blank=True, null=True, verbose_name="شماره مرجع")
    description = models.TextField(blank=True, null=True, verbose_name="توضیحات")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="تاریخ تراکنش")

    class Meta:
        verbose_name = "تراکنش کیف پول"
        verbose_name_plural = "تراکنش‌های کیف پول"
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.get_transaction_type_display()} - {self.amount} تومان - {self.wallet.user.mobileNumber}"


class CustomerLoyalty(models.Model):
    """مدل سیستم امتیازدهی مشتری (لویالتی)"""
    TIER_CHOICES = (
        ('select', 'انتخاب شده'),
        ('premium', 'پریمیوم'),
        ('elite', 'الیت'),
        ('private', 'پرایویت'),
    )

    user = models.OneToOneField(CustomUser, on_delete=models.CASCADE, related_name='loyalty', verbose_name="کاربر")
    total_points = models.IntegerField(default=0, validators=[MinValueValidator(0)], verbose_name="مجموع امتیازات")
    current_tier = models.CharField(max_length=10, choices=TIER_CHOICES, default='select', verbose_name="سطح عضویت")
    lifetime_purchase = models.DecimalField(max_digits=12, decimal_places=0, default=0, verbose_name="مجموع خرید مادام‌العمر (تومان)")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="تاریخ عضویت")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="تاریخ بروزرسانی")
    total_coins = models.IntegerField(default=0, validators=[MinValueValidator(0)], verbose_name="مجموع سکه‌ها")

    class Meta:
        verbose_name = "امتیاز مشتری"
        verbose_name_plural = "امتیازات مشتریان"

    def __str__(self):
        tier_display_map = {
            'select': 'انتخاب شده',
            'premium': 'پریمیوم',
            'elite': 'الیت',
            'private': 'پرایویت',
        }
        return f"{self.user.mobileNumber} - {self.total_points} امتیاز - {tier_display_map.get(self.current_tier, self.current_tier)}"


class LoyaltyTransaction(models.Model):
    """مدل تراکنش‌های امتیازی"""
    TRANSACTION_TYPES = (
        ('earn', 'کسب امتیاز'),
        ('redeem', 'استفاده از امتیاز'),
        ('expire', 'انقضای امتیاز'),
        ('adjust', 'تعدیل دستی'),
    )

    loyalty = models.ForeignKey(CustomerLoyalty, on_delete=models.CASCADE, related_name='transactions', verbose_name="امتیاز مشتری")
    points = models.IntegerField(verbose_name="تعداد امتیاز")
    transaction_type = models.CharField(max_length=10, choices=TRANSACTION_TYPES, verbose_name="نوع تراکنش")
    order_id = models.CharField(max_length=100, blank=True, null=True, verbose_name="شناسه سفارش")
    description = models.TextField(blank=True, null=True, verbose_name="توضیحات")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="تاریخ تراکنش")
    expires_at = models.DateTimeField(blank=True, null=True, verbose_name="تاریخ انقضا")

    class Meta:
        verbose_name = "تراکنش امتیازی"
        verbose_name_plural = "تراکنش‌های امتیازی"
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.get_transaction_type_display()} - {self.points} امتیاز - {self.loyalty.user.mobileNumber}"