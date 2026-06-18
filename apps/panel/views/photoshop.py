# views_operator.py
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.core.paginator import Paginator
from django.db.models import Q
from django.utils import timezone
from apps.pro.models import OrderMaterial, OrderDesignStatus, OrderReviewHistory
import json


# ==================== پنل اپراتور فتوشاپ ====================

@staff_member_required
def operator_dashboard(request):
    return render(request, 'panel_app/dashboard/photoshop.html')


@staff_member_required
def order_detail(request, order_id):
    order = get_object_or_404(
        OrderMaterial.objects.select_related(
            'installation', 'material', 'ready_template', 'pdf_document', 'user', 'design_status'
        ),
        id=order_id
    )
    review_history = order.review_history.all()
    reject_count = review_history.filter(action='user_reject').count()
    context = {
        'order': order,
        'review_history': review_history,
        'reject_count': reject_count,
        'max_reject': 3,
        'remaining_reject': 3 - reject_count,
    }
    return render(request, 'operator/order_detail.html', context)


@staff_member_required
@require_http_methods(["POST"])
def upload_design(request, order_id):
    order = get_object_or_404(OrderMaterial, id=order_id)

    final_image = request.FILES.get('final_image')
    psd_file = request.FILES.get('psd_file')
    operator_message = request.POST.get('message', '')

    if not final_image:
        return JsonResponse({'error': 'لطفاً تصویر نهایی را آپلود کنید'}, status=400)

    design_status, created = OrderDesignStatus.objects.get_or_create(order=order)
    design_status.status = 'ready_for_review'
    design_status.final_design_image = final_image
    if psd_file:
        design_status.final_design_psd = psd_file
    design_status.operator_message = operator_message
    design_status.save()

    OrderReviewHistory.objects.create(
        order=order,
        action='operator_submit',
        message=operator_message,
        attached_image=final_image,
        created_by=request.user
    )

    return JsonResponse({
        'success': True,
        'message': 'طراحی با موفقیت آپلود شد'
    })


@staff_member_required
@require_http_methods(["POST"])
def send_to_customer(request, order_id):
    order = get_object_or_404(OrderMaterial, id=order_id)

    if not hasattr(order, 'design_status') or not order.design_status.final_design_image:
        return JsonResponse({'error': 'ابتدا فایل طراحی را آپلود کنید'}, status=400)

    design_status = order.design_status
    design_status.status = 'ready_for_review'
    design_status.save()

    return JsonResponse({
        'success': True,
        'message': 'طراحی به مشتری ارسال شد و منتظر تایید است'
    })


@staff_member_required
@require_http_methods(["POST"])
def complete_order(request, order_id):
    order = get_object_or_404(OrderMaterial, id=order_id)

    if not hasattr(order, 'design_status'):
        return JsonResponse({'error': 'وضعیت طراحی برای این سفارش وجود ندارد'}, status=400)

    design_status = order.design_status
    design_status.status = 'finalized'
    design_status.delivered_at = timezone.now()
    design_status.save()

    order.status = 'delivered'
    order.isEnd = True
    order.save()

    return JsonResponse({
        'success': True,
        'message': 'سفارش با موفقیت تکمیل شد'
    })


# ==================== API ها ====================

