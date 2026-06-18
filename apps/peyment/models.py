from django.db import models
from apps.user.models.user import CustomUser
from django.utils import timezone
from apps.order.models import Order
import utils
import jdatetime


class PaymentMethod(models.TextChoices):
    """روش‌های پرداخت"""
    CARD_TO_CARD = 'card_to_card', 'کارت به کارت'
    ONLINE = 'online', 'درگاه پرداخت آنلاین'


class Peyment(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='peyment_order', verbose_name='سفارش',null=True,blank=True)
    customer = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='peyment_customer', verbose_name='مشتری')
    createAt = models.DateTimeField(default=timezone.now, verbose_name="تاریخ ساخته شده")
    updateAt = models.DateTimeField(auto_now=True, verbose_name="تاریخ بروزرسانی")
    amount = models.IntegerField(verbose_name='مبلغ پرداخت')
    description = models.TextField(verbose_name='توضیحات پرداخت')
    isFinaly = models.BooleanField(default=False, verbose_name='وضعیت پرداخت')
    statusCode = models.IntegerField(verbose_name='کد وضعیت پرداخت', null=True, blank=True)
    refId = models.CharField(max_length=50, verbose_name='کد پیگیری پرداخت', null=True, blank=True)
    # amount_toman = models.IntegerField(verbose_name='مبلغ پرداخت (تومان)', null=True, blank=True)

    # روش پرداخت
    payment_method = models.CharField(
        max_length=20,
        choices=PaymentMethod.choices,
        default=PaymentMethod.ONLINE,
        verbose_name='روش پرداخت'
    )

    # اطلاعات کارت به کارت
    receipt_image = models.ImageField(
        upload_to='payment_receipts/%Y/%m/%d/',
        blank=True,
        null=True,
        verbose_name='تصویر رسید'
    )
    card_number = models.CharField(max_length=16, blank=True, null=True, verbose_name='شماره کارت مبدا')
    card_holder_name = models.CharField(max_length=100, blank=True, null=True, verbose_name='نام دارنده کارت')
    tracking_number = models.CharField(max_length=100, blank=True, null=True, verbose_name='شماره پیگیری')

    def get_jalali_register_date(self):
        return jdatetime.datetime.fromgregorian(datetime=self.createAt).strftime('%Y/%m/%d')

    def __str__(self) -> str:
        return f'{self.order}\t\t{self.customer}\t\t{self.refId}'

    class Meta:
        verbose_name = 'پرداخت'
        verbose_name_plural = 'پرداخت ها'