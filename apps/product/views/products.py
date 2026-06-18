from django.http import JsonResponse
from django.views import View
from ..models import Product


class LatestProductsView(View):
    """نمایش ۲۰ محصول جدید به صورت JSON با تخفیف"""

    def get(self, request):
        # گرفتن ۲۰ محصول جدید
        latest_products = Product.objects.filter(status=True).order_by('-created_at')[:20]

        products_data = []
        for product in latest_products:
            try:
                # گرفتن آدرس کامل تصویر
                image_url = product.image.url if product.image else '/media/images/default-product.jpg'

                # دریافت نام برند
                brand_name = product.brand.title if product.brand and product.brand.title else "بدون برند"

                # ** محاسبه تخفیف با مدیریت خطا **
                best_discount = None
                discount_amount = 0

                if hasattr(product, 'get_best_discount'):
                    result = product.get_best_discount(1, 0)
                    if result and isinstance(result, tuple) and len(result) == 2:
                        best_discount, discount_amount = result
                        discount_amount = discount_amount or 0
                    elif isinstance(result, dict):
                        best_discount = result.get('discount')
                        discount_amount = result.get('amount', 0)

                original_price = float(product.price) if product.price else 0
                final_price = original_price - discount_amount if discount_amount > 0 else original_price
                has_discount = discount_amount > 0 and discount_amount < original_price
                discount_percent = 0
                badge_text = None
                badge_class = None

                if has_discount and best_discount:
                    try:
                        if hasattr(best_discount, 'discount_type') and best_discount.discount_type == 'percent':
                            discount_percent = int(best_discount.amount) if best_discount.amount else 0
                            badge_text = f"{discount_percent}٪ تخفیف"
                            badge_class = "bg-red-500 text-white px-2 py-1 rounded text-xs font-bold"
                        else:
                            discount_amount_int = int(discount_amount) if discount_amount else 0
                            badge_text = f"{discount_amount_int:,} تومان تخفیف"
                            badge_class = "bg-orange-500 text-white px-2 py-1 rounded text-xs font-bold"
                    except:
                        discount_percent = 0
                        badge_text = "تخفیف ویژه"
                        badge_class = "bg-red-500 text-white px-2 py-1 rounded text-xs font-bold"

                products_data.append({
                    'id': product.id,
                    'name': product.title,
                    'slug': product.slug,
                    'img': image_url,
                    'price': int(final_price) if final_price else 0,
                    'original_price': int(original_price) if has_discount else None,
                    'stock': float(product.stock) if product.stock else 0,
                    'code': product.code or "بدون کد",
                    'brand': brand_name,
                    'has_discount': has_discount,
                    'discount_percent': discount_percent,
                    'badge_text': badge_text,
                    'badge_class': badge_class,
                })

            except Exception as e:
                # در صورت خطا، محصول بدون تخفیف ارسال شود
                print(f"Error processing product {product.id}: {e}")
                products_data.append({
                    'id': product.id,
                    'name': product.title,
                    'slug': product.slug,
                    'img': product.image.url if product.image else '/media/images/default-product.jpg',
                    'price': int(product.price) if product.price else 0,
                    'original_price': None,
                    'stock': float(product.stock) if product.stock else 0,
                    'code': product.code or "بدون کد",
                    'brand': brand_name,
                    'has_discount': False,
                    'discount_percent': 0,
                    'badge_text': None,
                    'badge_class': None,
                })

        return JsonResponse({
            'status': 'success',
            'data': products_data,
            'total': len(products_data)
        }, status=200)



from django.db.models import Sum, Q, F
from django.views import View
from django.http import JsonResponse
from apps.order.models import OrderItem, OrderStatus
from apps.product.models import Product
from apps.discount.models import Discount
from decimal import Decimal


