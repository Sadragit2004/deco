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