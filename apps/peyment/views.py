# peyment/views.py - نسخه نهایی کامل

from django.shortcuts import render, redirect
from django.views import View
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.conf import settings
from django.urls import reverse
from django.http import JsonResponse
import json
from django.utils import timezone
import requests
import time

from apps.order.models import Order
from apps.peyment.models import Peyment, PaymentMethod
from apps.user.models import CustomUser, UserSecurity
from apps.user.models.profile import Wallet, WalletTransaction
import utils


# تنظیمات ZarinPal
MERCHANT_ID = "6fe93958-6832-4fbc-be2f-aa85e63233bd"
ZP_API_REQUEST = "https://api.zarinpal.com/pg/v4/payment/request.json"
ZP_API_VERIFY = "https://api.zarinpal.com/pg/v4/payment/verify.json"
ZP_API_STARTPAY = "https://www.zarinpal.com/pg/StartPay/{authority}"
CALLBACK_URL = "https://sayamedical.com/peyment/verify/"


def send_request(request, order_id):
    """درخواست پرداخت سفارش و هدایت به درگاه زرین‌پال"""

    if not utils.has_internet_connection():
        messages.error(request, "اتصال اینترنت شما قابل تایید نیست", "danger")
        return redirect("order:cart_page")

    try:
        if not request.user.is_authenticated:
            messages.error(request, "لطفا ابتدا وارد حساب کاربری خود شوید")
            return redirect("user:login")

        try:
            order = Order.objects.get(id=order_id, user=request.user)
        except Order.DoesNotExist:
            messages.error(request, "سفارش یافت نشد")
            return redirect("order:cart_page")

        if order.status == 'paid':
            messages.error(request, "این سفارش قبلا پرداخت شده است")
            return redirect("main:index")

        # محاسبه مبلغ نهایی
        amount_param = request.GET.get('amount')

        if amount_param:
            amount = int(amount_param)
        else:
            order.refresh_from_db()
            amount = int(order.subtotal - order.discount_amount - order.coupon_discount + order.shipping_cost - order.used_from_wallet)
            if amount < 0:
                amount = 0

        # اگر مبلغ صفر شد، مستقیم تایید کن
        if amount <= 0:
            order.status = 'paid'
            order.paid_at = timezone.now()
            order.save(update_fields=['status', 'paid_at'])

            from apps.order.signals import deduct_product_stock, assign_coins_and_wallet_bonus
            deduct_product_stock(order)
            assign_coins_and_wallet_bonus(order)

            messages.success(request, "پرداخت با موفقیت انجام شد (استفاده از کیف پول)")
            return redirect("order:order_detail", order_id=order.id)

        # ایجاد رکورد پرداخت
        peyment = Peyment.objects.create(
            order=order,
            customer=request.user,
            amount=amount,
            description=f"پرداخت سفارش {order.order_number}",
            statusCode=0,
            isFinaly=False,
            payment_method=PaymentMethod.ONLINE.value
        )

        # ذخیره در سشن
        session_key = f"peyment_{order_id}_{int(time.time())}"
        request.session[session_key] = {
            "order_id": str(order.id),
            "peyment_id": str(peyment.id),
            "amount": str(amount),
            "type": "order",
            "timestamp": str(time.time())
        }
        request.session["current_peyment_key"] = session_key
        request.session.set_expiry(3600)

        # آماده‌سازی داده برای زرین‌پال
        req_data = {
            "merchant_id": MERCHANT_ID,
            "amount": amount,
            "callback_url": CALLBACK_URL,
            "description": f"پرداخت سفارش شماره {order.order_number} - سایت سایا مدیکال",
            "metadata": {
                "email": request.user.email if request.user.email else "",
                "mobile": request.user.mobileNumber
            }
        }

        headers = {
            "accept": "application/json",
            "content-type": "application/json"
        }

        response = requests.post(
            ZP_API_REQUEST,
            data=json.dumps(req_data),
            headers=headers,
            timeout=30
        )

        if response.status_code == 200:
            data = response.json()
            if 'data' in data and data['data'] and 'authority' in data['data']:
                authority = data['data']['authority']
                request.session[session_key]["authority"] = authority
                request.session.modified = True
                request.session["last_authority"] = authority
                return redirect(ZP_API_STARTPAY.format(authority=authority))
            else:
                peyment.statusCode = -2
                peyment.save()
                messages.error(request, "خطا از سمت درگاه پرداخت")
                return redirect("order:cart_page")
        else:
            messages.error(request, "خطا در ارتباط با درگاه پرداخت")
            return redirect("order:cart_page")

    except Exception as e:
        print(f"❌ خطا در send_request: {str(e)}")
        messages.error(request, f"خطای غیرمنتظره: {str(e)}")
        return redirect("order:cart_page")


