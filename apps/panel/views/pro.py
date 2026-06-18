# apps/pro/views.py

from django.shortcuts import render, get_object_or_404
from django.contrib.admin.views.decorators import staff_member_required
from django.views.decorators.http import require_http_methods
from django.http import JsonResponse
from django.db.models import Q, Sum, Count, Value, DecimalField
from django.db.models.functions import Coalesce
from django.utils import timezone
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.views.decorators.csrf import csrf_exempt

from apps.pro.models import (
    OrderMaterial, Installation, InstallationMaterial,
    MaterialPDF, ReadyTemplate, TemplateGallery
)

import jdatetime
from datetime import datetime, timedelta
import json
from decimal import Decimal


@staff_member_required
def admin_print_orders_panel(request):
    """نمایش پنل مدیریت سفارشات چاپی"""
    return render(request, 'panel_app/dashboard/admin_print_orders_panel.html')


@staff_member_required
def api_print_orders_list(request):
    """
    API دریافت لیست سفارشات چاپی با فیلترها و جستجوی پیشرفته
    """
    orders = OrderMaterial.objects.select_related(
        'user', 'installation', 'material', 'pdf_document', 'ready_template'
    ).all()

    # ========== فیلتر بر اساس تاریخ ایرانی ==========
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

    # ========== فیلتر بر اساس قیمت ==========
    min_price = request.GET.get('min_price', '')
    max_price = request.GET.get('max_price', '')

    if min_price:
        try:
            orders = orders.filter(total_price__gte=Decimal(str(min_price)))
        except:
            pass
    if max_price:
        try:
            orders = orders.filter(total_price__lte=Decimal(str(max_price)))
        except:
            pass

    # ========== فیلتر بر اساس وضعیت ==========
    status = request.GET.get('status', '')
    if status:
        valid_statuses = ['pending', 'confirmed', 'processing', 'ready', 'delivered', 'cancelled']
        if status in valid_statuses:
            orders = orders.filter(status=status)

    # ========== فیلتر بر اساس نوع طراحی ==========
    design_type = request.GET.get('design_type', '')
    if design_type:
        valid_types = ['ready', 'custom', 'pdf']
        if design_type in valid_types:
            orders = orders.filter(design_type=design_type)

    # ========== فیلتر بر اساس نصبیات ==========
    installation_id = request.GET.get('installation_id', '')
    if installation_id:
        orders = orders.filter(installation_id=installation_id)

    # ========== فیلتر بر اساس جنس ==========
    material_id = request.GET.get('material_id', '')
    if material_id:
        orders = orders.filter(material_id=material_id)

    # ========== جستجوی پیشرفته ==========
    search = request.GET.get('search', '')
    if search:
        orders = orders.filter(
            Q(id__icontains=search) |
            Q(user__mobileNumber__icontains=search) |
            Q(user__name__icontains=search) |
            Q(user__family__icontains=search) |
            Q(installation__title__icontains=search) |
            Q(material__title__icontains=search) |
            Q(notes__icontains=search) |
            Q(pdf_document__code__icontains=search) |
            Q(pdf_document__title__icontains=search) |
            Q(ready_template__title__icontains=search)
        ).distinct()

    # ========== مرتب‌سازی ==========
    sort_by = request.GET.get('sort_by', '-created_at')
    allowed_sorts = ['created_at', '-created_at', 'total_price', '-total_price', 'status']
    if sort_by in allowed_sorts:
        orders = orders.order_by(sort_by)
    else:
        orders = orders.order_by('-created_at')

    # ========== Pagination ==========
    page = request.GET.get('page', 1)
    page_size = int(request.GET.get('page_size', 20))
    paginator = Paginator(orders, page_size)

    try:
        orders_page = paginator.page(page)
    except PageNotAnInteger:
        orders_page = paginator.page(1)
    except EmptyPage:
        orders_page = paginator.page(paginator.num_pages)

    # ========== آمار کلی ==========
    total_amount = orders.aggregate(
        total=Coalesce(Sum('total_price'), Value(0, output_field=DecimalField()))
    )['total']

    stats = {
        'total': orders.count(),
        'pending': orders.filter(status='pending').count(),
        'confirmed': orders.filter(status='confirmed').count(),
        'processing': orders.filter(status='processing').count(),
        'ready': orders.filter(status='ready').count(),
        'delivered': orders.filter(status='delivered').count(),
        'cancelled': orders.filter(status='cancelled').count(),
        'total_amount': format_price(total_amount),
        'ready_design': orders.filter(design_type='ready').count(),
        'custom_design': orders.filter(design_type='custom').count(),
        'pdf_design': orders.filter(design_type='pdf').count(),
    }

    # ========== ساخت لیست سفارشات ==========
    orders_list = []
    for order in orders_page:
        orders_list.append({
            'id': str(order.id),
            'order_id_display': str(order.id)[:8],
            'installation_title': order.installation.title if order.installation else '-',
            'material_title': order.material.title if order.material else '-',
            'customer_name': get_customer_full_name(order.user),
            'customer_mobile': order.user.mobileNumber if order.user else '-',
            'customer_email': order.user.email if order.user else '-',

            # ابعاد و مساحت
            'length': float(order.length),
            'width': float(order.width),
            'area': order.area,
            'area_display': f"{order.area:,.2f} متر مربع",

            # قیمت
            'total_price': format_price(order.total_price),
            'total_price_raw': float(order.total_price) if order.total_price else 0,

            # نوع طراحی
            'design_type': order.design_type,
            'design_type_display': dict(OrderMaterial.DESIGN_TYPES).get(order.design_type, ''),
            'design_type_badge_class': get_design_type_class(order.design_type),

            # اطلاعات طرح (بر اساس نوع)
            'design_info': get_design_info(order),

            # وضعیت
            'status': order.status,
            'status_display': dict(OrderMaterial.STATUS_CHOICES).get(order.status, ''),
            'status_badge_class': get_status_badge_class(order.status),

            # عکس پلن
            'has_plan_image': bool(order.plan_image),
            'plan_image_url': order.plan_image.url if order.plan_image else None,

            # توضیحات
            'notes': order.notes,

            # تاریخ‌ها
            'created_at': format_jalali_date(order.created_at),
            'created_at_raw': order.created_at.isoformat() if order.created_at else None,
            'updated_at': format_jalali_date(order.updated_at),
        })

    # دریافت لیست نصبیات و جنس‌ها برای فیلتر
    installations = list(Installation.objects.filter(is_active=True).values('id', 'title'))
    materials = list(InstallationMaterial.objects.filter(is_active=True).values('id', 'title', 'installation_id'))

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
        'filters_data': {
            'installations': installations,
            'materials': materials,
        }
    })


