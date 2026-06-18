from django.shortcuts import render, get_object_or_404
from django.views import View
import math
from ..models import Product, ProductGallery, ProductAttributeValue


class ProductDetailView(View):
    """صفحه جزییات محصول"""

    def get_best_discount_for_product(self, product, quantity=1):
        try:
            if hasattr(product, 'get_best_discount'):
                result = product.get_best_discount(quantity, 0)
                if result and isinstance(result, tuple) and len(result) == 2:
                    best_discount, discount_amount = result
                    if best_discount and discount_amount > 0:
                        discount_percent = 0
                        if hasattr(best_discount, 'discount_type') and best_discount.discount_type == 'percent':
                            discount_percent = int(best_discount.amount) if best_discount.amount else 0
                        return {
                            'has_discount': True,
                            'discount_amount': float(discount_amount),
                            'discount_percent': discount_percent,
                        }
        except:
            pass
        return {'has_discount': False, 'discount_amount': 0, 'discount_percent': 0}

    def get_final_price_with_discount(self, product, quantity=1, discount_info=None):
        if not product.price:
            return 0, 0
        product_price = float(product.price)
        if discount_info is None:
            discount_info = self.get_best_discount_for_product(product, quantity)
        if discount_info['has_discount']:
            total_original = product_price * quantity
            discount_amount = float(discount_info['discount_amount'])
            final_price = total_original - discount_amount
            return final_price, discount_amount
        return product_price * quantity, 0

    def get_related_products(self, product, limit=6):
        categories = product.categories.all()
        products = Product.objects.filter(status=True).exclude(id=product.id)
        if categories.exists():
            category_ids = list(categories.values_list('id', flat=True))
            related = products.filter(categories__id__in=category_ids).distinct()
            if related.count() >= limit:
                return list(related[:limit])
        return list(products.order_by('-created_at')[:limit])

    def get_next_previous(self, product):
        first_category = product.categories.first()
        if first_category:
            category_products = list(Product.objects.filter(
                categories=first_category, status=True
            ).order_by('sort_order', 'created_at'))
            for i, p in enumerate(category_products):
                if p.id == product.id:
                    return {
                        'prev': category_products[i - 1] if i > 0 else None,
                        'next': category_products[i + 1] if i + 1 < len(category_products) else None
                    }
        return {'prev': None, 'next': None}

    def get_features(self, product):
        attributes = ProductAttributeValue.objects.filter(product=product).select_related('attribute')
        return [{'name': av.attribute.name, 'value': av.value, 'icon': av.attribute.icon or 'fa-tag'} for av in attributes]

    def get_gallery_images(self, product):
        images = [product.image.url] if product.image and product.image.url else []
        gallery = ProductGallery.objects.filter(product=product).order_by('sort_order')
        for img in gallery:
            if img.image and img.image.url:
                images.append(img.image.url)
        return images if images else ['/media/images/placeholder.jpg']

    def get_sales_unit_info(self, product):
        """دریافت اطلاعات کامل واحد فروش - با دیباگ"""

        # ========== دیباگ ==========
        print("=" * 50)
        print(f"=== DEBUG: get_sales_unit_info ===")
        print(f"Product ID: {product.id}")
        print(f"Product Title: {product.title}")
        print(f"product.sales_unit: {product.sales_unit}")
        print(f"product.sales_unit_id: {product.sales_unit_id}")
        print(f"Has sales_unit attribute: {hasattr(product, 'sales_unit')}")

        if product.sales_unit:
            print(f"sales_unit.id: {product.sales_unit.id}")
            print(f"sales_unit.name: '{product.sales_unit.name}'")
            print(f"sales_unit.symbol: '{product.sales_unit.symbol}'")
            print(f"sales_unit.name_en: '{product.sales_unit.name_en}'")
        else:
            print("*** WARNING: product.sales_unit is None! ***")
            print("*** محصول واحد فروش ندارد! ***")

        # چک کردن مستقیم از دیتابیس
        from ..models import SalesUnit
        all_units = SalesUnit.objects.all()
        print(f"Total SalesUnit in DB: {all_units.count()}")
        for su in all_units:
            print(f"  - ID: {su.id}, Name: {su.name}, Symbol: {su.symbol}")
        print("=" * 50)
        # ========== پایان دیباگ ==========

        if product.sales_unit and product.sales_unit_id:
            return {
                'id': product.sales_unit.id,
                'name': product.sales_unit.name or 'واحد',
                'symbol': product.sales_unit.symbol or 'واحد',
            }

        # اگر sales_unit وجود ندارد، از دیتابیس یک واحد پیش‌فرض بگیر
        try:
            default_unit = SalesUnit.objects.first()
            if default_unit:
                print(f"*** Using default unit: {default_unit.name} ({default_unit.symbol}) ***")
                return {
                    'id': default_unit.id,
                    'name': default_unit.name or 'واحد',
                    'symbol': default_unit.symbol or 'واحد',
                }
        except:
            pass

        return {'id': None, 'name': 'واحد', 'symbol': 'عدد'}

    def get_package_info(self, product):
        if product.use_packaging and product.package_unit and product.package_unit_id:
            return {
                'use_packaging': True,
                'package_size': float(product.package_size) if product.package_size else 0,
                'package_unit_name': product.package_unit.name or 'بسته',
                'package_unit_symbol': product.package_unit.symbol or 'بسته',
                'min_order': float(product.min_order) if product.min_order else 1,
                'step': float(product.step) if product.step else 1,
                'stock': float(product.stock) if product.stock else 0,
            }
        return {
            'use_packaging': False,
            'package_size': 0,
            'package_unit_name': 'بسته',
            'package_unit_symbol': 'بسته',
            'min_order': float(product.min_order) if product.min_order else 1,
            'step': float(product.step) if product.step else 1,
            'stock': float(product.stock) if product.stock else 0,
        }

    def get(self, request, slug):
        product = get_object_or_404(
            Product.objects.select_related('brand', 'sales_unit', 'package_unit'),
            slug=slug, status=True
        )

        # ========== دیباگ قبل از هر کاری ==========
        print("\n" + "=" * 60)
        print(f"=== PRODUCT DETAIL VIEW ===")
        print(f"Slug: {slug}")
        print(f"Product: {product.title} (ID: {product.id})")
        print(f"Product sales_unit_id from DB: {product.sales_unit_id}")
        print(f"Product sales_unit (cached): {product.sales_unit}")
        print("=" * 60)
        # ========== پایان دیباگ ==========

        # اطلاعات پایه
        sales_unit_info = self.get_sales_unit_info(product)
        package_info = self.get_package_info(product)

        # ========== دیباگ نتیجه ==========
        print(f"\n=== sales_unit_info RESULT ===")
        print(f"Name: {sales_unit_info.get('name')}")
        print(f"Symbol: {sales_unit_info.get('symbol')}")
        print(f"ID: {sales_unit_info.get('id')}")
        print("=" * 60)
        # ========== پایان دیباگ ==========

        # تخفیف
        discount_info = self.get_best_discount_for_product(product, 1)
        final_price_for_one, discount_amount_one = self.get_final_price_with_discount(product, 1, discount_info)

        discount_percent = discount_info['discount_percent']
        original_price = float(product.price) if product.price else 0
        final_price = final_price_for_one if final_price_for_one > 0 else original_price
        old_price = original_price if discount_percent > 0 and final_price < original_price else None

        # گالری و ویژگی‌ها
        gallery_images = self.get_gallery_images(product)
        features = self.get_features(product)
        related_products = self.get_related_products(product)
        nav = self.get_next_previous(product)

        # خلاصه سفارش
        try:
            order_summary = product.get_order_summary(1)
            order_summary['sales_unit_symbol'] = sales_unit_info['symbol']
        except:
            order_summary = {
                'requested_quantity': 1,
                'actual_quantity': 1,
                'packages': 0,
                'total_price': final_price,
                'total_price_display': f"{int(final_price):,}",
                'sales_unit_symbol': sales_unit_info['symbol']
            }

        if discount_percent > 0 and final_price < original_price:
            order_summary['total_price'] = final_price_for_one
            order_summary['total_price_display'] = f"{int(final_price_for_one):,}"
            order_summary['has_discount'] = True
            order_summary['discount_percent'] = discount_percent

        # محصولات مرتبط
        related_data = []
        for rel in related_products:
            rel_discount = self.get_best_discount_for_product(rel, 1)
            rel_final_price, _ = self.get_final_price_with_discount(rel, 1, rel_discount)
            related_data.append({
                'id': rel.id,
                'title': rel.title,
                'slug': rel.slug,
                'image': rel.image.url if rel.image else '/media/images/placeholder.jpg',
                'price_display': f"{int(rel_final_price):,}" if rel_final_price else "۰",
                'has_discount': rel_discount['has_discount'],
                'discount_percent': rel_discount['discount_percent'],
            })

        # موجودی
        has_stock = True
        stock_status = 'موجود'
        stock_qty = float(product.stock) if product.stock else 0
        if stock_qty <= 0:
            has_stock = False
            stock_status = 'ناموجود'

        context = {
            'product': product,
            'final_price': int(final_price) if final_price else 0,
            'original_price_display': f"{int(original_price):,}" if original_price else "۰",
            'final_price_display': f"{int(final_price):,}" if final_price else "۰",
            'old_price_display': f"{int(old_price):,}" if old_price else None,
            'discount_percent': discount_percent,
            'show_discount_badge': discount_percent > 0 and final_price < original_price,
            'sales_unit_info': sales_unit_info,
            'package_info': package_info,
            'order_summary': order_summary,
            'gallery_images': gallery_images,
            'features': features,
            'related_products': related_data,
            'next_product': nav['next'],
            'prev_product': nav['prev'],
            'has_stock': has_stock,
            'stock_status': stock_status,
        }

        # ========== دیباگ نهایی ==========
        print(f"\n=== FINAL CONTEXT KEYS ===")
        print(f"sales_unit_info in context: {context.get('sales_unit_info')}")
        print(f"final_price: {context.get('final_price')}")
        print("=" * 60 + "\n")
        # ========== پایان دیباگ ==========

        return render(request, 'product_app/products/product_detail.html', context)