# views.py
from django.http import JsonResponse
from django.views import View
from django.core.serializers import serialize
from ..models import Category
import json

class CategoryListView(View):
    """نمایش دسته بندی‌های اصلی (parent=None) به صورت JSON"""

    def get(self, request):
        # گرفتن دسته بندی‌هایی که parent ندارند
        main_categories = Category.objects.filter(parent__isnull=True, status=True)

        # ساخت آرایه دیتا
        categories_data = []
        for category in main_categories:
            # گرفتن آدرس کامل تصویر
            image_url = category.image.url if category.image else '/media/images/default-category.jpg'

            categories_data.append({
                'id': category.id,
                'name': category.title,  # اسم دسته بندی
                'slug': category.slug,   # اسلاگ برای لینک‌ها
                'img': image_url,        # آدرس تصویر

                'sort_order': category.sort_order,  # ترتیب نمایش
                'child_count': category.children.count()  # تعداد زیرمجموعه‌ها
            })

        # مرتب‌سازی بر اساس sort_order
        categories_data.sort(key=lambda x: x['sort_order'])

        return JsonResponse({
            'status': 'success',
            'data': categories_data,
            'total': len(categories_data)
        }, status=200)

from django.shortcuts import render, get_object_or_404, redirect
from django.views import View
from django.db.models import Count, Q
from django.http import JsonResponse
from ..models import Category, Brand, Catalog, Product


class CategoryListView(View):
    """نمایش دسته بندی‌های اصلی (parent=None) به صورت JSON"""

    def get(self, request):
        main_categories = Category.objects.filter(parent__isnull=True, status=True)

        categories_data = []
        for category in main_categories:
            image_url = category.image.url if category.image else '/media/images/default-category.jpg'
            categories_data.append({
                'id': category.id,
                'name': category.title,
                'slug': category.slug,
                'img': image_url,
                'sort_order': category.sort_order,
                'child_count': category.children.count()
            })

        categories_data.sort(key=lambda x: x['sort_order'])

        return JsonResponse({
            'status': 'success',
            'data': categories_data,
            'total': len(categories_data)
        }, status=200)


class CategoryBrandsView(View):
    """
    نمایش برندهای مربوط به یک دسته بندی بر اساس اسلاگ با قابلیت فیلتر و جستجو
    """
    template_name = 'product_app/category/category_brands.html'

    def get(self, request, slug):
        category = get_object_or_404(Category, slug=slug, status=True)
        brands = category.brands.filter(status=True)
        sort_by = request.GET.get('sort', 'default')
        search_query = request.GET.get('search', '')

        brands = brands.annotate(
            product_count=Count('products', filter=Q(products__status=True), distinct=True),
            catalog_count=Count('catalogs', filter=Q(catalogs__status=True), distinct=True),
            total_content=Count('products', filter=Q(products__status=True), distinct=True) +
                         Count('catalogs', filter=Q(catalogs__status=True), distinct=True)
        )

        if search_query:
            brands = brands.filter(
                Q(title__icontains=search_query) |
                Q(description__icontains=search_query)
            )

        if sort_by == 'newest':
            brands = brands.order_by('-created_at')
        elif sort_by == 'most_content':
            brands = brands.order_by('-total_content', '-product_count')
        elif sort_by == 'most_products':
            brands = brands.order_by('-product_count')
        elif sort_by == 'most_catalogs':
            brands = brands.order_by('-catalog_count')
        elif sort_by == 'alphabetical':
            brands = brands.order_by('title')
        else:
            brands = brands.order_by('sort_order', 'title')

        subcategories = category.children.filter(status=True)
        popular_brands = brands.order_by('-total_content', '-product_count')

        context = {
            'category': category,
            'brands': brands,
            'subcategories': subcategories,
            'popular_brands': popular_brands,
            'total_brands': brands.count(),
            'sort_by': sort_by,
            'search_query': search_query,
        }

        return render(request, self.template_name, context)


class BrandCatalogsView(View):
    """
    نمایش کاتالوگ‌های مربوط به یک برند
    اگر isCatalog=False باشد، ریدایرکت به صفحه شاپ با فیلتر برند
    """
    template_name = 'product_app/category/category_catalog.html'

    def get(self, request, slug):
        brand = get_object_or_404(Brand, slug=slug, status=True)

        # اگر isCatalog=False، ریدایرکت به صفحه شاپ با فیلتر برند
        if not brand.isCatalog:
            return redirect(f'/product/shop/?brand={brand.slug}')

        sort_by = request.GET.get('sort', 'newest')
        search_query = request.GET.get('search', '')

        catalogs = Catalog.objects.filter(brand=brand, status=True)

        if search_query:
            catalogs = catalogs.filter(
                Q(title__icontains=search_query) |
                Q(description__icontains=search_query)
            )

        if sort_by == 'newest':
            catalogs = catalogs.order_by('-created_at')
        elif sort_by == 'oldest':
            catalogs = catalogs.order_by('created_at')
        elif sort_by == 'alphabetical':
            catalogs = catalogs.order_by('title')
        else:
            catalogs = catalogs.order_by('-created_at')

        categories = brand.categories.filter(status=True)
        products = brand.products.filter(status=True)

        context = {
            'brand': brand,
            'catalogs': catalogs,
            'categories': categories,
            'products': products,
            'total_catalogs': catalogs.count(),
            'sort_by': sort_by,
            'search_query': search_query,
        }

        return render(request, self.template_name, context)