@staff_member_required
def api_print_order_detail(request, order_id):
    """دریافت جزئیات کامل یک سفارش چاپی"""
    try:
        order = get_object_or_404(
            OrderMaterial.objects.select_related(
                'user', 'installation', 'material', 'pdf_document', 'ready_template'
            ),
            id=order_id
        )

        # دریافت گالری طرح آماده (اگر وجود داشته باشد)
        template_gallery = []
        if order.ready_template:
            template_gallery = list(order.ready_template.gallery.all().values('id', 'image', 'title', 'order'))

        # اطلاعات PDF (اگر وجود داشته باشد)
        pdf_info = None
        if order.pdf_document:
            pdf_info = {
                'code': order.pdf_document.code,
                'title': order.pdf_document.title,
                'file_url': order.pdf_document.pdf_file.url if order.pdf_document.pdf_file else None,
                'thumbnail': order.pdf_document.thumbnail.url if order.pdf_document.thumbnail else None,
            }

        return JsonResponse({
            'status': 'success',
            'order': {
                'id': str(order.id),
                'order_number': str(order.id)[:8],
                'installation': {
                    'id': order.installation.id if order.installation else None,
                    'title': order.installation.title if order.installation else '-',
                    'price': format_price(order.installation.price) if order.installation else '-',
                },
                'material': {
                    'id': order.material.id if order.material else None,
                    'title': order.material.title if order.material else '-',
                    'price_multiplier': float(order.material.price_multiplier) if order.material else 1.0,
                },
                'customer': {
                    'id': order.user.id if order.user else None,
                    'name': get_customer_full_name(order.user),
                    'mobile': order.user.mobileNumber if order.user else '-',
                    'email': order.user.email if order.user else '-',
                },
                'dimensions': {
                    'length': float(order.length),
                    'width': float(order.width),
                    'area': order.area,
                    'area_display': f"{order.area:,.2f} متر مربع",
                },
                'design_type': {
                    'type': order.design_type,
                    'display': dict(OrderMaterial.DESIGN_TYPES).get(order.design_type, ''),
                },
                'design_details': get_design_details(order),
                'ready_template_gallery': template_gallery,
                'pdf_info': pdf_info,
                'plan_image': {
                    'has': bool(order.plan_image),
                    'url': order.plan_image.url if order.plan_image else None,
                },
                'amounts': {
                    'subtotal': format_price(order.total_price),
                    'final_payable': format_price(order.total_price),
                    'discount_amount': '۰ تومان',
                    'shipping_cost': '۰ تومان',
                    'used_from_wallet': '۰ تومان',
                },
                'status': order.status,
                'status_display': dict(OrderMaterial.STATUS_CHOICES).get(order.status, ''),
                'status_badge_class': get_status_badge_class(order.status),
                'notes': order.notes,
                'items_count': 1,
                'items': [{
                    'product_title': order.installation.title if order.installation else 'محصول',
                    'quantity': 1,
                    'total': format_price(order.total_price),
                }],
                'address': {
                    'full_address': '-',
                    'province': '-',
                    'city': '-',
                },
                'created_at': format_jalali_date(order.created_at),
                'created_at_time': order.created_at.strftime('%H:%M:%S') if order.created_at else None,
                'updated_at': format_jalali_date(order.updated_at),
            }
        })

    except OrderMaterial.DoesNotExist:
        return JsonResponse({'status': 'error', 'message': 'سفارش یافت نشد'}, status=404)


