# apps/peyment/views.py

from django.shortcuts import render, get_object_or_404
from django.contrib.admin.views.decorators import staff_member_required
from django.views.decorators.http import require_http_methods
from django.http import JsonResponse
from django.db.models import Q, Sum, Count, Avg, Value, IntegerField, DecimalField
from django.db.models.functions import Coalesce, TruncDate, TruncMonth
from django.utils import timezone
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.core.files.storage import default_storage

from apps.peyment.models import Peyment, PaymentMethod
from apps.order.models import Order, OrderStatus
from apps.user.models.user import CustomUser

import jdatetime
from datetime import datetime, timedelta
import json
from decimal import Decimal


@staff_member_required
def admin_payments_panel(request):
    """نمایش پنل مدیریت پرداخت‌ها"""
    return render(request, 'panel_app/dashboard/admin_payments_panel.html')


@staff_member_required
def api_payments_list(request):
    """
    API دریافت لیست پرداخت‌ها با فیلترها و جستجوی پیشرفته
    """
    payments = Peyment.objects.select_related(
        'order', 'customer'
    ).all()

    # ========== فیلتر بر اساس تاریخ ایرانی ==========
    from_date = request.GET.get('from_date', '')
    to_date = request.GET.get('to_date', '')

    if from_date:
        try:
            year, month, day = map(int, from_date.split('-'))
            gregorian_date = jdatetime.date(year, month, day).togregorian()
            payments = payments.filter(createAt__date__gte=gregorian_date)
        except:
            pass

    if to_date:
        try:
            year, month, day = map(int, to_date.split('-'))
            gregorian_date = jdatetime.date(year, month, day).togregorian()
            payments = payments.filter(createAt__date__lte=gregorian_date)
        except:
            pass

    # ========== فیلتر بر اساس مبلغ ==========
    min_amount = request.GET.get('min_amount', '')
    max_amount = request.GET.get('max_amount', '')

    if min_amount:
        try:
            payments = payments.filter(amount__gte=int(min_amount))
        except:
            pass
    if max_amount:
        try:
            payments = payments.filter(amount__lte=int(max_amount))
        except:
            pass

    # ========== فیلتر بر اساس وضعیت پرداخت ==========
    is_final = request.GET.get('is_final', '')
    if is_final:
        if is_final == 'true':
            payments = payments.filter(isFinaly=True)
        elif is_final == 'false':
            payments = payments.filter(isFinaly=False)

    # ========== فیلتر بر اساس روش پرداخت ==========
    payment_method = request.GET.get('payment_method', '')
    if payment_method:
        valid_methods = [choice.value for choice in PaymentMethod]  # استفاده از .value
        if payment_method in valid_methods:
            payments = payments.filter(payment_method=payment_method)

    # ========== جستجوی پیشرفته ==========
    search = request.GET.get('search', '')
    if search:
        payments = payments.filter(
            Q(refId__icontains=search) |
            Q(tracking_number__icontains=search) |
            Q(card_number__icontains=search) |
            Q(card_holder_name__icontains=search) |
            Q(order__order_number__icontains=search) |
            Q(customer__mobileNumber__icontains=search) |
            Q(customer__name__icontains=search) |
            Q(customer__family__icontains=search)
        ).distinct()

    # ========== مرتب‌سازی ==========
    sort_by = request.GET.get('sort_by', '-createAt')
    allowed_sorts = ['createAt', '-createAt', 'amount', '-amount', 'isFinaly']
    if sort_by in allowed_sorts:
        payments = payments.order_by(sort_by)
    else:
        payments = payments.order_by('-createAt')

    # ========== Pagination ==========
    page = request.GET.get('page', 1)
    page_size = int(request.GET.get('page_size', 20))
    paginator = Paginator(payments, page_size)

    try:
        payments_page = paginator.page(page)
    except PageNotAnInteger:
        payments_page = paginator.page(1)
    except EmptyPage:
        payments_page = paginator.page(paginator.num_pages)

    # ========== آمار کلی ==========
    total_amount = payments.aggregate(
        total=Coalesce(Sum('amount'), Value(0, output_field=IntegerField()))
    )['total']

    successful_amount = payments.filter(isFinaly=True).aggregate(
        total=Coalesce(Sum('amount'), Value(0, output_field=IntegerField()))
    )['total']

    failed_amount = payments.filter(isFinaly=False).aggregate(
        total=Coalesce(Sum('amount'), Value(0, output_field=IntegerField()))
    )['total']

    stats = {
        'total': payments.count(),
        'successful': payments.filter(isFinaly=True).count(),
        'failed': payments.filter(isFinaly=False).count(),
        'total_amount': format_price(total_amount),
        'successful_amount': format_price(successful_amount),
        'failed_amount': format_price(failed_amount),
        'online_count': payments.filter(payment_method=PaymentMethod.ONLINE.value).count(),
        'card_to_card_count': payments.filter(payment_method=PaymentMethod.CARD_TO_CARD.value).count(),
    }

    # ========== ساخت لیست پرداخت‌ها ==========
    payments_list = []
    for payment in payments_page:
        payments_list.append({
            'id': payment.id,
            'ref_id': payment.refId or '-',
            'order_number': payment.order.order_number if payment.order else '-',
            'customer_name': get_customer_full_name(payment.customer),
            'customer_mobile': payment.customer.mobileNumber if payment.customer else '-',
            'amount': format_price(payment.amount),
            'amount_raw': payment.amount,
            'is_final': payment.isFinaly,
            'status_display': 'موفق' if payment.isFinaly else 'ناموفق',
            'status_badge_class': 'badge-success' if payment.isFinaly else 'badge-danger',
            'payment_method': dict(PaymentMethod.choices).get(payment.payment_method, ''),
            'payment_method_icon': get_payment_method_icon(payment.payment_method),
            'payment_method_class': get_payment_method_class(payment.payment_method),
            'card_number': payment.card_number or '-',
            'card_holder_name': payment.card_holder_name or '-',
            'tracking_number': payment.tracking_number or '-',
            'receipt_image': payment.receipt_image.url if payment.receipt_image else None,
            'description': payment.description,
            'status_code': payment.statusCode,
            'created_at': format_jalali_date(payment.createAt),
            'created_at_raw': payment.createAt.isoformat() if payment.createAt else None,
            'updated_at': format_jalali_date(payment.updateAt),
        })

    return JsonResponse({
        'status': 'success',
        'payments': payments_list,
        'pagination': {
            'current_page': payments_page.number,
            'total_pages': paginator.num_pages,
            'total_items': paginator.count,
            'page_size': page_size,
            'has_next': payments_page.has_next(),
            'has_previous': payments_page.has_previous(),
        },
        'stats': stats,
    })


