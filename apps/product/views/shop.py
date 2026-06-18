from django.http import JsonResponse
from django.views import View
from django.shortcuts import render, redirect
from django.db.models import Q, Min, Max
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from ..models import Product, Brand, Category, Catalog


class ShopView(View):
    template_name = 'product_app/products/shop.html'

    def get_discount_info(self, product):
        """دریافت اطلاعات تخفیف محصول با مدیریت خطا"""
        try:
            if hasattr(product, 'get_best_discount'):
                result = product.get_best_discount(1, 0)

                # مدیریت不同类型返回值
                best_discount = None
                discount_amount = 0

                if result is not None:
                    if isinstance(result, tuple) and len(result) == 2:
                        best_discount, discount_amount = result
                        discount_amount = discount_amount or 0
                    elif isinstance(result, dict):
                        best_discount = result.get('discount')
                        discount_amount = result.get('amount', 0)

                if best_discount and discount_amount > 0:
                    original_price = float(product.price) if product.price else 0
                    final_price = original_price - discount_amount
                    discount_percent = 0

                    if hasattr(best_discount, 'discount_type') and best_discount.discount_type == 'percent':
                        discount_percent = int(best_discount.amount) if best_discount.amount else 0

                    return {
                        'has_discount': True,
                        'discount_percent': discount_percent,
                        'discount_amount': discount_amount,
                        'final_price': final_price if final_price > 0 else original_price,
                        'final_price_display': f"{int(final_price):,}" if final_price > 0 else f"{int(original_price):,}",
                        'old_price_display': f"{int(original_price):,}" if discount_percent > 0 else None
                    }
        except Exception as e:
            print(f"Error getting discount for product {product.id}: {e}")

        # حالت بدون تخفیف
        original_price = float(product.price) if product.price else 0
        return {
            'has_discount': False,
            'discount_percent': 0,
            'discount_amount': 0,
            'final_price': original_price,
            'final_price_display': f"{int(original_price):,}" if original_price else "۰",
            'old_price_display': None
        }

    def get(self, request):
        # دریافت پارامترها
        search_query = request.GET.get('search', '').strip()
        sort_by = request.GET.get('sort', 'newest')
        min_price = request.GET.get('min_price', '')
        max_price = request.GET.get('max_price', '')
        brand_slug = request.GET.get('brand', '')
        category_slug = request.GET.get('category', '')
        catalog_slug = request.GET.get('catalog', '')
        page = request.GET.get('page', 1)

        # کوئری پایه
        products = Product.objects.filter(status=True).select_related('brand', 'sales_unit')

        # فیلترها
        if search_query:
            products = products.filter(
                Q(title__icontains=search_query) |
                Q(description__icontains=search_query) |
                Q(code__icontains=search_query) |
                Q(brand__title__icontains=search_query)
            )

        if brand_slug:
            products = products.filter(brand__slug=brand_slug)

        if category_slug:
            products = products.filter(categories__slug=category_slug)

        if catalog_slug:
            products = products.filter(catalog__slug=catalog_slug)

        if min_price:
            try:
                products = products.filter(price__gte=int(min_price))
            except:
                pass

        if max_price:
            try:
                products = products.filter(price__lte=int(max_price))
            except:
                pass

        # مرتب‌سازی
        if sort_by == 'newest':
            products = products.order_by('-created_at')
        elif sort_by == 'expensive':
            products = products.order_by('-price')
        elif sort_by == 'cheapest':
            products = products.order_by('price')
        elif sort_by == 'bestseller':
            products = products.order_by('-stock')
        else:
            products = products.order_by('-created_at')

        # پیجینیشن
        paginator = Paginator(products, 20)
        try:
            products_page = paginator.page(page)
        except PageNotAnInteger:
            products_page = paginator.page(1)
        except EmptyPage:
            products_page = paginator.page(paginator.num_pages)

        # داده‌های جانبی
        brands = Brand.objects.filter(status=True, products__isnull=False).distinct().order_by('title')
        categories = Category.objects.filter(status=True, products__isnull=False).distinct().order_by('title')
        price_range = products.aggregate(min_price=Min('price'), max_price=Max('price'))

        # آماده‌سازی محصولات با تخفیف
        products_with_discount = []
        for product in products_page:
            discount_info = self.get_discount_info(product)
            products_with_discount.append({
                'id': product.id,
                'title': product.title,
                'slug': product.slug,
                'code': product.code,
                'image': product.image,
                'brand': product.brand,
                'brand_slug': product.brand.slug if product.brand else '',
                'price': product.price,
                'sales_unit_symbol': product.get_sales_unit_symbol(),
                'has_discount': discount_info['has_discount'],
                'discount_percent': discount_info['discount_percent'],
                'final_price': discount_info['final_price'],
                'final_price_display': discount_info['final_price_display'],
                'old_price_display': discount_info['old_price_display']
            })

        # اگر درخواست AJAX باشد
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            data = []
            for p in products_with_discount:
                data.append({
                    'id': p['id'],
                    'title': p['title'],
                    'slug': p['slug'],
                    'price': p['final_price_display'],
                    'old_price': p['old_price_display'],
                    'discount_percent': p['discount_percent'],
                    'has_discount': p['has_discount'],
                    'image': p['image'].url if p['image'] else None,
                    'brand': p['brand'].title if p['brand'] else '',
                    'brand_slug': p['brand_slug'],
                    'code': p['code'] or '',
                    'has_next': products_page.has_next()
                })
            return JsonResponse({'status': 'success', 'data': data, 'has_next': products_page.has_next()})

        context = {
            'products': products_with_discount,
            'products_page_obj': products_page,
            'total_products': products.count(),
            'search_query': search_query,
            'sort_by': sort_by,
            'min_price': min_price,
            'max_price': max_price,
            'selected_brand': brand_slug,
            'selected_category': category_slug,
            'selected_catalog': catalog_slug,
            'brands': brands,
            'categories': categories,
            'price_min': int(price_range['min_price'] or 0),
            'price_max': int(price_range['max_price'] or 10000000),
        }
        return render(request, self.template_name, context)


