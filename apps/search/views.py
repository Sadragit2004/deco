# ... import های دیگر
from django.views import View
from django.http import JsonResponse
from django.db.models import Q
from django.utils.html import escape
from apps.product.models import Product, Brand, Category, Catalog

# ... کلاس های دیگر شما مثل ShopView ...

class SearchSuggestionsView(View):
    """
    API برای ارائه پیشنهادات جستجوی پیشرفته و زنده.
    این View در مدل‌های Product, Brand, Category, و Catalog جستجو می‌کند.
    """
    def get(self, request, *args, **kwargs):
        query = request.GET.get('q', '').strip()

        # 1. اعتبارسنجی و امنیت اولیه
        # اگر کوئری کوتاه بود یا وجود نداشت، نتیجه خالی برگردان
        if not query or len(query) < 2:
            return JsonResponse({'status': 'success', 'data': []})

        results = []
        limit_per_type = 5  # حداکثر تعداد نتیجه از هر نوع
        total_limit = 10    # حداکثر تعداد نتیجه کلی

        # 2. جستجو در محصولات (بر اساس عنوان و کد)
        products = Product.objects.filter(
            Q(status=True) & (Q(title__icontains=query) | Q(code__icontains=query))
        ).select_related('brand')[:limit_per_type]

        for p in products:
            # فرمت‌بندی نتیجه برای ارسال به فرانت‌اند
            results.append({
                'title': escape(p.title),
                'url': f'/product/{p.slug}/',
                'image': p.image.url if p.image else '/static/images/placeholder.png', # یک عکس پیشفرض
                'type': 'product',
                'type_name': f'محصول | {escape(p.brand.title)}' if p.brand else 'محصول'
            })

        # 3. جستجو در برندها
        brands = Brand.objects.filter(
            Q(status=True) & Q(title__icontains=query)
        )[:limit_per_type]

        for b in brands:
            # فرض می‌کنیم برای برندها یک صفحه لیست محصولات وجود دارد
            # اگر ندارید می‌توانید لینک را به صفحه شاپ با فیلتر برند تغییر دهید
            results.append({
                'title': escape(b.title),
                'url': f'/product/shop/?brand={b.slug}', # مثال: لینک به صفحه شاپ فیلتر شده
                'image': b.image.url if b.image else '/static/images/brand-placeholder.png',
                'type': 'brand',
                'type_name': 'برند'
            })

        # 4. جستجو در دسته‌بندی‌ها
        categories = Category.objects.filter(
            Q(status=True) & Q(title__icontains=query)
        )[:limit_per_type]

        for c in categories:
            results.append({
                'title': escape(c.title),
                'url': f'/product/shop/?category={c.slug}', # مثال: لینک به صفحه شاپ فیلتر شده
                'image': c.image.url if c.image else '/static/images/category-placeholder.png',
                'type': 'category',
                'type_name': 'دسته‌بندی'
            })

        # 5. جستجو در کاتالوگ‌ها
        catalogs = Catalog.objects.filter(
            Q(status=True) & Q(title__icontains=query)
        )[:limit_per_type]

        for cat in catalogs:
            results.append({
                'title': escape(cat.title),
                'url': f'/product/shop/?catalog={cat.slug}', # لینک مستقیم به فایل PDF
                'image': cat.image.url if cat.image else '/static/images/pdf-placeholder.png',
                'type': 'catalog',
                'type_name': 'کاتالوگ'
            })

        # 6. محدود کردن تعداد کل نتایج و ارسال پاسخ
        # می‌توانید نتایج را بر اساس اولویت مرتب کنید اگر نیاز بود
        final_results = results[:total_limit]

        return JsonResponse({'status': 'success', 'data': final_results})
