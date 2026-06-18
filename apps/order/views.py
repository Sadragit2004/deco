# order/views.py - نسخه نهایی کامل

import base64
import logging
from decimal import Decimal
from django.core.files.base import ContentFile
from django.shortcuts import render, redirect, get_object_or_404
from django.views import View
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.urls import reverse
from django.http import JsonResponse
from django.utils import timezone
from django.core.paginator import Paginator
from django.db.models import Q, Sum
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

from .models import Order, OrderStatus, OrderItem, OrderStatusHistory, ShippingMethod, PaymentReceipt
from apps.product.models import Product
from apps.user.models.profile import UserAddress, Wallet, WalletTransaction, CustomerLoyalty
from .signals import assign_coins_and_wallet_bonus
from apps.check.models import CheckPayment,CheckPaymentStatus

logger = logging.getLogger(__name__)


# ==================== کلاس ایجاد سفارش ====================

class CreateOrderView(LoginRequiredMixin, View):
    def get(self, request, *args, **kwargs):
        logger.error("===== CreateOrderView CALLED =====")

        try:
            is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'
            cart = request.session.get('cart', {})

            if not cart or len(cart) == 0:
                logger.error("Cart is empty!")
                if is_ajax:
                    return JsonResponse({
                        'success': False,
                        'message': 'سبد خرید شما خالی است.'
                    })
                messages.error(request, "سبد خرید شما خالی است.")
                return redirect("main:index")

            order = Order.objects.create(
                user=request.user,
                status='pending',
                subtotal=0,
                discount_amount=0,
                coupon_discount=0,
                shipping_cost=0,
                total=0
            )

            logger.error(f"Order created with ID: {order.id}")

            total_subtotal = Decimal('0')
            total_discount_amount = Decimal('0')
            items_created = 0

            for product_id, item_data in cart.items():
                try:
                    product = Product.objects.get(id=int(product_id))
                    quantity = Decimal(str(item_data.get('quantity', 1)))

                    original_price = Decimal(str(product.price)) if product.price else Decimal('0')
                    discount_info = product.get_final_price_info(float(quantity), 0)
                    final_unit_price = Decimal(str(discount_info['final_price'] / float(quantity))) if quantity > 0 else original_price
                    discount_amount_item = Decimal(str(discount_info['discount_amount']))
                    unit_price_before_discount = original_price
                    total_before_discount = original_price * quantity
                    total_item = final_unit_price * quantity
                    discount_percent = discount_info.get('discount_percent', 0)
                    applied_discount_title = discount_info.get('discount_title', '')

                    OrderItem.objects.create(
                        order=order,
                        product=product,
                        product_title=product.title,
                        product_code=getattr(product, 'code', ''),
                        product_image=product.main_image.url if hasattr(product, 'main_image') and product.main_image else '',
                        brand_name=product.brand.title if hasattr(product, 'brand') and product.brand else '',
                        quantity=quantity,
                        unit_price=final_unit_price,
                        unit_price_before_discount=original_price,
                        discount_percent=discount_percent,
                        discount_amount=discount_amount_item,
                        total=total_item,
                        applied_discount_title=applied_discount_title,
                        sales_unit_name=product.get_sales_unit_name(),
                        sales_unit_symbol=product.get_sales_unit_symbol(),
                        use_packaging=product.use_packaging,
                        package_unit_name=product.get_package_unit_name() if product.use_packaging else '',
                        package_size=float(product.package_size) if product.use_packaging and product.package_size else 1,
                        packages_count=product.calculate_packages(float(quantity)) if product.use_packaging else 0
                    )

                    total_subtotal += total_before_discount
                    total_discount_amount += discount_amount_item
                    items_created += 1

                except Product.DoesNotExist:
                    logger.error(f"Product {product_id} not found!")
                    continue

            if items_created == 0:
                order.delete()
                if is_ajax:
                    return JsonResponse({
                        'success': False,
                        'message': 'هیچ محصول معتبری در سبد خرید وجود ندارد.'
                    })
                messages.error(request, "هیچ محصول معتبری در سبد خرید وجود ندارد.")
                return redirect("main:index")

            order.subtotal = total_subtotal
            order.discount_amount = total_discount_amount
            order.shipping_cost = 0
            order.used_from_wallet = 0
            order.total = total_subtotal - total_discount_amount
            order.save()

            OrderStatusHistory.objects.create(
                order=order,
                status='pending',
                note=f"سفارش ایجاد شد - تخفیف کل: {total_discount_amount:,.0f} تومان"
            )

            request.session['cart'] = {}
            logger.error(f"Cart cleared. Order {order.id} created successfully.")

            if is_ajax:
                return JsonResponse({
                    'success': True,
                    'order_id': str(order.id),
                    'order_number': order.order_number,
                    'redirect_url': f'/order/checkout/{str(order.id)}/'
                })
            else:
                return redirect('order:checkout', order_id=order.id)

        except Exception as e:
            logger.error(f"Exception in CreateOrderView: {str(e)}", exc_info=True)
            is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'
            if is_ajax:
                return JsonResponse({
                    'success': False,
                    'message': f'خطا در ایجاد سفارش: {str(e)}'
                })
            messages.error(request, f"خطا در ایجاد سفارش: {str(e)}")
            return redirect("main:index")


