from django.shortcuts import render
from django.http import JsonResponse
from django.contrib.admin.views.decorators import staff_member_required
from django.db.models import Sum
from django.utils import timezone
from datetime import timedelta
import jdatetime
from decimal import Decimal
from django.shortcuts import render

from apps.user.models.user import CustomUser
from apps.order.models import Order
from apps.peyment.models import Peyment
from apps.pro.models import OrderMaterial


def to_jalali(date_time):
    """تبدیل تاریخ میلادی به شمسی"""
    if not date_time:
        return None
    jalali_date = jdatetime.datetime.fromgregorian(datetime=date_time)
    return jalali_date.strftime('%Y/%m/%d %H:%M')


@staff_member_required
def dashboard_api(request):
    """API دیتای داشبورد - خروجی JSON"""

    now = timezone.now()
    start_of_today = now.replace(hour=0, minute=0, second=0, microsecond=0)
    five_minutes_ago = now - timedelta(minutes=5)

    # ========== آمار کاربران ==========
    total_users = CustomUser.objects.filter(is_active=True).count()
    online_users = CustomUser.objects.filter(
        is_active=True, is_online=True, last_activity__gte=five_minutes_ago
    ).count()
    offline_users = total_users - online_users
    today_users = CustomUser.objects.filter(
        createAt__gte=start_of_today, is_active=True
    ).count()

    # لیست کاربران آنلاین
    online_users_list = []
    for user in CustomUser.objects.filter(is_active=True, is_online=True, last_activity__gte=five_minutes_ago)[:10]:
        online_users_list.append({
            'id': str(user.id),
            'name': user.name if user.name else str(user.mobileNumber),
            'mobile_number': str(user.mobileNumber),
        })

    # ========== لیست کاربران ==========
    users_list = []
    for user in CustomUser.objects.filter(is_active=True).order_by('-createAt')[:20]:
        users_list.append({
            'id': str(user.id),
            'name': user.name if user.name else str(user.mobileNumber),
            'mobile_number': str(user.mobileNumber),
            'email': user.email if user.email else '-',
            'online': user.is_online and user.last_activity and user.last_activity >= five_minutes_ago,
            'created_at': to_jalali(user.createAt),
        })

    # ========== آمار سفارشات ==========
    paid_orders = Order.objects.filter(status='paid').count()
    pending_orders = Order.objects.filter(status='pending').count()
    shipping_orders = Order.objects.filter(status='shipped').count()
    delivered_orders = Order.objects.filter(status='delivered').count()
    today_paid_orders = Order.objects.filter(
        created_at__gte=start_of_today, status='paid'
    ).count()

    # ========== لیست سفارشات ==========
    orders_list = []
    for order in Order.objects.select_related('user').order_by('-created_at')[:20]:
        payment_method = 'در انتظار پرداخت'
        payment_detail = ''
        receipt_image = None
        wallet_amount = 0

        if hasattr(order, 'payment_receipt') and order.payment_receipt and order.payment_receipt.status == 1:
            payment_method = 'رسید بانکی'
            payment_detail = f'شماره رسید: {order.payment_receipt.receipt_number or "-"}'
            if order.payment_receipt.receipt_file:
                receipt_image = order.payment_receipt.receipt_file.url

        if order.used_from_wallet and order.used_from_wallet > 0:
            wallet_amount = int(order.used_from_wallet) if isinstance(order.used_from_wallet, Decimal) else order.used_from_wallet
            if payment_method == 'در انتظار پرداخت':
                payment_method = 'کیف پول'
                payment_detail = f'مبلغ: {wallet_amount:,} تومان'
            else:
                payment_detail += f' + کیف پول: {wallet_amount:,} تومان'

        payment = Peyment.objects.filter(order=order, isFinaly=True).first()
        if payment:
            payment_method = 'پرداخت آنلاین'
            payment_detail = f'کد پیگیری: {payment.refId or "-"}'

        orders_list.append({
            'order_number': order.order_number,
            'customer_name': order.user.mobileNumber if order.user else 'مهمان',
            'total': int(order.total) if order.total else 0,
            'status': order.status,
            'status_display': order.get_status_display(),
            'created_at': to_jalali(order.created_at),
            'payment_method': payment_method,
            'payment_detail': payment_detail,
            'receipt_image': receipt_image,
            'wallet_amount': wallet_amount,
        })

    # ========== درآمد ==========
    total_income = Order.objects.filter(status__in=['paid', 'delivered']).aggregate(
        total=Sum('total')
    )['total'] or 0
    today_income = Order.objects.filter(
        created_at__gte=start_of_today, status__in=['paid', 'delivered']
    ).aggregate(total=Sum('total'))['total'] or 0

    if isinstance(total_income, Decimal):
        total_income = int(total_income)
    if isinstance(today_income, Decimal):
        today_income = int(today_income)

    # ========== لیست پرداخت‌ها ==========
    payments_list = []
    for payment in Peyment.objects.filter(isFinaly=True).select_related('customer', 'order').order_by('-createAt')[:20]:
        amount = payment.amount if isinstance(payment.amount, int) else int(payment.amount) if payment.amount else 0
        payments_list.append({
            'id': str(payment.id),
            'ref_id': payment.refId if payment.refId else f'TRX-{str(payment.id)[:8]}',
            'payer_name': payment.customer.mobileNumber if payment.customer else '-',
            'amount': amount,
            'payment_method': 'کارت به کارت',
            'status': 'success' if payment.isFinaly else 'pending',
            'status_display': 'موفق' if payment.isFinaly else 'در انتظار',
            'created_at': to_jalali(payment.createAt),
            'order_number': payment.order.order_number if payment.order else '-',
        })

    # ========== سفارشات چاپی ==========
    total_print_orders = OrderMaterial.objects.count()
    today_print_orders = OrderMaterial.objects.filter(
        created_at__gte=start_of_today
    ).count()
    print_pending = OrderMaterial.objects.filter(status='pending').count()
    print_confirmed = OrderMaterial.objects.filter(status='confirmed').count()
    print_processing = OrderMaterial.objects.filter(status='processing').count()
    print_ready = OrderMaterial.objects.filter(status='ready').count()
    print_delivered = OrderMaterial.objects.filter(status='delivered').count()

    # ========== چارت ۶ ماه اخیر ==========
    months = []
    user_growth = []
    sales_data = []
    persian_months = ['فروردین', 'اردیبهشت', 'خرداد', 'تیر', 'مرداد', 'شهریور',
                      'مهر', 'آبان', 'آذر', 'دی', 'بهمن', 'اسفند']

    for i in range(5, -1, -1):
        month_start = now.replace(day=1, hour=0, minute=0, second=0) - timedelta(days=30*i)
        month_end = (month_start + timedelta(days=32)).replace(day=1)

        jalali_date = jdatetime.date.fromgregorian(date=month_start.date())
        months.append(persian_months[jalali_date.month - 1])

        month_users = CustomUser.objects.filter(
            createAt__gte=month_start, createAt__lt=month_end, is_active=True
        ).count()
        user_growth.append(month_users)

        month_sales = Order.objects.filter(
            created_at__gte=month_start, created_at__lt=month_end,
            status__in=['paid', 'delivered']
        ).aggregate(total=Sum('total'))['total'] or 0

        if isinstance(month_sales, Decimal):
            month_sales = int(month_sales)

        sales_data.append(round(month_sales / 1000000, 1))

    data = {
        'status': 'success',
        'timestamp': to_jalali(now),
        'users': {
            'total': total_users,
            'online': online_users,
            'offline': offline_users,
            'today': today_users,
            'online_list': online_users_list,
            'list': users_list,
        },
        'orders': {
            'paid': paid_orders,
            'pending': pending_orders,
            'shipping': shipping_orders,
            'delivered': delivered_orders,
            'today': today_paid_orders,
            'list': orders_list,
        },
        'income': {
            'total': total_income,
            'total_display': f"{total_income:,}",
            'today': today_income,
            'today_display': f"{today_income:,}",
        },
        'payments': {
            'total': len(payments_list),
            'list': payments_list,
        },
        'print_orders': {
            'total': total_print_orders,
            'today': today_print_orders,
            'pending': print_pending,
            'confirmed': print_confirmed,
            'processing': print_processing,
            'ready': print_ready,
            'delivered': print_delivered,
        },
        'chart': {
            'months': months,
            'user_growth': user_growth,
            'sales_data': sales_data,
        },
    }

    return JsonResponse(data, safe=False, json_dumps_params={'ensure_ascii': False})


@staff_member_required
def main(request):
    """نمایش صفحه داشبورد"""
    return render(request, 'panel_app/panel1.html')


# views.py
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import login_required
from django.utils import timezone


@login_required
@csrf_exempt
def user_offline(request):
    """ست کردن کاربر به آفلاین وقتی صفحه بسته میشه"""
    if request.method == 'POST':
        request.user.is_online = False
        request.user.save(update_fields=['is_online'])
        return JsonResponse({'status': 'ok'})
    return JsonResponse({'status': 'error'}, status=400)


@login_required
@csrf_exempt
def update_activity(request):
    """آپدیت آخرین فعالیت کاربر"""
    if request.method == 'POST':
        request.user.last_activity = timezone.now()
        request.user.is_online = True
        request.user.save(update_fields=['last_activity', 'is_online'])
        return JsonResponse({'status': 'ok'})
    return JsonResponse({'status': 'error'}, status=400)