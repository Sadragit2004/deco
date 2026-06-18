import uuid
import secrets
from django.db import models
from django.utils import timezone
from django.core.validators import MinValueValidator

from apps.user.models.user import CustomUser
from apps.user.models.profile import UserAddress, CustomerLoyalty, LoyaltyTransaction
from apps.product.models import Product
from apps.discount.models import Discount, Coupon
from apps.pro.models import OrderMaterial


class OrderStatus(models.TextChoices):
    """وضعیت‌های مختلف سفارش"""
    PENDING = 'pending', 'در انتظار پرداخت'
    PAID = 'paid', 'پرداخت شده'
    PROCESSING = 'processing', 'در حال پردازش'
    PACKAGING = 'packaging', 'در حال بسته‌بندی'
    SHIPPED = 'shipped', 'ارسال شده'
    DELIVERED = 'delivered', 'تحویل شده'
    CANCELLED = 'cancelled', 'لغو شده'


class OrderType(models.TextChoices):
    """نوع سفارش"""
    REGULAR = 'regular', 'محصول معمولی'
    PRINT = 'print', 'سفارش چاپی'


class ShippingMethod(models.Model):
    """مدل نوع بار / روش ارسال"""

    name = models.CharField(max_length=100, unique=True, verbose_name="نام روش ارسال")
    logo = models.ImageField(
        upload_to='shipping/logos/',
        blank=True,
        null=True,
        verbose_name="لوگو"
    )
    delivery_time = models.CharField(
        max_length=100,
        verbose_name="زمان تحویل",
        help_text="مثلاً: ۲ تا ۳ روز کاری، ۲۴ ساعته، etc"
    )
    base_cost = models.DecimalField(
        max_digits=12,
        decimal_places=0,
        default=0,
        verbose_name="هزینه پایه (تومان)"
    )
    cost_per_unit = models.DecimalField(
        max_digits=10,
        decimal_places=0,
        default=0,
        verbose_name="هزینه به ازای هر کیلوگرم (تومان)"
    )
    free_shipping_min_amount = models.DecimalField(
        max_digits=15,
        decimal_places=0,
        default=0,
        blank=True,
        null=True,
        verbose_name="حداقل مبلغ برای ارسال رایگان"
    )
    is_active = models.BooleanField(default=True, verbose_name="فعال")
    sort_order = models.IntegerField(default=0, verbose_name="ترتیب نمایش")

    description = models.TextField(blank=True, null=True, verbose_name="توضیحات")

    created_at = models.DateTimeField(auto_now_add=True, verbose_name="تاریخ ایجاد")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="تاریخ بروزرسانی")

    class Meta:
        verbose_name = "روش ارسال"
        verbose_name_plural = "روش‌های ارسال"
        ordering = ['sort_order', 'base_cost']

    def __str__(self):
        return self.name

    def calculate_cost(self, total_amount, weight=0):
        """محاسبه هزینه ارسال بر اساس مبلغ سبد و وزن"""
        if self.free_shipping_min_amount and total_amount >= self.free_shipping_min_amount:
            return 0

        cost = self.base_cost
        if weight > 0:
            cost += self.cost_per_unit * weight
        return cost


class PaymentReceipt(models.Model):
    class ReceiptStatus(models.IntegerChoices):
        PENDING = 0, 'در انتظار بررسی'
        VERIFIED = 1, 'تایید شده'
        REJECTED = 2, 'رد شده'

    order = models.OneToOneField('Order', on_delete=models.CASCADE, related_name='payment_receipt')
    receipt_file = models.FileField(upload_to='payment_receipts/%Y/%m/%d/', verbose_name="فایل رسید")
    receipt_number = models.CharField(max_length=100, blank=True, null=True, verbose_name="شماره رسید")
    bank_name = models.CharField(max_length=100, blank=True, null=True, verbose_name="نام بانک")
    payment_date = models.DateTimeField(blank=True, null=True, verbose_name="تاریخ پرداخت")
    payment_amount = models.DecimalField(max_digits=15, decimal_places=0, blank=True, null=True, verbose_name="مبلغ پرداختی")
    tracking_code = models.CharField(max_length=100, blank=True, null=True, verbose_name="کد پیگیری")

    status = models.IntegerField(
        choices=ReceiptStatus.choices,
        default=ReceiptStatus.PENDING,
        verbose_name="وضعیت"
    )

    admin_note = models.TextField(blank=True, null=True, verbose_name="یادداشت ادمین")
    rejection_reason = models.TextField(blank=True, null=True, verbose_name="دلیل رد")

    verified_by = models.ForeignKey(
        CustomUser,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='verified_receipts',
        verbose_name="تایید کننده"
    )
    verified_at = models.DateTimeField(blank=True, null=True, verbose_name="تاریخ تایید")

    uploaded_at = models.DateTimeField(auto_now_add=True, verbose_name="تاریخ آپلود")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="تاریخ بروزرسانی")

    class Meta:
        verbose_name = "رسید پرداخت"
        verbose_name_plural = "رسیدهای پرداخت"
        ordering = ['-uploaded_at']

    def __str__(self):
        return f"رسید #{self.receipt_number or self.order.order_number} - {self.get_status_display()}"


