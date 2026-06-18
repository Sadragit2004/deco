# signals.py (در اپلیکیشن payments یا هر جای مناسب)

from django.db.models.signals import post_save
from django.dispatch import receiver
from django.db import transaction
from .models import Peyment  # مدل پرداخت شما
from apps.user.models.security import UserSecurity
from apps.user.models.profile import WalletTransaction, Wallet, CustomerLoyalty, LoyaltyTransaction
from decimal import Decimal

@receiver(post_save, sender=Peyment)
def handle_first_payment_membership(sender, instance, created, **kwargs):
    """
    اگر اولین پرداخت کاربر باشد (هیچ پرداخت دیگری نداشته باشد)
    و سفارش نداشته باشد (order == null)
    و مبلغ پرداختی برابر 5,000,000 تومان باشد
    حق عضویت کاربر تایید شده و کیف پول به مبلغ 5,000,000 تومان شارژ می‌شود
    و 1 سکه B2B به کاربر تعلق می‌گیرد
    """

    # فقط برای پرداخت‌های تازه ایجاد شده
    if not created:
        return

    # شرط: پرداخت باید نهایی شده باشد (isFinaly == True)
    if not instance.isFinaly:
        return

    # شرط: پرداخت نباید سفارش داشته باشد
    if instance.order is not None:
        return

    # شرط: مبلغ باید دقیقاً 5,000,000 تومان باشد
    if instance.amount != 5000000:
        return

    # بررسی می‌کنیم که این اولین پرداخت کاربر باشد
    # (هیچ پرداخت دیگری با isFinaly=True غیر از این پرداخت وجود نداشته باشد)
    previous_payments = Peyment.objects.filter(
        customer=instance.customer,
        isFinaly=True
    ).exclude(id=instance.id)

    # اگر قبلاً پرداختی داشته، اولین پرداخت نیست
    if previous_payments.exists():
        return

    # استفاده از transaction برای اتمیک بودن عملیات
    with transaction.atomic():
        # 1. تایید حق عضویت کاربر
        security, created = UserSecurity.objects.get_or_create(user=instance.customer)
        security.isPeymentuser = True
        security.isVerfiyByManager = True  # تایید خودکار توسط سیستم
        security.save()

        # 2. دریافت یا ایجاد کیف پول کاربر
        wallet, created = Wallet.objects.get_or_create(user=instance.customer)

        # 3. شارژ کیف پول به مبلغ 5,000,000 تومان
        amount_decimal = Decimal(instance.amount)

        # افزایش موجودی کیف پول
        wallet.balance += amount_decimal
        wallet.save()

        # 4. ثبت تراکنش کیف پول
        WalletTransaction.objects.create(
            wallet=wallet,
            amount=amount_decimal,
            transaction_type='deposit',  # واریز
            status='completed',
            reference_id=instance.refId or f"MEMBERSHIP_{instance.id}",
            description=f"شارژ کیف پول بابت پرداخت حق عضویت - کد پیگیری: {instance.refId or 'ندارد'}"
        )

        # 5. اضافه کردن 1 سکه B2B به کاربر
        loyalty, created = CustomerLoyalty.objects.get_or_create(user=instance.customer)
        loyalty.total_coins += 1
        loyalty.save()

        # 6. ثبت تراکنش سکه B2B
        LoyaltyTransaction.objects.create(
            loyalty=loyalty,
            points=1,
            transaction_type='earn',
            order_id=None,
            description=f"کسب 1 سکه B2B بابت پرداخت حق عضویت - کد پیگیری: {instance.refId or 'ندارد'}"
        )

        # 7. آپدیت وضعیت پرداخت در صورت نیاز (اختیاری)
        instance.description = f"{instance.description or ''} - حق عضویت تایید و کیف پول شارژ شد و 1 سکه B2B تعلق گرفت"
        instance.save(update_fields=['description'])


# همچنین می‌توانید یک سیگنال برای زمانی که پرداخت آپدیت می‌شود (وضعیت نهایی می‌شود) بنویسید
@receiver(post_save, sender=Peyment)
def handle_payment_finalization(sender, instance, created, **kwargs):
    """
    زمانی که یک پرداخت نهایی می‌شود (مثلاً بعد از تایید ادمین)
    اگر قبلاً سیگنال بالا اجرا نشده باشد، این سیگنال اجرا می‌شود
    """

    # اگر پرداخت تازه ساخته شده و قبلاً وضعیت نهایی داشته، نیازی نیست
    if created and instance.isFinaly:
        # سیگنال قبلی کار را انجام می‌دهد
        return

    # اگر پرداخت از حالت غیرنهایی به نهایی تغییر کرده باشد
    if not created and instance.isFinaly:
        # چک می‌کنیم که آیا سیگنال قبلی قبلاً این پرداخت را پردازش کرده است؟
        # با بررسی description یا یک فیلد جداگانه می‌توان این کار را کرد
        if "کیف پول شارژ شد" in (instance.description or ""):
            return  # قبلاً پردازش شده

        # بررسی شرایط و اجرای عملیات مشابه
        if instance.order is None and instance.amount == 5000000:
            previous_payments = Peyment.objects.filter(
                customer=instance.customer,
                isFinaly=True
            ).exclude(id=instance.id)

            if not previous_payments.exists():
                # اجرای عملیات شارژ کیف پول و تایید عضویت و اضافه کردن سکه
                with transaction.atomic():
                    security, _ = UserSecurity.objects.get_or_create(user=instance.customer)
                    security.isPeymentuser = True
                    security.isVerfiyByManager = True
                    security.save()

                    wallet, _ = Wallet.objects.get_or_create(user=instance.customer)
                    amount_decimal = Decimal(instance.amount)
                    wallet.balance += amount_decimal
                    wallet.save()

                    WalletTransaction.objects.create(
                        wallet=wallet,
                        amount=amount_decimal,
                        transaction_type='deposit',
                        status='completed',
                        reference_id=instance.refId or f"MEMBERSHIP_{instance.id}",
                        description=f"شارژ کیف پول بابت پرداخت حق عضویت - کد پیگیری: {instance.refId or 'ندارد'}"
                    )

                    # اضافه کردن 1 سکه B2B
                    loyalty, _ = CustomerLoyalty.objects.get_or_create(user=instance.customer)
                    loyalty.total_coins += 1
                    loyalty.save()

                    LoyaltyTransaction.objects.create(
                        loyalty=loyalty,
                        points=1,
                        transaction_type='earn',
                        order_id=None,
                        description=f"کسب 1 سکه B2B بابت پرداخت حق عضویت - کد پیگیری: {instance.refId or 'ندارد'}"
                    )

                    instance.description = f"{instance.description or ''} - حق عضویت تایید و کیف پول شارژ شد و 1 سکه B2B تعلق گرفت"
                    instance.save(update_fields=['description'])