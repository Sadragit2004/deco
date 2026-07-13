from django.shortcuts import render, redirect
from django.contrib import messages
from django.core.exceptions import ValidationError
from ...forms.auth.login_form import MobileForm
from ...service.auth_service import AuthService

def send_mobile(request):
    next_url = request.GET.get("next")
    if request.method == "POST":
        form = MobileForm(request.POST)
        if form.is_valid():
            mobile = form.cleaned_data['mobileNumber']

            try:
                # فقط کاربر فعال را دریافت می‌کنیم
                user = AuthService.get_active_user(mobile)
                security = AuthService.get_or_create_security(user)
                AuthService.send_activation_code(security, mobile)

                request.session["mobileNumber"] = mobile
                if next_url:
                    request.session["next_url"] = next_url

                messages.success(request, "کد فعال‌سازی ارسال شد")
                return redirect("account:verify_code")

            except ValidationError as e:
                messages.error(request, str(e))
                # هیچ کاربری ایجاد نمی‌شود
                return render(request, "user_app/login.html", {"form": form, "next": next_url})
    else:
        form = MobileForm()
    return render(request, "user_app/login.html", {"form": form, "next": next_url})