# ==================== توابع کمکی ====================

def get_tier_check_percent(user_tier):
    """درصد چک بر اساس سطح کاربر"""
    check_percent_map = {
        'premium': 15,
        'elite': 25,
        'private': 50,
        'select': 0
    }
    return check_percent_map.get(user_tier, 0)


def save_order_info(request, order, post_data):
    """تابع کمکی برای ذخیره اطلاعات سفارش"""
    try:
        name = post_data.get('name', '').strip()
        family = post_data.get('family', '').strip()
        phone = post_data.get('phone', '').strip()
        description = post_data.get('description', '').strip()
        selected_address_id = post_data.get('selected_address')
        shipping_method_id = post_data.get('shipping_method')

        if not all([name, family, phone, selected_address_id, shipping_method_id]):
            return False, "لطفاً تمام موارد ضروری را کامل کنید."

        try:
            address = UserAddress.objects.get(id=selected_address_id, user=request.user)
            order.address = address
        except UserAddress.DoesNotExist:
            return False, "آدرس انتخاب شده معتبر نیست."

        try:
            shipping_method = ShippingMethod.objects.get(id=shipping_method_id, is_active=True)
            order.shipping_method = shipping_method
            total_before_shipping = order.subtotal - order.discount_amount - order.coupon_discount
            order.shipping_cost = shipping_method.calculate_cost(total_before_shipping)
        except ShippingMethod.DoesNotExist:
            return False, "روش ارسال انتخاب شده معتبر نیست."

        if name:
            request.user.name = name
        if family:
            request.user.family = family
        if phone:
            request.user.mobileNumber = phone
        request.user.save()

        order.description = description
        order.total = order.subtotal - order.discount_amount - order.coupon_discount + order.shipping_cost - order.used_from_wallet
        if order.total < 0:
            order.total = 0
        order.save()

        request.session['checkout_data'] = {
            'name': name,
            'family': family,
            'phone': phone,
            'description': description,
            'selected_address_id': selected_address_id,
            'shipping_method_id': shipping_method_id,
        }

        return True, "اطلاعات با موفقیت ذخیره شد."

    except Exception as e:
        logger.error(f"Error in save_order_info: {str(e)}", exc_info=True)
        return False, str(e)


# ==================== کلاس ایجاد سفارش ====================