@staff_member_required
@csrf_exempt
@require_http_methods(['POST'])
def api_update_print_order_status(request):
    """تغییر وضعیت سفارش چاپی"""
    try:
        data = json.loads(request.body)
        order_id = data.get('order_id')
        new_status = data.get('status')
        note = data.get('note', '')

        if not order_id or not new_status:
            return JsonResponse({'status': 'error', 'message': 'شناسه سفارش و وضعیت جدید الزامی است'}, status=400)

        order = get_object_or_404(OrderMaterial, id=order_id)
        old_status = order.status

        valid_statuses = ['pending', 'confirmed', 'processing', 'ready', 'delivered', 'cancelled']
        if new_status not in valid_statuses:
            return JsonResponse({'status': 'error', 'message': 'وضعیت نامعتبر است'}, status=400)

        order.status = new_status
        order.save(update_fields=['status', 'updated_at'])

        # اگر سفارش مرتبط با Order اصلی وجود دارد، وضعیت آن را هم به‌روز کن
        if hasattr(order, 'order') and order.order:
            try:
                from apps.order.models import OrderStatus
                related_order = order.order
                if new_status == 'delivered':
                    related_order.status = OrderStatus.DELIVERED.value
                elif new_status == 'confirmed':
                    related_order.status = OrderStatus.PAID.value
                elif new_status == 'cancelled':
                    related_order.status = OrderStatus.CANCELLED.value
                related_order.save(update_fields=['status'])
            except:
                pass

        return JsonResponse({
            'status': 'success',
            'message': 'وضعیت سفارش با موفقیت تغییر کرد',
            'new_status': new_status,
            'new_status_display': dict(OrderMaterial.STATUS_CHOICES).get(new_status),
            'badge_class': get_status_badge_class(new_status)
        })

    except OrderMaterial.DoesNotExist:
        return JsonResponse({'status': 'error', 'message': 'سفارش یافت نشد'}, status=404)
    except json.JSONDecodeError:
        return JsonResponse({'status': 'error', 'message': 'داده‌های ارسالی نامعتبر است'}, status=400)
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=400)


