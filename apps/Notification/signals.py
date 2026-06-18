# apps/notifications/signals.py

from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from django.utils import timezone
from apps.order.models import Order


@receiver(pre_save, sender=Order)
def store_old_order_status(sender, instance, **kwargs):
    """ذخیره وضعیت قبلی سفارش قبل از تغییر"""
    if instance.pk:
        try:
            old_order = Order.objects.get(pk=instance.pk)
            instance._old_status = old_order.status
            print(f"📦 pre_save - سفارش: {instance.order_number} - وضعیت قبلی: {instance._old_status}")
        except Order.DoesNotExist:
            instance._old_status = None
            print(f"📦 pre_save - سفارش جدید: {instance.order_number}")
    else:
        instance._old_status = None
        print(f"📦 pre_save - سفارش جدید (بدون pk): {instance.order_number}")


@receiver(post_save, sender=Order)
def create_order_status_notification(sender, instance, created, **kwargs):
    """ساخت اعلان برای تغییر وضعیت سفارش"""

    from apps.Notification.models import OrderStatusNotification

    print(f"🔥 post_save - سفارش: {instance.order_number} - created: {created} - status: {instance.status}")

    # اگه سفارش جدید باشه
    if created:
        print("سفارش جدید است، اعلان ساخته نمی‌شود")
        return

    # اگه کاربر نداشته باشه
    if not instance.user:
        print("کاربر ندارد")
        return

    # گرفتن وضعیت قبلی
    old_status = getattr(instance, '_old_status', None)

    if old_status is None:
        print("وضعیت قبلی پیدا نشد")
        return

    print(f"وضعیت قبلی: {old_status}")
    print(f"وضعیت جدید: {instance.status}")

    # اگه وضعیت تغییر نکرده
    if old_status == instance.status:
        print("وضعیت تغییر نکرده")
        return

    # فقط برای وضعیت‌های غیر از pending
    if instance.status == 'pending':
        print("وضعیت جدید pending است، اعلان ساخته نمی‌شود")
        return

    # نام فارسی
    status_fa = {
        'pending': 'در انتظار پرداخت',
        'paid': 'پرداخت شده',
        'processing': 'در حال پردازش',
        'packaging': 'در حال بسته‌بندی',
        'shipped': 'ارسال شده',
        'delivered': 'تحویل شده',
        'cancelled': 'لغو شده',
    }

    message = f"سفارش #{instance.order_number}\nوضعیت: {status_fa.get(instance.status, instance.status)}"

    # ساخت اعلان
    try:
        notif = OrderStatusNotification.objects.create(
            order=instance,
            user=instance.user,
            old_status=old_status,
            new_status=instance.status,
            message=message,
            status_changed_at=timezone.now(),
            is_sent=False
        )
        print(f"✅ اعلان ساخته شد: {notif.id} - از {old_status} به {instance.status}")
    except Exception as e:
        print(f"❌ خطا در ساخت اعلان: {e}")