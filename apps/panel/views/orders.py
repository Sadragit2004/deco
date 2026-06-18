# apps/order/views.py

from django.shortcuts import render, get_object_or_404
from django.contrib.admin.views.decorators import staff_member_required
from django.views.decorators.http import require_http_methods
from django.http import JsonResponse
from django.db.models import Q, Sum, Count, F, Value, Case, When, IntegerField, DecimalField
from django.db.models.functions import Coalesce, TruncDate, TruncMonth
from django.utils import timezone
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.db import models

from apps.order.models import Order, OrderItem, OrderStatus, OrderStatusHistory, OrderType, PaymentReceipt
from apps.peyment.models import Peyment, PaymentMethod
from apps.user.models.user import CustomUser
from apps.user.models.profile import CustomerLoyalty, LoyaltyTransaction, Wallet, WalletTransaction, Province, City
from apps.discount.models import Coupon

import jdatetime
from datetime import datetime, timedelta
import json
from decimal import Decimal


@staff_member_required
def admin_orders_panel(request):
    """نمایش پنل مدیریت سفارشات"""
    return render(request, 'panel_app/dashboard/admin_orders_panel.html')


@staff_member_required
def api_orders_list(request):
    """
    API دریافت لیست سفارشات با فیلترها و جستجوی پیشرفته
    """
    orders = Order.objects.select_related(
        'user', 'address', 'address__province', 'address__city', 'shipping_method', 'coupon'
    ).prefetch_related(
        'items', 'items__product', 'applied_discounts', 'status_history', 'peyment_order'
    ).all()

    province = request.GET.get('province', '')
    city = request.GET.get('city', '')

    if province:
        orders = orders.filter(address__province__name__icontains=province)
    if city:
        orders = orders.filter(address__city__name__icontains=city)

    from_date = request.GET.get('from_date', '')
    to_date = request.GET.get('to_date', '')

    if from_date:
        try:
            year, month, day = map(int, from_date.split('-'))
            gregorian_date = jdatetime.date(year, month, day).togregorian()
            orders = orders.filter(created_at__date__gte=gregorian_date)
        except:
            pass

    if to_date:
        try:
            year, month, day = map(int, to_date.split('-'))
            gregorian_date = jdatetime.date(year, month, day).togregorian()
            orders = orders.filter(created_at__date__lte=gregorian_date)
        except:
            pass

    min_price = request.GET.get('min_price', '')
    max_price = request.GET.get('max_price', '')

    if min_price:
        try:
            orders = orders.filter(total__gte=Decimal(str(min_price)))
        except:
            pass
    if max_price:
        try:
            orders = orders.filter(total__lte=Decimal(str(max_price)))
        except:
            pass

    status = request.GET.get('status', '')
    if status:
        valid_status_values = [choice.value for choice in OrderStatus]
        if status in valid_status_values:
            orders = orders.filter(status=status)

    payment_method = request.GET.get('payment_method', '')
    if payment_method:
        if payment_method == 'wallet':
            orders = orders.filter(used_from_wallet__gt=0)
        elif payment_method == 'receipt':
            orders = orders.filter(has_uploaded_receipt=True)
        elif payment_method == 'online':
            orders = orders.filter(peyment_order__isnull=False, peyment_order__isFinaly=True)

    order_type = request.GET.get('order_type', '')
    if order_type:
        valid_type_values = [choice.value for choice in OrderType]
        if order_type in valid_type_values:
            orders = orders.filter(order_type=order_type)

    search = request.GET.get('search', '')
    if search:
        orders = orders.filter(
            Q(order_number__icontains=search) |
            Q(user__mobileNumber__icontains=search) |
            Q(user__name__icontains=search) |
            Q(user__family__icontains=search) |
            Q(address__address_text__icontains=search) |
            Q(address__province__name__icontains=search) |
            Q(address__city__name__icontains=search) |
            Q(items__product__title__icontains=search) |
            Q(tracking_code__icontains=search)
        ).distinct()

    sort_by = request.GET.get('sort_by', '-created_at')
    allowed_sorts = ['created_at', '-created_at', 'total', '-total', 'status', 'order_number']
    if sort_by in allowed_sorts:
        orders = orders.order_by(sort_by)
    else:
        orders = orders.order_by('-created_at')

    page = request.GET.get('page', 1)
    page_size = int(request.GET.get('page_size', 20))
    paginator = Paginator(orders, page_size)

    try:
        orders_page = paginator.page(page)
    except PageNotAnInteger:
        orders_page = paginator.page(1)
    except EmptyPage:
        orders_page = paginator.page(paginator.num_pages)

    total_amount = orders.aggregate(
        total=Coalesce(Sum('total'), Value(0, output_field=DecimalField()))
    )['total']

    total_wallet_used = orders.aggregate(
        total=Coalesce(Sum('used_from_wallet'), Value(0, output_field=DecimalField()))
    )['total']

    stats = {
        'total': orders.count(),
        'pending': orders.filter(status=OrderStatus.PENDING.value).count(),
        'paid': orders.filter(status=OrderStatus.PAID.value).count(),
        'processing': orders.filter(status=OrderStatus.PROCESSING.value).count(),
        'packaging': orders.filter(status=OrderStatus.PACKAGING.value).count(),
        'shipped': orders.filter(status=OrderStatus.SHIPPED.value).count(),
        'delivered': orders.filter(status=OrderStatus.DELIVERED.value).count(),
        'cancelled': orders.filter(status=OrderStatus.CANCELLED.value).count(),
        'total_amount': format_price(total_amount),
        'total_wallet_used': format_price(total_wallet_used),
    }

    orders_list = []
    for order in orders_page:
        payment_info = get_order_payment_info(order)
        payment_method_display = get_payment_method_display(order)
        wallet_amount = order.used_from_wallet or 0

        wallet_balance = 0
        if order.user and hasattr(order.user, 'wallet'):
            wallet_balance = order.user.wallet.balance

        used_points_value = 0
        if order.used_points > 0 and order.user and hasattr(order.user, 'loyalty'):
            used_points_value = order.used_points * 1000

        # دریافت آدرس مستقیم فایل رسید
        receipt_url = None
        if order.has_uploaded_receipt and hasattr(order, 'payment_receipt'):
            if order.payment_receipt.receipt_file:
                receipt_url = order.payment_receipt.receipt_file.url

        orders_list.append({
            'id': str(order.id),
            'order_number': order.order_number,
            'order_type': order.order_type,
            'order_type_display': dict(OrderType.choices).get(order.order_type, ''),
            'user_id': str(order.user.id) if order.user else None,
            'customer_name': get_customer_full_name(order),
            'customer_mobile': order.user.mobileNumber if order.user else '-',
            'customer_email': order.user.email if order.user else '-',
            'subtotal': format_price(order.subtotal),
            'subtotal_raw': float(order.subtotal),
            'discount_amount': format_price(order.discount_amount),
            'coupon_discount': format_price(order.coupon_discount),
            'shipping_cost': format_price(order.shipping_cost),
            'total': format_price(order.total),
            'total_raw': float(order.total),
            'wallet_amount': format_price(wallet_amount),
            'wallet_amount_raw': float(wallet_amount),
            'wallet_balance': format_price(wallet_balance),
            'used_points': order.used_points,
            'used_points_value': format_price(used_points_value),
            'final_payable': format_price(order.total - wallet_amount),
            'final_payable_raw': float(order.total - wallet_amount),
            'status': order.status,
            'status_display': dict(OrderStatus.choices).get(order.status, ''),
            'status_badge_class': get_status_badge_class(order.status),
            'payment_method': payment_method_display['method'],
            'payment_method_icon': payment_method_display['icon'],
            'payment_method_class': payment_method_display['class'],
            'payment_detail': payment_method_display['detail'],
            'payment_info': payment_info,
            'has_receipt': order.has_uploaded_receipt,
            'receipt_verified': order.receipt_verified,
            'receipt_rejection_reason': order.receipt_rejection_reason,
            'receipt_url': receipt_url,
            'shipping_method_name': order.shipping_method.name if order.shipping_method else '-',
            'tracking_code': order.tracking_code or '-',
            'shipped_date': format_jalali_date(order.shipped_date) if order.shipped_date else None,
            'delivered_date': format_jalali_date(order.delivered_date) if order.delivered_date else None,
            'address': get_address_display(order),
            'items_count': order.items.count(),
            'items_preview': get_order_items_preview(order),
            'created_at': format_jalali_date(order.created_at),
            'created_at_raw': order.created_at.isoformat() if order.created_at else None,
            'paid_at': format_jalali_date(order.paid_at) if order.paid_at else None,
            'coupon_code': order.coupon.code if order.coupon else None,
            'description': order.description,
            'admin_note': order.admin_note,
        })

    provinces = list(Province.objects.filter(is_active=True).values_list('name', flat=True))
    cities = list(City.objects.filter(is_active=True).values_list('name', flat=True))

    return JsonResponse({
        'status': 'success',
        'orders': orders_list,
        'pagination': {
            'current_page': orders_page.number,
            'total_pages': paginator.num_pages,
            'total_items': paginator.count,
            'page_size': page_size,
            'has_next': orders_page.has_next(),
            'has_previous': orders_page.has_previous(),
        },
        'stats': stats,
        'filters': {
            'provinces': provinces,
            'cities': cities,
        }
    })


