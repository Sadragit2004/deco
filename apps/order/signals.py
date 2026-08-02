from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from django.utils import timezone
from decimal import Decimal
import logging

from apps.order.models import Order, CustomerLoyalty, LoyaltyTransaction, OrderStatusHistory
from apps.order.models import OrderItem
from apps.peyment.models import Peyment, PaymentMethod
from apps.product.models import Product
from apps.user.models.profile import Wallet, WalletTransaction
from apps.check.models import CheckPayment, CheckPaymentStatus
import utils

logger = logging.getLogger(__name__)

# ==================== تنظیمات ثابت ====================

AMOUNT_PER_COIN = Decimal('50000000')  # هر ۵۰ میلیون تومان = ۱ سکه
COIN_VALUE = Decimal('500000')  # ارزش هر سکه = ۵۰۰ هزار تومان

# ==================== توابع کمکی ====================

def calculate_tier_by_lifetime(lifetime):
    """محاسبه سطح کاربر بر اساس مبلغ خرید مادام‌العمر"""
    if lifetime >= 950000000:
        return 'private'
    elif lifetime >= 500000000:
        return 'elite'
    elif lifetime >= 250000000:
        return 'premium'
    else:
        return 'select'


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
    else:
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
    """
    if not order.user:
        return None, None

    if paid_amount is None:
        paid_amount = order.total
        if paid_amount <= 0:
            paid_amount = order.subtotal - order.discount_amount - order.coupon_discount + order.shipping_cost - order.used_from_wallet
        if paid_amount < 0:
            paid_amount = 0

    if paid_amount <= 0:
        return 0, 0

    loyalty, created = CustomerLoyalty.objects.get_or_create(user=order.user)
    old_lifetime = loyalty.lifetime_purchase
    old_tier = loyalty.current_tier

    new_lifetime = old_lifetime + paid_amount
    loyalty.lifetime_purchase = new_lifetime
    loyalty.save(update_fields=['lifetime_purchase'])

    new_tier = calculate_tier_by_lifetime(new_lifetime)

    if old_tier != new_tier:
        loyalty.current_tier = new_tier
        loyalty.save(update_fields=['current_tier'])

        OrderStatusHistory.objects.create(
            order=order,
            status=order.status,
            note=f"🎖️ تبریک! سطح عضویت شما از {old_tier} به {new_tier} ارتقا یافت"
        )

    new_coins, wallet_amount = calculate_new_coins_and_wallet_amount(old_lifetime, new_lifetime)

    old_b2b_coins = get_tier_b2b_coins(old_tier)
    new_b2b_coins = get_tier_b2b_coins(new_tier)
    b2b_coins_earned = new_b2b_coins - old_b2b_coins

    total_new_coins = new_coins + b2b_coins_earned

    if total_new_coins == 0:
        return 0, 0

    loyalty.total_coins += total_new_coins
    loyalty.save(update_fields=['total_coins'])

    if new_coins > 0:
        LoyaltyTransaction.objects.create(
            loyalty=loyalty,
            points=new_coins,
            transaction_type='earn',
            order_id=order.order_number,
            description=f"کسب {new_coins} سکه از مجموع خرید {new_lifetime:,.0f} تومانی"
        )

    if b2b_coins_earned > 0:
        LoyaltyTransaction.objects.create(
            loyalty=loyalty,
            points=b2b_coins_earned,
            transaction_type='earn',
            order_id=order.order_number,
            description=f"کسب {b2b_coins_earned} سکه B2B بابت ارتقا سطح به {new_tier}"
        )

    if wallet_amount > 0:
        add_wallet_transaction(
            user=order.user,
            amount=wallet_amount,
            description=f"شارژ کیف پول بابت {new_coins} سکه جدید",
            reference_id=order.order_number,
            trans_type='bonus'
        )

    order.earned_points = total_new_coins
    order.save(update_fields=['earned_points'])

    return total_new_coins, wallet_amount


def finalize_order_payment(order):
    """نهایی‌سازی کامل پرداخت سفارش"""
    if order.status == 'paid':
        return True

    paid_amount = order.total
    if paid_amount <= 0:
        paid_amount = order.subtotal - order.discount_amount - order.coupon_discount + order.shipping_cost - order.used_from_wallet
    if paid_amount < 0:
        paid_amount = 0

    if order.used_from_wallet > 0:
        deduct_wallet_after_confirmation(order)

    payment, created = Peyment.objects.get_or_create(
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

    order.status = 'paid'
    order.paid_at = timezone.now()
    order.save(update_fields=['status', 'paid_at'])

    OrderStatusHistory.objects.create(
        order=order,
        status='paid',
        note=f"✅ پرداخت سفارش نهایی شد - مبلغ: {order.total:,.0f} تومان"
    )

    deduct_product_stock(order)

    if paid_amount > 0:
        assign_coins_and_wallet_bonus(order, paid_amount)

    return True


# ==================== سیگنال‌ها ====================

@receiver(pre_save, sender=Order)
def store_old_status(sender, instance, **kwargs):
    """ذخیره وضعیت قبلی سفارش"""
    if instance.pk:
        try:
            old_order = Order.objects.get(pk=instance.pk)
            instance._old_status = old_order.status
            instance._old_receipt_verified = old_order.receipt_verified
            instance._old_paid_at = old_order.paid_at
            instance._old_total = old_order.total
            instance._old_earned_points = old_order.earned_points
        except Order.DoesNotExist:
            instance._old_status = None
            instance._old_receipt_verified = False
            instance._old_paid_at = None
            instance._old_total = 0
            instance._old_earned_points = 0
    else:
        instance._old_status = None
        instance._old_receipt_verified = False
        instance._old_paid_at = None
        instance._old_total = 0
        instance._old_earned_points = 0


@receiver(post_save, sender=CheckPayment)
def check_payment_verified_signal(sender, instance, created, **kwargs):
    """وقتی چک تایید شد، سفارش رو نهایی کن و پیامک بفرست"""
    if created:
        return

    if instance.status != CheckPaymentStatus.VERIFIED.value:
        return

    if not instance.order:
        return

    order = instance.order

    if order.status == 'paid':
        return

    if instance.is_finalized:
        return

    try:
        finalize_order_payment(order)

        instance.is_finalized = True
        instance.finalized_at = timezone.now()
        instance.save(update_fields=['is_finalized', 'finalized_at'])

        OrderStatusHistory.objects.create(
            order=order,
            status='paid',
            note=f"📝 چک {instance.tracking_number} تأیید شد"
        )

        # ارسال پیامک
        if order.user and order.user.mobileNumber:
            # پیامک تایید چک
            utils.send_receipt_check_status_sms(
                number=order.user.mobileNumber,
                order_number=order.order_number,
                title="چک",
                status="تایید"
            )
            # پیامک تایید سفارش
            utils.send_order_confirmation_sms(
                number=order.user.mobileNumber,
                order_number=order.order_number,
                name=order.user.name or order.user.mobileNumber
            )

    except Exception as e:
        logger.error(f"Error in check_payment_verified_signal: {str(e)}")
        raise


@receiver(post_save, sender=Order)
def receipt_verified_signal(sender, instance, created, **kwargs):
    """
    وقتی رسید تایید شد، سفارش رو نهایی کن و پیامک بفرست
    """
    if created:
        return

    if instance.status == 'paid':
        return

    if not instance.receipt_verified:
        return

    old_receipt_verified = getattr(instance, '_old_receipt_verified', False)
    if old_receipt_verified == instance.receipt_verified:
        return

    old_paid_at = getattr(instance, '_old_paid_at', None)
    if old_paid_at is not None:
        return

    pending_checks = CheckPayment.objects.filter(
        order=instance,
        status=CheckPaymentStatus.PENDING.value
    ).exists()

    if pending_checks:
        return

    try:
        finalize_order_payment(instance)

        # ارسال پیامک
        if instance.user and instance.user.mobileNumber:
            # پیامک تایید رسید
            utils.send_receipt_check_status_sms(
                number=instance.user.mobileNumber,
                order_number=instance.order_number,
                title="رسید پرداخت",
                status="تایید"
            )
            # پیامک تایید سفارش
            utils.send_order_confirmation_sms(
                number=instance.user.mobileNumber,
                order_number=instance.order_number,
                name=instance.user.name or instance.user.mobileNumber
            )

    except Exception as e:
        logger.error(f"Error in receipt_verified_signal: {str(e)}")
        raise


@receiver(post_save, sender=Peyment)
def online_payment_signal(sender, instance, created, **kwargs):
    """وقتی پرداخت آنلاین موفق شد، سفارش رو نهایی کن و پیامک بفرست"""
    if not instance.isFinaly:
        return

    if instance.payment_method == PaymentMethod.CARD_TO_CARD.value:
        return

    order = instance.order
    if not order:
        return

    if order.status == 'paid':
        return

    if order.paid_at is not None:
        return

    pending_checks = CheckPayment.objects.filter(
        order=order,
        status=CheckPaymentStatus.PENDING.value
    ).exists()

    if pending_checks:
        return

    try:
        finalize_order_payment(order)

        # ارسال پیامک تایید سفارش
        if order.user and order.user.mobileNumber:
            utils.send_order_confirmation_sms(
                number=order.user.mobileNumber,
                order_number=order.order_number,
                name=order.user.name or order.user.mobileNumber
            )

    except Exception as e:
        logger.error(f"Error in online_payment_signal: {str(e)}")
        raise


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

    try:
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
    except Exception as e:
        logger.error(f"Error in order_status_notification: {str(e)}")


@receiver(post_save, sender=Order)
def restore_stock_on_cancel(sender, instance, created, **kwargs):
    """برگرداندن موجودی محصولات در صورت لغو سفارش"""
    if created:
        return

    old_status = getattr(instance, '_old_status', None)
    if old_status != instance.status and instance.status == 'cancelled':
        for item in instance.items.all():
            if item.product:
                product = item.product
                quantity = int(item.quantity)
                product.stock += quantity
                product.save(update_fields=['stock'])

        OrderStatusHistory.objects.create(
            order=instance,
            status='cancelled',
            note="📦 موجودی محصولات به انبار برگردانده شد"
        )


@receiver(post_save, sender=Order)
def update_user_stats(sender, instance, created, **kwargs):
    """بروزرسانی آمار کاربر بعد از پرداخت سفارش"""
    if created:
        return

    if instance.status != 'paid':
        return

    if not instance.user:
        return

    if instance.earned_points <= 0:
        return

    try:
        from apps.user.models.user import CustomUser
        user = instance.user
        logger.info(f"User {user.mobileNumber} stats updated for order {instance.order_number}")
    except Exception as e:
        logger.error(f"Error in update_user_stats: {str(e)}")