@staff_member_required
def api_payments_chart_data(request):
    """داده‌های نمودار برای پرداخت‌ها"""
    # داده‌های 12 ماه اخیر
    months_data = []
    current_date = timezone.now()

    for i in range(11, -1, -1):
        date = current_date - timedelta(days=30*i)
        month_start = date.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

        if month_start.month == 12:
            month_end = month_start.replace(year=month_start.year + 1, month=1, day=1)
        else:
            month_end = month_start.replace(month=month_start.month + 1, day=1)

        jalali_month = jdatetime.date.fromgregorian(date=month_start.date())
        month_name = f"{jalali_month.strftime('%B')} {jalali_month.year}"

        payments_in_month = Peyment.objects.filter(createAt__gte=month_start, createAt__lt=month_end)
        successful_payments = payments_in_month.filter(isFinaly=True)

        total_amount = payments_in_month.aggregate(
            total=Coalesce(Sum('amount'), Value(0, output_field=IntegerField()))
        )['total']

        successful_amount = successful_payments.aggregate(
            total=Coalesce(Sum('amount'), Value(0, output_field=IntegerField()))
        )['total']

        months_data.append({
            'month': month_name,
            'total_count': payments_in_month.count(),
            'successful_count': successful_payments.count(),
            'failed_count': payments_in_month.filter(isFinaly=False).count(),
            'total_amount': float(total_amount),
            'successful_amount': float(successful_amount),
        })

    # آمار روش‌های پرداخت
    payment_method_stats = []
    for method_code, method_name in PaymentMethod.choices:
        count = Peyment.objects.filter(payment_method=method_code).count()
        successful_count = Peyment.objects.filter(payment_method=method_code, isFinaly=True).count()
        if count > 0:
            payment_method_stats.append({
                'method': method_code,
                'label': method_name,
                'count': count,
                'successful_count': successful_count,
                'percentage': round((count / Peyment.objects.count()) * 100, 1) if Peyment.objects.count() > 0 else 0,
            })

    return JsonResponse({
        'status': 'success',
        'monthly_data': months_data,
        'payment_method_stats': payment_method_stats,
    })