@staff_member_required
@require_http_methods(['POST'])
def api_change_order_status(request):
    """تغییر وضعیت سفارش"""
    try:
        data = json.loads(request.body)
        order_id = data.get('order_id')
        new_status = data.get('status')
        note = data.get('note', '')

        order = get_object_or_404(Order, id=order_id)
        old_status = order.status

        valid_status_values = [choice.value for choice in OrderStatus]
        if new_status not in valid_status_values:
            return JsonResponse({'status': 'error', 'message': 'وضعیت نامعتبر است'}, status=400)

        order.status = new_status

        if new_status == OrderStatus.PAID.value and not order.paid_at:
            order.paid_at = timezone.now()
        elif new_status == OrderStatus.SHIPPED.value and not order.shipped_date:
            order.shipped_date = timezone.now()
        elif new_status == OrderStatus.DELIVERED.value and not order.delivered_date:
            order.delivered_date = timezone.now()
        elif new_status == OrderStatus.CANCELLED.value and not order.cancelled_at:
            order.cancelled_at = timezone.now()

        order.save()

        OrderStatusHistory.objects.create(
            order=order,
            status=new_status,
            note=note or f"تغییر وضعیت از {dict(OrderStatus.choices).get(old_status)} به {dict(OrderStatus.choices).get(new_status)}",
            created_by=request.user
        )

        if new_status == OrderStatus.PAID.value and order.earned_points == 0:
            order.assign_points()

        return JsonResponse({
            'status': 'success',
            'message': 'وضعیت سفارش با موفقیت تغییر کرد',
            'new_status': new_status,
            'new_status_display': dict(OrderStatus.choices).get(new_status),
            'badge_class': get_status_badge_class(new_status)
        })

    except Order.DoesNotExist:
        return JsonResponse({'status': 'error', 'message': 'سفارش یافت نشد'}, status=404)
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=400)