@staff_member_required
def api_orders_list(request):
    tab = request.GET.get('tab', 'all')
    page = int(request.GET.get('page', 1))
    page_size = 12

    orders = OrderMaterial.objects.select_related(
        'installation', 'material', 'user', 'design_status', 'ready_template', 'pdf_document'
    ).prefetch_related('review_history')

    if tab == 'urgent':
        orders = orders.filter(
            review_history__action='user_reject',
            design_status__status='pending_design'
        ).distinct()
    elif tab == 'pending':
        orders = orders.filter(
            Q(design_status__isnull=True) | Q(design_status__status='pending_design')
        ).exclude(review_history__action='user_reject').distinct()
    elif tab == 'designing':
        orders = orders.filter(design_status__status='designing')
    elif tab == 'review':
        orders = orders.filter(design_status__status='ready_for_review')
    elif tab == 'approved':
        orders = orders.filter(design_status__status='approved')
    elif tab == 'completed':
        orders = orders.filter(design_status__status='finalized')
    elif tab == 'all':
        pass

    paginator = Paginator(orders, page_size)
    page_obj = paginator.get_page(page)

    orders_data = []
    for order in page_obj:
        reject_count = order.review_history.filter(action='user_reject').count()
        design_status = getattr(order, 'design_status', None)

        length = float(order.length) if order.length else 0
        width = float(order.width) if order.width else 0
        area = length * width

        price_per_m2 = order.installation.price if order.installation and order.installation.price else 0
        total_price = price_per_m2 * area

        customer_name = '-'
        if order.user:
            if hasattr(order.user, 'name') and hasattr(order.user, 'family') and order.user.name:
                customer_name = f'{order.user.name} {order.user.family}'
            else:
                customer_name = order.user.name or str(order.user)

        customer_design_image = None
        ready_template_image = None
        ready_template_title = None

        if order.plan_image:
            customer_design_image = order.plan_image.url
        if order.ready_template:
            ready_template_image = order.ready_template.image.url if order.ready_template.image else None
            ready_template_title = order.ready_template.title
        if order.pdf_document:
            ready_template_image = order.pdf_document.thumbnail.url if order.pdf_document.thumbnail else None
            ready_template_title = order.pdf_document.title

        status_display_map = {
            'pending_design': 'در انتظار طراحی',
            'designing': 'در حال طراحی',
            'ready_for_review': 'منتظر تایید',
            'approved': '✅ تایید شده توسط مشتری',
            'rejected': 'رد شده',
            'finalized': '📦 تکمیل شده',
        }
        design_status_value = design_status.status if design_status else 'pending_design'

        orders_data.append({
            'id': str(order.id),
            'order_number': str(order.id)[:8],
            'installation_title': order.installation.title if order.installation else '-',
            'material_title': order.material.title if order.material else '-',
            'length': round(length, 2),
            'width': round(width, 2),
            'area': round(area, 2),
            'price_per_m2': f"{price_per_m2:,.0f}",
            'total_price': f"{total_price:,.0f}",
            'customer_name': customer_name,
            'customer_mobile': getattr(order.user, 'mobile', '-') if order.user else '-',
            'design_status': design_status_value,
            'design_status_display': status_display_map.get(design_status_value, 'در انتظار طراحی'),
            'reject_count': reject_count,
            'final_design_preview': design_status.final_design_image.url if design_status and design_status.final_design_image else None,
            'final_design_psd': design_status.final_design_psd.url if design_status and design_status.final_design_psd else None,
            'design_type_display': dict(OrderMaterial.DESIGN_TYPES).get(order.design_type, ''),
            'plan_image': order.plan_image.url if order.plan_image else None,
            'customer_design_image': customer_design_image,
            'ready_template_image': ready_template_image,
            'ready_template_title': ready_template_title,
        })

    return JsonResponse({
        'status': 'success',
        'orders': orders_data,
        'pagination': {
            'current_page': page_obj.number,
            'total_pages': paginator.num_pages,
            'has_previous': page_obj.has_previous(),
            'has_next': page_obj.has_next(),
            'total_count': paginator.count,
        }
    })


@staff_member_required
def api_order_detail(request, order_id):
    order = get_object_or_404(
        OrderMaterial.objects.select_related(
            'installation', 'material', 'user', 'design_status', 'ready_template', 'pdf_document'
        ),
        id=order_id
    )

    design_status = getattr(order, 'design_status', None)
    review_history = order.review_history.all()
    reject_count = review_history.filter(action='user_reject').count()

    length = float(order.length) if order.length else 0
    width = float(order.width) if order.width else 0
    area = length * width

    price_per_m2 = order.installation.price if order.installation and order.installation.price else 0
    total_price = price_per_m2 * area

    customer_name = '-'
    if order.user:
        if hasattr(order.user, 'name') and hasattr(order.user, 'family') and order.user.name:
            customer_name = f'{order.user.name} {order.user.family}'
        else:
            customer_name = order.user.name or str(order.user)

    customer_design_image = None
    ready_template_image = None
    ready_template_title = None

    if order.plan_image:
        customer_design_image = order.plan_image.url
    if order.ready_template:
        ready_template_image = order.ready_template.image.url if order.ready_template.image else None
        ready_template_title = order.ready_template.title
    if order.pdf_document:
        ready_template_image = order.pdf_document.thumbnail.url if order.pdf_document.thumbnail else None
        ready_template_title = order.pdf_document.title

    review_history_data = []
    for h in review_history:
        review_history_data.append({
            'action': h.action,
            'action_display': h.get_action_display(),
            'message': h.message,
            'created_at': h.created_at.strftime('%Y/%m/%d %H:%M'),
        })

    return JsonResponse({
        'status': 'success',
        'order': {
            'id': str(order.id),
            'order_number': str(order.id)[:8],
            'installation_title': order.installation.title if order.installation else '-',
            'material_title': order.material.title if order.material else '-',
            'design_type_display': dict(OrderMaterial.DESIGN_TYPES).get(order.design_type, ''),
            'length': round(length, 2),
            'width': round(width, 2),
            'area': round(area, 2),
            'price_per_m2': f"{price_per_m2:,.0f}",
            'total_price': f"{total_price:,.0f}",
            'notes': order.notes,
            'plan_image': order.plan_image.url if order.plan_image else None,
            'customer_design_image': customer_design_image,
            'ready_template_image': ready_template_image,
            'ready_template_title': ready_template_title,
            'design_status': design_status.status if design_status else 'pending_design',
            'reject_count': reject_count,
            'final_design_image': design_status.final_design_image.url if design_status and design_status.final_design_image else None,
            'final_design_psd': design_status.final_design_psd.url if design_status and design_status.final_design_psd else None,
            'operator_message': design_status.operator_message if design_status else '',
            'review_history': review_history_data,
            'customer_name': customer_name,
            'customer_mobile': getattr(order.user, 'mobile', '-') if order.user else '-',
        }
    })