class CreateOrderView(LoginRequiredMixin, View):
    def get(self, request, *args, **kwargs):
        logger.error("===== CreateOrderView CALLED =====")

        try:
            is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'
            cart = request.session.get('cart', {})

            if not cart or len(cart) == 0:
                logger.error("Cart is empty!")
                if is_ajax:
                    return JsonResponse({
                        'success': False,
                        'message': 'سبد خرید شما خالی است.'
                    })
                messages.error(request, "سبد خرید شما خالی است.")
                return redirect("main:index")

            order = Order.objects.create(
                user=request.user,
                status='pending',
                subtotal=0,
                discount_amount=0,
                coupon_discount=0,
                shipping_cost=0,
                total=0
            )

            logger.error(f"Order created with ID: {order.id}")

            total_subtotal = Decimal('0')
            total_discount_amount = Decimal('0')
            items_created = 0

            for product_id, item_data in cart.items():
                try:
                    product = Product.objects.get(id=int(product_id))
                    quantity = Decimal(str(item_data.get('quantity', 1)))

                    original_price = Decimal(str(product.price)) if product.price else Decimal('0')
                    discount_info = product.get_final_price_info(float(quantity), 0)
                    final_unit_price = Decimal(str(discount_info['final_price'] / float(quantity))) if quantity > 0 else original_price
                    discount_amount_item = Decimal(str(discount_info['discount_amount']))
                    unit_price_before_discount = original_price
                    total_before_discount = original_price * quantity
                    total_item = final_unit_price * quantity
                    discount_percent = discount_info.get('discount_percent', 0)
                    applied_discount_title = discount_info.get('discount_title', '')

                    OrderItem.objects.create(
                        order=order,
                        product=product,
                        product_title=product.title,
                        product_code=getattr(product, 'code', ''),
                        product_image=product.main_image.url if hasattr(product, 'main_image') and product.main_image else '',
                        brand_name=product.brand.title if hasattr(product, 'brand') and product.brand else '',
                        quantity=quantity,
                        unit_price=final_unit_price,
                        unit_price_before_discount=original_price,
                        discount_percent=discount_percent,
                        discount_amount=discount_amount_item,
                        total=total_item,
                        applied_discount_title=applied_discount_title,
                        sales_unit_name=product.get_sales_unit_name(),
                        sales_unit_symbol=product.get_sales_unit_symbol(),
                        use_packaging=product.use_packaging,
                        package_unit_name=product.get_package_unit_name() if product.use_packaging else '',
                        package_size=float(product.package_size) if product.use_packaging and product.package_size else 1,
                        packages_count=product.calculate_packages(float(quantity)) if product.use_packaging else 0
                    )

                    total_subtotal += total_before_discount
                    total_discount_amount += discount_amount_item
                    items_created += 1

                except Product.DoesNotExist:
                    logger.error(f"Product {product_id} not found!")
                    continue

            if items_created == 0:
                order.delete()
                if is_ajax:
                    return JsonResponse({
                        'success': False,
                        'message': 'هیچ محصول معتبری در سبد خرید وجود ندارد.'
                    })
                messages.error(request, "هیچ محصول معتبری در سبد خرید وجود ندارد.")
                return redirect("main:index")

            order.subtotal = total_subtotal
            order.discount_amount = total_discount_amount
            order.shipping_cost = 0
            order.used_from_wallet = 0
            order.total = total_subtotal - total_discount_amount
            order.save()

            OrderStatusHistory.objects.create(
                order=order,
                status='pending',
                note=f"سفارش ایجاد شد - تخفیف کل: {total_discount_amount:,.0f} تومان"
            )

            request.session['cart'] = {}

            if is_ajax:
                return JsonResponse({
                    'success': True,
                    'order_id': str(order.id),
                    'order_number': order.order_number,
                    'redirect_url': f'/order/checkout/{str(order.id)}/'
                })
            else:
                return redirect('order:checkout', order_id=order.id)

        except Exception as e:
            logger.error(f"Exception in CreateOrderView: {str(e)}", exc_info=True)
            is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'
            if is_ajax:
                return JsonResponse({
                    'success': False,
                    'message': f'خطا در ایجاد سفارش: {str(e)}'
                })
            messages.error(request, f"خطا در ایجاد سفارش: {str(e)}")
            return redirect("main:index")


# ==================== APIهای سیستم چک ====================

