from django.shortcuts import render
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.db.models import Q, Count
from django.core.paginator import Paginator
from django.utils import timezone
from django.db import transaction
from datetime import datetime
import json

from apps.check.models import CheckPayment, CheckPaymentStatus, CheckPaymentHistory


def admin_check_list(request):
    """نمایش صفحه مدیریت چک‌ها"""
    return render(request, 'panel_app/dashboard/check.html')


@csrf_exempt
@require_http_methods(["GET"])
def api_check_list(request):
    """API لیست چک‌ها با فیلتر و صفحه‌بندی"""
    try:
        # پارامترها
        page = int(request.GET.get('page', 1))
        page_size = int(request.GET.get('page_size', 20))
        status = request.GET.get('status', '')
        search = request.GET.get('search', '')
        date_from = request.GET.get('date_from', '')
        date_to = request.GET.get('date_to', '')
        sort_by = request.GET.get('sort_by', '-created_at')

        # کوئری اصلی
        queryset = CheckPayment.objects.all().select_related('user', 'order', 'pro_order')

        # فیلتر وضعیت - استفاده از .value
        if status:
            # پیدا کردن مقدار status
            status_values = [s.value for s in CheckPaymentStatus if s.value == status]
            if status_values:
                queryset = queryset.filter(status=status_values[0])

        # فیلتر تاریخ
        if date_from:
            try:
                date_from_obj = datetime.strptime(date_from, '%Y-%m-%d')
                queryset = queryset.filter(created_at__date__gte=date_from_obj)
            except:
                pass

        if date_to:
            try:
                date_to_obj = datetime.strptime(date_to, '%Y-%m-%d')
                queryset = queryset.filter(created_at__date__lte=date_to_obj)
            except:
                pass

        # جستجو
        if search:
            queryset = queryset.filter(
                Q(tracking_number__icontains=search) |
                Q(user__mobileNumber__icontains=search) |
                Q(bank_name__icontains=search) |
                Q(check_number__icontains=search)
            )

        # مرتب‌سازی
        queryset = queryset.order_by(sort_by)

        # آمار
        stats = {
            'total': CheckPayment.objects.count(),
            'pending': CheckPayment.objects.filter(status=CheckPaymentStatus.PENDING.value).count(),
            'verified': CheckPayment.objects.filter(status=CheckPaymentStatus.VERIFIED.value).count(),
            'rejected': CheckPayment.objects.filter(status=CheckPaymentStatus.REJECTED.value).count(),
        }

        # صفحه‌بندی
        paginator = Paginator(queryset, page_size)
        page_obj = paginator.get_page(page)

        # تبدیل به JSON
        checks = []
        for check in page_obj:
            checks.append({
                'id': str(check.id),
                'tracking_number': check.tracking_number,
                'user_mobile': check.user.mobileNumber if check.user else '',
                'user_name': f"{check.user.name} {check.user.family}".strip() if check.user else '',
                'check_image': check.check_image.url if check.check_image else '',
                'bank_name': check.bank_name or '',
                'check_number': check.check_number or '',
                'check_amount': str(check.check_amount) if check.check_amount else '',
                'status': check.status,
                'status_display': check.get_status_display(),
                'is_finalized': check.is_finalized,
                'created_at': check.created_at.strftime('%Y/%m/%d %H:%M'),
                'verified_at': check.verified_at.strftime('%Y/%m/%d %H:%M') if check.verified_at else '',
                'order_display': check.order.order_number if check.order else (str(check.pro_order.id)[:8] if check.pro_order else ''),
            })

        return JsonResponse({
            'status': 'success',
            'checks': checks,
            'stats': stats,
            'pagination': {
                'current_page': page_obj.number,
                'total_pages': paginator.num_pages,
                'total_count': paginator.count,
                'has_previous': page_obj.has_previous(),
                'has_next': page_obj.has_next(),
                'previous_page_number': page_obj.previous_page_number() if page_obj.has_previous() else None,
                'next_page_number': page_obj.next_page_number() if page_obj.has_next() else None,
            }
        })
    except Exception as e:
        return JsonResponse({'status': 'error', 'error': str(e)}, status=400)


