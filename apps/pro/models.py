from django.db import models
from django.conf import settings
from django.core.validators import MinValueValidator
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
import uuid

# ==================== 1. نصبیات (محصول اصلی) ====================
class Installation(models.Model):
    """نصبیات اصلی - مثل: سقف کشسان، پوستر سه بعدی"""
    title = models.CharField(_("عنوان"), max_length=200)
    description = models.TextField(_("توضیحات"), blank=True)
    main_image = models.ImageField(_("عکس اصلی"), upload_to="installations/")
    order = models.PositiveIntegerField(_("ترتیب نمایش"), default=0)
    is_active = models.BooleanField(_("فعال"), default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    price = models.PositiveIntegerField(default=0,verbose_name='قیمت نصبیات')

    class Meta:
        verbose_name = _("نصبیات")
        verbose_name_plural = _("نصبیات")
        ordering = ['order', 'title']

    def __str__(self):
        return self.title


# ==================== 2. جنس‌های هر نصبیات ====================
class InstallationMaterial(models.Model):
    """جنس‌های مختلف هر نصبیات (مات، براق، ساتن، ...)"""
    installation = models.ForeignKey(
        Installation,
        on_delete=models.CASCADE,
        related_name="materials",
        verbose_name=_("نصبیات")
    )
    title = models.CharField(_("عنوان جنس"), max_length=200)
    description = models.TextField(_("توضیحات"), blank=True)
    image = models.ImageField(_("عکس"), upload_to="materials/", blank=True)
    price_multiplier = models.DecimalField(
        _("ضریب قیمت"),
        max_digits=5,
        decimal_places=2,
        default=1.00,
        help_text="مثل: 1.15 برای پانزده درصد بیشتر"
    )
    is_active = models.BooleanField(_("فعال"), default=True)
    order = models.PositiveIntegerField(_("ترتیب"), default=0)

    class Meta:
        verbose_name = _("جنس نصبیات")
        verbose_name_plural = _("جنس‌های نصبیات")
        ordering = ['order', 'title']

    def __str__(self):
        return f"{self.installation.title} - {self.title}"


# ==================== 3. PDFهای هر جنس ====================
class MaterialPDF(models.Model):
    """PDFهای مخصوص هر جنس از نصبیات"""
    material = models.ForeignKey(
        InstallationMaterial,
        on_delete=models.CASCADE,
        related_name="pdfs",
        verbose_name=_("جنس")
    )
    title = models.CharField(_("عنوان PDF"), max_length=200)
    pdf_file = models.FileField(_("فایل PDF"), upload_to="pdfs/")
    code = models.CharField(_("کد PDF"), max_length=50, unique=True, blank=True)
    thumbnail = models.ImageField(_("تصویر بندانگشتی"), upload_to="pdf_thumbs/", blank=True)
    download_count = models.PositiveIntegerField(_("تعداد دانلود"), default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = _("PDF جنس")
        verbose_name_plural = _("PDFهای جنس")
        ordering = ['-created_at']

    def save(self, *args, **kwargs):
        if not self.code:
            self.code = f"PDF-{self.material.installation.id:02d}{self.material.id:02d}{self.id or 0:04d}"
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.material.title} - {self.title}"


# ==================== 4. طرح‌های آماده هر نصبیات ====================
class ReadyTemplate(models.Model):
    """طرح‌های آماده برای هر نصبیات"""
    installation = models.ForeignKey(
        Installation,
        on_delete=models.CASCADE,
        related_name="ready_templates",
        verbose_name=_("نصبیات")
    )
    title = models.CharField(_("عنوان طرح"), max_length=200)
    description = models.TextField(_("توضیحات"), blank=True)
    image = models.ImageField(_("تصویر طرح"), upload_to="templates/")
    width = models.PositiveIntegerField(_("عرض (سانتی‌متر)"), default=100)
    height = models.PositiveIntegerField(_("ارتفاع (سانتی‌متر)"), default=100)
    is_active = models.BooleanField(_("فعال"), default=True)
    order = models.PositiveIntegerField(_("ترتیب"), default=0)

    class Meta:
        verbose_name = _("طرح آماده")
        verbose_name_plural = _("طرح‌های آماده")
        ordering = ['order', 'title']

    def __str__(self):
        return f"{self.installation.title} - {self.title}"


# ==================== 5. گالری تصاویر هر طرح آماده ====================
class TemplateGallery(models.Model):
    """گالری تصاویر برای هر طرح آماده"""
    template = models.ForeignKey(
        ReadyTemplate,
        on_delete=models.CASCADE,
        related_name="gallery",
        verbose_name=_("طرح آماده")
    )
    image = models.ImageField(_("عکس"), upload_to="template_gallery/")
    title = models.CharField(_("عنوان"), max_length=200, blank=True)
    order = models.PositiveIntegerField(_("ترتیب"), default=0)

    class Meta:
        verbose_name = _("تصویر گالری")
        verbose_name_plural = _("تصاویر گالری")
        ordering = ['order']

    def __str__(self):
        return f"{self.template.title} - {self.order}"


# ==================== 6. سفارش نهایی ====================
class OrderMaterial(models.Model):
    """سفارش نهایی کاربر"""

    DESIGN_TYPES = [
        ('ready', 'طرح آماده'),
        ('custom', 'طراحی خودم'),
        ('pdf', 'بر اساس کد PDF'),
    ]

    UNIT_TYPES = [
        ('m2', 'متر مربع'),
        ('pcs', 'عدد'),
        ('set', 'ست'),
    ]

    STATUS_CHOICES = [
        ('pending', 'در انتظار بررسی'),
        ('confirmed', 'تأیید شده'),
        ('processing', 'در حال ساخت'),
        ('ready', 'آماده تحویل'),
        ('delivered', 'تحویل شده'),
        ('cancelled', 'لغو شده'),
    ]

    # شناسه یکتا
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
        verbose_name="شماره سفارش"
    )

    # کاربر
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="pro_orders",
        verbose_name="کاربر",
        null=True,
        blank=True
    )

    # اطلاعات سفارش
    installation = models.ForeignKey(
        Installation,
        on_delete=models.SET_NULL,
        null=True,
        related_name="orders",
        verbose_name="نصبیات"
    )

    material = models.ForeignKey(
        InstallationMaterial,
        on_delete=models.SET_NULL,
        null=True,
        related_name="orders",
        verbose_name="جنس"
    )

    pdf_document = models.ForeignKey(
        MaterialPDF,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="orders",
        verbose_name="PDF انتخابی"
    )

    ready_template = models.ForeignKey(
        ReadyTemplate,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="orders",
        verbose_name="طرح آماده"
    )

    design_type = models.CharField(
        "نوع طراحی",
        max_length=20,
        choices=DESIGN_TYPES,
        default='custom'
    )

    # ابعاد
    length = models.DecimalField(
        "طول (متر)",
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(0.1)]
    )

    width = models.DecimalField(
        "عرض (متر)",
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(0.1)]
    )

    # عکس پلن
    plan_image = models.ImageField(
        "عکس پلن",
        upload_to="order_plans/%Y/%m/%d/",
        blank=True,
        null=True
    )

    # قیمت
    total_price = models.DecimalField(
        "قیمت کل",
        max_digits=15,
        decimal_places=0,
        null=True,
        blank=True
    )

    # وضعیت
    status = models.CharField(
        "وضعیت",
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending'
    )

    # توضیحات
    notes = models.TextField(
        "توضیحات",
        blank=True,
        help_text="توضیحات اضافی سفارش"
    )

    # تاریخ‌ها
    created_at = models.DateTimeField("تاریخ ثبت", default=timezone.now)
    updated_at = models.DateTimeField("آخرین بروزرسانی", auto_now=True)
    isEnd = models.BooleanField(default=False,verbose_name='اتمام طرح')

    class Meta:
        verbose_name = "سفارش"
        verbose_name_plural = "سفارشات"
        ordering = ['-created_at']

    def __str__(self):
        return f"سفارش {str(self.id)[:8]} - {self.installation.title if self.installation else '-'}"

    @property
    def area(self):
        """مساحت به متر مربع"""
        return float(self.length) * float(self.width)