@login_required
def create_check_payment_api(request, order_id):
    """API برای ایجاد مدل چک هنگام تیک زدن کاربر"""
    try:
        order = get_object_or_404(Order, id=order_id, user=request.user)

        if order.status != 'pending':
            return JsonResponse({
                'success': False,
                'error': 'این سفارش قابل ویرایش نیست'
            }, status=400)

        user_tier = request.user.loyalty.current_tier if hasattr(request.user, 'loyalty') else 'select'
        check_percent = get_tier_check_percent(user_tier)

        if check_percent == 0:
            return JsonResponse({
                'success': False,
                'error': 'سطح کاربری شما امکان پرداخت با چک را ندارد'
            }, status=400)

        total_amount = order.subtotal - order.discount_amount - order.coupon_discount + order.shipping_cost
        amount_after_wallet = total_amount - order.used_from_wallet

        if amount_after_wallet <= 0:
            return JsonResponse({
                'success': False,
                'error': 'مبلغ سفارش پس از کسر کیف پول صفر است'
            }, status=400)

        check_amount = int(amount_after_wallet * check_percent / 100)
        final_payable = amount_after_wallet - check_amount

        # استفاده از .value برای Enum
        existing_check = CheckPayment.objects.filter(
            order=order,
            user=request.user,
            status=CheckPaymentStatus.PENDING.value
        ).first()

        if existing_check:
            existing_check.check_amount = check_amount
            existing_check.description = f'پرداخت با چک - سطح {user_tier} - {check_percent}% از مبلغ سفارش'
            existing_check.save()

            return JsonResponse({
                'success': True,
                'message': 'اطلاعات چک بروزرسانی شد',
                'data': {
                    'check_id': str(existing_check.id),
                    'check_percent': check_percent,
                    'check_amount': check_amount,
                    'check_amount_display': f'{check_amount:,}',
                    'final_payable': final_payable,
                    'final_payable_display': f'{final_payable:,}',
                    'status': existing_check.status
                }
            })

        check_payment = CheckPayment.objects.create(
            user=request.user,
            order=order,
            check_amount=check_amount,
            status=CheckPaymentStatus.PENDING.value,
            description=f'پرداخت با چک - سطح {user_tier} - {check_percent}% از مبلغ سفارش',
        )

        OrderStatusHistory.objects.create(
            order=order,
            status=order.status,
            note=f"📝 ثبت درخواست پرداخت با چک - {check_percent}% از مبلغ سفارش (مبلغ چک: {check_amount:,} تومان)"
        )

        return JsonResponse({
            'success': True,
            'message': 'اطلاعات چک با موفقیت ثبت شد',
            'data': {
                'check_id': str(check_payment.id),
                'check_percent': check_percent,
                'check_amount': check_amount,
                'check_amount_display': f'{check_amount:,}',
                'final_payable': final_payable,
                'final_payable_display': f'{final_payable:,}',
                'status': check_payment.status
            }
        })

    except Exception as e:
        logger.error(f"Error in create_check_payment_api: {str(e)}", exc_info=True)
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@login_required
def upload_check_image_api(request, order_id):
    """API برای آپلود عکس چک"""
    try:
        order = get_object_or_404(Order, id=order_id, user=request.user)

        # استفاده از .value برای Enum
        check_payment = CheckPayment.objects.filter(
            order=order,
            user=request.user,
            status=CheckPaymentStatus.PENDING.value
        ).first()

        if not check_payment:
            return JsonResponse({
                'success': False,
                'error': 'هیچ درخواست چک فعالی برای این سفارش یافت نشد. لطفاً ابتدا گزینه پرداخت با چک را فعال کنید.'
            }, status=400)

        check_image_base64 = request.POST.get('check_image_base64')

        if not check_image_base64:
            return JsonResponse({
                'success': False,
                'error': 'لطفاً عکس چک را آپلود کنید'
            }, status=400)

        if ';base64,' in check_image_base64:
            format, imgstr = check_image_base64.split(';base64,')
            ext = format.split('/')[-1]
        else:
            imgstr = check_image_base64
            ext = 'png'

        file_name = f"check_{order.order_number}_{int(timezone.now().timestamp())}.{ext}"

        check_payment.check_image.save(
            file_name,
            ContentFile(base64.b64decode(imgstr)),
            save=False
        )
        check_payment.save()

        total_amount = order.subtotal - order.discount_amount - order.coupon_discount + order.shipping_cost
        amount_after_wallet = total_amount - order.used_from_wallet
        final_payable = amount_after_wallet - check_payment.check_amount

        if final_payable < 0:
            final_payable = 0

        OrderStatusHistory.objects.create(
            order=order,
            status=order.status,
            note=f"📎 عکس چک آپلود شد - مبلغ چک: {check_payment.check_amount:,.0f} تومان"
        )

        return JsonResponse({
            'success': True,
            'message': 'عکس چک با موفقیت آپلود شد',
            'data': {
                'check_id': str(check_payment.id),
                'check_amount': int(check_payment.check_amount),
                'check_amount_display': f"{check_payment.check_amount:,.0f}",
                'final_payable': int(final_payable),
                'final_payable_display': f"{final_payable:,.0f}",
                'image_url': check_payment.check_image.url if check_payment.check_image else None
            }
        })

    except Exception as e:
        logger.error(f"Error in upload_check_image_api: {str(e)}", exc_info=True)
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@login_required
def cancel_check_payment_api(request, order_id):
    """API برای لغو پرداخت با چک"""
    try:
        order = get_object_or_404(Order, id=order_id, user=request.user)

        # استفاده از .value برای Enum
        check_payment = CheckPayment.objects.filter(
            order=order,
            user=request.user,
            status=CheckPaymentStatus.PENDING.value
        ).first()

        if check_payment:
            check_payment.status = CheckPaymentStatus.CANCELLED.value
            check_payment.save()

            OrderStatusHistory.objects.create(
                order=order,
                status=order.status,
                note="❌ لغو درخواست پرداخت با چک توسط کاربر"
            )

        return JsonResponse({
            'success': True,
            'message': 'پرداخت با چک لغو شد'
        })

    except Exception as e:
        logger.error(f"Error in cancel_check_payment_api: {str(e)}", exc_info=True)
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@login_required
def get_check_status_api(request, order_id):
    """API برای دریافت وضعیت چک سفارش"""
    try:
        order = get_object_or_404(Order, id=order_id, user=request.user)

        check_payment = CheckPayment.objects.filter(
            order=order,
            user=request.user
        ).exclude(status='cancelled').first()

        if not check_payment:
            return JsonResponse({
                'success': True,
                'has_check': False,
                'data': None
            })

        total_amount = order.subtotal - order.discount_amount - order.coupon_discount + order.shipping_cost
        amount_after_wallet = total_amount - order.used_from_wallet
        final_payable = amount_after_wallet - (check_payment.check_amount or 0)

        user_tier = request.user.loyalty.current_tier if hasattr(request.user, 'loyalty') else 'select'

        return JsonResponse({
            'success': True,
            'has_check': True,
            'data': {
                'check_id': str(check_payment.id),
                'check_percent': get_tier_check_percent(user_tier),
                'check_amount': int(check_payment.check_amount) if check_payment.check_amount else 0,
                'check_amount_display': f"{check_payment.check_amount:,.0f}" if check_payment.check_amount else '۰',
                'final_payable': int(final_payable),
                'final_payable_display': f"{final_payable:,.0f}",
                'has_image': bool(check_payment.check_image),
                'image_url': check_payment.check_image.url if check_payment.check_image else None,
                'status': check_payment.status,
                'created_at': check_payment.created_at.strftime('%Y/%m/%d %H:%M')
            }
        })

    except Exception as e:
        logger.error(f"Error in get_check_status_api: {str(e)}", exc_info=True)
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