# =============================== API برای پرداخت حق عضویت ===============================

class MembershipPaymentAPIView(LoginRequiredMixin, View):
    """API برای پرداخت مبلغ 5,000,000 تومان حق عضویت"""

    def get(self, request):
        """درخواست GET برای شروع پرداخت حق عضویت"""
        try:
            # بررسی وجود کاربر و احراز هویت
            if not request.user.is_authenticated:
                return JsonResponse({
                    'status': 'error',
                    'message': 'لطفا ابتدا وارد حساب کاربری خود شوید'
                }, status=401)

            # بررسی اینکه کاربر قبلاً حق عضویت پرداخت کرده است
            try:
                security = UserSecurity.objects.get(user=request.user)
                if security.isPeymentuser:
                    return JsonResponse({
                        'status': 'error',
                        'message': 'شما قبلاً حق عضویت را پرداخت کرده‌اید'
                    }, status=400)
            except UserSecurity.DoesNotExist:
                pass

            # بررسی اینکه کاربر قبلاً پرداخت نهایی 5 میلیونی داشته باشد
            existing_membership_payment = Peyment.objects.filter(
                customer=request.user,
                amount=50000000,
                isFinaly=True
            ).exists()

            if existing_membership_payment:
                return JsonResponse({
                    'status': 'error',
                    'message': 'شما قبلاً حق عضویت را پرداخت کرده‌اید'
                }, status=400)

            # مقدار مبلغ ثابت 5,000,000 تومان
            amount = 50000000

            # ایجاد رکورد پرداخت جدید (بدون سفارش)
            peyment = Peyment.objects.create(
                order=None,  # بدون سفارش
                customer=request.user,
                amount=amount,
                description=f"پرداخت حق عضویت - کاربر {request.user.mobileNumber}",
                statusCode=0,
                isFinaly=False,
                payment_method=PaymentMethod.ONLINE.value
            )

            # ذخیره در سشن
            session_key = f"membership_{request.user.id}_{int(time.time())}"
            request.session[session_key] = {
                "peyment_id": str(peyment.id),
                "amount": str(amount),
                "type": "membership",
                "membership_amount": amount,
                "timestamp": str(time.time())
            }
            request.session["current_peyment_key"] = session_key
            request.session.set_expiry(3600)

            # آماده‌سازی داده برای زرین‌پال
            req_data = {
                "merchant_id": MERCHANT_ID,
                "amount": amount,
                "callback_url": CALLBACK_URL,
                "description": f"پرداخت حق عضویت سایت سایا مدیکال - کاربر {request.user.mobileNumber}",
                "metadata": {
                    "email": request.user.email if request.user.email else "",
                    "mobile": request.user.mobileNumber
                }
            }

            headers = {
                "accept": "application/json",
                "content-type": "application/json"
            }

            response = requests.post(
                ZP_API_REQUEST,
                data=json.dumps(req_data),
                headers=headers,
                timeout=30
            )

            if response.status_code == 200:
                data = response.json()
                if 'data' in data and data['data'] and 'authority' in data['data']:
                    authority = data['data']['authority']
                    request.session[session_key]["authority"] = authority
                    request.session.modified = True
                    request.session["last_authority"] = authority

                    # برگرداندن لینک پرداخت
                    payment_url = ZP_API_STARTPAY.format(authority=authority)
                    return JsonResponse({
                        'status': 'success',
                        'message': 'درخواست پرداخت با موفقیت ایجاد شد',
                        'payment_url': payment_url,
                        'authority': authority,
                        'amount': amount
                    })
                else:
                    peyment.statusCode = -2
                    peyment.save()
                    return JsonResponse({
                        'status': 'error',
                        'message': 'خطا از سمت درگاه پرداخت'
                    }, status=500)
            else:
                return JsonResponse({
                    'status': 'error',
                    'message': 'خطا در ارتباط با درگاه پرداخت'
                }, status=500)

        except Exception as e:
            print(f"❌ خطا در MembershipPaymentAPIView: {str(e)}")
            return JsonResponse({
                'status': 'error',
                'message': f'خطای غیرمنتظره: {str(e)}'
            }, status=500)

    def post(self, request):
        """درخواست POST برای شروع پرداخت حق عضویت (همانند GET)"""
        return self.get(request)


