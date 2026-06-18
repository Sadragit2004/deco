# apps/product/views.py - نسخه تصحیح شده

import json
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.contrib import messages
from django.core.paginator import Paginator
from apps.order.models import Product, Wishlist


@login_required
def check_in_wishlist(request, product_id):
    """بررسی اینکه محصول در لیست علاقه‌مندی هست یا نه (AJAX)"""
    try:
        exists = Wishlist.objects.filter(
            user=request.user,
            product_id=product_id,
            is_active=True
        ).exists()

        return JsonResponse({
            'success': True,
            'in_wishlist': exists
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'in_wishlist': False,
            'error': str(e)
        })


@login_required
def toggle_wishlist(request):
    """افزودن/حذف محصول به لیست علاقه‌مندی (AJAX)"""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'message': 'متد غیرمجاز'}, status=405)

    try:
        data = json.loads(request.body)
        product_id = data.get('product_id')

        if not product_id:
            return JsonResponse({'success': False, 'message': 'شناسه محصول یافت نشد'})

        product = get_object_or_404(Product, id=product_id)
        wishlist_item = Wishlist.objects.filter(user=request.user, product=product).first()

        if wishlist_item:
            wishlist_item.delete()
            return JsonResponse({
                'success': True,
                'added': False,
                'message': f'{product.title} از علاقه‌مندی‌ها حذف شد'
            })
        else:
            Wishlist.objects.create(
                user=request.user,
                product=product,
                product_title=product.title,
                product_price=product.price,
                product_image=product.image.url if product.image else '',
                product_slug=product.slug
            )
            return JsonResponse({
                'success': True,
                'added': True,
                'message': f'{product.title} به علاقه‌مندی‌ها اضافه شد'
            })

    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)})


@login_required
def wishlist_page(request):
    """صفحه لیست علاقه‌مندی‌ها"""
    wishlist_items = Wishlist.objects.filter(user=request.user, is_active=True).order_by('-added_at')

    # بروزرسانی قیمت‌ها - نسخه تصحیح شده
    items_with_prices = []
    for item in wishlist_items:
        # ایجاد یک دیکشنری برای هر آیتم با اطلاعات اضافی
        item_data = {
            'id': item.id,
            'product_id': item.product.id if item.product else None,
            'product_title': item.product_title,
            'product_slug': item.product_slug,
            'product_image': item.product_image,
            'product_price': item.product_price,
            'added_at': item.added_at,
            'is_active': item.is_active,
            'has_discount': False,
            'discount_percent': 0,
            'current_price': item.product_price,
            'product_deleted': not bool(item.product),
            'stock': 0,
        }

        if item.product:
            # محصول وجود دارد
            item_data['stock'] = item.product.stock or 0

            if hasattr(item.product, 'has_discount') and item.product.has_discount():
                item_data['has_discount'] = True
                item_data['discount_percent'] = item.product.get_discount_percent()
                item_data['current_price'] = item.product.get_final_price()
            else:
                item_data['current_price'] = item.product.price
        else:
            # محصول حذف شده
            item_data['current_price'] = item.product_price
            item_data['stock'] = 0

        items_with_prices.append(item_data)

    # Pagination
    paginator = Paginator(items_with_prices, 12)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'wishlist_items': page_obj,
        'total_items': wishlist_items.count(),
    }
    return render(request, 'product_app/products/wishlist.html', context)

@login_required
def remove_wishlist_item(request, item_id):
    """حذف آیتم از علاقه‌مندی"""
    import json
    from django.http import JsonResponse

    # برای AJAX (درخواست از جاوااسکریپت)
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        try:
            wishlist_item = get_object_or_404(Wishlist, id=item_id, user=request.user)
            product_title = wishlist_item.product_title
            wishlist_item.delete()

            return JsonResponse({
                'success': True,
                'message': f'{product_title} از لیست علاقه‌مندی‌ها حذف شد'
            })
        except Exception as e:
            return JsonResponse({
                'success': False,
                'message': str(e)
            }, status=400)

    # برای درخواست عادی GET
    try:
        wishlist_item = get_object_or_404(Wishlist, id=item_id, user=request.user)
        wishlist_item.delete()
        messages.success(request, 'محصول از لیست علاقه‌مندی‌ها حذف شد')
    except Exception as e:
        messages.error(request, f'خطا در حذف محصول: {str(e)}')

    return redirect('product:wishlist')


@login_required
def clear_wishlist(request):
    """پاک کردن تمام لیست علاقه‌مندی"""
    if request.method == 'POST':
        try:
            count = Wishlist.objects.filter(user=request.user).count()
            Wishlist.objects.filter(user=request.user).delete()
            return JsonResponse({
                'success': True,
                'message': f'{count} محصول از لیست علاقه‌مندی‌ها حذف شد'
            })
        except Exception as e:
            return JsonResponse({
                'success': False,
                'message': str(e)
            })
    return JsonResponse({'success': False, 'message': 'متد غیرمجاز'}, status=405)


@login_required
def get_wishlist_count(request):
    """دریافت تعداد محصولات لیست علاقه‌مندی (برای نمایش در هدر)"""
    try:
        count = Wishlist.objects.filter(user=request.user, is_active=True).count()
        return JsonResponse({'success': True, 'count': count})
    except Exception as e:
        return JsonResponse({'success': False, 'count': 0})