@staff_member_required
def api_print_orders_chart_data(request):
    """داده‌های نمودار برای سفارشات چاپی"""
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

        orders_in_month = OrderMaterial.objects.filter(created_at__gte=month_start, created_at__lt=month_end)

        total_amount = orders_in_month.aggregate(
            total=Coalesce(Sum('total_price'), Value(0, output_field=DecimalField()))
        )['total']

        months_data.append({
            'month': month_name,
            'orders_count': orders_in_month.count(),
            'total_amount': float(total_amount),
            'confirmed_orders': orders_in_month.filter(status='confirmed').count(),
            'delivered_orders': orders_in_month.filter(status='delivered').count(),
        })

    # آمار وضعیت‌ها
    status_stats = []
    total_orders = OrderMaterial.objects.count()
    for status_code, status_name in OrderMaterial.STATUS_CHOICES:
        count = OrderMaterial.objects.filter(status=status_code).count()
        status_stats.append({
            'status': status_code,
            'label': status_name,
            'count': count,
            'percentage': round((count / total_orders) * 100, 1) if total_orders > 0 else 0,
        })

    # آمار نوع طراحی
    design_stats = []
    total_orders = OrderMaterial.objects.count()
    for design_code, design_name in OrderMaterial.DESIGN_TYPES:
        count = OrderMaterial.objects.filter(design_type=design_code).count()
        design_stats.append({
            'type': design_code,
            'label': design_name,
            'count': count,
            'percentage': round((count / total_orders) * 100, 1) if total_orders > 0 else 0,
        })

    return JsonResponse({
        'status': 'success',
        'monthly_data': months_data,
        'status_stats': status_stats,
        'design_stats': design_stats,
    })


# ========== توابع کمکی ==========

def get_customer_full_name(user):
    if not user:
        return 'کاربر مهمان'
    name = f"{user.name or ''} {user.family or ''}".strip()
    return name if name else (user.mobileNumber or 'کاربر')


def get_design_type_class(design_type):
    classes = {
        'ready': 'badge-primary',
        'custom': 'badge-warning',
        'pdf': 'badge-info',
    }
    return classes.get(design_type, 'badge-secondary')


def get_status_badge_class(status):
    classes = {
        'pending': 'badge-warning',
        'confirmed': 'badge-info',
        'processing': 'badge-primary',
        'ready': 'badge-success',
        'delivered': 'badge-success',
        'cancelled': 'badge-danger',
    }
    return classes.get(status, 'badge-secondary')


def get_design_info(order):
    """دریافت اطلاعات خلاصه طرح"""
    if order.design_type == 'ready' and order.ready_template:
        return {
            'type': 'ready',
            'title': order.ready_template.title,
            'image': order.ready_template.image.url if order.ready_template.image else None,
            'dimensions': f"{order.ready_template.width}×{order.ready_template.height} سانتی‌متر",
        }
    elif order.design_type == 'pdf' and order.pdf_document:
        return {
            'type': 'pdf',
            'code': order.pdf_document.code,
            'title': order.pdf_document.title,
        }
    elif order.design_type == 'custom':
        return {
            'type': 'custom',
            'has_plan': bool(order.plan_image),
            'message': 'طراحی اختصاصی مشتری',
        }
    return {'type': 'unknown', 'message': 'اطلاعاتی موجود نیست'}


def get_design_details(order):
    """دریافت جزئیات کامل طرح"""
    if order.design_type == 'ready' and order.ready_template:
        return {
            'template_id': str(order.ready_template.id),
            'title': order.ready_template.title,
            'description': order.ready_template.description,
            'image': order.ready_template.image.url if order.ready_template.image else None,
            'original_width': order.ready_template.width,
            'original_height': order.ready_template.height,
        }
    elif order.design_type == 'pdf' and order.pdf_document:
        return {
            'pdf_id': order.pdf_document.id,
            'code': order.pdf_document.code,
            'title': order.pdf_document.title,
            'file_url': order.pdf_document.pdf_file.url if order.pdf_document.pdf_file else None,
        }
    elif order.design_type == 'custom':
        return {
            'has_plan_image': bool(order.plan_image),
            'plan_image_url': order.plan_image.url if order.plan_image else None,
            'notes': order.notes,
        }
    return {}


def format_price(amount):
    if amount is None:
        return '۰ تومان'
    try:
        return f"{int(float(amount)):,}".replace(',', '٬') + ' تومان'
    except:
        return '۰ تومان'


def format_jalali_date(date):
    if not date:
        return None
    try:
        jalali = jdatetime.datetime.fromgregorian(datetime=date)
        return jalali.strftime('%Y/%m/%d')
    except:
        return date.strftime('%Y-%m-%d') if date else None