import logging
logger = logging.getLogger(__name__)
from django.utils import timezone
from django.http import HttpResponseForbidden
from datetime import timedelta
import random
import web.settings as settings
import os
from uuid import uuid4
from functools import wraps


import socket

def has_internet_connection():
    """
    Check if the device has an active internet connection.

    Returns:
        bool: True if the device has an active internet connection, False otherwise.
    """
    try:
        # Try to connect to a well-known website
        socket.create_connection(("www.google.com", 80))
        return True
    except OSError:
        pass

    try:
        # Try to connect to a different well-known website
        socket.create_connection(("www.example.com", 80))
        return True
    except OSError:
        pass

    return False

def create_random_code(num):
    import random
    num-=1
    return random.randint(10**num,10**(num+1)-1)



class FileUpload:


    def __init__(self,dir,prefix):
        self.dir = dir
        self.prefix = prefix



    def upload_to(self,instance,filename):
        filename,ext=os.path.splitext(filename)
        return f'{self.dir}/{self.prefix}/{uuid4()}{filename}{ext}'





def rate_limit_ip(max_requests, time_frame_seconds=None, time_frame_minutes=None, time_frame_hours=None):


    def decorator(view_func):

        from apps.user.models.loguser_model import BlockedIP,RequestLog

        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            # محاسبه کل زمان بر حسب ثانیه
            total_seconds = 0
            if time_frame_seconds:
                total_seconds += time_frame_seconds
            if time_frame_minutes:
                total_seconds += time_frame_minutes * 60
            if time_frame_hours:
                total_seconds += time_frame_hours * 3600

            if not total_seconds:
                total_seconds = 3600  # مقدار پیش‌فرض: 1 ساعت

            # دریافت IP کاربر
            ip = get_client_ip(request)

            # بررسی وجود IP در لیست بلاک‌شده‌های فعال
            blocked_ip = BlockedIP.objects.filter(
                ip_address=ip,
                is_active=True
            ).first()

            if blocked_ip:
                # بررسی انقضای بلاک
                if blocked_ip.is_block_expired():
                    blocked_ip.is_active = False
                    blocked_ip.save()
                else:
                    return HttpResponseForbidden(
                        f'دسترسی شما به این سرویس موقتاً محدود شده است. دلیل: {blocked_ip.reason}'
                    )

            # ساخت کلید برای لاگ درخواست‌ها
            request_log_key = f'request_log_{ip}'
            request_log = RequestLog.objects.filter(ip_address=ip).order_by('-timestamp')

            # محاسبه درخواست‌های اخیر
            time_threshold = timezone.now() - timedelta(seconds=total_seconds)
            recent_requests = request_log.filter(timestamp__gte=time_threshold).count()

            # ذخیره لاگ درخواست فعلی
            RequestLog.objects.create(ip_address=ip)

            # بررسی تعداد درخواست‌ها
            if recent_requests >= max_requests:
                # بلاک کردن IP
                BlockedIP.objects.create(
                    ip_address=ip,
                    max_requests=max_requests,
                    time_frame_seconds=total_seconds,
                    requests_count=recent_requests,
                    reason=f'تعداد درخواست‌ها بیش از حد مجاز ({max_requests} درخواست در {total_seconds} ثانیه)'
                )
                return HttpResponseForbidden(
                    f'تعداد درخواست‌های شما بیش از حد مجاز است. IP شما برای {total_seconds} ثانیه بلاک شد.'
                )

            return view_func(request, *args, **kwargs)
        return _wrapped_view
    return decorator


def get_client_ip(request):
    """
    دریافت IP واقعی کاربر با در نظر گرفتن X-Forwarded-For
    """
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip



from decimal import Decimal

def price_by_delivery_tax(price, discount=0):
    # تبدیل قیمت به Decimal برای دقت بیشتر
    price_decimal = Decimal(str(price))

    tax = price_decimal * Decimal('0.09')
    total_sum = price_decimal + tax
    total_sum = total_sum - (total_sum * Decimal(str(discount)) / Decimal('100'))

    return int(total_sum), int(tax)







from sms_ir import SmsIr
def send_sms(number,code):

    pass
    sms_ir = SmsIr('he4QV5RJiXYsfgjHBpgjpJ2GMFtemy28GSEcDlCpEweK9q0ahroGcmgT5kexuJUR')

    result = sms_ir.send_verify_code(
        number=str(number),
        template_id=172582,
        parameters=[
            {

                "name" : "CODE",
                "value": str(code)

            }
        ],
    )



# apps/discount/utils.py
from decimal import Decimal
import math


