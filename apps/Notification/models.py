from django.db import models
from django.utils import timezone
from apps.user.models.user import CustomUser
from apps.order.models import Order  # فقط Order رو بیار، OrderStatus نیاز نیست


class OrderStatusNotification(models.Model):
    """مدل اعلان تغییر وضعیت سفارش"""

    # انتخاب‌های وضعیت (دوباره تعریف کن تا وابسته نباشه)
    STATUS_CHOICES = [
        ('pending', 'در انتظار پرداخت'),
        ('paid', 'پرداخت شده'),
        ('processing', 'در حال پردازش'),
        ('packaging', 'در حال بسته‌بندی'),
        ('shipped', 'ارسال شده'),
        ('delivered', 'تحویل شده'),
        ('cancelled', 'لغو شده'),
    ]

    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='status_notifications')
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='order_notifications')

    old_status = models.CharField(max_length=20, choices=STATUS_CHOICES)
    new_status = models.CharField(max_length=20, choices=STATUS_CHOICES)

    message = models.TextField()

    is_sent = models.BooleanField(default=False)
    sent_at = models.DateTimeField(null=True, blank=True)

    status_changed_at = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'is_sent']),
            models.Index(fields=['order', 'new_status']),
        ]

    def __str__(self):
        return f"{self.order.order_number}: {self.old_status} -> {self.new_status}"