# apps/slider/views.py

from django.shortcuts import render, get_object_or_404
from django.contrib.admin.views.decorators import staff_member_required
from django.views.decorators.http import require_http_methods
from django.http import JsonResponse
from django.core.paginator import Paginator
from django.utils import timezone
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
from django.conf import settings

from apps.main.models import Slider
import json
import os
from datetime import datetime
import jdatetime


@staff_member_required
def admin_slider_panel(request):
    """پنل مدیریت اسلایدر"""
    return render(request, 'panel_app/dashboard/admin_slider_panel.html')


@staff_member_required
def api_slider_list(request):
    """API دریافت لیست اسلایدرها"""
    sliders = Slider.objects.all().order_by('order', '-created_at')

    search = request.GET.get('search', '')
    if search:
        sliders = sliders.filter(title__icontains=search)

    is_active = request.GET.get('is_active', '')
    if is_active:
        if is_active == 'true':
            sliders = sliders.filter(is_active=True)
        elif is_active == 'false':
            sliders = sliders.filter(is_active=False)

    page = request.GET.get('page', 1)
    page_size = int(request.GET.get('page_size', 10))
    paginator = Paginator(sliders, page_size)

    try:
        sliders_page = paginator.page(page)
    except:
        sliders_page = paginator.page(1)

    sliders_list = []
    for slider in sliders_page:
        sliders_list.append({
            'id': slider.id,
            'title': slider.title,
            'description': slider.description[:100] if slider.description else '',
            'is_active': slider.is_active,
            'is_active_display': 'فعال' if slider.is_active else 'غیرفعال',
            'is_active_badge': 'badge-success' if slider.is_active else 'badge-danger',
            'is_available': slider.is_available(),
            'image_pc_url': slider.get_image_pc_url(),
            'image_mobile_url': slider.get_image_mobile_url(),
            'link': slider.link,
            'order': slider.order,
            'start_date': convert_to_jalali(slider.start_date) if slider.start_date else None,
            'end_date': convert_to_jalali(slider.end_date) if slider.end_date else None,
            'created_at': convert_to_jalali(slider.created_at),
        })

    stats = {
        'total': Slider.objects.count(),
        'active': Slider.objects.filter(is_active=True).count(),
        'inactive': Slider.objects.filter(is_active=False).count(),
        'available_now': Slider.objects.filter(is_active=True).count(),
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
    """دریافت جزئیات یک اسلایدر"""
    slider = get_object_or_404(Slider, id=slider_id)

    return JsonResponse({
        'status': 'success',
        'slider': {
            'id': slider.id,
            'title': slider.title,
            'description': slider.description,
            'is_active': slider.is_active,
            'image_pc_url': slider.image_pc.url if slider.image_pc else None,
            'image_mobile_url': slider.image_mobile.url if slider.image_mobile else None,
            'link': slider.link,
            'order': slider.order,
            'start_date': slider.start_date.isoformat() if slider.start_date else None,
            'end_date': slider.end_date.isoformat() if slider.end_date else None,
        }
    })


@staff_member_required
@require_http_methods(['POST'])
def api_slider_create(request):
    """ایجاد اسلایدر جدید با آپلود عکس"""
    try:
        title = request.POST.get('title')
        description = request.POST.get('description', '')
        link = request.POST.get('link', '')
        order = request.POST.get('order', 0)
        is_active = request.POST.get('is_active', 'true') == 'true'

        # دریافت تاریخ‌های شمسی و تبدیل به میلادی
        start_date_jalali = request.POST.get('start_date', '')
        end_date_jalali = request.POST.get('end_date', '')

        start_date = timezone.now()
        if start_date_jalali:
            try:
                year, month, day = map(int, start_date_jalali.split('-'))
                hour = int(request.POST.get('start_hour', 0))
                minute = int(request.POST.get('start_minute', 0))
                gregorian_date = jdatetime.date(year, month, day).togregorian()
                start_date = datetime(gregorian_date.year, gregorian_date.month, gregorian_date.day, hour, minute)
            except:
                start_date = timezone.now()

        end_date = None
        if end_date_jalali:
            try:
                year, month, day = map(int, end_date_jalali.split('-'))
                hour = int(request.POST.get('end_hour', 23))
                minute = int(request.POST.get('end_minute', 59))
                gregorian_date = jdatetime.date(year, month, day).togregorian()
                end_date = datetime(gregorian_date.year, gregorian_date.month, gregorian_date.day, hour, minute)
            except:
                end_date = None

        slider = Slider.objects.create(
            title=title,
            description=description,
            is_active=is_active,
            link=link,
            order=order,
            start_date=start_date,
            end_date=end_date,
        )

        # آپلود عکس PC
        if request.FILES.get('image_pc'):
            image_pc = request.FILES['image_pc']
            ext = os.path.splitext(image_pc.name)[1]
            filename = f'slider/pc/{timezone.now().year}/{timezone.now().month:02d}/slider_{slider.id}_pc{ext}'
            slider.image_pc.save(filename, ContentFile(image_pc.read()), save=True)

        # آپلود عکس موبایل
        if request.FILES.get('image_mobile'):
            image_mobile = request.FILES['image_mobile']
            ext = os.path.splitext(image_mobile.name)[1]
            filename = f'slider/mobile/{timezone.now().year}/{timezone.now().month:02d}/slider_{slider.id}_mobile{ext}'
            slider.image_mobile.save(filename, ContentFile(image_mobile.read()), save=True)

        slider.save()

        return JsonResponse({
            'status': 'success',
            'message': 'اسلایدر با موفقیت ایجاد شد',
            'slider_id': slider.id
        })

    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=400)