def get_product_discount_info(product, quantity=1, cart_amount=0):
    """
    تابع سراسری برای دریافت اطلاعات تخفیف محصول
    این تابع در هر جایی (ویوها، تمپلیت‌ها، APIها) قابل استفاده است

    پارامترها:
    - product: شیء محصول
    - quantity: تعداد (پیش‌فرض 1)
    - cart_amount: مبلغ کل سبد خرید (پیش‌فرض 0)

    خروجی:
    {
        'has_discount': bool,
        'discount_amount': float,
        'discount_percent': int,
        'discount_type': str | None,
        'discount_title': str | None,
        'original_price': float,
        'original_price_display': str,
        'final_price': float,
        'final_price_display': str,
        'saved_percent': int,
        'badge_text': str | None,
        'badge_class': str | None
    }
    """
    # مقدار پیش‌فرض
    default_result = {
        'has_discount': False,
        'discount_amount': 0,
        'discount_percent': 0,
        'discount_type': None,
        'discount_title': None,
        'original_price': 0,
        'original_price_display': '۰',
        'final_price': 0,
        'final_price_display': '۰',
        'saved_percent': 0,
        'badge_text': None,
        'badge_class': None
    }

    try:
        # گرفتن قیمت اصلی
        original_price = float(product.price) if product.price else 0
        if original_price == 0:
            return default_result

        # محاسبه تخفیف
        best_discount = None
        discount_amount = 0

        if hasattr(product, 'get_best_discount'):
            result = product.get_best_discount(quantity, cart_amount)

            # مدیریت انواع خروجی
            if result is not None:
                if isinstance(result, tuple) and len(result) == 2:
                    best_discount, discount_amount = result
                    discount_amount = discount_amount or 0
                elif isinstance(result, dict):
                    best_discount = result.get('discount')
                    discount_amount = result.get('amount', 0)

        # محاسبه قیمت نهایی
        final_price = original_price - discount_amount if discount_amount > 0 else original_price
        has_discount = discount_amount > 0 and discount_amount < original_price

        if not has_discount:
            return {
                'has_discount': False,
                'discount_amount': 0,
                'discount_percent': 0,
                'discount_type': None,
                'discount_title': None,
                'original_price': original_price,
                'original_price_display': f"{int(original_price):,}",
                'final_price': original_price,
                'final_price_display': f"{int(original_price):,}",
                'saved_percent': 0,
                'badge_text': None,
                'badge_class': None
            }

        # محاسبه درصد تخفیف
        saved_percent = int((discount_amount / original_price) * 100)
        discount_percent = 0
        discount_type = None
        discount_title = None

        if best_discount:
            if hasattr(best_discount, 'discount_type'):
                discount_type = best_discount.discount_type
                if discount_type == 'percent':
                    discount_percent = int(best_discount.amount) if best_discount.amount else saved_percent
            if hasattr(best_discount, 'title'):
                discount_title = best_discount.title

        # تنظیم متن و کلاس badge
        badge_text = None
        badge_class = None

        if discount_percent > 0:
            badge_text = f"{discount_percent}٪ تخفیف"
            badge_class = "bg-red-500 text-white px-2 py-1 rounded text-xs font-bold"
        else:
            badge_text = f"{int(discount_amount):,} تومان تخفیف"
            badge_class = "bg-orange-500 text-white px-2 py-1 rounded text-xs font-bold"

        # تخفیف بالای 30% برجسته‌تر
        if saved_percent > 30:
            badge_class = "bg-red-600 text-white px-2 py-1 rounded text-xs font-bold animate-pulse"

        return {
            'has_discount': True,
            'discount_amount': discount_amount,
            'discount_percent': discount_percent,
            'discount_type': discount_type,
            'discount_title': discount_title,
            'original_price': original_price,
            'original_price_display': f"{int(original_price):,}",
            'final_price': final_price,
            'final_price_display': f"{int(final_price):,}",
            'saved_percent': saved_percent,
            'badge_text': badge_text,
            'badge_class': badge_class
        }

    except Exception as e:
        print(f"Error in get_product_discount_info: {e}")
        return default_result


def prepare_products_with_discount(products, quantity=1, cart_amount=0):
    """
    آماده‌سازی لیست محصولات با تخفیف برای استفاده در ویوها

    پارامترها:
    - products: queryset یا لیست محصولات
    - quantity: تعداد پیش‌فرض
    - cart_amount: مبلغ سبد

    خروجی: لیست دیکشنری‌های آماده
    """
    result = []
    for product in products:
        discount_info = get_product_discount_info(product, quantity, cart_amount)

        result.append({
            'id': product.id,
            'title': product.title,
            'slug': product.slug,
            'code': product.code,
            'image': product.image.url if product.image else None,
            'brand': product.brand.title if product.brand else None,
            'price_display': discount_info['final_price_display'],
            'original_price_display': discount_info['original_price_display'] if discount_info['has_discount'] else None,
            'has_discount': discount_info['has_discount'],
            'discount_percent': discount_info['discount_percent'],
            'badge_text': discount_info['badge_text'],
            'badge_class': discount_info['badge_class'],
        })

    return result