# apps/peyment/views.py

from django.shortcuts import render
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views import View
from django.core.paginator import Paginator
from django.db.models import Q, Sum
from django.utils import timezone
from .models import Peyment, PaymentMethod


class PaymentListView(LoginRequiredMixin, View):
    """لیست پرداخت‌های کاربر"""

    def get(self, request):
        # دریافت پرداخت‌های کاربر
        payments = Peyment.objects.filter(
            customer=request.user
        ).select_related('order').order_by('-createAt')

        # آمار کلی
        total_payments = payments.filter(isFinaly=True).count()
        total_amount = payments.filter(isFinaly=True).aggregate(Sum('amount'))['amount__sum'] or 0
        success_payments = payments.filter(isFinaly=True, statusCode=100).count()
        failed_payments = payments.filter(isFinaly=False).count()

        # فیلتر بر اساس وضعیت
        status_filter = request.GET.get('status', 'all')
        if status_filter == 'success':
            payments = payments.filter(isFinaly=True)
        elif status_filter == 'failed':
            payments = payments.filter(isFinaly=False)
        elif status_filter == 'online':
            payments = payments.filter(payment_method=PaymentMethod.ONLINE.value)
        elif status_filter == 'card_to_card':
            payments = payments.filter(payment_method=PaymentMethod.CARD_TO_CARD.value)

        # فیلتر بر اساس تاریخ
        date_filter = request.GET.get('date', '')
        today = timezone.now().date()
        if date_filter == 'today':
            payments = payments.filter(createAt__date=today)
        elif date_filter == 'week':
            week_ago = today - timezone.timedelta(days=7)
            payments = payments.filter(createAt__date__gte=week_ago)
        elif date_filter == 'month':
            month_ago = today - timezone.timedelta(days=30)
            payments = payments.filter(createAt__date__gte=month_ago)

        # جستجو
        search_query = request.GET.get('search', '')
        if search_query:
            payments = payments.filter(
                Q(order__order_number__icontains=search_query) |
                Q(refId__icontains=search_query)
            )

        # صفحه‌بندی
        paginator = Paginator(payments, 15)
        page_number = request.GET.get('page')
        page_obj = paginator.get_page(page_number)

        context = {
            'payments': page_obj,
            'total_payments': total_payments,
            'total_amount': total_amount,
            'success_payments': success_payments,
            'failed_payments': failed_payments,
            'current_status': status_filter,
            'current_date': date_filter,
            'search_query': search_query,
            'status_choices': [
                {'value': 'all', 'label': 'همه', 'count': Peyment.objects.filter(customer=request.user).count()},
                {'value': 'success', 'label': 'موفق', 'count': Peyment.objects.filter(customer=request.user, isFinaly=True).count()},
                {'value': 'failed', 'label': 'ناموفق', 'count': Peyment.objects.filter(customer=request.user, isFinaly=False).count()},
                {'value': 'online', 'label': 'درگاه آنلاین', 'count': Peyment.objects.filter(customer=request.user, payment_method=PaymentMethod.ONLINE.value).count()},
                {'value': 'card_to_card', 'label': 'کارت به کارت', 'count': Peyment.objects.filter(customer=request.user, payment_method=PaymentMethod.CARD_TO_CARD.value).count()},
            ],
            'date_choices': [
                {'value': '', 'label': 'همه تاریخ‌ها'},
                {'value': 'today', 'label': 'امروز'},
                {'value': 'week', 'label': 'هفته گذشته'},
                {'value': 'month', 'label': 'ماه گذشته'},
            ],
        }

        return render(request, 'peyment_app/payment_list.html', context)


class PaymentDetailView(LoginRequiredMixin, View):
    """جزئیات یک پرداخت"""

    def get(self, request, payment_id):
        payment = Peyment.objects.filter(
            id=payment_id,
            customer=request.user
        ).select_related('order', 'order__user').first()

        if not payment:
            from django.shortcuts import redirect
            from django.contrib import messages
            messages.error(request, 'پرداخت یافت نشد')
            return redirect('peyment:payment_list')

        context = {
            'payment': payment,
        }

        return render(request, 'peyment_app/payment_detail.html', context)