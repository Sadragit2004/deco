# middleware.py
from django.utils.deprecation import MiddlewareMixin
from django.utils import timezone


class UserActivityMiddleware(MiddlewareMixin):
    def process_request(self, request):
        if request.user.is_authenticated:
            # به‌روز رسانی آخرین فعالیت
            request.user.last_activity = timezone.now()
            request.user.is_online = True
            request.user.save(update_fields=['last_activity', 'is_online'])