@staff_member_required
def api_order_detail(request, order_id):
    """دریافت جزئیات کامل یک سفارش"""
    try:
        order = get_object_or_404(
            Order.objects.select_related(
                'user', 'address', 'address__province', 'address__city', 'shipping_method', 'coupon'
            ).prefetch_related(
                'items', 'items__product', 'applied_discounts', 'status_history', 'peyment_order'
            ),
            id=order_id
        )

        items = []
        for item in order.items.all():
            items.append({
                'id': item.id,
                'product_title': item.product_title,
                'product_code': item.product_code,
                'quantity': float(item.quantity),
                'unit_price': format_price(item.unit_price),
                'unit_price_before_discount': format_price(item.unit_price_before_discount),
                'discount_amount': format_price(item.discount_amount),
                'discount_percent': item.discount_percent,
                'total': format_price(item.total),
                'product_image': item.product_image,
                'brand_name': item.brand_name,
            })

        status_history = []
        for history in order.status_history.all()[:20]:
            status_history.append({
                'status': history.status,
                'status_display': dict(OrderStatus.choices).get(history.status),
                'note': history.note,
                'created_by': f'{history.created_by.name},{history.created_by.family}' if history.created_by else 'سیستم',
                'created_at': format_jalali_date(history.created_at),
                'created_at_time': history.created_at.strftime('%H:%M')
            })

        payments = []
        for payment in order.peyment_order.all():
            payments.append({
                'id': payment.id,
                'amount': format_price(payment.amount),
                'ref_id': payment.refId,
                'status_code': payment.statusCode,
                'is_final': payment.isFinaly,
                'payment_method': dict(PaymentMethod.choices).get(payment.payment_method, ''),
                'receipt_image': payment.receipt_image.url if payment.receipt_image else None,
                'card_number': payment.card_number,
                'tracking_number': payment.tracking_number,
                'created_at': format_jalali_date(payment.createAt),
            })

        wallet_info = None
        if order.user and hasattr(order.user, 'wallet'):
            wallet = order.user.wallet
            wallet_info = {
                'balance': format_price(wallet.balance),
                'frozen_balance': format_price(wallet.frozen_balance),
            }

        loyalty_info = None
        if order.user and hasattr(order.user, 'loyalty'):
            loyalty = order.user.loyalty
            loyalty_info = {
                'total_points': loyalty.total_points,
                'total_coins': loyalty.total_coins,
                'current_tier': loyalty.get_current_tier_display(),
                'lifetime_purchase': format_price(loyalty.lifetime_purchase),
            }

        receipt_url = None
        if order.has_uploaded_receipt and hasattr(order, 'payment_receipt'):
            if order.payment_receipt.receipt_file:
                receipt_url = order.payment_receipt.receipt_file.url

        return JsonResponse({
            'status': 'success',
            'order': {
                'id': str(order.id),
                'order_number': order.order_number,
                'order_type': dict(OrderType.choices).get(order.order_type),
                'customer': {
                    'id': str(order.user.id) if order.user else None,
                    'name': get_customer_full_name(order),
                    'mobile': order.user.mobileNumber if order.user else '-',
                    'email': order.user.email if order.user else '-',
                },
                'address': {
                    'full_address': order.address.address_text if order.address else '-',
                    'province': order.address.province.name if order.address and order.address.province else '-',
                    'city': order.address.city.name if order.address and order.address.city else '-',
                    'postal_code': order.address.postal_code if order.address else '-',
                    'address_type': order.address.get_address_type_display() if order.address else '-',
                } if order.address else None,
                'shipping': {
                    'method': order.shipping_method.name if order.shipping_method else '-',
                    'cost': format_price(order.shipping_cost),
                    'tracking_code': order.tracking_code or '-',
                },
                'amounts': {
                    'subtotal': format_price(order.subtotal),
                    'discount_amount': format_price(order.discount_amount),
                    'coupon_discount': format_price(order.coupon_discount),
                    'shipping_cost': format_price(order.shipping_cost),
                    'total': format_price(order.total),
                    'used_from_wallet': format_price(order.used_from_wallet),
                    'final_payable': format_price(order.total - (order.used_from_wallet or 0)),
                },
                'status': order.status,
                'status_display': dict(OrderStatus.choices).get(order.status),
                'coupon_code': order.coupon.code if order.coupon else None,
                'items': items,
                'items_count': len(items),
                'status_history': status_history,
                'payments': payments,
                'wallet_info': wallet_info,
                'loyalty_info': loyalty_info,
                'description': order.description,
                'admin_note': order.admin_note,
                'created_at': format_jalali_date(order.created_at),
                'paid_at': format_jalali_date(order.paid_at) if order.paid_at else None,
                'shipped_date': format_jalali_date(order.shipped_date) if order.shipped_date else None,
                'delivered_date': format_jalali_date(order.delivered_date) if order.delivered_date else None,
                'has_receipt': order.has_uploaded_receipt,
                'receipt_verified': order.receipt_verified,
                'receipt_rejection_reason': order.receipt_rejection_reason,
                'receipt_url': receipt_url,
            }
        })

    except Order.DoesNotExist:
        return JsonResponse({'status': 'error', 'message': 'سفارش یافت نشد'}, status=404)


