# product/views/catalogs.py
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.core.cache import cache
from django.conf import settings
from ..models import Catalog


@csrf_exempt
def latest_catalogs(request):
    """
    دریافت آخرین کاتالوگ‌های فعال با کش
    """
    # کلید کش
    cache_key = 'latest_catalogs'

    # دریافت داده از کش
    cached_data = cache.get(cache_key)

    if cached_data is not None:
        return JsonResponse({
            'status': 'success',
            'data': cached_data['data'],
            'total': cached_data['total'],
            'cached': True,
            'cache_timeout': getattr(settings, 'CATALOGS_CACHE_TIMEOUT', 3600)
        }, status=200)

    # اگر در کش نبود، از دیتابیس می‌خوانیم
    catalogs = Catalog.objects.filter(status=True).order_by('-created_at')

    data = []
    for catalog in catalogs:
        # مدیریت تصویر با بررسی وجود فایل
        image_url = None
        if catalog.image and hasattr(catalog.image, 'url') and catalog.image:
            image_url = catalog.image.url

        # مدیریت فایل PDF
        file_url = None
        if catalog.files and hasattr(catalog.files, 'url') and catalog.files:
            file_url = catalog.files.url

        # دریافت نام برند (با بهینه‌سازی برای جلوگیری از کوئری اضافی)
        brand_name = catalog.brand.title if catalog.brand else None

        # دریافت نام دسته‌بندی‌ها
        category_names = [cat.title for cat in catalog.categories.all()]

        data.append({
            'id': catalog.id,
            'title': catalog.title,
            'slug': catalog.slug,
            'brand_name': brand_name,
            'brand_id': catalog.brand.id if catalog.brand else None,
            'category_names': category_names,
            'category_ids': [cat.id for cat in catalog.categories.all()],
            'image_url': image_url,
            'file_url': file_url,
            'has_file': bool(file_url),
            'created_at': catalog.created_at.strftime('%Y/%m/%d %H:%M') if catalog.created_at else None,
            'sort_order': catalog.sort_order,
            'status': catalog.status,
        })

    # ساخت داده برای ذخیره در کش
    cache_data = {
        'data': data,
        'total': len(data),
        'timestamp': cache.get('catalogs_timestamp') or 0
    }

    # ذخیره در کش
    cache_timeout = getattr(settings, 'CATALOGS_CACHE_TIMEOUT', 3600)  # پیش‌فرض ۱ ساعت
    cache.set(cache_key, cache_data, timeout=cache_timeout)
    cache.set('catalogs_timestamp', cache_data['timestamp'] + 1, timeout=86400)  # ۲۴ ساعت

    return JsonResponse({
        'status': 'success',
        'data': data,
        'total': len(data),
        'cached': False,
        'cache_timeout': cache_timeout
    }, status=200)


@csrf_exempt
def catalog_detail(request, catalog_id=None, slug=None):
    """
    دریافت جزئیات یک کاتالوگ با کش
    """
    if not catalog_id and not slug:
        return JsonResponse({
            'status': 'error',
            'message': 'شناسه یا اسلاگ کاتالوگ الزامی است'
        }, status=400)

    # کلید کش بر اساس شناسه یا اسلاگ
    if catalog_id:
        cache_key = f'catalog_detail_{catalog_id}'
    else:
        cache_key = f'catalog_detail_slug_{slug}'

    # دریافت از کش
    cached_data = cache.get(cache_key)
    if cached_data is not None:
        return JsonResponse({
            'status': 'success',
            'data': cached_data,
            'cached': True
        }, status=200)

    # دریافت از دیتابیس
    try:
        if catalog_id:
            catalog = Catalog.objects.get(id=catalog_id, status=True)
        else:
            catalog = Catalog.objects.get(slug=slug, status=True)
    except Catalog.DoesNotExist:
        return JsonResponse({
            'status': 'error',
            'message': 'کاتالوگ مورد نظر یافت نشد'
        }, status=404)

    # ساخت داده
    data = {
        'id': catalog.id,
        'title': catalog.title,
        'slug': catalog.slug,
        'brand': {
            'id': catalog.brand.id if catalog.brand else None,
            'name': catalog.brand.title if catalog.brand else None,
            'slug': catalog.brand.slug if catalog.brand else None,
        },
        'categories': [
            {
                'id': cat.id,
                'title': cat.title,
                'slug': cat.slug
            } for cat in catalog.categories.all()
        ],
        'description': catalog.description,
        'image_url': catalog.image.url if catalog.image and hasattr(catalog.image, 'url') else None,
        'file_url': catalog.files.url if catalog.files and hasattr(catalog.files, 'url') else None,
        'has_file': bool(catalog.files and hasattr(catalog.files, 'url')),
        'products': [
            {
                'id': product.id,
                'title': product.title,
                'slug': product.slug,
                'price': str(product.price) if product.price else None,
                'image': product.image.url if product.image and hasattr(product.image, 'url') else None,
            } for product in catalog.products.filter(status=True)[:10]  # فقط ۱۰ محصول اول
        ],
        'created_at': catalog.created_at.strftime('%Y/%m/%d %H:%M') if catalog.created_at else None,
        'updated_at': catalog.updated_at.strftime('%Y/%m/%d %H:%M') if catalog.updated_at else None,
        'sort_order': catalog.sort_order,
        'status': catalog.status,
    }

    # ذخیره در کش
    cache_timeout = getattr(settings, 'CATALOG_DETAIL_CACHE_TIMEOUT', 1800)  # ۳۰ دقیقه
    cache.set(cache_key, data, timeout=cache_timeout)

    return JsonResponse({
        'status': 'success',
        'data': data,
        'cached': False
    }, status=200)


@csrf_exempt
def clear_catalogs_cache(request):
    """
    پاک کردن کش کاتالوگ‌ها (فقط برای ادمین)
    """
    if not request.user.is_staff:
        return JsonResponse({
            'status': 'error',
            'message': 'شما دسترسی به این عملیات ندارید'
        }, status=403)

    # پاک کردن کش‌های مرتبط
    cache.delete('latest_catalogs')
    cache.delete('catalogs_list')
    cache.delete('catalogs_timestamp')
    cache.delete_pattern('catalog_detail_*')
    cache.delete_pattern('catalog_detail_slug_*')

    return JsonResponse({
        'status': 'success',
        'message': 'کش کاتالوگ‌ها با موفقیت پاک شد'
    }, status=200)