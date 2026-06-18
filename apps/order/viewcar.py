from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.shortcuts import get_object_or_404
import json
from apps.product.models import Product
from .shopcart import Cart


@require_http_methods(['POST'])
def cart_add_api(request):
    """افزودن به سبد خرید با احتساب تخفیف"""
    try:
        data = json.loads(request.body)
        product_id = data.get('product_id')
        quantity = int(data.get('quantity', 1))

        product = get_object_or_404(Product, id=product_id)

        # محاسبه قیمت نهایی با تخفیف برای یک واحد محصول
        final_price_info = product.get_final_price_info(quantity=quantity)
        unit_final_price = final_price_info['final_price'] / quantity

        cart = Cart(request)
        cart.add_with_price(product, quantity, unit_final_price)

        return JsonResponse({
            'success': True,
            'message': f'{product.title} به سبد خرید اضافه شد',
            'cart_total_quantity': cart.get_total_quantity(),
            'cart_total_price': cart.get_total_price(),
        })
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)}, status=400)


@require_http_methods(['POST'])
def cart_remove_api(request):
    try:
        data = json.loads(request.body)
        product_id = data.get('product_id')

        cart = Cart(request)
        cart.remove(product_id)

        return JsonResponse({
            'success': True,
            'message': 'محصول از سبد خرید حذف شد',
            'cart_total_quantity': cart.get_total_quantity(),
            'cart_total_price': cart.get_total_price(),
        })
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)}, status=400)


@require_http_methods(['POST'])
def cart_update_api(request):
    try:
        data = json.loads(request.body)
        product_id = data.get('product_id')
        quantity = int(data.get('quantity', 1))

        cart = Cart(request)

        # برای به‌روزرسانی، نیاز به محاسبه مجدد قیمت با تخفیف هستیم
        product = get_object_or_404(Product, id=product_id)
        final_price_info = product.get_final_price_info(quantity=quantity)
        unit_final_price = final_price_info['final_price'] / quantity if quantity > 0 else 0

        cart.update_with_price(product_id, quantity, unit_final_price)

        item = cart.get_item(product_id)
        item_total = 0
        if item:
            item_total = float(item['price']) * item['quantity']

        return JsonResponse({
            'success': True,
            'message': 'سبد خرید به‌روزرسانی شد',
            'item_total': item_total,
            'cart_total_quantity': cart.get_total_quantity(),
            'cart_total_price': cart.get_total_price(),
        })
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)}, status=400)


@require_http_methods(['POST'])
def cart_clear_api(request):
    try:
        cart = Cart(request)
        cart.clear()

        return JsonResponse({
            'success': True,
            'message': 'سبد خرید خالی شد',
            'cart_total_quantity': 0,
            'cart_total_price': 0,
        })
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)}, status=400)


def cart_data_api(request):
    """دریافت اطلاعات سبد خرید با اطلاعات تخفیف"""
    cart = Cart(request)

    items = []
    for item in cart:
        product = item['product']
        quantity = item['quantity']

        # دریافت اطلاعات تخفیف کامل برای این محصول با این تعداد
        discount_info = product.get_final_price_info(quantity=quantity)

        items.append({
            'product_id': product.id,
            'name': product.title,
            'price': item['price'],  # قیمت واحد نهایی (تخفیف خورده)
            'price_display': f"{int(item['price']):,}",
            'original_price': float(product.price) if product.price else 0,
            'original_price_display': f"{int(product.price):,}" if product.price else None,
            'quantity': quantity,
            'total': item['total'],
            'total_display': f"{int(item['total']):,}",
            'image': product.image.url if product.image and hasattr(product.image, 'url') else '/media/images/placeholder.jpg',
            'slug': product.slug,
            'code': product.code,
            'brand': product.brand.title if product.brand else 'برند',
            'has_discount': discount_info['has_discount'],
            'discount_percent': discount_info['discount_percent'],
            'discount_title': discount_info['discount_title'],
            'discount_amount': discount_info['discount_amount'],
            'discount_amount_display': discount_info['discount_amount_display'],
        })

    return JsonResponse({
        'success': True,
        'items': items,
        'total_price': cart.get_total_price(),
        'total_price_display': f"{int(cart.get_total_price()):,}",
        'total_quantity': cart.get_total_quantity(),
        'items_count': len(cart.cart)
    })