@staff_member_required
def api_payment_detail(request, payment_id):
    """دریافت جزئیات کامل یک پرداخت"""
    try:
        payment = get_object_or_404(
            Peyment.objects.select_related('order', 'customer'),
            id=payment_id
        )

        # اطلاعات سفارش مرتبط
        order_info = None
        if payment.order:
            order_info = {
                'id': str(payment.order.id),
                'order_number': payment.order.order_number,
                'status': payment.order.status,
                'status_display': dict(OrderStatus.choices).get(payment.order.status, ''),
                'total_amount': format_price(payment.order.total),
                'created_at': format_jalali_date(payment.order.created_at),
            }

        return JsonResponse({
            'status': 'success',
            'payment': {
                'id': payment.id,
                'ref_id': payment.refId or '-',
                'order': order_info,
                'customer': {
                    'id': payment.customer.id if payment.customer else None,
                    'name': get_customer_full_name(payment.customer),
                    'mobile': payment.customer.mobileNumber if payment.customer else '-',
                    'email': payment.customer.email if payment.customer else '-',
                },
                'amount': format_price(payment.amount),
                'amount_raw': payment.amount,
                'is_final': payment.isFinaly,
                'status_display': 'موفق' if payment.isFinaly else 'ناموفق',
                'status_code': payment.statusCode,
                'payment_method': dict(PaymentMethod.choices).get(payment.payment_method, ''),
                'card_number': payment.card_number or '-',
                'card_holder_name': payment.card_holder_name or '-',
                'tracking_number': payment.tracking_number or '-',
                'receipt_image': payment.receipt_image.url if payment.receipt_image else None,
                'description': payment.description,
                'created_at': format_jalali_date(payment.createAt),
                'created_at_time': payment.createAt.strftime('%H:%M:%S') if payment.createAt else None,
                'updated_at': format_jalali_date(payment.updateAt),
            }
        })

    except Peyment.DoesNotExist:
        return JsonResponse({'status': 'error', 'message': 'پرداخت یافت نشد'}, status=404)


@staff_member_required
@require_http_methods(['POST'])
def api_update_payment_status(request):
    """تغییر وضعیت پرداخت (تایید/رد)"""
    try:
        data = json.loads(request.body)
        payment_id = data.get('payment_id')
        is_final = data.get('is_final')
        status_code = data.get('status_code', None)
        ref_id = data.get('ref_id', None)

        payment = get_object_or_404(Peyment, id=payment_id)

        old_status = payment.isFinaly
        payment.isFinaly = is_final

        if status_code is not None:
            payment.statusCode = status_code
        if ref_id:
            payment.refId = ref_id

        payment.save()

        # اگر پرداخت تایید شد و سفارش در وضعیت pending بود، وضعیت سفارش را به paid تغییر بده
        if is_final and not old_status and payment.order and payment.order.status == OrderStatus.PENDING.value:
            payment.order.mark_as_paid()

        return JsonResponse({
            'status': 'success',
            'message': 'وضعیت پرداخت با موفقیت تغییر کرد',
            'is_final': payment.isFinaly,
            'status_display': 'موفق' if payment.isFinaly else 'ناموفق',
        })

    except Peyment.DoesNotExist:
        return JsonResponse({'status': 'error', 'message': 'پرداخت یافت نشد'}, status=404)
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=400)


# ========== توابع کمکی ==========

def get_customer_full_name(user):
    if not user:
        return 'کاربر حذف شده'
    name = f"{user.name or ''} {user.family or ''}".strip()
    return name if name else user.mobileNumber


def get_payment_method_icon(method):
    icons = {
        PaymentMethod.ONLINE.value: 'fa-credit-card',
        PaymentMethod.CARD_TO_CARD.value: 'fa-exchange-alt',
    }
    return icons.get(method, 'fa-money-bill')


def get_payment_method_class(method):
    classes = {
        PaymentMethod.ONLINE.value: 'payment-online',
        PaymentMethod.CARD_TO_CARD.value: 'payment-card',
    }
    return classes.get(method, 'payment-other')


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