def check_membership_status(request):
    """API برای بررسی وضعیت حق عضویت کاربر"""
    try:
        if not request.user.is_authenticated:
            return JsonResponse({
                'status': 'error',
                'message': 'لطفا ابتدا وارد شوید'
            }, status=401)

        # بررسی وضعیت حق عضویت
        try:
            security = UserSecurity.objects.get(user=request.user)
            is_member = security.isPeymentuser
        except UserSecurity.DoesNotExist:
            is_member = False

        # بررسی پرداخت موفق 5 میلیونی
        has_paid = Peyment.objects.filter(
            customer=request.user,
            amount=50000000,
            isFinaly=True
        ).exists()

        return JsonResponse({
            'status': 'success',
            'is_member': is_member or has_paid,
            'has_active_membership': is_member,
            'has_successful_payment': has_paid,
            'message': 'کاربر عضو است' if (is_member or has_paid) else 'کاربر عضو نیست'
        })

    except Exception as e:
        return JsonResponse({
            'status': 'error',
            'message': str(e)
        }, status=500)


# =============================== صفحه پرداخت حق عضویت ===============================

class MembershipPaymentView(LoginRequiredMixin, View):
    """نمایش صفحه پرداخت حق عضویت ۵ میلیون تومانی"""

    def get(self, request):
        """نمایش صفحه پرداخت حق عضویت"""
        try:
            # بررسی وضعیت عضویت کاربر
            try:
                security = UserSecurity.objects.get(user=request.user)
                is_member = security.isPeymentuser
            except UserSecurity.DoesNotExist:
                is_member = False

            # بررسی پرداخت موفق قبلی ۵ میلیونی
            has_successful_payment = Peyment.objects.filter(
                customer=request.user,
                amount=50000000,
                isFinaly=True
            ).exists()

            # اگر قبلاً عضو شده یا پرداخت موفق داشته
            if is_member or has_successful_payment:
                # اگر کاربر عضو است ولی فلگ isPeymentuser False است، آن را اصلاح کن
                if has_successful_payment and not is_member:
                    try:
                        security = UserSecurity.objects.get(user=request.user)
                        security.isPeymentuser = True
                        security.isVerfiyByManager = True
                        security.save()
                    except UserSecurity.DoesNotExist:
                        UserSecurity.objects.create(
                            user=request.user,
                            isPeymentuser=True,
                            isVerfiyByManager=True
                        )

                context = {
                    'is_member': True,
                    'membership_amount': 50000000,
                    'membership_amount_toman': '۵,۰۰۰,۰۰۰'
                }
                return render(request, 'peyment_app/membership_payment.html', context)

            # بررسی پرداخت ناموفق یا در انتظار
            pending_payment = Peyment.objects.filter(
                customer=request.user,
                amount=50000000,
                isFinaly=False
            ).exclude(statusCode=0).first()

            context = {
                'is_member': False,
                'membership_amount': 50000000,
                'membership_amount_toman': '۵,۰۰۰,۰۰۰',
                'pending_payment': pending_payment
            }

            return render(request, 'peyment_app/membership_payment.html', context)

        except Exception as e:
            print(f"❌ خطا در MembershipPaymentView: {str(e)}")
            messages.error(request, f"خطا در نمایش صفحه: {str(e)}")
            return redirect("main:index")


# =============================== هدایت مستقیم به درگاه پرداخت حق عضویت ===============================

