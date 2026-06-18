# apps/payment/models/check_payment.py

from django.db import models
from django.utils import timezone
from django.core.validators import FileExtensionValidator
import uuid

from apps.user.models.user import CustomUser
from apps.order.models import Order
from apps.pro.models import OrderMaterial


class CheckPaymentStatus(models.TextChoices):
    """وضعیت‌های چک پرداختی"""
    PENDING = 'pending', 'در انتظار بررسی'
    VERIFIED = 'verified', 'تأیید شده'
    REJECTED = 'rejected', 'رد شده'
    CANCELLED = 'cancelled', 'لغو شده توسط کاربر'


class CheckPayment(models.Model):
    """
    مدل پرداخت با چک
    کاربر می‌تواند عکس چک را آپلود کند و ادمین آن را بررسی و تأیید/رد کند
    """

    # شناسه یکتا
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
        verbose_name="شناسه چک"
    )

    # شماره پیگیری یکتا (برای کاربر قابل نمایش)
    tracking_number = models.CharField(
        max_length=30,
        unique=True,
        editable=False,
        verbose_name="شماره پیگیری"
    )

    # ارتباط با کاربر (اجباری)
    user = models.ForeignKey(
        CustomUser,
        on_delete=models.CASCADE,
        related_name='check_payments',
        verbose_name="کاربر"
    )

    # ارتباط با سفارش عادی (اختیاری)
    order = models.ForeignKey(
        Order,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='check_payments',
        verbose_name="سفارش عادی"
    )

    # ارتباط با سفارش چاپی (اختیاری)
    pro_order = models.ForeignKey(
        OrderMaterial,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='check_payments',
        verbose_name="سفارش چاپی"
    )

    # تصویر چک (اجباری)
    check_image = models.ImageField(
        upload_to='checks/%Y/%m/%d/',
        validators=[
            FileExtensionValidator(
                allowed_extensions=['jpg', 'jpeg', 'png', 'pdf', 'heic']
            )
        ],
        verbose_name="تصویر چک"
    )

    # اطلاعات چک (اختیاری - کاربر می‌تواند وارد کند)
    bank_name = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        verbose_name="نام بانک صادرکننده"
    )

    check_number = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        verbose_name="شماره چک"
    )

    check_date = models.DateField(
        blank=True,
        null=True,
        verbose_name="تاریخ چک (درج شده روی چک)"
    )

    check_amount = models.DecimalField(
        max_digits=15,
        decimal_places=0,
        blank=True,
        null=True,
        verbose_name="مبلغ چک (تومان)"
    )

    # توضیحات کاربر
    description = models.TextField(
        blank=True,
        null=True,
        verbose_name="توضیحات کاربر",
        help_text="توضیحات اضافی درباره چک یا سفارش"
    )

    # وضعیت چک
    status = models.CharField(
        max_length=20,
        choices=CheckPaymentStatus.choices,
        default=CheckPaymentStatus.PENDING,
        verbose_name="وضعیت"
    )

    # اطلاعات تأیید/رد توسط ادمین
    admin_note = models.TextField(
        blank=True,
        null=True,
        verbose_name="یادداشت ادمین"
    )

    rejection_reason = models.TextField(
        blank=True,
        null=True,
        verbose_name="علت رد"
    )

    verified_by = models.ForeignKey(
        CustomUser,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='verified_checks',
        verbose_name="تأیید کننده"
    )

    verified_at = models.DateTimeField(
        blank=True,
        null=True,
        verbose_name="تاریخ تأیید"
    )

    # آیا پرداخت با این چک نهایی شده است؟
    is_finalized = models.BooleanField(
        default=False,
        verbose_name="پرداخت نهایی شده",
        help_text="بعد از تأیید چک و واریز وجه توسط ادمین، این فیلد true می‌شود"
    )

    finalized_at = models.DateTimeField(
        blank=True,
        null=True,
        verbose_name="تاریخ نهایی‌سازی پرداخت"
    )

    # زمان‌ها
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="تاریخ آپلود"
    )

    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name="تاریخ بروزرسانی"
    )

    class Meta:
        verbose_name = "پرداخت با چک"
        verbose_name_plural = "پرداخت‌های با چک"
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['tracking_number']),
            models.Index(fields=['user']),
            models.Index(fields=['status']),
            models.Index(fields=['order']),
            models.Index(fields=['pro_order']),
            models.Index(fields=['created_at']),
        ]
        constraints = [
            # حداقل یکی از سفارش‌ها باید وجود داشته باشد
            models.CheckConstraint(
                check=(
                    models.Q(order__isnull=False) |
                    models.Q(pro_order__isnull=False)
                ),
                name="check_payment_has_at_least_one_order"
            ),
        ]

    def __str__(self):
        order_ref = None
        if self.order:
            order_ref = self.order.order_number
        elif self.pro_order:
            order_ref = str(self.pro_order.id)[:8]
        return f"چک {self.tracking_number} - {self.user.mobileNumber} - {order_ref}"

    def save(self, *args, **kwargs):
        if not self.tracking_number:
            self.tracking_number = self.generate_tracking_number()
        super().save(*args, **kwargs)

    def generate_tracking_number(self):
        """تولید شماره پیگیری یکتا"""
        import secrets
        from datetime import datetime

        year = datetime.now().year
        month = datetime.now().month
        random_part = secrets.token_hex(3).upper()
        return f"CHK-{year}{month:02d}-{random_part}"

    def verify(self, admin_user, note=None):
        """
        تأیید چک توسط ادمین
        """
        if self.status != CheckPaymentStatus.PENDING:
            return False, "فقط چک‌های در انتظار بررسی قابل تأیید هستند"

        self.status = CheckPaymentStatus.VERIFIED
        self.verified_by = admin_user
        self.verified_at = timezone.now()
        if note:
            self.admin_note = note
        self.save()

        # ایجاد تاریخچه
        CheckPaymentHistory.objects.create(
            check_payment=self,
            action=CheckPaymentHistory.ActionType.ADMIN_VERIFIED,
            message=f"چک تأیید شد توسط {admin_user.mobileNumber}",
            created_by=admin_user
        )

        return True, "چک با موفقیت تأیید شد"

    def reject(self, admin_user, reason, note=None):
        """
        رد چک توسط ادمین با ذکر دلیل
        """
        if self.status != CheckPaymentStatus.PENDING:
            return False, "فقط چک‌های در انتظار بررسی قابل رد هستند"

        if not reason:
            return False, "لطفاً دلیل رد چک را وارد کنید"

        self.status = CheckPaymentStatus.REJECTED
        self.rejection_reason = reason
        self.verified_by = admin_user
        if note:
            self.admin_note = note
        self.save()

        # ایجاد تاریخچه
        CheckPaymentHistory.objects.create(
            check_payment=self,
            action=CheckPaymentHistory.ActionType.ADMIN_REJECTED,
            message=f"چک رد شد: {reason}",
            created_by=admin_user
        )

        return True, "چک با موفقیت رد شد"

    def cancel(self, user):
        """
        لغو چک توسط کاربر (فقط در حالت pending)
        """
        if self.status != CheckPaymentStatus.PENDING:
            return False, "فقط چک‌های در انتظار بررسی قابل لغو هستند"

        if self.user != user:
            return False, "شما اجازه لغو این چک را ندارید"

        self.status = CheckPaymentStatus.CANCELLED
        self.save()

        CheckPaymentHistory.objects.create(
            check_payment=self,
            action=CheckPaymentHistory.ActionType.USER_CANCELLED,
            message="چک توسط کاربر لغو شد",
            created_by=user
        )

        return True, "چک با موفقیت لغو شد"

    def finalize_payment(self, admin_user):
        """
        نهایی‌سازی پرداخت بعد از واریز وجه چک توسط ادمین
        """
        if self.status != CheckPaymentStatus.VERIFIED:
            return False, "فقط چک‌های تأیید شده قابل نهایی‌سازی هستند"

        if self.is_finalized:
            return False, "این پرداخت قبلاً نهایی شده است"

        self.is_finalized = True
        self.finalized_at = timezone.now()
        self.save()

        # بروزرسانی وضعیت سفارش مربوطه
        if self.order and self.order.status == 'pending':
            self.order.mark_as_paid()

        # اگر سفارش چاپی داریم، وضعیت آن را به پرداخت شده تغییر دهید
        if self.pro_order and self.pro_order.status == 'pending':
            self.pro_order.status = 'paid'
            self.pro_order.save(update_fields=['status'])

        CheckPaymentHistory.objects.create(
            check_payment=self,
            action=CheckPaymentHistory.ActionType.PAYMENT_FINALIZED,
            message="پرداخت چک نهایی شد و سفارش تأیید گردید",
            created_by=admin_user
        )

        return True, "پرداخت نهایی شد و سفارش تأیید گردید"

    @property
    def related_order_display(self):
        """نمایش مرتبط با سفارش برای نمایش در ادمین"""
        if self.order:
            return f"سفارش عادی: {self.order.order_number}"
        elif self.pro_order:
            return f"سفارش چاپی: {str(self.pro_order.id)[:8]}"
        return "بدون سفارش"

    @property
    def total_amount_to_pay(self):
        """مبلغ قابل پرداخت برای سفارش مربوطه"""
        if self.order:
            return self.order.total
        elif self.pro_order and self.pro_order.total_price:
            return self.pro_order.total_price
        return 0