# ==================== 7. وضعیت طراحی و فایل نهایی ====================
class OrderDesignStatus(models.Model):
    """وضعیت طراحی و فایل‌های نهایی هر سفارش"""

    DESIGN_STATUS_CHOICES = [
        ('pending_design', 'در انتظار طراحی'),
        ('designing', 'در حال طراحی'),
        ('ready_for_review', 'آماده بررسی کاربر'),
        ('approved', 'تأیید شده توسط کاربر'),
        ('rejected', 'رد شده توسط کاربر'),
        ('finalized', 'اتمام کار - تحویل نهایی'),
    ]

    order = models.OneToOneField(
        OrderMaterial,
        on_delete=models.CASCADE,
        related_name="design_status",
        verbose_name="سفارش"
    )

    status = models.CharField(
        "وضعیت طراحی",
        max_length=30,
        choices=DESIGN_STATUS_CHOICES,
        default='pending_design'
    )

    # فایل نهایی طراحی شده توسط فتوشاپ کار
    final_design_image = models.ImageField(
        "تصویر نهایی طراحی شده",
        upload_to="final_designs/%Y/%m/%d/",
        blank=True,
        null=True
    )

    final_design_psd = models.FileField(
        "فایل PSD نهایی",
        upload_to="final_psd/%Y/%m/%d/",
        blank=True,
        null=True
    )

    # توضیحات اپراتور برای کاربر
    operator_message = models.TextField(
        "پیام اپراتور به کاربر",
        blank=True,
        help_text="مثلاً: لطفاً فایل نهایی را بررسی کنید"
    )

    # تاریخ تحویل نهایی
    delivered_at = models.DateTimeField(
        "تاریخ تحویل نهایی",
        blank=True,
        null=True
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "وضعیت طراحی سفارش"
        verbose_name_plural = "وضعیت‌های طراحی سفارشات"

    def __str__(self):
        return f"وضعیت طراحی سفارش {self.order.id} - {self.get_status_display()}"


# ==================== 8. تاریخچه رد و تاییدها (حداکثر ۳ بار) ====================
class OrderReviewHistory(models.Model):
    """تاریخچه بررسی‌های کاربر و اپراتور (رد/تایید)"""

    ACTION_CHOICES = [
        ('operator_submit', 'اپراتور ارسال کرد'),
        ('user_approve', 'کاربر تأیید کرد'),
        ('user_reject', 'کاربر رد کرد'),
    ]

    order = models.ForeignKey(
        OrderMaterial,
        on_delete=models.CASCADE,
        related_name="review_history",
        verbose_name="سفارش"
    )

    action = models.CharField(
        "نوع اقدام",
        max_length=20,
        choices=ACTION_CHOICES
    )

    message = models.TextField(
        "پیام",
        blank=True,
        help_text="دلیل رد یا توضیحات"
    )

    # تصویر یا فایل ارسالی در این مرحله (در صورت وجود)
    attached_image = models.ImageField(
        "تصویر پیوست",
        upload_to="review_images/%Y/%m/%d/",
        blank=True,
        null=True
    )

    # مرحله چندم رد شدن (از ۱ تا ۳)
    reject_round = models.PositiveSmallIntegerField(
        "مرحله رد شدن",
        blank=True,
        null=True,
        help_text="چندمین بار رد شدن؟ (حداکثر ۳)"
    )

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="review_actions",
        verbose_name="انجام دهنده"
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "تاریخچه بررسی"
        verbose_name_plural = "تاریخچه بررسی‌ها"
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.order.id} - {self.get_action_display()} - {self.created_at.strftime('%Y/%m/%d %H:%M')}"