def membership_payment_redirect(request):
    """
    هدایت مستقیم کاربر به درگاه پرداخت حق عضویت
    (بدون نمایش صفحه واسط)
    """
    if not request.user.is_authenticated:
        messages.error(request, "لطفا ابتدا وارد حساب کاربری خود شوید")
        return redirect("user:login")

    # بررسی اینکه کاربر قبلاً حق عضویت پرداخت کرده است
    try:
        security = UserSecurity.objects.get(user=request.user)
        if security.isPeymentuser:
            messages.error(request, "شما قبلاً حق عضویت را پرداخت کرده‌اید")
            return redirect("main:index")
    except UserSecurity.DoesNotExist:
        pass

    # بررسی پرداخت موفق قبلی
    existing_payment = Peyment.objects.filter(
        customer=request.user,
        amount=50000000,
        isFinaly=True
    ).exists()

    if existing_payment:
        # اگر پرداخت موفق داشته ولی فلگ آپدیت نشده
        try:
            security = UserSecurity.objects.get(user=request.user)
            security.isPeymentuser = True
            security.isVerfiyByManager = True
            security.save()
        except UserSecurity.DoesNotExist:
            UserSecurity.objects.create(
                user=request.user,
                isPeymentuser=True,
                isVerfiyByManager=True
            )
        messages.error(request, "شما قبلاً حق عضویت را پرداخت کرده‌اید")
        return redirect("main:index")

    try:
        amount = 50000000

        # ایجاد رکورد پرداخت جدید
        peyment = Peyment.objects.create(
            order=None,
            customer=request.user,
            amount=amount,
            description=f"پرداخت حق عضویت - کاربر {request.user.mobileNumber}",
            statusCode=0,
            isFinaly=False,
            payment_method=PaymentMethod.ONLINE.value
        )

        # ذخیره در سشن
        session_key = f"membership_{request.user.id}_{int(time.time())}"
        request.session[session_key] = {
            "peyment_id": str(peyment.id),
            "amount": str(amount),
            "type": "membership",
            "membership_amount": amount,
            "timestamp": str(time.time())
        }
        request.session["current_peyment_key"] = session_key
        request.session.set_expiry(3600)

        # درخواست به زرین‌پال
        req_data = {
            "merchant_id": MERCHANT_ID,
            "amount": amount,
            "callback_url": CALLBACK_URL,
            "description": f"پرداخت حق عضویت سایت سایا مدیکال - کاربر {request.user.mobileNumber}",
            "metadata": {
                "email": request.user.email if request.user.email else "",
                "mobile": request.user.mobileNumber
            }
        }

        headers = {
            "accept": "application/json",
            "content-type": "application/json"
        }

        response = requests.post(
            ZP_API_REQUEST,
            data=json.dumps(req_data),
            headers=headers,
            timeout=30
        )

        if response.status_code == 200:
            data = response.json()
            if 'data' in data and data['data'] and 'authority' in data['data']:
                authority = data['data']['authority']
                request.session[session_key]["authority"] = authority
                request.session.modified = True
                request.session["last_authority"] = authority

                # هدایت به درگاه پرداخت
                return redirect(ZP_API_STARTPAY.format(authority=authority))
            else:
                peyment.statusCode = -2
                peyment.save()
                messages.error(request, "خطا از سمت درگاه پرداخت")
                return redirect("main:index")
        else:
            messages.error(request, "خطا در ارتباط با درگاه پرداخت")
            return redirect("main:index")

    except Exception as e:
        print(f"❌ خطا در membership_payment_redirect: {str(e)}")
        messages.error(request, f"خطای غیرمنتظره: {str(e)}")
        return redirect("main:index")


# =============================== ویو تایید پرداخت زرین‌پال ===============================

