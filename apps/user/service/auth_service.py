from django.utils import timezone
from datetime import timedelta
from django.contrib.auth import login
from django.contrib import messages
from django.core.exceptions import ValidationError
from ..models.user import CustomUser
from ..models.security import UserSecurity
from ..validators.common import generate_activation_code
from ..validators.code_validator import validate_activation_code
import utils

class AuthService:
    @staticmethod
    def get_active_user(mobile):
        """
        دریافت کاربر فعال بر اساس شماره موبایل
        فقط کاربرانی که وجود دارند و is_active=True هستند برگردانده می‌شوند
        """
        try:
            user = CustomUser.objects.get(mobileNumber=mobile, is_active=True)
            return user
        except CustomUser.DoesNotExist:
            raise ValidationError("کاربری با این شماره موبایل یافت نشد یا غیرفعال است.")

    @staticmethod
    def get_or_create_security(user):
        """
        گرفتن یا ایجاد UserSecurity
        """
        security, created = UserSecurity.objects.get_or_create(user=user)
        return security

    @staticmethod
    def send_activation_code(security, mobile='', code_length=5, expire_minutes=2):
        """
        تولید و ذخیره کد فعال‌سازی
        """
        code = generate_activation_code(code_length)
        expire_time = timezone.now() + timedelta(minutes=expire_minutes)
        security.activeCode = code
        utils.send_sms(mobile, code)
        security.expireCode = expire_time
        security.isBan = False
        security.save()
        return code

    @staticmethod
    def verify_code(security, code):
        """
        بررسی صحت و انقضای کد
        """
        if security.expireCode < timezone.now():
            raise ValueError("کد منقضی شده است.")
        if not validate_activation_code(security, code):
            raise ValueError("کد واردشده معتبر نیست")
        # پاکسازی کد بعد از موفقیت
        security.activeCode = None
        security.expireCode = None
        security.save()
        return True

    @staticmethod
    def login_user(request, user):
        """
        لاگین کاربر
        """
        login(request, user)
        return True