@csrf_exempt
@require_http_methods(["GET"])
def admin_check_detail(request, check_id):
    """دریافت جزئیات یک چک"""
    try:
        check = CheckPayment.objects.get(id=check_id)

        data = {
            'id': str(check.id),
            'tracking_number': check.tracking_number,
            'user_mobile': check.user.mobileNumber if check.user else '',
            'user_name': f"{check.user.name} {check.user.family}".strip() if check.user else '',
            'check_image': check.check_image.url if check.check_image else '',
            'bank_name': check.bank_name or '',
            'check_number': check.check_number or '',
            'check_date': check.check_date.strftime('%Y/%m/%d') if check.check_date else '',
            'check_amount': str(check.check_amount) if check.check_amount else '',
            'description': check.description or '',
            'status': check.status,
            'status_display': check.get_status_display(),
            'admin_note': check.admin_note or '',
            'rejection_reason': check.rejection_reason or '',
            'verified_at': check.verified_at.strftime('%Y/%m/%d %H:%M') if check.verified_at else '',
            'verified_by': check.verified_by.mobileNumber if check.verified_by else '',
            'is_finalized': check.is_finalized,
            'finalized_at': check.finalized_at.strftime('%Y/%m/%d %H:%M') if check.finalized_at else '',
            'created_at': check.created_at.strftime('%Y/%m/%d %H:%M'),
            'updated_at': check.updated_at.strftime('%Y/%m/%d %H:%M'),
            'order_ref': check.order.order_number if check.order else (str(check.pro_order.id)[:8] if check.pro_order else ''),
            'history': [
                {
                    'action': h.action,
                    'action_display': h.get_action_display(),
                    'message': h.message or '',
                    'created_at': h.created_at.strftime('%Y/%m/%d %H:%M')
                }
                for h in check.history.all().order_by('-created_at')
            ]
        }

        return JsonResponse({'status': 'success', 'check': data})
    except CheckPayment.DoesNotExist:
        return JsonResponse({'status': 'error', 'error': 'چک یافت نشد'}, status=404)


@csrf_exempt
@require_http_methods(["POST"])
def admin_check_verify(request, check_id):
    """تایید چک توسط ادمین"""
    try:
        check = CheckPayment.objects.get(id=check_id)

        if check.status != CheckPaymentStatus.PENDING.value:
            return JsonResponse({'success': False, 'error': 'فقط چک‌های در انتظار قابل تایید هستند'})

        note = request.POST.get('note', '')
        admin_user = request.user if request.user.is_authenticated else None

        check.status = CheckPaymentStatus.VERIFIED.value
        check.verified_by = admin_user
        check.verified_at = timezone.now()
        if note:
            check.admin_note = note
        check.save()

        # تاریخچه
        CheckPaymentHistory.objects.create(
            check_payment=check,
            action=CheckPaymentHistory.ActionType.ADMIN_VERIFIED.value,
            message=f"چک تایید شد توسط {admin_user.mobileNumber if admin_user else 'ادمین'}",
            created_by=admin_user
        )

        return JsonResponse({'success': True, 'message': 'چک با موفقیت تایید شد'})
    except CheckPayment.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'چک یافت نشد'}, status=404)


@csrf_exempt
@require_http_methods(["POST"])
def admin_check_reject(request, check_id):
    """رد چک توسط ادمین"""
    try:
        check = CheckPayment.objects.get(id=check_id)

        if check.status != CheckPaymentStatus.PENDING.value:
            return JsonResponse({'success': False, 'error': 'فقط چک‌های در انتظار قابل رد هستند'})

        reason = request.POST.get('reason', '')
        if not reason:
            return JsonResponse({'success': False, 'error': 'لطفاً دلیل رد را وارد کنید'})

        note = request.POST.get('note', '')
        admin_user = request.user if request.user.is_authenticated else None

        check.status = CheckPaymentStatus.REJECTED.value
        check.rejection_reason = reason
        check.verified_by = admin_user
        if note:
            check.admin_note = note
        check.save()

        CheckPaymentHistory.objects.create(
            check_payment=check,
            action=CheckPaymentHistory.ActionType.ADMIN_REJECTED.value,
            message=f"چک رد شد: {reason}",
            created_by=admin_user
        )

        return JsonResponse({'success': True, 'message': 'چک با موفقیت رد شد'})
    except CheckPayment.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'چک یافت نشد'}, status=404)


