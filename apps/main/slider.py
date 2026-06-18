# views.py

import json
from django.http import JsonResponse
from django.views import View
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from .models import Slider

# views.py - اضافه کردن isdiscount به API
# views.py - اضافه کردن isdiscount به API

def slider_list_api(request):
    """API دریافت لیست اسلایدرها - GET"""
    if request.method == 'GET':
        now = timezone.now()
        sliders = Slider.objects.filter(
            is_active=True,
            start_date__lte=now
        ).exclude(
            end_date__lt=now
        ).order_by('order', '-created_at')

        data = []
        for slider in sliders:
            data.append({
                'id': slider.id,
                'title': slider.title,
                'description': slider.description,
                'link': slider.link,
                'image_pc': slider.image_pc.url if slider.image_pc else None,
                'image_mobile': slider.image_mobile.url if slider.image_mobile else None,
                'start_date': slider.start_date.strftime('%Y-%m-%d %H:%M:%S'),
                'end_date': slider.end_date.strftime('%Y-%m-%d %H:%M:%S') if slider.end_date else None,
                'order': slider.order,
                'is_available': slider.is_available(),
                'isdiscount': slider.isdiscount,  # اضافه کردن فیلد حراجی
            })

        return JsonResponse({
            'status': 'success',
            'data': data,
            'count': len(data)
        }, status=200)

    return JsonResponse({
        'status': 'error',
        'message': 'Method not allowed'
    }, status=405)


@csrf_exempt
def slider_create_api(request):
    """API ایجاد اسلایدر جدید - POST"""
    if request.method == 'POST':
        try:
            # دریافت داده‌ها
            data = json.loads(request.body)

            # ایجاد اسلایدر جدید
            slider = Slider.objects.create(
                title=data.get('title'),
                description=data.get('description', ''),
                link=data.get('link', ''),
                order=data.get('order', 0),
                is_active=data.get('is_active', True),
                start_date=data.get('start_date', timezone.now()),
                end_date=data.get('end_date', None)
            )

            return JsonResponse({
                'status': 'success',
                'message': 'اسلایدر با موفقیت ایجاد شد',
                'data': {
                    'id': slider.id,
                    'title': slider.title,
                    'order': slider.order
                }
            }, status=201)

        except Exception as e:
            return JsonResponse({
                'status': 'error',
                'message': str(e)
            }, status=400)

    return JsonResponse({
        'status': 'error',
        'message': 'Method not allowed'
    }, status=405)


@csrf_exempt
def slider_update_api(request, slider_id):
    """API بروزرسانی اسلایدر - PUT/POST"""
    try:
        slider = Slider.objects.get(id=slider_id)
    except Slider.DoesNotExist:
        return JsonResponse({
            'status': 'error',
            'message': 'اسلایدر یافت نشد'
        }, status=404)

    if request.method in ['PUT', 'POST']:
        try:
            data = json.loads(request.body)

            # بروزرسانی فیلدها
            if 'title' in data:
                slider.title = data['title']
            if 'description' in data:
                slider.description = data['description']
            if 'link' in data:
                slider.link = data['link']
            if 'order' in data:
                slider.order = data['order']
            if 'is_active' in data:
                slider.is_active = data['is_active']
            if 'start_date' in data:
                slider.start_date = data['start_date']
            if 'end_date' in data:
                slider.end_date = data['end_date']

            slider.save()

            return JsonResponse({
                'status': 'success',
                'message': 'اسلایدر با موفقیت بروزرسانی شد',
                'data': {
                    'id': slider.id,
                    'title': slider.title,
                    'order': slider.order
                }
            }, status=200)

        except Exception as e:
            return JsonResponse({
                'status': 'error',
                'message': str(e)
            }, status=400)

    return JsonResponse({
        'status': 'error',
        'message': 'Method not allowed'
    }, status=405)


@csrf_exempt
def slider_delete_api(request, slider_id):
    """API حذف اسلایدر - DELETE"""
    if request.method == 'DELETE':
        try:
            slider = Slider.objects.get(id=slider_id)
            slider.delete()

            return JsonResponse({
                'status': 'success',
                'message': 'اسلایدر با موفقیت حذف شد'
            }, status=200)

        except Slider.DoesNotExist:
            return JsonResponse({
                'status': 'error',
                'message': 'اسلایدر یافت نشد'
            }, status=404)
        except Exception as e:
            return JsonResponse({
                'status': 'error',
                'message': str(e)
            }, status=400)

    return JsonResponse({
        'status': 'error',
        'message': 'Method not allowed'
    }, status=405)


def slider_detail_api(request, slider_id):
    """API دریافت جزئیات یک اسلایدر - GET"""
    if request.method == 'GET':
        try:
            slider = Slider.objects.get(id=slider_id)

            data = {
                'id': slider.id,
                'title': slider.title,
                'description': slider.description,
                'link': slider.link,
                'image_pc': slider.image_pc.url if slider.image_pc else None,
                'image_mobile': slider.image_mobile.url if slider.image_mobile else None,
                'start_date': slider.start_date.strftime('%Y-%m-%d %H:%M:%S'),
                'end_date': slider.end_date.strftime('%Y-%m-%d %H:%M:%S') if slider.end_date else None,
                'order': slider.order,
                'is_active': slider.is_active,
                'is_available': slider.is_available(),
                'created_at': slider.created_at.strftime('%Y-%m-%d %H:%M:%S'),
                'updated_at': slider.updated_at.strftime('%Y-%m-%d %H:%M:%S')
            }

            return JsonResponse({
                'status': 'success',
                'data': data
            }, status=200)

        except Slider.DoesNotExist:
            return JsonResponse({
                'status': 'error',
                'message': 'اسلایدر یافت نشد'
            }, status=404)

    return JsonResponse({
        'status': 'error',
        'message': 'Method not allowed'
    }, status=405)