# ==================== پنل مشتری ====================

def customer_review_page(request, order_id):
    order = get_object_or_404(
        OrderMaterial.objects.select_related('installation', 'design_status'),
        id=order_id,
        user=request.user
    )

    if not hasattr(order, 'design_status') or order.design_status.status != 'ready_for_review':
        messages.error(request, 'هیچ طراحی برای بررسی وجود ندارد')
        return redirect('customer_dashboard')

    length = float(order.length) if order.length else 0
    width = float(order.width) if order.width else 0
    area = length * width
    price_per_m2 = order.installation.price if order.installation and order.installation.price else 0
    total_price = area * price_per_m2

    reject_count = order.review_history.filter(action='user_reject').count()
    can_reject = reject_count < 3

    context = {
        'order': order,
        'design': order.design_status,
        'reject_count': reject_count,
        'can_reject': can_reject,
        'remaining_reject': 3 - reject_count,
        'length': length,
        'width': width,
        'area': area,
        'price_per_m2': price_per_m2,
        'total_price': total_price,
    }
    return render(request, 'panel_app/review_design.html', context)


@csrf_exempt
@require_http_methods(["POST"])
def api_approve_design(request, order_id):
    try:
        data = json.loads(request.body)
        order = get_object_or_404(OrderMaterial, id=order_id, user=request.user)

        design_status = order.design_status
        if design_status.status != 'ready_for_review':
            return JsonResponse({'error': 'وضعیت سفارش برای تایید مناسب نیست'}, status=400)

        design_status.status = 'approved'
        design_status.save()

        OrderReviewHistory.objects.create(
            order=order,
            action='user_approve',
            message=data.get('message', ''),
            created_by=request.user
        )

        return JsonResponse({'success': True, 'message': 'طراحی با موفقیت تایید شد'})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)


@csrf_exempt
@require_http_methods(["POST"])
def api_reject_design(request, order_id):
    try:
        data = json.loads(request.body)
        order = get_object_or_404(OrderMaterial, id=order_id, user=request.user)

        design_status = order.design_status
        if design_status.status != 'ready_for_review':
            return JsonResponse({'error': 'وضعیت سفارش برای رد مناسب نیست'}, status=400)

        reject_count = order.review_history.filter(action='user_reject').count()

        if reject_count >= 3:
            return JsonResponse({'error': 'شما بیش از ۳ بار نمی‌توانید رد کنید'}, status=400)

        reason = data.get('reason', '')
        if not reason:
            return JsonResponse({'error': 'لطفاً دلیل رد را وارد کنید'}, status=400)

        if reject_count + 1 == 3:
            design_status.status = 'rejected'
            order.status = 'cancelled'
            order.save()
        else:
            design_status.status = 'pending_design'
            design_status.final_design_image = None
            design_status.final_design_psd = None
            design_status.operator_message = ''

        design_status.save()

        OrderReviewHistory.objects.create(
            order=order,
            action='user_reject',
            message=reason,
            reject_round=reject_count + 1,
            created_by=request.user
        )

        return JsonResponse({
            'success': True,
            'message': f'طراحی رد شد (مرحله {reject_count + 1} از ۳)',
            'reject_round': reject_count + 1,
            'is_final_reject': (reject_count + 1) >= 3
        })
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)