class Order(models.Model):
    """مدل اصلی سفارش"""

    # شناسه‌ها
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    order_number = models.CharField(max_length=20, unique=True, editable=False, verbose_name="شماره سفارش")

    # نوع سفارش
    order_type = models.CharField(
        max_length=20,
        choices=OrderType.choices,
        default=OrderType.REGULAR.value,
        verbose_name="نوع سفارش"
    )

    # ارتباط با کاربر
    user = models.ForeignKey(
        CustomUser,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='orders',
        verbose_name="کاربر"
    )

    # ارتباط با آدرس (از مدل UserAddress استفاده میکنه)
    address = models.ForeignKey(
        UserAddress,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='orders',
        verbose_name="آدرس ارسال"
    )

    # روش ارسال
    shipping_method = models.ForeignKey(
        ShippingMethod,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='orders',
        verbose_name="روش ارسال"
    )

    # توضیحات سفارش
    description = models.TextField(blank=True, null=True, verbose_name="توضیحات سفارش")
    admin_note = models.TextField(blank=True, null=True, verbose_name="یادداشت داخلی")

    # قیمت‌ها و هزینه‌ها
    subtotal = models.DecimalField(
        max_digits=15, decimal_places=0, default=0,
        verbose_name="جمع کل محصولات (قبل از تخفیف)"
    )
    discount_amount = models.DecimalField(
        max_digits=15, decimal_places=0, default=0,
        verbose_name="مبلغ تخفیف"
    )
    coupon_discount = models.DecimalField(
        max_digits=15, decimal_places=0, default=0,
        verbose_name="تخفیف کوپن"
    )
    shipping_cost = models.DecimalField(
        max_digits=12, decimal_places=0, default=0,
        verbose_name="هزینه ارسال"
    )
    total = models.DecimalField(
        max_digits=15, decimal_places=0, default=0,
        verbose_name="مبلغ نهایی قابل پرداخت"
    )

    # وضعیت‌ها
    status = models.CharField(
        max_length=20,
        choices=OrderStatus.choices,
        default=OrderStatus.PENDING,
        verbose_name="وضعیت سفارش"
    )

    # اطلاعات تخفیف و کوپن
    applied_discounts = models.ManyToManyField(
        Discount,
        blank=True,
        related_name='orders',
        verbose_name="تخفیف‌های اعمال شده"
    )
    coupon = models.ForeignKey(
        Coupon,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='orders',
        verbose_name="کوپن استفاده شده"
    )

    # اطلاعات ارسال
    tracking_code = models.CharField(max_length=100, blank=True, null=True, verbose_name="کد رهگیری مرسوله")
    shipped_date = models.DateTimeField(blank=True, null=True, verbose_name="تاریخ ارسال")
    delivered_date = models.DateTimeField(blank=True, null=True, verbose_name="تاریخ تحویل")

    # امتیاز
    earned_points = models.IntegerField(default=0, verbose_name="امتیاز کسب شده از این سفارش")
    used_points = models.IntegerField(default=0, verbose_name="امتیاز استفاده شده")
    used_from_wallet = models.DecimalField(
    max_digits=15, decimal_places=0, default=0,
    verbose_name="مبلغ استفاده شده از کیف پول"
)

    # اطلاعات رسید پرداخت
    has_uploaded_receipt = models.BooleanField(
        default=False,
        verbose_name="رسید پرداخت آپلود شده است"
    )
    receipt_verified = models.BooleanField(
        default=False,
        verbose_name="رسید پرداخت تایید شده است"
    )
    receipt_verified_at = models.DateTimeField(
        blank=True,
        null=True,
        verbose_name="تاریخ تایید رسید"
    )
    receipt_rejection_reason = models.TextField(
        blank=True,
        null=True,
        verbose_name="دلیل رد رسید"
    )

    # زمان‌ها
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="تاریخ ثبت سفارش")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="تاریخ بروزرسانی")
    paid_at = models.DateTimeField(blank=True, null=True, verbose_name="تاریخ پرداخت")
    cancelled_at = models.DateTimeField(blank=True, null=True, verbose_name="تاریخ لغو")
    printing = models.ForeignKey(OrderMaterial,on_delete=models.CASCADE,verbose_name='سفارش چاپی',blank=True,null=True)

    class Meta:
        verbose_name = "سفارش"
        verbose_name_plural = "سفارش‌ها"
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['order_number']),
            models.Index(fields=['user']),
            models.Index(fields=['status']),
            models.Index(fields=['order_type']),
            models.Index(fields=['created_at']),
            models.Index(fields=['has_uploaded_receipt']),
            models.Index(fields=['receipt_verified']),
        ]

    def __str__(self):
        return f"#{self.order_number} - {self.user.mobileNumber if self.user else 'مهمان'}"

    def save(self, *args, **kwargs):
        if not self.order_number:
            self.order_number = self.generate_order_number()
        super().save(*args, **kwargs)

    def generate_order_number(self):
        """تولید شماره سفارش یکتا"""
        year = timezone.now().year
        month = timezone.now().month
        random_part = secrets.token_hex(4).upper()
        return f"ORD-{year}{month:02d}-{random_part}"

    def calculate_total(self):
        """محاسبه مجدد مبلغ نهایی - بدون مالیات"""
        self.total = self.subtotal - self.discount_amount - self.coupon_discount + self.shipping_cost
        if self.total < 0:
            self.total = 0
        self.save(update_fields=['total'])
        return self.total

    def calculate_shipping_cost(self):
        """محاسبه هزینه ارسال بر اساس روش ارسال انتخاب شده"""
        if self.shipping_method:
            self.shipping_cost = self.shipping_method.calculate_cost(self.subtotal - self.discount_amount - self.coupon_discount)
            self.save(update_fields=['shipping_cost'])
        return self.shipping_cost

    def can_cancel(self):
        """آیا سفارش قابل لغو است؟"""
        return self.status in [OrderStatus.PENDING, OrderStatus.PAID, OrderStatus.PROCESSING]

    def cancel(self, reason=None):
        """لغو سفارش"""
        if self.can_cancel():
            self.status = OrderStatus.CANCELLED
            self.cancelled_at = timezone.now()
            if reason:
                self.admin_note = reason
            self.save()

            OrderStatusHistory.objects.create(
                order=self,
                status=OrderStatus.CANCELLED,
                note=reason
            )
            return True
        return False

    def mark_as_paid(self):
        """علامت‌گذاری سفارش به عنوان پرداخت شده"""
        if self.status == OrderStatus.PENDING:
            self.status = OrderStatus.PAID
            self.paid_at = timezone.now()
            self.save()

            OrderStatusHistory.objects.create(
                order=self,
                status=OrderStatus.PAID,
                note="پرداخت با موفقیت انجام شد"
            )

            self.assign_points()
            return True
        return False

    def mark_receipt_as_verified(self):
        """علامت‌گذاری رسید به عنوان تایید شده"""
        self.receipt_verified = True
        self.receipt_verified_at = timezone.now()
        self.save(update_fields=['receipt_verified', 'receipt_verified_at'])

    def mark_receipt_as_rejected(self, reason):
        """علامت‌گذاری رسید به عنوان رد شده"""
        self.receipt_verified = False
        self.receipt_rejection_reason = reason
        self.save(update_fields=['receipt_verified', 'receipt_rejection_reason'])

    def assign_points(self):
        """اختصاص امتیاز به کاربر به ازای این سفارش"""
        if self.user and self.status == OrderStatus.PAID:
            points = int(self.total / 10000)
            if points > 0:
                loyalty, created = CustomerLoyalty.objects.get_or_create(user=self.user)
                loyalty.total_points += points
                loyalty.lifetime_purchase += self.total

                if loyalty.lifetime_purchase >= 50000000:
                    loyalty.current_tier = 'platinum'
                elif loyalty.lifetime_purchase >= 20000000:
                    loyalty.current_tier = 'gold'
                elif loyalty.lifetime_purchase >= 5000000:
                    loyalty.current_tier = 'silver'
                else:
                    loyalty.current_tier = 'bronze'
                loyalty.save()

                LoyaltyTransaction.objects.create(
                    loyalty=loyalty,
                    points=points,
                    transaction_type='earn',
                    order_id=self.order_number,
                    description=f"امتیاز خرید از سفارش #{self.order_number}"
                )

                self.earned_points = points
                self.save(update_fields=['earned_points'])