@staff_member_required
@require_http_methods(['POST'])
def api_slider_update(request, slider_id):
    """بروزرسانی اسلایدر با آپلود عکس"""
    try:
        slider = get_object_or_404(Slider, id=slider_id)

        slider.title = request.POST.get('title', slider.title)
        slider.description = request.POST.get('description', slider.description)
        slider.is_active = request.POST.get('is_active', 'true') == 'true'
        slider.link = request.POST.get('link', slider.link)
        slider.order = request.POST.get('order', slider.order)

        # دریافت تاریخ‌های شمسی و تبدیل به میلادی
        start_date_jalali = request.POST.get('start_date', '')
        end_date_jalali = request.POST.get('end_date', '')

        if start_date_jalali:
            try:
                year, month, day = map(int, start_date_jalali.split('-'))
                hour = int(request.POST.get('start_hour', 0))
                minute = int(request.POST.get('start_minute', 0))
                gregorian_date = jdatetime.date(year, month, day).togregorian()
                slider.start_date = datetime(gregorian_date.year, gregorian_date.month, gregorian_date.day, hour, minute)
            except:
                pass

        if end_date_jalali:
            try:
                year, month, day = map(int, end_date_jalali.split('-'))
                hour = int(request.POST.get('end_hour', 23))
                minute = int(request.POST.get('end_minute', 59))
                gregorian_date = jdatetime.date(year, month, day).togregorian()
                slider.end_date = datetime(gregorian_date.year, gregorian_date.month, gregorian_date.day, hour, minute)
            except:
                slider.end_date = None
        else:
            slider.end_date = None

        # آپلود عکس PC (در صورت وجود)
        if request.FILES.get('image_pc'):
            if slider.image_pc:
                slider.image_pc.delete()
            image_pc = request.FILES['image_pc']
            ext = os.path.splitext(image_pc.name)[1]
            filename = f'slider/pc/{timezone.now().year}/{timezone.now().month:02d}/slider_{slider.id}_pc{ext}'
            slider.image_pc.save(filename, ContentFile(image_pc.read()), save=True)

        # آپلود عکس موبایل (در صورت وجود)
        if request.FILES.get('image_mobile'):
            if slider.image_mobile:
                slider.image_mobile.delete()
            image_mobile = request.FILES['image_mobile']
            ext = os.path.splitext(image_mobile.name)[1]
            filename = f'slider/mobile/{timezone.now().year}/{timezone.now().month:02d}/slider_{slider.id}_mobile{ext}'
            slider.image_mobile.save(filename, ContentFile(image_mobile.read()), save=True)

        slider.save()

        return JsonResponse({
            'status': 'success',
            'message': 'اسلایدر با موفقیت بروزرسانی شد'
        })

    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=400)


@staff_member_required
@require_http_methods(['POST'])
def api_slider_delete(request, slider_id):
    """حذف اسلایدر به همراه عکس‌ها"""
    try:
        slider = get_object_or_404(Slider, id=slider_id)

        # حذف فایل‌های عکس
        if slider.image_pc:
            slider.image_pc.delete()
        if slider.image_mobile:
            slider.image_mobile.delete()

        slider.delete()

        return JsonResponse({
            'status': 'success',
            'message': 'اسلایدر با موفقیت حذف شد'
        })

    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=400)


@staff_member_required
@require_http_methods(['POST'])
def api_slider_toggle_status(request, slider_id):
    """تغییر وضعیت فعال/غیرفعال اسلایدر"""
    try:
        slider = get_object_or_404(Slider, id=slider_id)
        slider.is_active = not slider.is_active
        slider.save()

        return JsonResponse({
            'status': 'success',
            'message': 'وضعیت اسلایدر تغییر کرد',
            'is_active': slider.is_active
        })

    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=400)


@staff_member_required
@require_http_methods(['POST'])
def api_slider_reorder(request):
    """تغییر ترتیب اسلایدرها"""
    try:
        data = json.loads(request.body)
        orders = data.get('orders', [])

        for item in orders:
            Slider.objects.filter(id=item['id']).update(order=item['order'])

        return JsonResponse({
            'status': 'success',
            'message': 'ترتیب اسلایدرها با موفقیت ذخیره شد'
        })

    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=400)


# ========== توابع کمکی ==========

def convert_to_jalali(date):
    """تبدیل تاریخ میلادی به شمسی"""
    if not date:
        return None
    try:
        jalali_date = jdatetime.datetime.fromgregorian(datetime=date)
        return jalali_date.strftime('%Y/%m/%d %H:%M')
    except:
        return str(date)