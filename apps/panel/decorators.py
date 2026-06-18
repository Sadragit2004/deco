# apps/admin_panel/decorators.py

from django.contrib.auth.decorators import user_passes_test
from functools import wraps
from django.contrib import messages

def admin_required(function=None, redirect_url='user:login'):
    """
    دکوراتور برای اطمینان از اینکه کاربر ادمین است (is_staff=True)
    """
    actual_decorator = user_passes_test(
        lambda u: u.is_authenticated and u.is_staff,
        login_url=redirect_url,
        redirect_field_name=None
    )
    if function:
        return actual_decorator(function)
    return actual_decorator

def superuser_required(function=None, redirect_url='admin_panel:dashboard'):
    """
    فقط سوپریوزرها می‌توانند دسترسی داشته باشند
    """
    actual_decorator = user_passes_test(
        lambda u: u.is_authenticated and u.is_superuser,
        login_url=redirect_url,
        redirect_field_name=None
    )
    if function:
        return actual_decorator(function)
    return actual_decorator