@staff_member_required
def api_orders_chart_data(request):
    """داده‌های نمودار برای سفارشات"""
    months_data = []
    current_date = timezone.now()

    for i in range(11, -1, -1):
        date = current_date - timedelta(days=30*i)
        month_start = date.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

        if month_start.month == 12:
            month_end = month_start.replace(year=month_start.year + 1, month=1, day=1)
        else:
            month_end = month_start.replace(month=month_start.month + 1, day=1)

        jalali_date = jdatetime.date.fromgregorian(date=month_start.date())
        month_name = f"{jalali_date.strftime('%B')} {jalali_date.year}"

        orders_in_month = Order.objects.filter(created_at__gte=month_start, created_at__lt=month_end)

        total_amount = orders_in_month.aggregate(
            total=Coalesce(Sum('total'), Value(0, output_field=DecimalField()))
        )['total']

        months_data.append({
            'month': month_name,
            'orders_count': orders_in_month.count(),
            'total_amount': float(total_amount),
            'paid_orders': orders_in_month.filter(status=OrderStatus.PAID.value).count(),
            'delivered_orders': orders_in_month.filter(status=OrderStatus.DELIVERED.value).count(),
        })

    status_stats = []
    total_orders_count = Order.objects.count()

    for status_code, status_name in OrderStatus.choices:
        count = Order.objects.filter(status=status_code).count()
        if count > 0:
            percentage = round((count / total_orders_count) * 100, 1) if total_orders_count > 0 else 0
            status_stats.append({
                'status': status_code,
                'label': status_name,
                'count': count,
                'percentage': percentage,
            })

    return JsonResponse({
        'status': 'success',
        'monthly_data': months_data,
        'status_stats': status_stats,
    })