class SearchSuggestionsView(View):
    """پیشنهادات جستجو با AJAX"""

    def get(self, request):
        query = request.GET.get('q', '').strip()

        if len(query) < 2:
            return JsonResponse({'status': 'success', 'data': []})

        products = Product.objects.filter(
            Q(title__icontains=query) | Q(brand__title__icontains=query),
            status=True
        )[:8]

        brands = Brand.objects.filter(title__icontains=query, status=True)[:4]

        data = []
        for p in products:
            # محاسبه تخفیف با مدیریت خطا
            price_display = f"{int(p.price):,}" if p.price else '0'
            try:
                if hasattr(p, 'get_best_discount'):
                    result = p.get_best_discount(1, 0)
                    if result and isinstance(result, tuple) and len(result) == 2:
                        best_discount, _ = result
                        if best_discount and hasattr(best_discount, 'discount_type') and best_discount.discount_type == 'percent':
                            final_price = float(p.price) * (1 - float(best_discount.amount) / 100) if p.price else 0
                            price_display = f"{int(final_price):,}"
            except Exception as e:
                print(f"Error in suggestion discount: {e}")

            data.append({
                'type': 'product',
                'type_name': 'محصول',
                'title': p.title,
                'url': f'/product/{p.slug}/',
                'image': p.image.url if p.image else None,
                'price': price_display,
                'brand': p.brand.title if p.brand else ''
            })

        for b in brands:
            data.append({
                'type': 'brand',
                'type_name': 'برند',
                'title': b.title,
                'url': f'/brand/{b.slug}/',
                'image': b.image.url if b.image else None,
            })

        return JsonResponse({'status': 'success', 'data': data})