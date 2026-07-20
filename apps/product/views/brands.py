# product/views/brands.py
from django.http import JsonResponse
from django.views import View
from django.db.models import Count, Q
from ..models import Brand, Product

class PopularBrandsView(View):
    """نمایش ۲۰ برند محبوب و پر محتوا به صورت JSON"""

    def get(self, request):
        popular_brands = Brand.objects.filter(
            status=True,
            products__status=True
        ).annotate(
            product_count=Count('products', filter=Q(products__status=True))
        ).filter(
            product_count__gt=0
        ).order_by('-product_count', '-sort_order', '-created_at')[:20]

        brands_data = []
        for brand in popular_brands:
            image_url = brand.image.url if brand.image else '/media/images/default-brand.jpg'
            product_count = brand.products.filter(status=True).count()

            brands_data.append({
                'id': brand.id,
                'name': brand.title,
                'slug': brand.slug,
                'img': image_url,
                'description': brand.description or "",
                'product_count': product_count,
                'sort_order': brand.sort_order,
                'pdf_file': brand.pdf_file.url if brand.pdf_file else None,  # اضافه کردن PDF
                'has_pdf': bool(brand.pdf_file),  # آیا PDF دارد
            })

        return JsonResponse({
            'status': 'success',
            'data': brands_data,
            'total': len(brands_data)
        }, status=200)