@staff_member_required
@require_http_methods(['POST'])
def api_update_tracking_code(request):
    """بروزرسانی کد رهگیری سفارش"""
    try:
        data = json.loads(request.body)
        order_id = data.get('order_id')
        tracking_code = data.get('tracking_code', '')

        order = get_object_or_404(Order, id=order_id)
        order.tracking_code = tracking_code
        order.save(update_fields=['tracking_code'])

        OrderStatusHistory.objects.create(
            order=order,
            status=order.status,
            note=f"کد رهگیری ثبت شد: {tracking_code}",
            created_by=request.user
        )

        return JsonResponse({
            'status': 'success',
            'message': 'کد رهگیری با موفقیت ثبت شد'
        })
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=400)


@staff_member_required
@require_http_methods(['POST'])
def api_verify_receipt(request):
    """تایید یا رد رسید پرداخت"""
    try:
        data = json.loads(request.body)
        order_id = data.get('order_id')
        action = data.get('action')
        reason = data.get('reason', '')

        order = get_object_or_404(Order, id=order_id)

        if not order.has_uploaded_receipt:
            return JsonResponse({'status': 'error', 'message': 'این سفارش رسید آپلود شده ندارد'}, status=400)

        if action == 'verify':
            order.mark_receipt_as_verified()

            if hasattr(order, 'payment_receipt'):
                receipt = order.payment_receipt
                receipt.status = PaymentReceipt.ReceiptStatus.VERIFIED
                receipt.verified_by = request.user
                receipt.verified_at = timezone.now()
                receipt.save()

            message = 'رسید پرداخت با موفقیت تایید شد'

            if order.status == OrderStatus.PENDING.value:
                order.mark_as_paid()
                message += ' و سفارش به وضعیت پرداخت شده تغییر یافت'

        elif action == 'reject':
            order.mark_receipt_as_rejected(reason)

            if hasattr(order, 'payment_receipt'):
                receipt = order.payment_receipt
                receipt.status = PaymentReceipt.ReceiptStatus.REJECTED
                receipt.rejection_reason = reason
                receipt.save()

            message = 'رسید پرداخت رد شد'
        else:
            return JsonResponse({'status': 'error', 'message': 'عملیات نامعتبر'}, status=400)

        OrderStatusHistory.objects.create(
            order=order,
            status=order.status,
            note=message + (f" - دلیل: {reason}" if reason else ""),
            created_by=request.user
        )

        return JsonResponse({
            'status': 'success',
            'message': message,
            'receipt_verified': order.receipt_verified,
            'order_status': order.status,
            'order_status_display': dict(OrderStatus.choices).get(order.status),
            'receipt_rejection_reason': order.receipt_rejection_reason
        })

    except Order.DoesNotExist:
        return JsonResponse({'status': 'error', 'message': 'سفارش یافت نشد'}, status=404)
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=400)


# ========== توابع کمکی ==========

def get_customer_full_name(order):
    if not order.user:
        return 'کاربر مهمان'
    name = f"{order.user.name or ''} {order.user.family or ''}".strip()
    return name if name else order.user.mobileNumber


