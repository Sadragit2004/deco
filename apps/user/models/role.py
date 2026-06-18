# ==================== فایل apps/user/models/role.py ====================

from django.db import models
from django.utils import timezone
import uuid
from .user import CustomUser


class Role(models.Model):
    """مدل نقش‌های کاربری (لیست نقش‌ها)"""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    title = models.CharField(max_length=100, unique=True, verbose_name="عنوان نقش")
    isActive = models.BooleanField(default=True, verbose_name="فعال")
    createAt = models.DateTimeField(default=timezone.now, verbose_name="تاریخ ایجاد")
    slug=models.CharField(max_length=200,verbose_name='اسلاگ',blank=True,null=True)

    class Meta:
        verbose_name = "نقش"
        verbose_name_plural = "نقش‌ها"
        ordering = ['title']

    def __str__(self):
        return self.title


class RoleBanUrl(models.Model):
    """مدل URL های ممنوع برای هر نقش (لیست سیاه)"""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    role = models.ForeignKey(Role, on_delete=models.CASCADE, related_name='ban_urls', verbose_name="نقش")
    url_pattern = models.CharField(max_length=500, verbose_name="الگوی URL ممنوع")
    description = models.TextField(blank=True, null=True, verbose_name="توضیحات")
    isActive = models.BooleanField(default=True, verbose_name="فعال")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "URL ممنوع"
        verbose_name_plural = "URL های ممنوع"
        unique_together = ['role', 'url_pattern']

    def __str__(self):
        return f"{self.role.title} ❌ {self.url_pattern}"

    def match(self, path):
        import re
        pattern = self.url_pattern.replace('*', '.*')
        if not pattern.startswith('^'):
            pattern = '^' + pattern
        if not pattern.endswith('$'):
            pattern = pattern + '$'
        try:
            return re.match(pattern, path) is not None
        except:
            return False


class UserBan(models.Model):
    """مدل تاریخچه بن کاربران"""

    REASON_CHOICES = (
        ('spam', 'اسپم و تبلیغات'),
        ('abuse', 'سوء استفاده'),
        ('fraud', 'کلاهبرداری'),
        ('violation', 'نقض قوانین'),
        ('other', 'سایر موارد'),
    )

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='bans', verbose_name="کاربر")
    reason = models.CharField(max_length=20, choices=REASON_CHOICES, default='other', verbose_name="دلیل بن")
    description = models.TextField(blank=True, null=True, verbose_name="توضیحات")
    started_at = models.DateTimeField(default=timezone.now, verbose_name="تاریخ شروع")
    expires_at = models.DateTimeField(blank=True, null=True, verbose_name="تاریخ انقضا")
    is_permanent = models.BooleanField(default=False, verbose_name="بن دائمی")
    is_active = models.BooleanField(default=True, verbose_name="فعال")
    banned_by = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True, blank=True, related_name='banned_users', verbose_name="بن کننده")

    class Meta:
        verbose_name = "بن کاربر"
        verbose_name_plural = "بن‌های کاربران"
        ordering = ['-started_at']

    def __str__(self):
        return f"{self.user.mobileNumber} - {self.get_reason_display()}"

    @property
    def is_expired(self):
        if self.is_permanent:
            return False
        if self.expires_at and timezone.now() > self.expires_at:
            return True
        return False

    def unban(self):
        self.is_active = False
        self.save()