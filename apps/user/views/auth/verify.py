from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth import login
from django.utils import timezone
from django.http import JsonResponse
from ...forms.auth.verify_form import VerificationCodeForm
from ...models.user import CustomUser
from ...service.auth_service import AuthService

def verify_code(request):
    mobile = request.session.get("mobileNumber")
    next_url = request.session.get("next_url")

    if not mobile:
        messages.error(request, "شماره موبایل یافت نشد.")
        return redirect("account:send_mobile")

    try:
        user = CustomUser.objects.get(mobileNumber=mobile)
        security = AuthService.get_or_create_security(user)
    except CustomUser.DoesNotExist:
        messages.error(request, "کاربر یافت نشد.")
        return redirect("account:send_mobile")

    # بررسی درخواست ارسال مجدد (AJAX)
    if request.method == "POST" and request.POST.get("resend") == "true":
        try:
            new_code = AuthService.send_activation_code(security, mobile)

            # محاسبه زمان جدید
            remaining_seconds = 0
            if security.expireCode:
                remaining_seconds = max(0, int((security.expireCode - timezone.now()).total_seconds()))

            return JsonResponse({
                'success': True,
                'remaining_seconds': remaining_seconds,
                'message': 'کد جدید با موفقیت ارسال شد'
            })
        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': str(e)
            }, status=400)

    # محاسبه زمان باقی‌مانده برای تایمر
    remaining_seconds = 0
    can_resend = True

    if security.expireCode:
        remaining_seconds = max(0, int((security.expireCode - timezone.now()).total_seconds()))
        can_resend = remaining_seconds <= 0

    # تبدیل ثانیه به فرمت دقیقه:ثانیه
    remaining_time = f"{remaining_seconds // 60:02d}:{remaining_seconds % 60:02d}"

    # پردازش کد تایید (ارسال عادی فرم)
    if request.method == "POST" and "verification_code" in request.POST:
        form = VerificationCodeForm(request.POST)
        if form.is_valid():
            code = form.cleaned_data.get('activeCode') or request.POST.get('verification_code')
            try:
                AuthService.verify_code(security, code)
                AuthService.activate_user(user)
                login(request, user)
                messages.success(request, "ورود با موفقیت انجام شد.")
                return redirect(next_url or "main:index")
            except Exception as e:
                messages.error(request, str(e))
                return redirect("account:verify_code")
    else:
        form = VerificationCodeForm()

    context = {
        "form": form,
        "mobile": mobile,
        "remaining_time": remaining_time,
        "remaining_seconds": remaining_seconds,
        "can_resend": can_resend
    }

    return render(request, "user_app/code.html", context)