# ==================== صفحه اصلی تسویه حساب (Checkout) ====================

@login_required
def checkout(request, order_id):
    try:
        order = get_object_or_404(Order, id=order_id, user=request.user)

        if order.status != 'pending':
            messages.error(request, "این سفارش قابل ویرایش نیست.")
            return redirect('main:index')

        wallet, _ = Wallet.objects.get_or_create(user=request.user)
        loyalty, _ = CustomerLoyalty.objects.get_or_create(user=request.user)

        if request.method == 'POST':
            is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'
            action = request.POST.get('action', 'save')

            if action == 'save':
                success, message = save_order_info(request, order, request.POST)
                if is_ajax:
                    return JsonResponse({'success': success, 'message': message})
                if success:
                    messages.success(request, message)
                else:
                    messages.error(request, message)
                return redirect('order:checkout', order_id=order.id)

            elif action == 'use_wallet':
                try:
                    use_amount = Decimal(request.POST.get('use_amount', '0'))

                    if use_amount <= 0:
                        return JsonResponse({'success': False, 'error': 'مبلغ باید بیشتر از صفر باشد'})

                    if use_amount > wallet.balance:
                        return JsonResponse({'success': False, 'error': f'موجودی کیف پول شما {wallet.balance:,.0f} تومان است'})

                    current_total = order.subtotal - order.discount_amount - order.coupon_discount + order.shipping_cost

                    if use_amount > current_total:
                        return JsonResponse({'success': False, 'error': 'مبلغ استفاده شده نمی‌تواند از مبلغ سفارش بیشتر باشد'})

                    order.used_from_wallet = use_amount
                    order.total = current_total - use_amount
                    if order.total < 0:
                        order.total = 0
                    order.save(update_fields=['used_from_wallet', 'total'])

                    OrderStatusHistory.objects.create(
                        order=order,
                        status=order.status,
                        note=f"💰 ثبت درخواست استفاده از مبلغ {use_amount:,.0f} تومان از کیف پول"
                    )

                    return JsonResponse({
                        'success': True,
                        'used_amount': int(use_amount),
                        'used_amount_display': f"{use_amount:,.0f}",
                        'new_total': int(order.total),
                        'new_total_display': f"{order.total:,.0f}",
                        'wallet_remaining': int(wallet.balance),
                        'wallet_remaining_display': f"{wallet.balance:,.0f}"
                    })

                except Exception as e:
                    return JsonResponse({'success': False, 'error': str(e)})

            elif action == 'cancel_wallet':
                try:
                    order.used_from_wallet = 0
                    current_total = order.subtotal - order.discount_amount - order.coupon_discount + order.shipping_cost
                    order.total = current_total
                    order.save(update_fields=['used_from_wallet', 'total'])

                    OrderStatusHistory.objects.create(
                        order=order,
                        status=order.status,
                        note=f"🔄 لغو استفاده از کیف پول"
                    )

                    return JsonResponse({
                        'success': True,
                        'new_total': int(order.total),
                        'new_total_display': f"{order.total:,.0f}",
                        'wallet_balance': int(wallet.balance),
                        'wallet_balance_display': f"{wallet.balance:,.0f}"
                    })

                except Exception as e:
                    return JsonResponse({'success': False, 'error': str(e)})

            elif action == 'pay':
                success, message = save_order_info(request, order, request.POST)

                if not success:
                    if is_ajax:
                        return JsonResponse({'success': False, 'error': message})
                    messages.error(request, message)
                    return redirect('order:checkout', order_id=order.id)

                total_amount = order.subtotal - order.discount_amount - order.coupon_discount + order.shipping_cost
                amount_after_wallet = total_amount - order.used_from_wallet

                # استفاده از .value برای Enum
                active_check = CheckPayment.objects.filter(
                    order=order,
                    user=request.user,
                    status=CheckPaymentStatus.PENDING.value
                ).first()

                if active_check and active_check.check_image:
                    final_total = amount_after_wallet - active_check.check_amount
                else:
                    final_total = amount_after_wallet

                if final_total < 0:
                    final_total = 0

                if final_total <= 0:
                    order.status = 'paid'
                    order.paid_at = timezone.now()
                    order.save(update_fields=['status', 'paid_at'])

                    if active_check and active_check.check_image:
                        active_check.status = CheckPaymentStatus.VERIFIED.value
                        active_check.save()

                    OrderStatusHistory.objects.create(
                        order=order,
                        status='paid',
                        note="پرداخت با استفاده از کیف پول و چک انجام شد (مبلغ سفارش صفر شد)"
                    )

                    for item in order.items.all():
                        if item.product:
                            product = item.product
                            quantity = int(item.quantity)
                            if product.stock >= quantity:
                                product.stock -= quantity
                                product.save(update_fields=['stock'])

                    assign_coins_and_wallet_bonus(order)

                    if is_ajax:
                        return JsonResponse({
                            'success': True,
                            'redirect_url': f'/order/order-detail/{str(order.id)}/'
                        })

                    messages.success(request, "سفارش شما با موفقیت ثبت شد")
                    return redirect('order:order_detail', order_id=order.id)

                payment_method_value = request.POST.get('payment_method_value', 'online')

                if payment_method_value == 'card_to_card':
                    receipt_file_base64 = request.POST.get('receipt_file_base64')

                    if not receipt_file_base64:
                        if is_ajax:
                            return JsonResponse({'success': False, 'error': 'لطفاً تصویر رسید را آپلود کنید'})
                        messages.error(request, 'لطفاً تصویر رسید را آپلود کنید')
                        return redirect('order:checkout', order_id=order.id)

                    try:
                        file_data = base64.b64decode(receipt_file_base64)
                        file_name = f"receipt_{order.order_number}_{timezone.now().timestamp()}.png"

                        receipt = PaymentReceipt.objects.create(
                            order=order,
                            receipt_file=ContentFile(file_data, name=file_name),
                            status=PaymentReceipt.ReceiptStatus.PENDING
                        )

                        order.has_uploaded_receipt = True
                        order.save(update_fields=['has_uploaded_receipt'])

                        OrderStatusHistory.objects.create(
                            order=order,
                            status=order.status,
                            note=f"رسید پرداخت کارت به کارت آپلود شد - مبلغ نهایی: {final_total:,} تومان"
                        )

                        if is_ajax:
                            return JsonResponse({
                                'success': True,
                                'redirect_url': f'/order/order-detail/{str(order.id)}/'
                            })

                        messages.success(request, "رسید شما با موفقیت ثبت شد و در انتظار تایید است")
                        return redirect('order:order_detail', order_id=order.id)

                    except Exception as e:
                        if is_ajax:
                            return JsonResponse({'success': False, 'error': f'خطا در ذخیره رسید: {str(e)}'})
                        messages.error(request, f'خطا در ذخیره رسید: {str(e)}')
                        return redirect('order:checkout', order_id=order.id)

                else:
                    if is_ajax:
                        return JsonResponse({
                            'success': True,
                            'redirect_url': f'/peyment/request/{str(order.id)}/?amount={int(final_total)}'
                        })

                    return redirect(f'/peyment/request/{str(order.id)}/?amount={int(final_total)}')

        checkout_data = request.session.get('checkout_data', {})

        total_amount = order.subtotal - order.discount_amount - order.coupon_discount + order.shipping_cost
        amount_after_wallet = total_amount - order.used_from_wallet

        active_check = CheckPayment.objects.filter(
            order=order,
            user=request.user,
            status=CheckPaymentStatus.PENDING.value
        ).first()

        if active_check and active_check.check_image:
            final_total = amount_after_wallet - active_check.check_amount
        else:
            final_total = amount_after_wallet

        if final_total < 0:
            final_total = 0

        user_tier = loyalty.current_tier
        check_percent = get_tier_check_percent(user_tier)

        tier_display_map = {
            'select': 'انتخاب شده',
            'premium': 'پریمیوم',
            'elite': 'الیت',
            'private': 'پرایویت',
        }

        context = {
            'order': order,
            'order_items': order.items.all(),
            'addresses': UserAddress.objects.filter(user=request.user, is_active=True),
            'shipping_methods': ShippingMethod.objects.filter(is_active=True),
            'checkout_data': checkout_data,
            'wallet_balance': wallet.balance,
            'wallet_balance_display': f"{wallet.balance:,.0f}",
            'used_from_wallet': order.used_from_wallet,
            'used_from_wallet_display': f"{order.used_from_wallet:,.0f}",
            'final_total': final_total,
            'final_total_display': f"{final_total:,.0f}",
            'user_tier': user_tier,
            'user_tier_display': tier_display_map.get(user_tier, user_tier),
            'user_total_points': loyalty.total_points,
            'user_total_coins': loyalty.total_coins,
            'check_percent': check_percent,
            'can_use_check': check_percent > 0,
            'has_active_check': active_check is not None,
            'check_image_uploaded': active_check and active_check.check_image,
            'check_amount': int(active_check.check_amount) if active_check and active_check.check_amount else 0,
        }

        return render(request, 'order_app/checkout.html', context)

    except Exception as e:
        logger.error(f"Error in checkout view: {str(e)}", exc_info=True)
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'success': False, 'error': str(e)})
        messages.error(request, f"خطا در صفحه تسویه حساب: {str(e)}")
        return redirect('main:index')