@method_decorator(csrf_exempt, name='dispatch')
class Zarin_pal_view_verfiy(LoginRequiredMixin, View):

    def get(self, request):
        t_status = request.GET.get("Status")
        t_authority = request.GET.get("Authority")

        if not t_status or not t_authority:
            messages.error(request, "پارامترهای لازم ارسال نشده است")
            return redirect("main:index")

        session_data = None
        session_key = None

        # پیدا کردن سشن مربوطه
        for key in list(request.session.keys()):
            if key.startswith("peyment_") or key.startswith("charge_wallet_") or key.startswith("membership_"):
                data = request.session.get(key)
                if data and data.get("authority") == t_authority:
                    session_data = data
                    session_key = key
                    break

        if not session_data:
            try:
                payment = Peyment.objects.filter(
                    customer=request.user,
                    isFinaly=False
                ).order_by('-createAt').first()
                if payment:
                    session_data = {
                        "peyment_id": str(payment.id),
                        "amount": str(payment.amount),
                        "type": "unknown"
                    }
            except Exception:
                pass

        if not session_data:
            messages.error(request, "اطلاعات پرداخت یافت نشد")
            return redirect("main:index")

        try:
            peyment_id = session_data.get("peyment_id")
            payment = Peyment.objects.get(id=peyment_id, customer=request.user)
        except Peyment.DoesNotExist:
            messages.error(request, "اطلاعات پرداخت نامعتبر است")
            return redirect("main:index")

        # پاک کردن سشن
        if session_key and session_key in request.session:
            del request.session[session_key]
        if "current_peyment_key" in request.session:
            del request.session["current_peyment_key"]
        if "last_authority" in request.session:
            del request.session["last_authority"]
        request.session.modified = True

        if t_status == "OK":
            return self.verify_payment(request, payment, t_authority, session_data)
        else:
            payment.statusCode = -10
            payment.save()
            return redirect("peyment:show_verfiy_unmessage", message="پرداخت لغو شد")

    def verify_payment(self, request, payment, authority, session_data):
        amount = session_data.get("amount")
        transaction_type = session_data.get("type", "order")

        req_data = {
            "merchant_id": MERCHANT_ID,
            "amount": int(amount),
            "authority": authority
        }

        headers = {
            "accept": "application/json",
            "content-type": "application/json"
        }

        try:
            response = requests.post(
                ZP_API_VERIFY,
                data=json.dumps(req_data),
                headers=headers,
                timeout=30
            )

            if response.status_code == 200:
                data = response.json()
                if 'data' in data and data['data']:
                    code = data['data'].get('code')

                    if code == 100:
                        # پرداخت موفق
                        payment.isFinaly = True
                        payment.statusCode = 100
                        if 'ref_id' in data['data']:
                            payment.refId = str(data['data']['ref_id'])
                        payment.save()

                        # پردازش بر اساس نوع تراکنش
                        if transaction_type == "charge_wallet":
                            # شارژ کیف پول
                            return self.process_wallet_charge(request, payment, session_data)
                        elif transaction_type == "membership":
                            # پرداخت حق عضویت
                            return self.process_membership_payment(request, payment, session_data)
                        else:
                            # پرداخت سفارش
                            return self.process_order_payment(request, payment, session_data)

                    elif code == 101:
                        payment.isFinaly = True
                        payment.statusCode = 101
                        if 'ref_id' in data['data']:
                            payment.refId = str(data['data']['ref_id'])
                        payment.save()
                        return redirect("peyment:show_sucess", message="این تراکنش قبلا تایید شده است")
                    else:
                        payment.statusCode = code
                        payment.save()
                        return redirect("peyment:show_verfiy_unmessage", message="خطا در پرداخت")
                else:
                    return redirect("peyment:show_verfiy_unmessage", message="خطا در تایید پرداخت")
            else:
                return redirect("peyment:show_verfiy_unmessage", message="خطا در ارتباط با درگاه")

        except Exception as e:
            return redirect("peyment:show_verfiy_unmessage", message=f"خطا: {str(e)}")

    def process_order_payment(self, request, payment, session_data):
        """پردازش پرداخت سفارش"""
        try:
            order_id = session_data.get("order_id")
            order = Order.objects.get(id=order_id, user=request.user)

            order.status = 'paid'
            order.paid_at = timezone.now()
            order.save(update_fields=['status', 'paid_at'])

            from apps.order.signals import deduct_product_stock, assign_coins_and_wallet_bonus
            deduct_product_stock(order)
            assign_coins_and_wallet_bonus(order)

            return redirect("peyment:show_sucess", message="پرداخت با موفقیت انجام شد")
        except Order.DoesNotExist:
            return redirect("peyment:show_sucess", message="پرداخت موفق بود اما سفارش یافت نشد")

    def process_wallet_charge(self, request, payment, session_data):
        """پردازش شارژ کیف پول"""
        try:
            amount_toman = session_data.get("amount_toman", int(payment.amount) // 10)

            # دریافت یا ایجاد کیف پول کاربر
            wallet, created = Wallet.objects.get_or_create(user=request.user)

            # افزایش موجودی کیف پول
            wallet.balance += int(amount_toman)
            wallet.save()

            # ثبت تراکنش
            WalletTransaction.objects.create(
                wallet=wallet,
                amount=amount_toman,
                transaction_type='deposit',
                status='completed',
                reference_id=payment.refId,
                description=f"شارژ کیف پول از طریق درگاه پرداخت - مبلغ {amount_toman} تومان"
            )

            return redirect("peyment:show_sucess", message=f"کیف پول شما به مبلغ {amount_toman} تومان شارژ شد")
        except Exception as e:
            print(f"❌ خطا در شارژ کیف پول: {str(e)}")
            return redirect("peyment:show_sucess", message="پرداخت موفق بود اما شارژ کیف پول با خطا مواجه شد")

    def process_membership_payment(self, request, payment, session_data):
        """پردازش پرداخت حق عضویت (5 میلیون تومان)"""
        try:
            from decimal import Decimal

            # بررسی مبلغ پرداختی
            if payment.amount != 50000000:
                return redirect("peyment:show_verfiy_unmessage",
                              message=f"مبلغ پرداختی {payment.amount} تومان است در حالی که مبلغ حق عضویت 5,000,000 تومان می‌باشد")

            # دریافت یا ایجاد UserSecurity
            security, created = UserSecurity.objects.get_or_create(user=request.user)

            # فعال کردن حق عضویت
            security.isPeymentuser = True
            security.isVerfiyByManager = True  # تایید خودکار توسط سیستم
            security.save()

            # دریافت یا ایجاد کیف پول کاربر
            wallet, created = Wallet.objects.get_or_create(user=request.user)

            # شارژ کیف پول به مبلغ 5,000,000 تومان
            amount_decimal = Decimal(payment.amount)
            wallet.balance += amount_decimal
            wallet.save()

            # ثبت تراکنش کیف پول
            WalletTransaction.objects.create(
                wallet=wallet,
                amount=amount_decimal,
                transaction_type='deposit',
                status='completed',
                reference_id=payment.refId or f"MEMBERSHIP_{payment.id}",
                description=f"شارژ کیف پول بابت پرداخت حق عضویت - کد پیگیری: {payment.refId or 'ندارد'}"
            )

            # بروزرسانی توضیحات پرداخت
            payment.description = f"{payment.description} - حق عضویت تایید و کیف پول به مبلغ {payment.amount} تومان شارژ شد"
            payment.save(update_fields=['description'])

            return redirect("peyment:show_sucess",
                          message=f"پرداخت حق عضویت با موفقیت انجام شد. کیف پول شما به مبلغ {payment.amount:,} تومان شارژ گردید.")

        except Exception as e:
            print(f"❌ خطا در process_membership_payment: {str(e)}")
            return redirect("peyment:show_verfiy_unmessage",
                          message=f"خطا در پردازش حق عضویت: {str(e)}")


# =============================== ویوهای نمایش پیام ===============================

def show_verfiy_message(request, message):
    return render(request, "peyment_app/peyment.html", {"message": message})


def show_verfiy_unmessage(request, message):
    return render(request, "peyment_app/unpeyment.html", {"message": message})




# peyment/views.py - اضافه کن به انتهای فایل

def check_membership_status(request):
    """برگشت وضعیت عضویت به صورت JSON ساده"""
    is_pay = False

    if request.user.is_authenticated:
        try:
            security = UserSecurity.objects.get(user=request.user)
            is_pay = security.isPeymentuser
        except UserSecurity.DoesNotExist:
            is_pay = False

    context = {
        'is_pay':is_pay
    }

    return context