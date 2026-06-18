# apps/payment/views.py

from django.shortcuts import render, get_object_or_404
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import ListView, DetailView
from django.db.models import Q
from django.http import JsonResponse
from django.core.paginator import Paginator
from django.utils import timezone

from apps.check.models import CheckPayment, CheckPaymentStatus
from apps.user.models.user import CustomUser


class UserCheckPaymentListView(LoginRequiredMixin, ListView):
    """
    نمایش لیست چک‌های کاربر با قابلیت فیلتر
    """
    model = CheckPayment
    template_name = 'check_app/user_check_list.html'
    context_object_name = 'checks'
    paginate_by = 10

    def get_queryset(self):
        queryset = CheckPayment.objects.filter(
            user=self.request.user
        ).select_related(
            'user', 'order', 'pro_order'
        ).prefetch_related(
            'history'
        )

        # فیلتر بر اساس وضعیت - استفاده از .value
        status_filter = self.request.GET.get('status')
        if status_filter:
            valid_statuses = [
                CheckPaymentStatus.PENDING.value,
                CheckPaymentStatus.VERIFIED.value,
                CheckPaymentStatus.REJECTED.value,
                CheckPaymentStatus.CANCELLED.value
            ]
            if status_filter in valid_statuses:
                queryset = queryset.filter(status=status_filter)

        # فیلتر بر اساس تاریخ (از - تا)
        date_from = self.request.GET.get('date_from')
        date_to = self.request.GET.get('date_to')

        if date_from:
            try:
                from datetime import datetime
                date_from_obj = datetime.strptime(date_from, '%Y-%m-%d')
                queryset = queryset.filter(created_at__date__gte=date_from_obj.date())
            except ValueError:
                pass

        if date_to:
            try:
                from datetime import datetime
                date_to_obj = datetime.strptime(date_to, '%Y-%m-%d')
                queryset = queryset.filter(created_at__date__lte=date_to_obj.date())
            except ValueError:
                pass

        # جستجو در شماره پیگیری یا شماره سفارش
        search_query = self.request.GET.get('search')
        if search_query:
            queryset = queryset.filter(
                Q(tracking_number__icontains=search_query) |
                Q(order__order_number__icontains=search_query) |
                Q(pro_order__id__icontains=search_query)
            )

        # مرتب‌سازی
        sort_by = self.request.GET.get('sort', '-created_at')
        if sort_by in ['created_at', '-created_at', 'status', '-status', 'tracking_number']:
            queryset = queryset.order_by(sort_by)

        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # آمار چک‌ها - استفاده از .value در همه جا
        user_checks = CheckPayment.objects.filter(user=self.request.user)
        context['stats'] = {
            'total': user_checks.count(),
            'pending': user_checks.filter(status=CheckPaymentStatus.PENDING.value).count(),
            'verified': user_checks.filter(status=CheckPaymentStatus.VERIFIED.value).count(),
            'rejected': user_checks.filter(status=CheckPaymentStatus.REJECTED.value).count(),
            'cancelled': user_checks.filter(status=CheckPaymentStatus.CANCELLED.value).count(),
            'finalized': user_checks.filter(is_finalized=True).count(),
        }

        # وضعیت‌های موجود برای فیلتر
        context['status_choices'] = CheckPaymentStatus.choices

        # پارامترهای فیلتر فعلی
        context['current_filters'] = {
            'status': self.request.GET.get('status', ''),
            'date_from': self.request.GET.get('date_from', ''),
            'date_to': self.request.GET.get('date_to', ''),
            'search': self.request.GET.get('search', ''),
            'sort': self.request.GET.get('sort', '-created_at'),
        }

        return context


class UserCheckPaymentDetailView(LoginRequiredMixin, DetailView):
    """
    نمایش جزئیات یک چک خاص
    """
    model = CheckPayment
    template_name = 'payment/user_check_detail.html'
    context_object_name = 'check'
    slug_field = 'tracking_number'
    slug_url_kwarg = 'tracking_number'

    def get_queryset(self):
        return CheckPayment.objects.filter(
            user=self.request.user
        ).select_related(
            'user', 'order', 'pro_order', 'verified_by'
        ).prefetch_related(
            'history'
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        check = self.object

        # تاریخچه تغییرات
        context['history'] = check.history.all().order_by('-created_at')

        # اطلاعات سفارش مرتبط
        if check.order:
            context['related_order'] = check.order
            context['order_type'] = 'regular'
        elif check.pro_order:
            context['related_order'] = check.pro_order
            context['order_type'] = 'print'

        # قابلیت لغو (فقط در حالت pending) - استفاده از .value
        context['can_cancel'] = (
            check.status == CheckPaymentStatus.PENDING.value and
            not check.is_finalized
        )

        return context


def check_payment_cancel(request, tracking_number):
    """
    لغو چک توسط کاربر (AJAX)
    """
    if not request.user.is_authenticated:
        return JsonResponse({'success': False, 'error': 'لطفاً وارد شوید'})

    check = get_object_or_404(
        CheckPayment,
        tracking_number=tracking_number,
        user=request.user
    )

    if request.method == 'POST':
        success, message = check.cancel(request.user)
        return JsonResponse({
            'success': success,
            'message': message,
            'status': check.status if success else None
        })

    return JsonResponse({'success': False, 'error': 'متود نامعتبر'})


def get_check_status_badge(status):
    """
    تابع کمکی برای نمایش وضعیت چک با رنگ مناسب
    """
    badges = {
        CheckPaymentStatus.PENDING.value: 'warning',
        CheckPaymentStatus.VERIFIED.value: 'success',
        CheckPaymentStatus.REJECTED.value: 'danger',
        CheckPaymentStatus.CANCELLED.value: 'secondary',
    }
    return badges.get(status, 'secondary')