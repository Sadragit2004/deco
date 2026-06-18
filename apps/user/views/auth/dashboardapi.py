from django.http import JsonResponse
from django.views import View
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.db.models import Sum, Count
from ...models.profile import CustomerLoyalty, Wallet
from apps.order.models import Order, OrderStatus
import os

class UserDashboardAPIView(LoginRequiredMixin, View):
    def get(self, request):
        user = request.user
        wallet, _ = Wallet.objects.get_or_create(user=user)
        loyalty, _ = CustomerLoyalty.objects.get_or_create(user=user)

        # محاسبه مجموع خرید فقط از روی lifetime_purchase خود لویالتی
        total_purchase = loyalty.lifetime_purchase

        # محاسبه تعداد سفارش‌های فعال
        active_orders_count = Order.objects.filter(
            user=user
        ).exclude(
            status__in=[OrderStatus.DELIVERED.value, OrderStatus.CANCELLED.value]
        ).count()

        # سطح‌بندی جدید با تخفیف‌های جدید
        discount_percent = {
            'premium': 15,
            'elite': 25,
            'private': 50,
            'select': 0
        }.get(loyalty.current_tier, 0)

        # نام فارسی سطوح جدید
        tier_persian = {
            'premium': 'پریمیوم',
            'elite': 'الیت',
            'private': 'پرایویت',
            'انتخاب شده': 'select'
        }.get(loyalty.current_tier, 'انتخاب شده')

        avatar_url = user.avatar.url if user.avatar else '/media/images/default-avatar.jpg'

        data = {
            'success': True,
            'data': {
                'user': {
                    'mobile': user.mobileNumber,
                    'name': user.name or '',
                    'family': user.family or '',
                    'full_name': f"{user.name or ''} {user.family or ''}".strip() or user.mobileNumber,
                    'email': user.email or '',
                    'gender': 'مرد' if user.gender == 'M' else 'زن',
                    'avatar_url': avatar_url,
                    'shop_name': user.shop_name or ''
                },
                'wallet': {
                    'balance': int(wallet.balance),
                    'balance_display': f"{wallet.balance:,}",
                    'frozen_balance': int(wallet.frozen_balance),
                    'frozen_balance_display': f"{wallet.frozen_balance:,}",
                },
                'loyalty': {
                    'total_coins': loyalty.total_coins,
                    'total_coins_display': f"{loyalty.total_coins:,}",
                    'total_points': loyalty.total_points,
                    'current_tier': loyalty.current_tier,
                    'current_tier_display': tier_persian,
                    'lifetime_purchase': int(loyalty.lifetime_purchase),
                    'lifetime_purchase_display': f"{int(loyalty.lifetime_purchase):,}",
                },
                'stats': {
                    'active_orders_count': active_orders_count,
                    'total_purchase': int(total_purchase),
                    'total_purchase_display': f"{int(total_purchase):,}",
                    'membership_level': tier_persian,
                    'special_discount': f"{discount_percent}%",
                }
            }
        }

        return JsonResponse(data)


@method_decorator(csrf_exempt, name='dispatch')
class UploadAvatarAPIView(LoginRequiredMixin, View):
    def post(self, request):
        try:
            user = request.user
            if 'avatar' in request.FILES:
                if user.avatar:
                    try:
                        os.remove(user.avatar.path)
                    except:
                        pass
                user.avatar = request.FILES['avatar']
                user.save()
                return JsonResponse({
                    'success': True,
                    'avatar_url': user.avatar.url,
                    'message': 'عکس با موفقیت آپلود شد'
                })
            return JsonResponse({'success': False, 'error': 'فایلی ارسال نشده'})
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})


@method_decorator(csrf_exempt, name='dispatch')
class DeleteAvatarAPIView(LoginRequiredMixin, View):
    def post(self, request):
        try:
            user = request.user
            if user.avatar:
                try:
                    os.remove(user.avatar.path)
                except:
                    pass
                user.avatar = None
                user.save()
            return JsonResponse({
                'success': True,
                'message': 'عکس با موفقیت حذف شد'
            })
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})