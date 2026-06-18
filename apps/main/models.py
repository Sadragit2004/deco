# models.py

from django.db import models
from django.utils import timezone
from django.core.validators import FileExtensionValidator
from django.core.exceptions import ValidationError

class Slider(models.Model):
    """مدل اسلایدر اصلی"""

    # فیلدهای اصلی
    title = models.CharField(
        max_length=200,
        verbose_name="عنوان",
        help_text="عنوان اصلی اسلایدر"
    )

    description = models.TextField(
        verbose_name="توضیحات",
        blank=True,
        null=True,
        help_text="توضیحات کوتاه برای اسلایدر"
    )

    isdiscount = models.BooleanField(default=False,verbose_name='حراجی ها')

    is_active = models.BooleanField(
        default=True,
        verbose_name="فعال بودن",
        help_text="آیا این اسلایدر نمایش داده شود؟"
    )

    # فیلدهای عکس
    image_pc = models.ImageField(
        upload_to='slider/pc/%Y/%m/',
        verbose_name="عکس برای پی‌سی",
        help_text="اندازه پیشنهادی: 2880x600 پیکسل",
        validators=[
            FileExtensionValidator(allowed_extensions=['jpg', 'jpeg', 'png', 'webp', 'svg'])
        ]
    )

    image_mobile = models.ImageField(
        upload_to='slider/mobile/%Y/%m/',
        verbose_name="عکس برای موبایل",
        help_text="اندازه پیشنهادی: 1080x540 پیکسل",
        validators=[
            FileExtensionValidator(allowed_extensions=['jpg', 'jpeg', 'png', 'webp', 'svg'])
        ]
    )

    # فیلدهای تاریخ
    start_date = models.DateTimeField(
        default=timezone.now,
        verbose_name="تاریخ شروع",
        help_text="از چه تاریخی نمایش داده شود؟"
    )

    end_date = models.DateTimeField(
        verbose_name="تاریخ پایان",
        blank=True,
        null=True,
        help_text="تا چه تاریخی نمایش داده شود؟ (اختیاری)"
    )

    # فیلد لینک
    link = models.URLField(
        max_length=500,
        verbose_name="لینک مورد نظر",
        blank=True,
        null=True,
        help_text="لینک هدایت کاربر پس از کلیک روی اسلایدر"
    )

    # فیلدهای اضافی برای مدیریت بهتر
    order = models.PositiveIntegerField(
        default=0,
        verbose_name="ترتیب نمایش",
        help_text="اعداد کوچکتر زودتر نمایش داده می‌شوند"
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="تاریخ ایجاد"
    )

    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name="تاریخ بروزرسانی"
    )

    class Meta:
        verbose_name = "اسلایدر"
        verbose_name_plural = "اسلایدرها"
        ordering = ['order', '-created_at']
        indexes = [
            models.Index(fields=['is_active', 'start_date', 'end_date']),
            models.Index(fields=['order']),
        ]

    def __str__(self):
        return self.title

    def clean(self):
        """اعتبارسنجی تاریخ‌ها"""
        if self.end_date and self.start_date > self.end_date:
            raise ValidationError({'end_date': 'تاریخ پایان باید بزرگتر از تاریخ شروع باشد.'})

    def is_available(self):
        """بررسی آیا اسلایدر در تاریخ فعلی فعال است"""
        now = timezone.now()
        is_date_valid = self.start_date <= now
        if self.end_date:
            is_date_valid = is_date_valid and now <= self.end_date
        return self.is_active and is_date_valid

    def save(self, *args, **kwargs):
        """ذخیره خودکار با اعتبارسنجی"""
        self.clean()
        super().save(*args, **kwargs)

    def get_image_pc_url(self):
        """دریافت لینک عکس پی‌سی"""
        if self.image_pc:
            return self.image_pc.url
        return '/static/images/default-slider-pc.jpg'

    def get_image_mobile_url(self):
        """دریافت لینک عکس موبایل"""
        if self.image_mobile:
            return self.image_mobile.url
        return '/static/images/default-slider-mobile.jpg'



# models.py

# apps/portfolio/models.py

from django.db import models
from django.conf import settings


class Portfolio(models.Model):
    """
    مدل نمونه کار با وضعیت تایید
    """
    title = models.CharField(max_length=200, verbose_name="عنوان")
    description = models.TextField(verbose_name="توضیحات")
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="portfolios",
        verbose_name="کاربر مربوطه"
    )
    is_active = models.BooleanField(
        default=False,
        verbose_name="تایید شده",
        help_text="آیا این نمونه کار تایید و منتشر شود؟"
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="تاریخ ثبت")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="تاریخ بروزرسانی")

    class Meta:
        verbose_name = "نمونه کار"
        verbose_name_plural = "نمونه کارها"
        ordering = ['-is_active', '-created_at']

    def __str__(self):
        return f"{self.title} - {'تایید شده' if self.is_active else 'در انتظار تایید'}"


class PortfolioGallery(models.Model):
    """
    گالری عکس‌های نمونه کار
    """
    portfolio = models.ForeignKey(
        Portfolio,
        on_delete=models.CASCADE,
        related_name="gallery",
        verbose_name="نمونه کار"
    )
    image = models.ImageField(upload_to='portfolio/gallery/%Y/%m/', verbose_name="عکس")
    sort_order = models.IntegerField(default=0, verbose_name="ترتیب نمایش")

    class Meta:
        verbose_name = "عکس گالری"
        verbose_name_plural = "گالری عکس‌ها"
        ordering = ['sort_order']

    def __str__(self):
        return f"عکس برای {self.portfolio.title}"