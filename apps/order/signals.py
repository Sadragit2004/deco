# apps/order/signals.py

from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from django.utils import timezone
from decimal import Decimal
from apps.order.models import Order, CustomerLoyalty, LoyaltyTransaction, OrderStatusHistory
from apps.order.models import OrderItem
from apps.peyment.models import Peyment, PaymentMethod
from apps.product.models import Product
from apps.user.models.profile import Wallet, WalletTransaction
from apps.check.models import CheckPayment, CheckPaymentStatus


AMOUNT_PER_COIN = Decimal('50000000')  # هر ۵۰ میلیون تومان = ۱ سکه
COIN_VALUE = Decimal('500000')  # ارزش هر سکه = ۵۰۰ هزار تومان


def calculate_new_coins_and_wallet_amount(old_lifetime, new_lifetime):
    """محاسبه سکه‌های جدید و مبلغ شارژ کیف پول"""
    if new_lifetime <= old_lifetime:
        return 0, 0
    old_coins = int(old_lifetime // AMOUNT_PER_COIN)
    new_coins = int(new_lifetime // AMOUNT_PER_COIN)
    new_coins_earned = new_coins - old_coins
    if new_coins_earned <= 0:
        return 0, 0
    wallet_amount = new_coins_earned * COIN_VALUE
    return new_coins_earned, wallet_amount


def add_wallet_transaction(user, amount, description, reference_id=None, trans_type='bonus'):
    """افزایش موجودی کیف پول کاربر"""
    if amount <= 0:
        return None
    wallet, created = Wallet.objects.get_or_create(user=user)
    if trans_type == 'bonus':
        wallet.balance += amount
    elif trans_type == 'payment':
        wallet.balance -= amount
    elif trans_type == 'refund':
        wallet.balance += amount
    wallet.save()
    return WalletTransaction.objects.create(
        wallet=wallet,
        amount=amount,
        transaction_type=trans_type,
        status='completed',
        reference_id=reference_id,
        description=description
    )


def update_user_tier(loyalty):
    """بروزرسانی سطح کاربر بر اساس خرید"""
    lifetime = loyalty.lifetime_purchase
    if lifetime >= 950000000:
        new_tier = 'private'
    elif lifetime >= 500000000:
        new_tier = 'elite'
    elif lifetime >= 250000000:
        new_tier = 'premium'
    else:
        new_tier = 'select'
    old_tier = loyalty.current_tier
    if old_tier != new_tier:
        loyalty.current_tier = new_tier
        loyalty.save(update_fields=['current_tier'])
        try:
            from apps.order.models import OrderStatusHistory
            last_order = Order.objects.filter(user=loyalty.user, status='paid').order_by('-created_at').first()
            if last_order:
                OrderStatusHistory.objects.create(
                    order=last_order,
                    status=last_order.status,
                    note=f"🎖️ تبریک! سطح عضویت شما از {old_tier} به {new_tier} ارتقا یافت"
                )
        except:
            pass
    return loyalty.current_tier


def get_tier_b2b_coins(tier):
    """سکه‌های B2B برای هر سطح"""
    b2b_coins = {
        'premium': 4,
        'elite': 10,
        'private': 20,
        'select': 0,
    }
    return b2b_coins.get(tier, 0)


def deduct_product_stock(order):
    """کسر موجودی محصولات"""
    for item in order.items.all():
        if item.product:
            product = item.product
            quantity = int(item.quantity)
            if product.stock >= quantity:
                product.stock -= quantity
                product.save(update_fields=['stock'])


def deduct_wallet_after_confirmation(order):
    """کسر مبلغ استفاده شده از کیف پول بعد از تایید سفارش"""
    if not order.user:
        return False
    if order.used_from_wallet <= 0:
        return True
    already_deducted = OrderStatusHistory.objects.filter(
        order=order,
        note__icontains='از کیف پول کسر شد'
    ).exists()
    if already_deducted:
        return True
    wallet, _ = Wallet.objects.get_or_create(user=order.user)
    if wallet.balance >= order.used_from_wallet:
        wallet.balance -= order.used_from_wallet
        wallet.save()
        WalletTransaction.objects.create(
            wallet=wallet,
            amount=order.used_from_wallet,
            transaction_type='payment',
            status='completed',
            reference_id=order.order_number,
            description=f"پرداخت سفارش #{order.order_number} از کیف پول"
        )
        OrderStatusHistory.objects.create(
            order=order,
            status=order.status,
            note=f"💰 مبلغ {order.used_from_wallet:,.0f} تومان از کیف پول کسر شد"
        )
        return True
    return False


def assign_coins_and_wallet_bonus(order, paid_amount=None):
    """
    تخصیص سکه و شارژ کیف پول بر اساس مبلغ واقعی پرداختی

    Args:
        order: سفارش
        paid_amount: مبلغ واقعی پرداختی (اختیاری)
    """
    if not order.user:
        return None, None

    # محاسبه مبلغ واقعی پرداختی
    if paid_amount is None:
        # مبلغ کل سفارش - تخفیف‌ها + هزینه ارسال - استفاده از کیف پول
        paid_amount = order.subtotal - order.discount_amount - order.coupon_discount + order.shipping_cost - order.used_from_wallet

    # اگر مبلغ پرداختی صفر یا منفی بود، سکه تعلق نمی‌گیرد
    if paid_amount <= 0:
        return 0, 0

    # دریافت یا ایجاد لایفتایم کاربر
    loyalty, created = CustomerLoyalty.objects.get_or_create(user=order.user)
    old_lifetime = loyalty.lifetime_purchase
    old_tier = loyalty.current_tier

    # اضافه کردن مبلغ واقعی پرداختی به لایفتایم
    new_lifetime = old_lifetime + paid_amount
    loyalty.lifetime_purchase = new_lifetime
    loyalty.save(update_fields=['lifetime_purchase'])

    # بروزرسانی سطح کاربر
    new_tier = update_user_tier(loyalty)

    # محاسبه سکه‌های جدید بر اساس افزایش لایفتایم
    new_coins, wallet_amount = calculate_new_coins_and_wallet_amount(old_lifetime, new_lifetime)

    # محاسبه سکه‌های B2B بر اساس تغییر سطح
    old_b2b_coins = get_tier_b2b_coins(old_tier)
    new_b2b_coins = get_tier_b2b_coins(new_tier)
    b2b_coins_earned = new_b2b_coins - old_b2b_coins

    # جمع کل سکه‌های جدید
    total_new_coins = new_coins + b2b_coins_earned

    # اگر سکه جدیدی وجود نداشت، برمی‌گردیم
    if total_new_coins == 0:
        return 0, 0

    # اضافه کردن سکه‌ها به لایفتایم
    loyalty.total_coins += total_new_coins
    loyalty.save(update_fields=['total_coins'])

    # ثبت تراکنش سکه برای سکه‌های معمولی
    if new_coins > 0:
        LoyaltyTransaction.objects.create(
            loyalty=loyalty,
            points=new_coins,
            transaction_type='earn',
            order_id=order.order_number,
            description=f"کسب {new_coins} سکه از مجموع خرید {new_lifetime:,.0f} تومانی"
        )

    # ثبت تراکنش سکه برای سکه‌های B2B
    if b2b_coins_earned > 0:
        LoyaltyTransaction.objects.create(
            loyalty=loyalty,
            points=b2b_coins_earned,
            transaction_type='earn',
            order_id=order.order_number,
            description=f"کسب {b2b_coins_earned} سکه B2B بابت ارتقا سطح به {new_tier}"
        )

    # شارژ کیف پول به ازای سکه‌های معمولی (نه B2B)
    if wallet_amount > 0:
        add_wallet_transaction(
            user=order.user,
            amount=wallet_amount,
            description=f"شارژ کیف پول بابت {new_coins} سکه جدید",
            reference_id=order.order_number,
            trans_type='bonus'
        )

    # ذخیره سکه‌های کسب شده در سفارش
    order.earned_points = total_new_coins
    order.save(update_fields=['earned_points'])

    # ثبت ارتقا سطح در تاریخچه
    if old_tier != new_tier:
        OrderStatusHistory.objects.create(
            order=order,
            status=order.status,
            note=f"🎖️ سطح عضویت شما از {old_tier} به {new_tier} ارتقا یافت"
        )

    return total_new_coins, wallet_amount


def finalize_order_payment(order):
    """نهایی‌سازی کامل پرداخت سفارش"""
    if order.status == 'paid':
        return True

    # محاسبه مبلغ واقعی پرداختی
    paid_amount = order.subtotal - order.discount_amount - order.coupon_discount + order.shipping_cost - order.used_from_wallet

    # کسر مبلغ کیف پول
    deduct_wallet_after_confirmation(order)

    # ایجاد یا بروزرسانی پرداخت
    payment, _ = Peyment.objects.get_or_create(
        order=order,
        customer=order.user,
        defaults={
            'amount': int(order.total),
            'description': f"پرداخت سفارش {order.order_number}",
            'isFinaly': True,
            'statusCode': 200,
            'refId': f"ORDER-{order.order_number}",
            'payment_method': PaymentMethod.CARD_TO_CARD.value if order.has_uploaded_receipt else PaymentMethod.ONLINE.value,
            'createAt': timezone.now(),
        }
    )

    # بروزرسانی وضعیت سفارش
    order.status = 'paid'
    order.paid_at = timezone.now()
    order.save(update_fields=['status', 'paid_at'])

    # ثبت تاریخچه
    OrderStatusHistory.objects.create(
        order=order,
        status='paid',
        note=f"✅ پرداخت سفارش نهایی شد - مبلغ: {order.total:,.0f} تومان"
    )

    # کسر موجودی محصولات
    deduct_product_stock(order)

    # تخصیص سکه و شارژ کیف پول (با مبلغ واقعی پرداختی)
    assign_coins_and_wallet_bonus(order, paid_amount)

    return True


# ==================== سیگنال‌ها ====================

@receiver(pre_save, sender=Order)
def store_old_status(sender, instance, **kwargs):
    """ذخیره وضعیت قبلی سفارش برای استفاده در سیگنال بعدی"""
    if instance.pk:
        try:
            old_order = Order.objects.get(pk=instance.pk)
            instance._old_status = old_order.status
        except Order.DoesNotExist:
            instance._old_status = None
    else:
        instance._old_status = None


@receiver(post_save, sender=CheckPayment)
def check_payment_verified_signal(sender, instance, created, **kwargs):
    """وقتی چک تایید شد، سفارش رو نهایی کن"""
    if created:
        return
    if instance.status != CheckPaymentStatus.VERIFIED.value:
        return
    if not instance.order:
        return

    order = instance.order
    if order.status == 'paid':
        return

    finalize_order_payment(order)

    instance.is_finalized = True
    instance.finalized_at = timezone.now()
    instance.save(update_fields=['is_finalized', 'finalized_at'])

    OrderStatusHistory.objects.create(
        order=order,
        status='paid',
        note=f"📝 چک {instance.tracking_number} تأیید شد"
    )


@receiver(post_save, sender=Order)
def receipt_verified_signal(sender, instance, created, **kwargs):
    """وقتی رسید تایید شد، اگر چکی نباشه سفارش رو نهایی کن"""
    if created:
        return
    if not instance.receipt_verified:
        return
    if instance.status == 'paid':
        return

    # آیا چک تایید نشده وجود دارد؟
    pending_checks = CheckPayment.objects.filter(
        order=instance,
        status=CheckPaymentStatus.PENDING.value
    ).exists()

    if pending_checks:
        return

    finalize_order_payment(instance)


@receiver(post_save, sender=Peyment)
def online_payment_signal(sender, instance, created, **kwargs):
    """وقتی پرداخت آنلاین موفق شد، اگر چکی نباشه سفارش رو نهایی کن"""
    if not instance.isFinaly:
        return
    if instance.payment_method == PaymentMethod.CARD_TO_CARD.value:
        return

    order = instance.order
    if not order:
        return
    if order.status == 'paid':
        return

    # آیا چک تایید نشده وجود دارد؟
    pending_checks = CheckPayment.objects.filter(
        order=order,
        status=CheckPaymentStatus.PENDING.value
    ).exists()

    if pending_checks:
        return

    finalize_order_payment(order)


@receiver(post_save, sender=OrderItem)
def update_order_totals(sender, instance, created, **kwargs):
    """بروزرسانی مبالغ سفارش بعد از تغییر آیتم‌ها"""
    order = instance.order
    items = order.items.all()
    if items.exists():
        subtotal = sum(item.unit_price_before_discount * item.quantity for item in items)
        discount_amount = sum(
            (item.unit_price_before_discount - item.unit_price) * item.quantity
            for item in items
        )
        order.subtotal = subtotal
        order.discount_amount = discount_amount
        order.total = order.subtotal - order.discount_amount - order.coupon_discount + order.shipping_cost - order.used_from_wallet
        if order.total < 0:
            order.total = 0
        order.save(update_fields=['subtotal', 'discount_amount', 'total'])


@receiver(pre_save, sender=Order)
def calculate_total_with_wallet(sender, instance, **kwargs):
    """محاسبه مبلغ نهایی با در نظر گرفتن استفاده از کیف پول"""
    if instance.pk:
        try:
            old = Order.objects.get(pk=instance.pk)
            if old.used_from_wallet != instance.used_from_wallet:
                instance.total = instance.subtotal - instance.discount_amount - instance.coupon_discount + instance.shipping_cost - instance.used_from_wallet
                if instance.total < 0:
                    instance.total = 0
        except Order.DoesNotExist:
            pass
    else:
        instance.total = instance.subtotal - instance.discount_amount - instance.coupon_discount + instance.shipping_cost - instance.used_from_wallet
        if instance.total < 0:
            instance.total = 0


@receiver(post_save, sender=Order)
def order_status_notification(sender, instance, created, **kwargs):
    """ایجاد نوتیفیکیشن برای تغییر وضعیت سفارش"""
    if created:
        return
    if not instance.user:
        return
    old_status = getattr(instance, '_old_status', None)
    if old_status is None or old_status == instance.status or instance.status == 'pending':
        return

    status_fa = {
        'pending': 'در انتظار پرداخت',
        'paid': 'پرداخت شده',
        'processing': 'در حال پردازش',
        'packaging': 'در حال بسته‌بندی',
        'shipped': 'ارسال شده',
        'delivered': 'تحویل شده',
        'cancelled': 'لغو شده',
    }

    from apps.Notification.models import OrderStatusNotification

    OrderStatusNotification.objects.create(
        order=instance,
        user=instance.user,
        old_status=old_status,
        new_status=instance.status,
        message=f"سفارش #{instance.order_number}\nوضعیت: {status_fa.get(instance.status, instance.status)}",
        status_changed_at=timezone.now(),
        is_sent=False
    )