def get_address_display(order):
    if not order.address:
        return '-'
    parts = []
    if order.address.province:
        parts.append(order.address.province.name)
    if order.address.city:
        parts.append(order.address.city.name)
    if order.address.address_text:
        address_preview = order.address.address_text[:50]
        if len(order.address.address_text) > 50:
            address_preview += '...'
        parts.append(address_preview)
    return ' - '.join(parts)


def get_order_items_preview(order):
    items = []
    for item in order.items.all()[:3]:
        items.append({
            'title': item.product_title,
            'quantity': float(item.quantity),
            'price': format_price(item.unit_price)
        })
    return {
        'items': items,
        'has_more': order.items.count() > 3,
        'total_count': order.items.count()
    }


def get_order_payment_info(order):
    info = {
        'method': None,
        'ref_id': None,
        'tracking_code': None,
        'card_number': None,
        'receipt_url': None,
        'bank_name': None,
        'payment_date': None,
        'verified': False,
        'rejection_reason': None
    }

    online_payment = order.peyment_order.filter(isFinaly=True).first()
    if online_payment:
        info['method'] = 'online'
        info['ref_id'] = online_payment.refId
        info['tracking_code'] = online_payment.tracking_number
        info['card_number'] = online_payment.card_number
        info['payment_date'] = format_jalali_date(online_payment.createAt)
        info['verified'] = True
        return info

    if order.has_uploaded_receipt and hasattr(order, 'payment_receipt'):
        receipt = order.payment_receipt
        info['method'] = 'receipt'
        info['receipt_url'] = receipt.receipt_file.url if receipt.receipt_file else None
        info['receipt_number'] = receipt.receipt_number
        info['bank_name'] = receipt.bank_name
        info['tracking_code'] = receipt.tracking_code
        info['payment_date'] = format_jalali_date(receipt.payment_date) if receipt.payment_date else None
        info['verified'] = receipt.status == 1
        info['rejection_reason'] = receipt.rejection_reason
        return info

    if order.used_from_wallet and order.used_from_wallet > 0:
        info['method'] = 'wallet'
        info['verified'] = True
        return info

    return info


def get_payment_method_display(order):
    if order.used_from_wallet and order.used_from_wallet > 0:
        return {
            'method': 'کیف پول',
            'icon': 'fa-wallet',
            'class': 'payment-wallet',
            'detail': f"{format_price(order.used_from_wallet)} تومان از کیف پول"
        }

    if order.has_uploaded_receipt:
        status_text = "تایید شده" if order.receipt_verified else "در انتظار تایید"
        if order.receipt_rejection_reason:
            status_text = "رد شده"
        return {
            'method': 'رسید بانکی',
            'icon': 'fa-receipt',
            'class': 'payment-receipt',
            'detail': status_text
        }

    online_payment = order.peyment_order.filter(isFinaly=True).first()
    if online_payment:
        return {
            'method': 'درگاه آنلاین',
            'icon': 'fa-credit-card',
            'class': 'payment-online',
            'detail': f"کد پیگیری: {online_payment.refId or '-'}"
        }

    return {
        'method': 'در انتظار پرداخت',
        'icon': 'fa-hourglass-half',
        'class': 'payment-pending',
        'detail': ''
    }


def get_status_badge_class(status):
    classes = {
        OrderStatus.PENDING.value: 'badge-warning',
        OrderStatus.PAID.value: 'badge-info',
        OrderStatus.PROCESSING.value: 'badge-primary',
        OrderStatus.PACKAGING.value: 'badge-primary',
        OrderStatus.SHIPPED.value: 'badge-info',
        OrderStatus.DELIVERED.value: 'badge-success',
        OrderStatus.CANCELLED.value: 'badge-danger',
    }
    return classes.get(status, 'badge-secondary')


def format_price(amount):
    if amount is None:
        return '۰'
    try:
        return f"{int(amount):,}".replace(',', '٬')
    except:
        return '۰'


def format_jalali_date(date):
    if not date:
        return None
    try:
        jalali = jdatetime.datetime.fromgregorian(datetime=date)
        return jalali.strftime('%Y/%m/%d')
    except:
        return date.strftime('%Y-%m-%d') if date else None