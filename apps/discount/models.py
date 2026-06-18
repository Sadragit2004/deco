from django.db import models
from django.utils import timezone
from apps.product.models import Category, Product, Catalog, Brand
from apps.user.models.user import CustomUser
import re


class DiscountType(models.TextChoices):
    PERCENT = 'percent', 'درصدی'
    FIXED = 'fixed', 'مبلغ ثابت (تومان)'


class DiscountScope(models.TextChoices):
    GLOBAL = 'global', 'کل سایت'
    CATEGORY = 'category', 'دسته‌بندی'
    BRAND = 'brand', 'برند'
    PRODUCT = 'product', 'محصول خاص'


class Discount(models.Model):
    title = models.CharField(max_length=255, verbose_name="عنوان تخفیف")
    slug = models.SlugField(max_length=255, unique=True, allow_unicode=True, blank=True, null=True)
    description = models.TextField(blank=True, null=True, verbose_name="توضیحات")

    discount_type = models.CharField(
        max_length=20, choices=DiscountType.choices, default=DiscountType.PERCENT,
        verbose_name="نوع تخفیف"
    )
    scope = models.CharField(
        max_length=20, choices=DiscountScope.choices, default=DiscountScope.GLOBAL,
        verbose_name="محدوده اعمال"
    )

    amount = models.DecimalField(
        max_digits=12, decimal_places=0,
        verbose_name="مقدار تخفیف (درصد یا مبلغ ثابت به تومان)"
    )

    min_quantity = models.DecimalField(
        max_digits=10, decimal_places=2, default=0, blank=True, null=True,
        verbose_name="حداقل تعداد محصول (بر حسب واحد فروش)"
    )
    min_cart_amount = models.DecimalField(
        max_digits=15, decimal_places=0, default=0, blank=True, null=True,
        verbose_name="حداقل مبلغ سبد خرید (تومان)"
    )

    start_date = models.DateTimeField(verbose_name="تاریخ شروع")
    end_date = models.DateTimeField(verbose_name="تاریخ پایان")

    usage_limit = models.PositiveIntegerField(default=0, blank=True, null=True,
                                               verbose_name="حداکثر تعداد استفاده (۰=نامحدود)")
    used_count = models.PositiveIntegerField(default=0, verbose_name="تعداد دفعات استفاده شده")

    is_active = models.BooleanField(default=True, verbose_name="فعال")
    priority = models.IntegerField(default=0, verbose_name="اولویت (عدد بالاتر = اولویت بیشتر)")

    categories = models.ManyToManyField(Category, blank=True, related_name="discounts",
                                        verbose_name="دسته‌بندی‌های مشمول")
    brands = models.ManyToManyField(Brand, blank=True, related_name="discounts",
                                    verbose_name="برندهای مشمول")
    products = models.ManyToManyField(Product, blank=True, related_name="discounts",
                                      verbose_name="محصولات مشمول")

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "تخفیف"
        verbose_name_plural = "تخفیف‌ها"
        ordering = ['-priority', 'start_date']

    def __str__(self):
        return f"{self.title} ({self.get_discount_type_display()}: {self.amount})"

    def save(self, *args, **kwargs):
        if not self.slug and self.title:
            self.slug = re.sub(r'[\s\u200c]+', '_', self.title.strip())
        super().save(*args, **kwargs)

    def is_valid_now(self):
        """آیا تخفیف در حال حاضر معتبر است؟"""
        now = timezone.now()
        return (
            self.is_active and
            self.start_date <= now <= self.end_date and
            (self.usage_limit == 0 or self.used_count < self.usage_limit)
        )

    def applies_to_product(self, product):
        """آیا این تخفیف روی محصول خاص اعمال می‌شود؟"""
        if not self.is_valid_now():
            return False

        if self.scope == DiscountScope.GLOBAL:
            return True

        if self.scope == DiscountScope.PRODUCT:
            return self.products.filter(id=product.id).exists()

        if self.scope == DiscountScope.BRAND:
            return product.brand and self.brands.filter(id=product.brand.id).exists()

        if self.scope == DiscountScope.CATEGORY:
            product_cats = product.categories.all()
            return self.categories.filter(id__in=product_cats).exists()

        return False

    def calculate_discount(self, price, quantity=1, cart_amount=0):
        """
        محاسبه مبلغ تخفیف برای یک محصول
        price: قیمت واحد محصول
        quantity: تعداد سفارش
        cart_amount: کل مبلغ سبد (برای اعمال شرط min_cart_amount)
        """
        if not self.is_valid_now():
            return 0

        if self.min_quantity and quantity < self.min_quantity:
            return 0

        if self.min_cart_amount and cart_amount < self.min_cart_amount:
            return 0

        total_price = float(price) * float(quantity)

        if self.discount_type == DiscountType.PERCENT:
            return (total_price * float(self.amount)) / 100
        else:
            return min(float(self.amount), total_price)

    def use(self):
        """افزایش شمارنده استفاده"""
        if self.usage_limit and self.used_count < self.usage_limit:
            self.used_count += 1
            self.save()


class Coupon(models.Model):
    """کوپن تخفیف برای کاربران خاص"""
    code = models.CharField(max_length=50, unique=True, verbose_name="کد کوپن")
    title = models.CharField(max_length=255, verbose_name="عنوان")
    discount_type = models.CharField(max_length=20, choices=DiscountType.choices, default=DiscountType.PERCENT)
    amount = models.DecimalField(max_digits=12, decimal_places=0, verbose_name="مقدار تخفیف")

    min_cart_amount = models.DecimalField(max_digits=15, decimal_places=0, default=0, blank=True, null=True)
    max_discount_amount = models.DecimalField(max_digits=15, decimal_places=0, default=0, blank=True, null=True,
                                              verbose_name="حداکثر مبلغ تخفیف (برای درصدی)")

    start_date = models.DateTimeField()
    end_date = models.DateTimeField()

    usage_limit = models.PositiveIntegerField(default=1)
    used_count = models.PositiveIntegerField(default=0)

    users = models.ManyToManyField(CustomUser, blank=True, related_name="coupons")

    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "کوپن تخفیف"
        verbose_name_plural = "کوپن‌های تخفیف"

    def __str__(self):
        return f"{self.code} - {self.title}"

    def is_valid_for_user(self, user=None):
        if not self.is_active:
            return False
        now = timezone.now()
        if not (self.start_date <= now <= self.end_date):
            return False
        if self.usage_limit and self.used_count >= self.usage_limit:
            return False
        if user and self.users.exists() and not self.users.filter(id=user.id).exists():
            return False
        return True

    def calculate_discount(self, cart_amount, user=None):
        if not self.is_valid_for_user(user):
            return 0
        if self.min_cart_amount and cart_amount < self.min_cart_amount:
            return 0

        if self.discount_type == DiscountType.PERCENT:
            discount = (cart_amount * self.amount) / 100
            if self.max_discount_amount:
                discount = min(discount, self.max_discount_amount)
            return discount
        else:
            return min(float(self.amount), cart_amount)

    def use(self):
        if self.usage_limit and self.used_count < self.usage_limit:
            self.used_count += 1
            self.save()