def brand_catalogs_view(request, slug):
    """
    نمایش کاتالوگ‌های یک برند (نسخه تابعی)
    اگر isCatalog=False باشد، ریدایرکت به صفحه شاپ با فیلتر برند
    """
    brand = get_object_or_404(Brand, slug=slug, status=True)

    if not brand.isCatalog:
        return redirect(f'/product/shop/?brand={brand.slug}')

    catalogs = Catalog.objects.filter(brand=brand, status=True).order_by('-created_at')
    categories = brand.categories.filter(status=True)
    products = brand.products.filter(status=True)

    context = {
        'brand': brand,
        'catalogs': catalogs,
        'categories': categories,
        'products': products,
        'total_catalogs': catalogs.count(),
    }

    return render(request, 'product_app/category/category_catalog.html', context)

from django.db.models import Count, Sum, Q
from django.views import View
from django.shortcuts import get_object_or_404
from django.http import JsonResponse
from apps.product.models import Category, Brand, Catalog, Product
from apps.order.models import OrderItem, OrderStatus


class CategoryMegaMenuView(View):
    """دریافت دیتای منوی 3 ستونه برای یک دسته‌بندی خاص"""

    def get(self, request, slug):
        category = get_object_or_404(Category, slug=slug, status=True)

        subcategories = category.children.filter(status=True)
        sub_ids = list(subcategories.values_list('id', flat=True))
        sub_ids.append(category.id)

        # ========== برندها ==========
        brands = Brand.objects.filter(
            categories__id__in=sub_ids,
            status=True
        ).distinct().annotate(
            product_count=Count('products', filter=Q(products__status=True, products__categories__id__in=sub_ids))
        ).order_by('-product_count')

        brands_data = [
            {
                'id': b.id,
                'name': b.title,
                'slug': b.slug,
                'image': b.image.url if b.image else None,
                'product_count': b.product_count,
                'is_catalog': b.isCatalog
            }
            for b in brands
        ]

        # ========== کاتالوگ‌ها ==========
        catalogs = Catalog.objects.filter(
            categories__id__in=sub_ids,
            status=True
        ).distinct().order_by('-created_at')

        catalogs_data = [
            {
                'id': c.id,
                'title': c.title,
                'slug': c.slug,
                'file_url': c.files.url if c.files else '#',
                'date': c.created_at.strftime('%Y/%m/%d') if c.created_at else ''
            }
            for c in catalogs
        ]

        # ========== پرفروش‌ترین محصولات (از OrderItem) ==========
        # محاسبه مجموع تعداد فروش برای هر محصول در سفارش‌های پرداخت شده
        bestsellers = Product.objects.filter(
            categories__id__in=sub_ids,
            status=True
        ).annotate(
            total_sold=Sum('order_items__quantity', filter=Q(
                order_items__order__status=OrderStatus.PAID.value,
                order_items__order__receipt_verified=True
            ))
        ).filter(total_sold__gt=0).order_by('-total_sold')

        # اگر محصول پرفروشی نبود، محصولات تصادفی یا جدید نشون بده
        if not bestsellers:
            bestsellers = Product.objects.filter(
                categories__id__in=sub_ids,
                status=True
            ).order_by('-created_at')

        bestsellers_data = []
        for p in bestsellers:
            # قیمت رو safe handling کن
            price_value = 0
            if p.price is not None:
                try:
                    price_value = int(float(p.price))
                except (TypeError, ValueError):
                    price_value = 0

            bestsellers_data.append({
                'id': p.id,
                'name': p.title,
                'slug': p.slug,
                'image': p.image.url if p.image else None,
                'price': price_value,
                'price_display': f"{price_value:,}" if price_value > 0 else 'تماس بگیرید',
                'total_sold': p.total_sold if hasattr(p, 'total_sold') and p.total_sold else 0
            })

        return JsonResponse({
            'status': 'success',
            'data': {
                'category_id': category.id,
                'category_name': category.title,
                'brands': brands_data,
                'catalogs': catalogs_data,
                'bestsellers': bestsellers_data
            }
        })