from django.shortcuts import render, redirect
from django.contrib import messages
from django.utils import timezone
from django.db import transaction
from django.views import View
from django.http import JsonResponse

from ...models.user import CustomUser
from ...models.profile import Province, City, UserAddress
from ...validators.mobile_validator import validate_iranian_mobile
from datetime import datetime
import re
import json

from django.shortcuts import render, redirect
from django.contrib import messages
from django.utils import timezone
from django.db import transaction
from django.views import View
from django.http import JsonResponse
from django.core.exceptions import ValidationError  # این رو هم اضافه کن


from persiantools.jdatetime import JalaliDate  # <--- این خط رو اضافه کن


class RegistrationFormView(View):
    """نمایش فرم پیش ثبت نام"""

    def get(self, request):
        provinces = Province.objects.filter(is_active=True)

        context = {
            'provinces': provinces,
            'page_title': 'پیش ثبت نام و درخواست همکاری',
        }
        return render(request, 'user_app/registration.html', context)

    def post(self, request):
        """پردازش فرم پیش ثبت نام"""
        try:
            with transaction.atomic():
                # گرفتن اطلاعات از فرم
                first_name = request.POST.get('first_name', '').strip()
                last_name = request.POST.get('last_name', '').strip()
                national_code = request.POST.get('national_code', '').strip()
                birth_date_persian = request.POST.get('birth_date', '').strip()
                mobile_number = request.POST.get('mobile_number', '').strip()
                phone_number = request.POST.get('phone_number', '').strip()
                email = request.POST.get('email', '').strip()
                shop_name = request.POST.get('shop_name', '').strip()

                # اطلاعات آدرس
                province_id = request.POST.get('province')
                city_id = request.POST.get('city')
                street = request.POST.get('street', '').strip()
                alley = request.POST.get('alley', '').strip()
                plaque = request.POST.get('plaque', '').strip()
                address_text = request.POST.get('address_text', '').strip()
                postal_code = request.POST.get('postal_code', '').strip()

                # فایل‌ها
                profile_image = request.FILES.get('profile_image')
                national_card_image = request.FILES.get('national_card_image')
                visit_card_image = request.FILES.get('visit_card_image')
                shop_image = request.FILES.get('shop_image')

                # اعتبارسنجی شماره موبایل
                try:
                    validate_iranian_mobile(mobile_number)
                except ValidationError as e:
                    messages.error(request, str(e))
                    return redirect('account:registration_form')

                # بررسی وجود شماره موبایل
                if CustomUser.objects.filter(mobileNumber=mobile_number).exists():
                    messages.error(request, 'این شماره موبایل قبلاً ثبت نام کرده است')
                    return redirect('account:registration_form')

                # تبدیل تاریخ شمسی به میلادی
                birth_date = None
                if birth_date_persian:
                    try:
                        # پاک کردن فاصله‌ها
                        birth_date_persian = birth_date_persian.strip()

                        parts = re.split(r'[\/\-]', birth_date_persian)

                        if len(parts) == 3:
                            persian_to_english = {
                                '۰': '0', '۱': '1', '۲': '2', '۳': '3', '۴': '4',
                                '۵': '5', '۶': '6', '۷': '7', '۸': '8', '۹': '9'
                            }

                            year_str = ''.join(persian_to_english.get(c, c) for c in parts[0].strip())
                            month_str = ''.join(persian_to_english.get(c, c) for c in parts[1].strip())
                            day_str = ''.join(persian_to_english.get(c, c) for c in parts[2].strip())

                            year = int(year_str)
                            month = int(month_str)
                            day = int(day_str)

                            # اعتبارسنجی سال (۱۳۰۰ تا ۱۵۰۰)
                            if not (1300 <= year <= 1500):
                                messages.error(request, 'سال باید بین ۱۳۰۰ تا ۱۵۰۰ باشد')
                                return redirect('account:registration_form')

                            if not (1 <= month <= 12):
                                messages.error(request, 'ماه باید بین ۱ تا ۱۲ باشد')
                                return redirect('account:registration_form')

                            if not (1 <= day <= 31):
                                messages.error(request, 'روز باید بین ۱ تا ۳۱ باشد')
                                return redirect('account:registration_form')

                            # تبدیل تاریخ شمسی به میلادی
                            jalali_date = JalaliDate(year, month, day)
                            birth_date = jalali_date.to_gregorian()

                            # اعتبارسنجی سن (حداقل ۱۸ سال)
                            today = datetime.now().date()
                            age = today.year - birth_date.year - (
                                (today.month, today.day) < (birth_date.month, birth_date.day)
                            )
                            if age < 18:
                                messages.error(request, 'سن باید حداقل ۱۸ سال باشد')
                                return redirect('account:registration_form')

                    except ValueError as e:
                        messages.error(request, f'تاریخ تولد نامعتبر است: {str(e)}')
                        return redirect('account:registration_form')
                    except Exception as e:
                        messages.error(request, 'تاریخ تولد نامعتبر است. فرمت صحیح: ۱۳۸۸/۰۳/۱۲')
                        return redirect('account:registration_form')

                # ایجاد کاربر جدید
                user = CustomUser(
                    mobileNumber=mobile_number,
                    email=email,
                    name=first_name,
                    family=last_name,
                    birth_date=birth_date,
                    shop_name=shop_name,
                    is_active=False,
                )

                # ذخیره فایل‌ها
                if profile_image:
                    user.avatar = profile_image
                if national_card_image:
                    user.nationCard = national_card_image
                if visit_card_image:
                    user.visitCard = visit_card_image
                if shop_image:
                    user.shopImage = shop_image

                user.save()

                # ذخیره آدرس
                if province_id and city_id:
                    province = Province.objects.get(id=province_id)
                    city = City.objects.get(id=city_id)

                    full_address = address_text or f"{street} {alley} {plaque}".strip()

                    UserAddress.objects.create(
                        user=user,
                        address_type='work',
                        province=province,
                        city=city,
                        address_text=full_address or 'آدرس فروشگاه',
                        postal_code=postal_code,
                        is_default=True,
                        is_active=True
                    )

                messages.success(request, 'درخواست شما با موفقیت ثبت شد. پس از تایید ادمین، حساب کاربری شما فعال خواهد شد.')
                return redirect('account:registration_success')

        except Exception as e:
            messages.error(request, f'خطا در ثبت درخواست: {str(e)}')
            return redirect('account:registration_form')


class RegistrationSuccessView(View):
    """نمایش صفحه موفقیت آمیز ثبت درخواست"""

    def get(self, request):
        return render(request, 'user_app/success.html')


class GetCitiesView(View):
    """دریافت شهرهای یک استان برای استفاده در فرم (AJAX)"""

    def get(self, request):
        province_id = request.GET.get('province_id')
        if province_id:
            cities = City.objects.filter(province_id=province_id, is_active=True).values('id', 'name')
            return JsonResponse({'cities': list(cities)})
        return JsonResponse({'cities': []})