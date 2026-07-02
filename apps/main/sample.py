# views.py

from django.shortcuts import render
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
import json
from .models import Portfolio, PortfolioGallery


def portfolio_list_api(request):
    """API لیست همه نمونه کارها"""
    if request.method == 'GET':
        portfolios = Portfolio.objects.filter(is_active=True).order_by('-created_at')

        data = []
        for p in portfolios:
            # گرفتن عکس اول گالری
            first_image = p.gallery.first()

            data.append({
                'id': p.id,
                'title': p.title,
                'description': p.description,
                'user_name': p.user.name or p.user.mobileNumber,
                'created_at': p.created_at.strftime('%Y-%m-%d %H:%M:%S'),
                'image': first_image.image.url if first_image else None,
                'images_count': p.gallery.count()
            })

        return JsonResponse({
            'status': 'success',
            'data': data,
            'count': len(data)
        })

    return JsonResponse({'status': 'error', 'message': 'Method not allowed'}, status=405)


@login_required
def my_portfolio_list_api(request):
    """API لیست نمونه کارهای کاربر جاری"""
    if request.method == 'GET':
        portfolios = Portfolio.objects.filter(user=request.user).order_by('-created_at')

        data = []
        for p in portfolios:
            gallery_images = []
            for img in p.gallery.all():
                gallery_images.append({
                    'id': img.id,
                    'image': img.image.url,
                    'sort_order': img.sort_order
                })

            data.append({
                'id': p.id,
                'title': p.title,
                'description': p.description,
                'created_at': p.created_at.strftime('%Y-%m-%d %H:%M:%S'),
                'gallery': gallery_images,
                'images_count': len(gallery_images)
            })

        return JsonResponse({
            'status': 'success',
            'data': data,
            'count': len(data)
        })

    return JsonResponse({'status': 'error', 'message': 'Method not allowed'}, status=405)


@login_required
@csrf_exempt
def create_portfolio_api(request):
    """API ایجاد نمونه کار جدید"""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)

            portfolio = Portfolio.objects.create(
                title=data.get('title'),
                description=data.get('description'),
                user=request.user
            )

            return JsonResponse({
                'status': 'success',
                'message': 'نمونه کار با موفقیت ایجاد شد',
                'data': {'id': portfolio.id, 'title': portfolio.title}
            }, status=201)

        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=400)

    return JsonResponse({'status': 'error', 'message': 'Method not allowed'}, status=405)


@login_required
@csrf_exempt
def upload_portfolio_image_api(request, portfolio_id):
    """API آپلود عکس برای نمونه کار"""
    if request.method == 'POST':
        try:
            portfolio = Portfolio.objects.get(id=portfolio_id, user=request.user)

            if request.FILES.get('image'):
                image = request.FILES['image']

                gallery = PortfolioGallery.objects.create(
                    portfolio=portfolio,
                    image=image,
                    sort_order=portfolio.gallery.count()
                )

                return JsonResponse({
                    'status': 'success',
                    'message': 'عکس با موفقیت آپلود شد',
                    'data': {
                        'id': gallery.id,
                        'image': gallery.image.url
                    }
                }, status=201)

            return JsonResponse({'status': 'error', 'message': 'عکسی ارسال نشده'}, status=400)

        except Portfolio.DoesNotExist:
            return JsonResponse({'status': 'error', 'message': 'نمونه کار یافت نشد'}, status=404)
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=400)

    return JsonResponse({'status': 'error', 'message': 'Method not allowed'}, status=405)


@login_required
@csrf_exempt
def delete_portfolio_api(request, portfolio_id):
    """API حذف نمونه کار"""
    if request.method == 'DELETE':
        try:
            portfolio = Portfolio.objects.get(id=portfolio_id, user=request.user)
            portfolio.delete()

            return JsonResponse({
                'status': 'success',
                'message': 'نمونه کار با موفقیت حذف شد'
            }, status=200)

        except Portfolio.DoesNotExist:
            return JsonResponse({'status': 'error', 'message': 'نمونه کار یافت نشد'}, status=404)

    return JsonResponse({'status': 'error', 'message': 'Method not allowed'}, status=405)


def portfolio_page(request):
    """صفحه نمونه کارها"""
    return render(request, 'main_app/sample.html')