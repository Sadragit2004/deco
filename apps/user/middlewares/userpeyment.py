# peyment/middleware.py - نسخه نهایی خیلی ساده

from django.shortcuts import redirect
from django.utils.deprecation import MiddlewareMixin
from django.contrib import messages
from django.http import JsonResponse

from apps.user.models import UserSecurity


class MembershipRequiredMiddleware(MiddlewareMixin):
    """
    میدلور بررسی حق عضویت
    فقط چک میکنه isPeymentuser == True باشه
    """

    PROTECTED_URLS = [
        '/order/',
       
        '/pro/',
    ]

    def process_request(self, request):
        # فقط برای کاربران لاگین شده
        if not request.user.is_authenticated:
            return None

        # بررسی سه URL
        for protected_url in self.PROTECTED_URLS:
            if request.path.startswith(protected_url):
                # فقط چک کن isPeymentuser == True
                try:
                    security = UserSecurity.objects.get(user=request.user)
                    if not security.isPeymentuser:
                        # برای AJAX
                        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                            return JsonResponse({
                                'status': 'error',
                                'message': 'برای دسترسی به این بخش باید حق عضویت را پرداخت کنید',
                                'redirect_url': '/peyment/membership/pay/page/'
                            }, status=403)

                        messages.error(request, 'برای دسترسی به این بخش باید حق عضویت را پرداخت کنید')
                        return redirect('peyment:membership_payment_page')
                except UserSecurity.DoesNotExist:
                    # اگر不存在، یعنی حق عضویت ندارد
                    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                        return JsonResponse({
                            'status': 'error',
                            'message': 'برای دسترسی به این بخش باید حق عضویت را پرداخت کنید',
                            'redirect_url': '/peyment/membership/pay/page/'
                        }, status=403)

                    messages.error(request, 'برای دسترسی به این بخش باید حق عضویت را پرداخت کنید')
                    return redirect('peyment:membership_payment_page')

        return None