class CheckPaymentHistory(models.Model):
    """
    تاریخچه تغییرات وضعیت چک
    """

    class ActionType(models.TextChoices):
        USER_UPLOADED = 'user_uploaded', 'آپلود توسط کاربر'
        USER_CANCELLED = 'user_cancelled', 'لغو توسط کاربر'
        ADMIN_VERIFIED = 'admin_verified', 'تأیید توسط ادمین'
        ADMIN_REJECTED = 'admin_rejected', 'رد توسط ادمین'
        PAYMENT_FINALIZED = 'payment_finalized', 'پرداخت نهایی شد'
        CHECK_UPDATED = 'check_updated', 'بروزرسانی اطلاعات'

    # تغییر نام فیلد از 'check' به 'check_payment' برای جلوگیری از تداخل
    check_payment = models.ForeignKey(
        CheckPayment,
        on_delete=models.CASCADE,
        related_name='history',
        verbose_name="چک"
    )

    action = models.CharField(
        max_length=30,
        choices=ActionType.choices,
        verbose_name="نوع اقدام"
    )

    message = models.TextField(
        blank=True,
        null=True,
        verbose_name="توضیحات"
    )

    created_by = models.ForeignKey(
        CustomUser,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='check_history_actions',
        verbose_name="انجام دهنده"
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="تاریخ"
    )

    class Meta:
        verbose_name = "تاریخچه چک"
        verbose_name_plural = "تاریخچه چک‌ها"
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.check_payment.tracking_number} - {self.get_action_display()} - {self.created_at.strftime('%Y/%m/%d %H:%M')}"