# ==================== سایر صفحات ====================

@login_required
def user_orders(request):
    """لیست سفارشات کاربر لاگین شده"""
    try:
        orders = Order.objects.filter(user=request.user).order_by('-created_at')

        total_orders = orders.count()
        total_spent = orders.filter(status='paid').aggregate(Sum('total'))['total__sum'] or 0
        total_discount = orders.aggregate(Sum('discount_amount'))['discount_amount__sum'] or 0

        status_filter = request.GET.get('status', 'all')
        if status_filter != 'all':
            orders = orders.filter(status=status_filter)

        paginator = Paginator(orders, 10)
        page_number = request.GET.get('page')
        page_obj = paginator.get_page(page_number)

        status_choices = [
            {'value': 'all', 'label': 'همه', 'count': orders.count()},
            {'value': 'pending', 'label': 'در انتظار پرداخت', 'count': orders.filter(status='pending').count()},
            {'value': 'paid', 'label': 'پرداخت شده', 'count': orders.filter(status='paid').count()},
            {'value': 'processing', 'label': 'در حال پردازش', 'count': orders.filter(status='processing').count()},
            {'value': 'packaging', 'label': 'در حال بسته‌بندی', 'count': orders.filter(status='packaging').count()},
            {'value': 'shipped', 'label': 'ارسال شده', 'count': orders.filter(status='shipped').count()},
            {'value': 'delivered', 'label': 'تحویل شده', 'count': orders.filter(status='delivered').count()},
            {'value': 'cancelled', 'label': 'لغو شده', 'count': orders.filter(status='cancelled').count()},
        ]

        context = {
            'orders': page_obj,
            'total_orders': total_orders,
            'total_spent': total_spent,
            'total_discount': total_discount,
            'status_choices': status_choices,
            'current_status': status_filter,
        }

        return render(request, 'order_app/user_orders.html', context)

    except Exception as e:
        logger.error(f"Error in user_orders: {str(e)}", exc_info=True)
        messages.error(request, "خطا در دریافت لیست سفارشات")
        return redirect('main:index')