class OrderItem(models.Model):
    """مدل اقلام سفارش (محصولات خریداری شده)"""

    order = models.ForeignKey(
        Order,
        on_delete=models.CASCADE,
        related_name='items',
        verbose_name="سفارش"
    )

    product = models.ForeignKey(
        Product,
        on_delete=models.SET_NULL,
        null=True,
        related_name='order_items',
        verbose_name="محصول"
    )

    # اطلاعات snapshot
    product_title = models.CharField(max_length=255, verbose_name="نام محصول")
    product_code = models.CharField(max_length=100, blank=True, null=True, verbose_name="کد محصول")
    product_image = models.CharField(max_length=500, blank=True, null=True, verbose_name="تصویر محصول")
    brand_name = models.CharField(max_length=255, blank=True, null=True, verbose_name="نام برند")

    quantity = models.DecimalField(
        max_digits=10, decimal_places=2, default=1,
        validators=[MinValueValidator(0.01)],
        verbose_name="تعداد"
    )
    unit_price = models.DecimalField(
        max_digits=15, decimal_places=0,
        verbose_name="قیمت واحد (تومان)"
    )
    unit_price_before_discount = models.DecimalField(
        max_digits=15, decimal_places=0,
        verbose_name="قیمت واحد قبل از تخفیف"
    )
    discount_amount = models.DecimalField(
        max_digits=15, decimal_places=0, default=0,
        verbose_name="مبلغ تخفیف این قلم"
    )
    discount_percent = models.IntegerField(default=0, verbose_name="درصد تخفیف")
    total = models.DecimalField(
        max_digits=15, decimal_places=0,
        verbose_name="جمع کل این قلم"
    )

    sales_unit_name = models.CharField(max_length=100, blank=True, null=True, verbose_name="واحد فروش")
    sales_unit_symbol = models.CharField(max_length=20, blank=True, null=True, verbose_name="نماد واحد")

    use_packaging = models.BooleanField(default=False, verbose_name="فروش بسته‌بندی شده")
    package_unit_name = models.CharField(max_length=100, blank=True, null=True, verbose_name="واحد بسته‌بندی")
    package_size = models.DecimalField(max_digits=10, decimal_places=2, default=1, verbose_name="اندازه هر بسته")
    packages_count = models.IntegerField(default=0, verbose_name="تعداد بسته‌ها")

    applied_discount_title = models.CharField(max_length=255, blank=True, null=True, verbose_name="عنوان تخفیف اعمال شده")

    created_at = models.DateTimeField(auto_now_add=True, verbose_name="تاریخ ایجاد")

    class Meta:
        verbose_name = "قلم سفارش"
        verbose_name_plural = "اقلام سفارش"
        ordering = ['order', 'id']

    def __str__(self):
        return f"{self.product_title} × {self.quantity} - {self.order.order_number}"

    def save(self, *args, **kwargs):
        self.total = self.unit_price * self.quantity
        super().save(*args, **kwargs)

    def get_saved_amount(self):
        """مبلغ پس‌انداز شده برای این قلم"""
        return (self.unit_price_before_discount * self.quantity) - (self.unit_price * self.quantity)

    def get_saved_percent(self):
        """درصد تخفیف این قلم"""
        if self.unit_price_before_discount and self.unit_price_before_discount > 0:
            original_total = self.unit_price_before_discount * self.quantity
            final_total = self.unit_price * self.quantity
            if original_total > 0:
                return int(((original_total - final_total) / original_total) * 100)
        return 0

    def get_original_total_display(self):
        """نمایش قیمت اصلی کل"""
        total = self.unit_price_before_discount * self.quantity
        return f"{int(total):,}"

    def get_final_total_display(self):
        """نمایش قیمت نهایی کل"""
        return f"{int(self.total):,}"

    def get_total_display(self):
        return f"{int(self.total):,}"

    def get_unit_price_display(self):
        return f"{int(self.unit_price):,}"


