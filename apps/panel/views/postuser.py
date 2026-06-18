# apps/panel/views.py - فقط API افزودن کاربر

from django.shortcuts import render, get_object_or_404
from django.contrib.admin.views.decorators import staff_member_required
from django.views.decorators.http import require_http_methods
from django.http import JsonResponse
from django.core.files.base import ContentFile
from django.utils import timezone
import json
import os

from apps.user.models.user import CustomUser
from apps.user.models.profile import UserAddress, Province, City, Wallet, CustomerLoyalty


@staff_member_required
@require_http_methods(['POST'])
def api_add_user(request):
    """
    API افزودن کاربر جدید توسط ادمین
    مسیر: /panel/api/add-user/
    """
    try:
        # دریافت اطلاعات از فرم
        name = request.POST.get('name', '').strip()
        family = request.POST.get('family', '').strip()
        mobile_number = request.POST.get('mobileNumber', '').strip()
        email = request.POST.get('email', '').strip()
        shop_name = request.POST.get('shopName', '').strip()
        address_json = request.POST.get('address', 'null')

        # اعتبارسنجی شماره موبایل
        if not mobile_number:
            return JsonResponse({'status': 'error', 'message': 'شماره موبایل الزامی است'}, status=400)

        # بررسی وجود کاربر
        if CustomUser.objects.filter(mobileNumber=mobile_number).exists():
            return JsonResponse({'status': 'error', 'message': 'این شماره موبایل قبلاً ثبت شده است'}, status=400)

        # ایجاد کاربر جدید
        user = CustomUser.objects.create(
            mobileNumber=mobile_number,
            name=name,
            family=family,
            email=email if email else None,
            shop_name=shop_name if shop_name else None,
            is_active=True,
            is_staff=False,
            is_superuser=False,
            createAt=timezone.now()
        )

        # تنظیم رمز عبور پیش‌فرض (شماره موبایل)
        user.set_password(mobile_number)
        user.save()

        # پردازش آواتار
        if request.FILES.get('avatar'):
            avatar = request.FILES['avatar']
            ext = os.path.splitext(avatar.name)[1]
            filename = f'avatars/user_{user.id}{ext}'
            user.avatar.save(filename, ContentFile(avatar.read()), save=True)

        # پردازش آدرس
        if address_json and address_json != 'null':
            try:
                address_data = json.loads(address_json)
                province_name = address_data.get('province', '').strip()
                city_name = address_data.get('city', '').strip()
                full_address = address_data.get('fullAddress', '').strip()
                postal_code = address_data.get('postalCode', '').strip()

                if province_name and city_name and full_address:
                    # ایجاد یا دریافت استان
                    province, _ = Province.objects.get_or_create(
                        name=province_name,
                        defaults={'is_active': True}
                    )

                    # ایجاد یا دریافت شهر
                    city, _ = City.objects.get_or_create(
                        province=province,
                        name=city_name,
                        defaults={'is_active': True}
                    )

                    # ایجاد آدرس
                    UserAddress.objects.create(
                        user=user,
                        address_type='home',
                        province=province,
                        city=city,
                        address_text=full_address,
                        postal_code=postal_code if postal_code else None,
                        is_default=True,
                        is_active=True
                    )
            except Exception as e:
                print(f"خطا در ذخیره آدرس: {e}")

        # ایجاد کیف پول برای کاربر
        Wallet.objects.get_or_create(
            user=user,
            defaults={
                'balance': 0,
                'frozen_balance': 0
            }
        )

        # ایجاد حساب وفاداری (لویالتی)
        CustomerLoyalty.objects.get_or_create(
            user=user,
            defaults={
                'total_points': 0,
                'total_coins': 0,
                'current_tier': 'bronze',
                'lifetime_purchase': 0
            }
        )

        return JsonResponse({
            'status': 'success',
            'message': 'کاربر با موفقیت ایجاد شد',
            'user': {
                'id': str(user.id),
                'mobileNumber': user.mobileNumber,
                'name': user.name,
                'family': user.family,
                'email': user.email,
                'shop_name': user.shop_name,
                'created_at': user.createAt.strftime('%Y/%m/%d')
            }
        })

    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=400)


@staff_member_required
@require_http_methods(['POST'])
def api_admin_login_check(request):
    """
    بررسی رمز عبور مدیر ارشد
    مسیر: /panel/api/admin-login-check/
    """
    try:
        data = json.loads(request.body)
        password = data.get('password', '')

        # بررسی رمز عبور با کاربر فعلی
        if request.user.check_password(password):
            return JsonResponse({'status': 'success', 'message': 'رمز عبور صحیح است'})
        else:
            return JsonResponse({'status': 'error', 'message': 'رمز عبور اشتباه است'}, status=401)

    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=400)