@csrf_exempt
@require_http_methods(["POST"])
def admin_check_finalize(request, check_id):
    """نهایی‌سازی پرداخت چک"""
    try:
        check = CheckPayment.objects.get(id=check_id)

        if check.status != CheckPaymentStatus.VERIFIED.value:
            return JsonResponse({'success': False, 'error': 'فقط چک‌های تایید شده قابل نهایی‌سازی هستند'})

        if check.is_finalized:
            return JsonResponse({'success': False, 'error': 'این پرداخت قبلاً نهایی شده است'})

        admin_user = request.user if request.user.is_authenticated else None

        check.is_finalized = True
        check.finalized_at = timezone.now()
        check.save()

        # بروزرسانی سفارش
        if check.order and check.order.status == 'pending':
            check.order.mark_as_paid()
        elif check.pro_order and check.pro_order.status == 'pending':
            check.pro_order.status = 'paid'
            check.pro_order.save(update_fields=['status'])

        CheckPaymentHistory.objects.create(
            check_payment=check,
            action=CheckPaymentHistory.ActionType.PAYMENT_FINALIZED.value,
            message="پرداخت چک نهایی شد و سفارش تایید گردید",
            created_by=admin_user
        )

        return JsonResponse({'success': True, 'message': 'پرداخت نهایی شد و سفارش تایید گردید'})
    except CheckPayment.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'چک یافت نشد'}, status=404)


@csrf_exempt
@require_http_methods(["POST"])
def admin_check_bulk_action(request):
    """عملیات گروهی روی چک‌ها"""
    try:
        check_ids = request.POST.getlist('check_ids[]')
        if not check_ids:
            return JsonResponse({'success': False, 'error': 'هیچ چکی انتخاب نشده است'})

        action = request.POST.get('action', '')
        if action not in ['verify', 'reject']:
            return JsonResponse({'success': False, 'error': 'عملیات نامعتبر'})

        checks = CheckPayment.objects.filter(id__in=check_ids, status=CheckPaymentStatus.PENDING.value)

        if not checks.exists():
            return JsonResponse({'success': False, 'error': 'هیچ چک قابل عملیاتی یافت نشد'})

        admin_user = request.user if request.user.is_authenticated else None
        success_count = 0

        with transaction.atomic():
            for check in checks:
                if action == 'verify':
                    check.status = CheckPaymentStatus.VERIFIED.value
                    check.verified_by = admin_user
                    check.verified_at = timezone.now()
                    check.save()

                    CheckPaymentHistory.objects.create(
                        check_payment=check,
                        action=CheckPaymentHistory.ActionType.ADMIN_VERIFIED.value,
                        message=f"تایید گروهی توسط {admin_user.mobileNumber if admin_user else 'ادمین'}",
                        created_by=admin_user
                    )
                else:  # reject
                    reason = request.POST.get('reason', 'رد گروهی')
                    check.status = CheckPaymentStatus.REJECTED.value
                    check.rejection_reason = reason
                    check.verified_by = admin_user
                    check.save()

                    CheckPaymentHistory.objects.create(
                        check_payment=check,
                        action=CheckPaymentHistory.ActionType.ADMIN_REJECTED.value,
                        message=f"رد گروهی: {reason}",
                        created_by=admin_user
                    )
                success_count += 1

        return JsonResponse({
            'success': True,
            'message': f'{success_count} چک با موفقیت {"تایید" if action == "verify" else "رد"} شدند'
        })
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=400)


@csrf_exempt
@require_http_methods(["GET"])
def admin_check_export_csv(request):
    """خروجی CSV از چک‌ها"""
    import csv
    from django.http import HttpResponse

    response = HttpResponse(content_type='text/csv; charset=utf-8')
    response['Content-Disposition'] = 'attachment; filename="checks_export.csv"'

    writer = csv.writer(response)
    writer.writerow([
        'شماره پیگیری', 'کاربر', 'موبایل', 'بانک', 'شماره چک', 'مبلغ',
        'وضعیت', 'تاریخ ثبت', 'تاریخ تایید', 'نهایی شده'
    ])

    checks = CheckPayment.objects.all().select_related('user')
    for check in checks:
        writer.writerow([
            check.tracking_number,
            f"{check.user.name} {check.user.family}".strip() or check.user.mobileNumber,
            check.user.mobileNumber,
            check.bank_name or '',
            check.check_number or '',
            str(check.check_amount) if check.check_amount else '',
            check.get_status_display(),
            check.created_at.strftime('%Y/%m/%d %H:%M'),
            check.verified_at.strftime('%Y/%m/%d %H:%M') if check.verified_at else '',
            'بله' if check.is_finalized else 'خیر'
        ])

    return response