class OrderStatusHistory(models.Model):
    """مدل تاریخچه تغییرات وضعیت سفارش"""

    order = models.ForeignKey(
        Order,
        on_delete=models.CASCADE,
        related_name='status_history',
        verbose_name="سفارش"
    )
    status = models.CharField(max_length=20, choices=OrderStatus.choices, verbose_name="وضعیت")
    note = models.TextField(blank=True, null=True, verbose_name="توضیحات تغییر وضعیت")
    created_by = models.ForeignKey(
        CustomUser,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='order_status_changes',
        verbose_name="تغییر دهنده"
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="تاریخ تغییر")

    class Meta:
        verbose_name = "تاریخچه وضعیت سفارش"
        verbose_name_plural = "تاریخچه وضعیت سفارش‌ها"
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.order.order_number} - {self.get_status_display()} - {self.created_at.strftime('%Y/%m/%d %H:%M')}"


class Wishlist(models.Model):
    """
    مدل لیست علاقه‌مندی‌های کاربر
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        CustomUser,
        on_delete=models.CASCADE,
        related_name='wishlists',
        verbose_name=("کاربر")
    )
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name='wishlists',
        verbose_name=("محصول")
    )

    # اطلاعات محصول در زمان ذخیره (snapshot)
    product_title = models.CharField(
        max_length=255,
        null=True, blank=True,
        verbose_name=("نام محصول")
    )
    product_price = models.DecimalField(
        max_digits=15, decimal_places=0,
        null=True, blank=True,
        verbose_name=("قیمت محصول")
    )
    product_image = models.CharField(
        max_length=500,
        null=True, blank=True,
        verbose_name=("تصویر محصول")
    )
    product_slug = models.SlugField(
        max_length=255,
        null=True, blank=True,
        verbose_name=("اسلاگ محصول")
    )

    # تخفیف
    has_discount = models.BooleanField(default=False, verbose_name=("دارای تخفیف"))
    discount_percent = models.IntegerField(default=0, verbose_name=("درصد تخفیف"))
    final_price = models.DecimalField(
        max_digits=15, decimal_places=0,
        default=0,
        verbose_name=("قیمت نهایی با تخفیف")
    )

    # زمان
    added_at = models.DateTimeField(auto_now_add=True, verbose_name=("تاریخ افزودن"))
    updated_at = models.DateTimeField(auto_now=True, verbose_name=("تاریخ بروزرسانی"))

    # وضعیت
    is_active = models.BooleanField(default=True, verbose_name=("فعال"))
    notify_on_price_drop = models.BooleanField(
        default=False,
        verbose_name=("اعلام کاهش قیمت")
    )
    notify_on_back_in_stock = models.BooleanField(
        default=False,
        verbose_name=("اعلام موجودی مجدد")
    )

    class Meta:
        verbose_name = ("علاقه‌مندی")
        verbose_name_plural = ("علاقه‌مندی‌ها")
        ordering = ['-added_at']
        unique_together = ['user', 'product']

    def __str__(self):
        return f"{self.user.mobileNumber} - {self.product_title}"

    def save(self, *args, **kwargs):
        """ذخیره اطلاعات snapshot از محصول"""
        if self.product_id:
            if not self.product_title:
                self.product_title = self.product.title
            if not self.product_price:
                self.product_price = self.product.price
            if not self.product_image:
                self.product_image = self.product.image.url if self.product.image else ''
            if not self.product_slug:
                self.product_slug = self.product.slug

            if hasattr(self.product, 'has_discount') and self.product.has_discount():
                self.has_discount = True
                self.discount_percent = self.product.get_discount_percent()
                self.final_price = self.product.get_final_price()
            else:
                self.has_discount = False
                self.discount_percent = 0
                self.final_price = self.product_price or 0

        super().save(*args, **kwargs)

    @property
    def current_price(self):
        """قیمت فعلی محصول (به‌روز)"""
        if self.product:
            return self.product.price
        return self.product_price

    @property
    def current_final_price(self):
        """قیمت نهایی فعلی با تخفیف"""
        if self.product and hasattr(self.product, 'get_final_price'):
            return self.product.get_final_price()
        return self.final_price

    @property
    def price_changed(self):
        """آیا قیمت محصول تغییر کرده است؟"""
        if self.product and self.product.price != self.product_price:
            return True
        return False

    @property
    def discount_status_changed(self):
        """آیا وضعیت تخفیف تغییر کرده است؟"""
        if self.product:
            current_has_discount = self.product.has_discount()
            return current_has_discount != self.has_discount
        return False