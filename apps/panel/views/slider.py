# apps/slider/views.py

from django.shortcuts import render, get_object_or_404
from django.contrib.admin.views.decorators import staff_member_required
from django.views.decorators.http import require_http_methods
from django.http import JsonResponse
from django.core.paginator import Paginator
from django.utils import timezone
from django.core.files.base import ContentFile
from django.conf import settings

from apps.main.models import Slider
import json
import os
from datetime import datetime
import jdatetime


# ========== کمکی ==========

def _parse_jalali_to_dt(jalali_str, default_hour=0, default_minute=0):
    """'1403-01-01' + ساعت/دقیقه → datetime aware یا None"""
    if not jalali_str:
        return None
    try:
        parts = jalali_str.strip().split('-')
        if len(parts) != 3:
            return None
        year, month, day = map(int, parts)
        g = jdatetime.date(year, month, day).togregorian()
        dt = datetime(g.year, g.month, g.day,
                      int(default_hour), int(default_minute))
        return timezone.make_aware(dt, timezone.get_current_timezone())
    except Exception:
        return None


def _dt_to_jalali(dt):
    if not dt:
        return ''
    try:
        return jdatetime.datetime.fromgregorian(datetime=dt).strftime('%Y-%m-%d')
    except Exception:
        return ''


def convert_to_jalali(date):
    if not date:
        return None
    try:
        return jdatetime.datetime.fromgregorian(datetime=date).strftime('%Y/%m/%d %H:%M')
    except Exception:
        return str(date)


def _get_int(request, key, default=0):
    try:
        return int(request.POST.get(key, default))
    except (TypeError, ValueError):
        return default


# ========== پنل و لیست ==========

@staff_member_required
def admin_slider_panel(request):
    return render(request, 'panel_app/dashboard/admin_slider_panel.html')


@staff_member_required
def api_slider_list(request):
    sliders = Slider.objects.all().order_by('order', '-created_at')

    search = request.GET.get('search', '').strip()
    if search:
        sliders = sliders.filter(title__icontains=search)

    is_active = request.GET.get('is_active', '')
    if is_active in ('true', 'false'):
        sliders = sliders.filter(is_active=(is_active == 'true'))

    page = request.GET.get('page', 1)
    try:
        page = int(page)
    except (TypeError, ValueError):
        page = 1
    page_size = int(request.GET.get('page_size', 10))

    paginator = Paginator(sliders, page_size)
    try:
        sliders_page = paginator.page(page)
    except Exception:
        sliders_page = paginator.page(1)

    sliders_list = []
    for s in sliders_page:
        sliders_list.append({
            'id': s.id,
            'title': s.title,
            'description': (s.description or '')[:100],
            'is_active': s.is_active,
            'is_active_display': 'فعال' if s.is_active else 'غیرفعال',
            'is_active_badge': 'badge-success' if s.is_active else 'badge-danger',
            'is_available': s.is_available(),
            'image_pc_url': s.get_image_pc_url(),
            'image_mobile_url': s.get_image_mobile_url(),
            'link': s.link or '',
            'order': s.order,
            'start_date': convert_to_jalali(s.start_date) if s.start_date else None,
            'end_date': convert_to_jalali(s.end_date) if s.end_date else None,
            'created_at': convert_to_jalali(s.created_at),
        })

    stats = {
        'total': Slider.objects.count(),
        'active': Slider.objects.filter(is_active=True).count(),
        'inactive': Slider.objects.filter(is_active=False).count(),
        'available_now': sum(1 for s in Slider.objects.filter(is_active=True) if s.is_available()),
    }

    return JsonResponse({
        'status': 'success',
        'sliders': sliders_list,
        'pagination': {
            'current_page': sliders_page.number,
            'total_pages': paginator.num_pages,
            'total_items': paginator.count,
            'has_next': sliders_page.has_next(),
            'has_previous': sliders_page.has_previous(),
        },
        'stats': stats,
    })


@staff_member_required
def api_slider_detail(request, slider_id):
    s = get_object_or_404(Slider, id=slider_id)
    return JsonResponse({
        'status': 'success',
        'slider': {
            'id': s.id,
            'title': s.title,
            'description': s.description or '',
            'is_active': s.is_active,
            'image_pc_url': s.image_pc.url if s.image_pc else None,
            'image_mobile_url': s.image_mobile.url if s.image_mobile else None,
            'link': s.link or '',
            'order': s.order,
            'start_date': s.start_date.isoformat() if s.start_date else None,
            'end_date': s.end_date.isoformat() if s.end_date else None,
            'start_date_jalali': _dt_to_jalali(s.start_date),
            'end_date_jalali': _dt_to_jalali(s.end_date),
        }
    })


# ========== ایجاد ==========

