# middlewares/admin_verification_middleware.py

from django.utils.deprecation import MiddlewareMixin
from django.shortcuts import redirect


class AdminVerificationMiddleware(MiddlewareMixin):

    """
    Middleware برای مدیریت دسترسی کاربران
    """

    # ==================== لیست سفید ثابت (همیشه عمومی) ====================
    PUBLIC_PREFIXES = [
        '/static/',
        '/media/',
    ]

    # ==================== لیست سفید دلخواه (شما تعیین می‌کنید) ====================
    CUSTOM_PUBLIC_PATHS = [
        '/accounts/login/',
        '/admin/',
        '/accounts/verify/',
        '/accounts/verify-code/',
        '/accounts/logout/',
        # مسیرهای موبایل و هرچیزی که خودت اضافه کنی اینجا می‌نویسی
    ]

    def __init__(self, get_response):
        super().__init__(get_response)
        self.get_response = get_response

    def __call__(self, request):
        response = self.process_request(request)
        if response:
            return response
        return self.get_response(request)

    def is_public_path(self, path):
        """آیا مسیر عمومی است (بدون نیاز به لاگین)؟"""
        # بررسی پیشوندهای ثابت
        for prefix in self.PUBLIC_PREFIXES:
            if path.startswith(prefix):
                return True

        # بررسی مسیرهای دلخواه (exact match یا startswith برای مسیرهای دارای پارامتر)
        for public_path in self.CUSTOM_PUBLIC_PATHS:
            if path == public_path:
                return True
            if public_path.endswith('/') and path.startswith(public_path):
                return True

        return False

    def process_request(self, request):
        path = request.path_info

        # ========== مسیرهای عمومی ==========
        if self.is_public_path(path):
            return None  # دسترسی آزاد (لاگین هم نمی‌خواد)

        # ========== کاربر لاگین نکرده ==========
        if not request.user.is_authenticated:
            return redirect(f'/accounts/login/?next={request.path}')

        # ========== ادمین‌ها و سوپر یوزرها ==========
        # همه چیز براشون آزاده، هیچ محدودیتی ندارن
        if request.user.is_superuser or request.user.is_staff:
            return None

        # ========== کاربر لاگین کرده ولی تأیید نشده ==========
        try:
            is_verified = request.user.security.isVerfiyByManager
        except:
            is_verified = False

        if not is_verified:
            # فقط میتونه به /wait بره
            if path != '/wait/' and not path.startswith('/wait/'):
                return redirect('/wait/')
            return None

        # ========== کاربر تایید شده ==========
        # اگه تایید شده و خواست بره /wait ببرش خونه
        if path == '/wait/' or path.startswith('/wait/'):
            return redirect('/')

        return None