@login_required
def order_detail(request, order_id):
    """نمایش جزییات کامل یک سفارش"""
    try:
        order = get_object_or_404(Order, id=order_id, user=request.user)

        order_items = order.items.all()
        status_history = order.status_history.all()
        total_items = order_items.count()
        total_quantity = order_items.aggregate(Sum('quantity'))['quantity__sum'] or 0
        address = order.address
        shipping_method = order.shipping_method
        applied_discounts = order.applied_discounts.all()

        try:
            payment_receipt = order.payment_receipt
        except:
            payment_receipt = None

        check_payment = CheckPayment.objects.filter(order=order, user=request.user).first()

        context = {
            'order': order,
            'order_items': order_items,
            'status_history': status_history,
            'address': address,
            'shipping_method': shipping_method,
            'applied_discounts': applied_discounts,
            'coupon': order.coupon,
            'total_items': total_items,
            'total_quantity': total_quantity,
            'subtotal': order.subtotal,
            'discount': order.discount_amount,
            'coupon_discount': order.coupon_discount,
            'shipping_cost': order.shipping_cost,
            'total': order.total,
            'payment_receipt': payment_receipt,
            'check_payment': check_payment,
        }

        return render(request, 'order_app/order_detail.html', context)

    except Exception as e:
        logger.error(f"Error in order_detail: {str(e)}", exc_info=True)
        messages.error(request, f"خطا: {str(e)}")
        return redirect('order:user_orders')


@login_required
@require_http_methods(['GET'])
def get_order_total_api(request, order_id):
    """دریافت مبلغ نهایی به‌روز سفارش (با احتساب کیف پول و چک)"""
    try:
        order = get_object_or_404(Order, id=order_id, user=request.user)

        total_amount = order.subtotal - order.discount_amount - order.coupon_discount + order.shipping_cost
        amount_after_wallet = total_amount - order.used_from_wallet

        active_check = CheckPayment.objects.filter(
            order=order,
            user=request.user,
            status=CheckPaymentStatus.PENDING.value
        ).first()

        if active_check and active_check.check_image:
            final_total = amount_after_wallet - active_check.check_amount
        else:
            final_total = amount_after_wallet

        if final_total < 0:
            final_total = 0

        return JsonResponse({
            'success': True,
            'final_total': int(final_total),
            'final_total_display': f"{final_total:,.0f}",
            'used_from_wallet': int(order.used_from_wallet),
            'subtotal': int(order.subtotal),
            'discount_amount': int(order.discount_amount),
            'shipping_cost': int(order.shipping_cost),
        })
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})