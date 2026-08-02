# ==================== فایل apps/user/signals.py ====================

from django.db.models.signals import post_save
from django.dispatch import receiver
from .models.user import CustomUser
from .models.security import UserSecurity
from .models.role import Role


@receiver(post_save, sender=CustomUser)
def create_user_security_and_role(sender, instance, created, **kwargs):
    if created:
        # ایجاد امنیت کاربر
        UserSecurity.objects.create(user=instance)

        # اختصاص نقش پیش‌فرض با slug='user'
        try:
            default_role = Role.objects.get(slug='user', isActive=True)
            instance.roles.add(default_role)
        except Role.DoesNotExist:
            # اگر نقش با slug='user' وجود نداشت، سعی می‌کنیم اولین نقش فعال رو بگیریم
            default_role = Role.objects.filter(isActive=True).first()
            if default_role:
                instance.roles.add(default_role)


@receiver(post_save, sender=CustomUser)
def save_user_security(sender, instance, **kwargs):
    try:
        instance.security.save()
    except UserSecurity.DoesNotExist:
        UserSecurity.objects.create(user=instance)





# signals.py
from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from .models import CustomUser, UserSecurity
import utils
import logging

logger = logging.getLogger(__name__)


@receiver(pre_save, sender=UserSecurity)
def check_activation_conditions(sender, instance, **kwargs):
    """
    بررسی شرایط فعال‌سازی کاربر
    """
    try:
        old_instance = UserSecurity.objects.get(pk=instance.pk)
    except UserSecurity.DoesNotExist:
        return

    if not instance.user:
        return

    user = instance.user

    # وضعیت فعلی و قبلی
    is_active_now = user.is_active
    is_active_before = old_instance.user.is_active if old_instance.user else False

    is_verified_now = instance.isVerfiyByManager
    is_verified_before = old_instance.isVerfiyByManager

    # اگر هر دو true شدن (قبلا نبودن)
    if (is_active_now and is_verified_now) and (not is_active_before or not is_verified_before):
        instance._pending_sms = True


@receiver(post_save, sender=UserSecurity)
def send_activation_sms(sender, instance, created, **kwargs):
    """
    ارسال پیامک بعد از فعال‌سازی
    """
    if hasattr(instance, '_pending_sms') and instance._pending_sms:
        try:
            if instance.user and instance.user.mobileNumber:
                # ارسال پیامک با نام کاربر
                utils.send_confirmation_sms(
                    instance.user.mobileNumber,
                    instance.user.name or instance.user.mobileNumber
                )
                logger.info(f"SMS sent to {instance.user.mobileNumber}")

        except Exception as e:
            logger.error(f"Error sending SMS: {str(e)}")

        delattr(instance, '_pending_sms')