@staff_member_required
@require_http_methods(['POST'])
def api_slider_create(request):
    try:
        title = (request.POST.get('title') or '').strip()
        if not title:
            return JsonResponse({'status': 'error', 'message': 'عنوان الزامی است'}, status=400)

        start_dt = _parse_jalali_to_dt(
            request.POST.get('start_date', ''),
            _get_int(request, 'start_hour', 0),
            _get_int(request, 'start_minute', 0),
        ) or timezone.now()

        end_dt = _parse_jalali_to_dt(
            request.POST.get('end_date', ''),
            _get_int(request, 'end_hour', 23),
            _get_int(request, 'end_minute', 59),
        )

        slider = Slider.objects.create(
            title=title,
            description=request.POST.get('description', ''),
            is_active=request.POST.get('is_active', 'true') == 'true',
            link=request.POST.get('link', ''),
            order=_get_int(request, 'order', 0),
            start_date=start_dt,
            end_date=end_dt,
        )

        if request.FILES.get('image_pc'):
            f = request.FILES['image_pc']
            ext = os.path.splitext(f.name)[1]
            fn = f'slider/pc/{timezone.now().year}/{timezone.now().month:02d}/slider_{slider.id}_pc{ext}'
            slider.image_pc.save(fn, ContentFile(f.read()), save=False)

        if request.FILES.get('image_mobile'):
            f = request.FILES['image_mobile']
            ext = os.path.splitext(f.name)[1]
            fn = f'slider/mobile/{timezone.now().year}/{timezone.now().month:02d}/slider_{slider.id}_mobile{ext}'
            slider.image_mobile.save(fn, ContentFile(f.read()), save=False)

        slider.save()
        return JsonResponse({'status': 'success', 'message': 'اسلایدر ایجاد شد', 'slider_id': slider.id})
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=400)


# ========== بروزرسانی ==========

@staff_member_required
@require_http_methods(['POST'])
def api_slider_update(request, slider_id):
    try:
        s = get_object_or_404(Slider, id=slider_id)

        if 'title' in request.POST:
            s.title = (request.POST.get('title') or '').strip() or s.title
        if 'description' in request.POST:
            s.description = request.POST.get('description', '')
        if 'link' in request.POST:
            s.link = request.POST.get('link', '')
        if 'order' in request.POST:
            s.order = _get_int(request, 'order', s.order)
        if 'is_active' in request.POST:
            s.is_active = request.POST.get('is_active') == 'true'

        # تاریخ شروع
        if request.POST.get('start_date'):
            start_dt = _parse_jalali_to_dt(
                request.POST.get('start_date'),
                _get_int(request, 'start_hour', 0),
                _get_int(request, 'start_minute', 0),
            )
            if start_dt:
                s.start_date = start_dt

        # تاریخ پایان
        if request.POST.get('end_date'):
            end_dt = _parse_jalali_to_dt(
                request.POST.get('end_date'),
                _get_int(request, 'end_hour', 23),
                _get_int(request, 'end_minute', 59),
            )
            if end_dt:
                s.end_date = end_dt
        elif request.POST.get('clear_end_date') == 'true':
            s.end_date = None

        # آپلود عکس PC
        if request.FILES.get('image_pc'):
            if s.image_pc:
                s.image_pc.delete(save=False)
            f = request.FILES['image_pc']
            ext = os.path.splitext(f.name)[1]
            fn = f'slider/pc/{timezone.now().year}/{timezone.now().month:02d}/slider_{s.id}_pc{ext}'
            s.image_pc.save(fn, ContentFile(f.read()), save=False)

        # آپلود عکس موبایل
        if request.FILES.get('image_mobile'):
            if s.image_mobile:
                s.image_mobile.delete(save=False)
            f = request.FILES['image_mobile']
            ext = os.path.splitext(f.name)[1]
            fn = f'slider/mobile/{timezone.now().year}/{timezone.now().month:02d}/slider_{s.id}_mobile{ext}'
            s.image_mobile.save(fn, ContentFile(f.read()), save=False)

        s.save()
        return JsonResponse({'status': 'success', 'message': 'اسلایدر بروزرسانی شد'})
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=400)


# ========== حذف / toggle / reorder ==========

@staff_member_required
@require_http_methods(['POST'])
def api_slider_delete(request, slider_id):
    try:
        s = get_object_or_404(Slider, id=slider_id)
        if s.image_pc:
            s.image_pc.delete(save=False)
        if s.image_mobile:
            s.image_mobile.delete(save=False)
        s.delete()
        return JsonResponse({'status': 'success', 'message': 'اسلایدر حذف شد'})
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=400)


@staff_member_required
@require_http_methods(['POST'])
def api_slider_toggle_status(request, slider_id):
    try:
        s = get_object_or_404(Slider, id=slider_id)
        s.is_active = not s.is_active
        s.save(update_fields=['is_active', 'updated_at'])
        return JsonResponse({'status': 'success', 'message': 'وضعیت تغییر کرد', 'is_active': s.is_active})
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=400)


@staff_member_required
@require_http_methods(['POST'])
def api_slider_reorder(request):
    try:
        data = json.loads(request.body)
        for item in data.get('orders', []):
            Slider.objects.filter(id=item['id']).update(order=item['order'])
        return JsonResponse({'status': 'success', 'message': 'ترتیب ذخیره شد'})
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=400)