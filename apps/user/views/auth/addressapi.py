from django.http import JsonResponse
from django.views import View
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
import json
from ...models.profile import Province, City, UserAddress


class UserAddressesAPIView(LoginRequiredMixin, View):
    """دریافت لیست آدرس‌های کاربر"""

    def get(self, request):
        user = request.user
        addresses = UserAddress.objects.filter(user=user, is_active=True)

        addresses_data = []
        for addr in addresses:
            addresses_data.append({
                'id': str(addr.id),
                'address_type': addr.address_type,
                'address_type_display': addr.get_address_type_display(),
                'province_id': str(addr.province.id),
                'province_name': addr.province.name,
                'city_id': str(addr.city.id),
                'city_name': addr.city.name,
                'address_text': addr.address_text,
                'postal_code': addr.postal_code or '',
                'is_default': addr.is_default,
                'latitude': str(addr.latitude) if addr.latitude else '',
                'longitude': str(addr.longitude) if addr.longitude else '',
            })

        return JsonResponse({
            'success': True,
            'addresses': addresses_data
        })


class ProvinceCityAPIView(View):
    """دریافت لیست استان‌ها و شهرها"""

    def get(self, request):
        provinces = Province.objects.filter(is_active=True)

        provinces_data = []
        for province in provinces:
            cities = City.objects.filter(province=province, is_active=True)
            provinces_data.append({
                'id': str(province.id),
                'name': province.name,
                'cities': [
                    {'id': str(city.id), 'name': city.name}
                    for city in cities
                ]
            })

        return JsonResponse({
            'success': True,
            'provinces': provinces_data
        })


@method_decorator(csrf_exempt, name='dispatch')
class AddAddressAPIView(LoginRequiredMixin, View):
    """افزودن آدرس جدید"""

    def post(self, request):
        try:
            data = json.loads(request.body)
            user = request.user

            # دریافت استان و شهر
            province_id = data.get('province_id')
            city_id = data.get('city_id')

            try:
                province = Province.objects.get(id=province_id)
                city = City.objects.get(id=city_id)
            except:
                return JsonResponse({'success': False, 'error': 'استان یا شهر نامعتبر است'})

            # ایجاد آدرس جدید
            address = UserAddress.objects.create(
                user=user,
                address_type=data.get('address_type', 'home'),
                province=province,
                city=city,
                address_text=data.get('address_text'),
                postal_code=data.get('postal_code', ''),
                is_default=data.get('is_default', False)
            )

            # اگه آدرس پیش‌فرض بود، بقیه رو آپدیت کن
            if address.is_default:
                UserAddress.objects.filter(user=user).exclude(id=address.id).update(is_default=False)

            return JsonResponse({
                'success': True,
                'message': 'آدرس با موفقیت اضافه شد',
                'address_id': str(address.id)
            })

        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})


@method_decorator(csrf_exempt, name='dispatch')
class SetDefaultAddressAPIView(LoginRequiredMixin, View):
    """تنظیم آدرس پیش‌فرض"""

    def post(self, request):
        try:
            data = json.loads(request.body)
            address_id = data.get('address_id')

            # غیرفعال کردن پیش‌فرض بقیه آدرس‌ها
            UserAddress.objects.filter(user=request.user).update(is_default=False)

            # فعال کردن آدرس انتخاب شده
            UserAddress.objects.filter(id=address_id, user=request.user).update(is_default=True)

            return JsonResponse({'success': True, 'message': 'آدرس پیش‌فرض تغییر کرد'})

        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})


@method_decorator(csrf_exempt, name='dispatch')
class DeleteAddressAPIView(LoginRequiredMixin, View):
    """حذف آدرس"""

    def post(self, request):
        try:
            data = json.loads(request.body)
            address_id = data.get('address_id')

            UserAddress.objects.filter(id=address_id, user=request.user).delete()

            return JsonResponse({'success': True, 'message': 'آدرس حذف شد'})

        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})




from django.http import JsonResponse
from django.contrib.auth.decorators import login_required

@login_required
def get_shop_name(request):
    print("=== USER:", request.user.mobileNumber)  # دیباگ
    print("=== SHOP NAME:", request.user.shop_name)  # دیباگ

    return JsonResponse({
        'shop_name': request.user.shop_name if request.user.shop_name else ''
    })