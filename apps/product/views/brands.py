# product/views/brands.py
from django.http import JsonResponse
from django.views import View
from django.db.models import Count, Q
from ..models import Brand, Product

class PopularBrandsView(View):
    """نمایش ۲۰ برند محبوب و پر محتوا به صورت JSON"""

    def get(self, request):
        # گرفتن برندهایی که حداقل یک محصول فعال دارند
        # مرتب سازی بر اساس تعداد محصولات (بیشترین به کمترین)
        popular_brands = Brand.objects.filter(
            status=True,
            products__status=True  # فقط برندهایی که محصول فعال دارند
        ).annotate(
            product_count=Count('products', filter=Q(products__status=True))
        ).filter(
            product_count__gt=0  # حداقل یک محصول داشته باشند
        ).order_by('-product_count', '-sort_order', '-created_at')[:20]

        brands_data = []
        for brand in popular_brands:
            # گرفتن آدرس کامل تصویر یا تصویر پیش‌فرض
            image_url = brand.image.url if brand.image else '/media/images/default-brand.jpg'

            # شمارش تعداد محصولات فعال این برند
            product_count = brand.products.filter(status=True).count()

            brands_data.append({
                'id': brand.id,
                'name': brand.title,
                'slug': brand.slug,
                'img': image_url,
                'description': brand.description or "",
                'product_count': product_count,
                'sort_order': brand.sort_order,
            })

        return JsonResponse({
            'status': 'success',
            'data': brands_data,
            'total': len(brands_data)
        }, status=200)