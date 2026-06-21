from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from ..models import Catalog

@csrf_exempt
def latest_catalogs(request):
    """
    دریافت آخرین کاتالوگ‌های فعال
    """
    catalogs = Catalog.objects.filter(status=True).order_by('-created_at')
    data = []
    for catalog in catalogs:
        data.append({
            'id': catalog.id,
            'title': catalog.title,
            'slug': catalog.slug,
            'brand_name': catalog.brand.title if catalog.brand else None,
            'category_names': [cat.title for cat in catalog.categories.all()],
            'image_url': catalog.image.url if catalog.image else None,
            'file_url': catalog.files.url if catalog.files else None,
            'created_at': catalog.created_at.strftime('%Y/%m/%d %H:%M') if catalog.created_at else None,
        })

    return JsonResponse({
        'status': 'success',
        'data': data
    })