class BestsellersAPIView(View):
    """دریافت پرفروش‌ترین محصولات با اطلاعات کامل تخفیف"""

    def get(self, request):
        limit = int(request.GET.get('limit', 12))

        # محاسبه پرفروش‌ترین محصولات از OrderItem
        bestsellers = Product.objects.filter(
            status=True
        ).annotate(
            total_sold=Sum(
                'order_items__quantity',
                filter=Q(
                    order_items__order__status=OrderStatus.PAID.value,
                    order_items__order__receipt_verified=True
                )
            )
        ).filter(total_sold__gt=0).order_by('-total_sold')[:limit]

        # اگر محصول پرفروشی نبود، جدیدترین محصولات رو نشون بده
        if not bestsellers:
            bestsellers = Product.objects.filter(status=True).order_by('-created_at')[:limit]

        products_data = []
        for product in bestsellers:
            # اطلاعات قیمت و تخفیف
            price_info = self.get_product_price_info(product)

            products_data.append({
                'id': product.id,
                'name': product.title,
                'slug': product.slug,
                'code': product.code or '',
                'image': product.image.url if product.image else None,
                'brand': product.brand.title if product.brand else None,
                'brand_slug': product.brand.slug if product.brand else None,
                'sales_unit': product.get_sales_unit_symbol() if product.sales_unit else 'عدد',
                'total_sold': product.total_sold if hasattr(product, 'total_sold') and product.total_sold else 0,
                'price_info': price_info
            })

        return JsonResponse({
            'status': 'success',
            'data': products_data
        })

    def get_product_price_info(self, product, quantity=1, cart_amount=0):
        """محاسبه اطلاعات قیمت و تخفیف محصول"""

        price = float(product.price) if product.price else 0
        total_original = price * quantity

        # دریافت بهترین تخفیف
        best_discount, discount_amount = self.get_best_discount(product, quantity, cart_amount)

        final_price = total_original - discount_amount
        if final_price < 0:
            final_price = 0

        # قیمت هر واحد بعد از تخفیف
        unit_final_price = final_price / quantity if quantity > 0 else price

        result = {
            'original_price': total_original,
            'original_price_display': f"{int(total_original):,}",
            'unit_original_price': price,
            'unit_original_price_display': f"{int(price):,}" if price > 0 else "۰",
            'discount_amount': discount_amount,
            'discount_amount_display': f"{int(discount_amount):,}" if discount_amount > 0 else "۰",
            'final_price': final_price,
            'final_price_display': f"{int(final_price):,}" if final_price > 0 else "۰",
            'unit_final_price': unit_final_price,
            'unit_final_price_display': f"{int(unit_final_price):,}" if unit_final_price > 0 else "۰",
            'has_discount': discount_amount > 0,
            'discount_percent': 0,
            'discount_title': None,
            'discount_type': None,
            'badge_text': None,
            'badge_color': None
        }

        # اگر تخفیف داریم، اطلاعات کامل رو پر کن
        if discount_amount > 0 and best_discount and total_original > 0:
            discount_percent = int((discount_amount / total_original) * 100)
            result['discount_percent'] = discount_percent
            result['discount_title'] = best_discount.title
            result['discount_type'] = best_discount.discount_type

            if best_discount.discount_type == 'percent':
                result['badge_text'] = f"{int(best_discount.amount)}٪ تخفیف"
                result['badge_color'] = 'red'
            else:
                result['badge_text'] = f"{int(best_discount.amount):,} تومان تخفیف"
                result['badge_color'] = 'orange'

        return result

    def get_discounts(self, product, quantity=1, cart_amount=0):
        """دریافت تمام تخفیف‌های معتبر برای محصول"""
        all_discounts = Discount.objects.filter(is_active=True)
        valid_discounts = []

        for discount in all_discounts:
            if not discount.is_valid_now():
                continue
            if not discount.applies_to_product(product):
                continue
            if discount.min_quantity and quantity < discount.min_quantity:
                continue
            if discount.min_cart_amount and cart_amount < discount.min_cart_amount:
                continue
            valid_discounts.append(discount)

        valid_discounts.sort(key=lambda x: x.priority, reverse=True)
        return valid_discounts

    def get_best_discount(self, product, quantity=1, cart_amount=0):
        """بهترین تخفیف موجود را برمی‌گرداند (بیشترین مبلغ تخفیف)"""
        discounts = self.get_discounts(product, quantity, cart_amount)
        if not discounts:
            return None, 0

        price = float(product.price) if product.price else 0
        best_discount = None
        best_amount = 0

        for discount in discounts:
            amount = discount.calculate_discount(price, quantity, cart_amount)
            if amount > best_amount:
                best_amount = amount
                best_discount = discount

        return best_discount, best_amount