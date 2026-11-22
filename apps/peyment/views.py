
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


MERCHANT_ID = "9f39aedf-f67b-487a-9911-ea3832f99eb8"
ZP_API_REQUEST = "https://api.zarinpal.com/pg/v4/payment/request.json"
ZP_API_VERIFY = "https://api.zarinpal.com/pg/v4/payment/verify.json"
ZP_API_STARTPAY = "https://www.zarinpal.com/pg/StartPay/{authority}"
CALLBACK_URL = "https://www.decob2b.net/peyment/verify/"


def send_request(request, order_id):
    """درخواست پرداخت سفارش و نمایش صفحه بررسی پرداخت"""

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

        if order.status == "paid":
            messages.error(request, "این سفارش قبلا پرداخت شده است")
            return redirect("main:index")

        amount_param = request.GET.get("amount")

        if amount_param:
            amount = int(amount_param) * 10
        else:
            order.refresh_from_db()
            amount = int(
                order.subtotal
                - order.discount_amount
                - order.coupon_discount
                + order.shipping_cost
                - order.used_from_wallet
            )
            if amount < 0:
                amount = 0

        if amount <= 0:
            order.status = "paid"
            order.paid_at = timezone.now()
            order.save(update_fields=["status", "paid_at"])

            from apps.order.signals import (
                deduct_product_stock,
                assign_coins_and_wallet_bonus,
            )

            deduct_product_stock(order)
            assign_coins_and_wallet_bonus(order)

            messages.success(
                request,
                "پرداخت با موفقیت انجام شد (استفاده از کیف پول)",
            )
            return redirect("order:order_detail", order_id=order.id)

        peyment = Peyment.objects.create(
            order=order,
            customer=request.user,
            amount=amount,
            description=f"پرداخت سفارش {order.order_number}",
            statusCode=0,
            isFinaly=False,
            payment_method=PaymentMethod.ONLINE.value,
        )

        session_key = f"peyment_{order_id}_{int(time.time())}"
        request.session[session_key] = {
            "order_id": str(order.id),
            "peyment_id": str(peyment.id),
            "amount": str(amount),
            "type": "order",
            "timestamp": str(time.time()),
        }
        request.session["current_peyment_key"] = session_key
        request.session.set_expiry(3600)

        req_data = {
            "merchant_id": MERCHANT_ID,
            "amount": amount,
            "callback_url": CALLBACK_URL,
            "description": (
                f"پرداخت سفارش شماره {order.order_number} - سایت دکو بی تو بی"
            ),
            "metadata": {
                "email": request.user.email if request.user.email else "",
                "mobile": request.user.mobileNumber,
            },
        }

        headers = {
            "accept": "application/json",
            "content-type": "application/json",
        }

        response = requests.post(
            ZP_API_REQUEST,
            data=json.dumps(req_data),
            headers=headers,
            timeout=30,
        )

        if response.status_code == 200:
            data = response.json()

            if "data" in data and data["data"] and "authority" in data["data"]:
                authority = data["data"]["authority"]
                request.session[session_key]["authority"] = authority
                request.session.modified = True
                request.session["last_authority"] = authority

                return redirect(
                    "peyment:payment_review",
                    session_key=session_key,
                )

            peyment.statusCode = -2
            peyment.save()
            messages.error(request, "خطا از سمت درگاه پرداخت")
            return redirect("order:cart_page")

        messages.error(request, "خطا در ارتباط با درگاه پرداخت")
        return redirect("order:cart_page")

    except Exception as e:
        print(f"❌ خطا در send_request: {str(e)}")
        messages.error(request, f"خطای غیرمنتظره: {str(e)}")
        return redirect("order:cart_page")


# =============================== API پرداخت حق عضویت ===============================

class MembershipPaymentAPIView(LoginRequiredMixin, View):
    """API برای پرداخت مبلغ 5,000,000 تومان حق عضویت"""

    def get(self, request):
        try:
            if not request.user.is_authenticated:
                return JsonResponse({
                    "status": "error",
                    "message": "لطفا ابتدا وارد حساب کاربری خود شوید",
                }, status=401)

            try:
                security = UserSecurity.objects.get(user=request.user)
                if security.isPeymentuser:
                    return JsonResponse({
                        "status": "error",
                        "message": "شما قبلاً حق عضویت را پرداخت کرده‌اید",
                    }, status=400)
            except UserSecurity.DoesNotExist:
                pass

            existing_membership_payment = Peyment.objects.filter(
                customer=request.user,
                amount=50000000,
                isFinaly=True,
            ).exists()

            if existing_membership_payment:
                return JsonResponse({
                    "status": "error",
                    "message": "شما قبلاً حق عضویت را پرداخت کرده‌اید",
                }, status=400)

            amount = 50000000

            peyment = Peyment.objects.create(
                order=None,
                customer=request.user,
                amount=amount,
                description=f"پرداخت حق عضویت - کاربر {request.user.mobileNumber}",
                statusCode=0,
                isFinaly=False,
                payment_method=PaymentMethod.ONLINE.value,
            )

            session_key = f"membership_{request.user.id}_{int(time.time())}"
            request.session[session_key] = {
                "peyment_id": str(peyment.id),
                "amount": str(amount),
                "type": "membership",
                "membership_amount": amount,
                "timestamp": str(time.time()),
            }
            request.session["current_peyment_key"] = session_key
            request.session.set_expiry(3600)

            req_data = {
                "merchant_id": MERCHANT_ID,
                "amount": amount,
                "callback_url": CALLBACK_URL,
                "description": (
                    f"پرداخت حق عضویت سایت دکو بی تو بی - کاربر "
                    f"{request.user.mobileNumber}"
                ),
                "metadata": {
                    "email": request.user.email if request.user.email else "",
                    "mobile": request.user.mobileNumber,
                },
            }

            headers = {
                "accept": "application/json",
                "content-type": "application/json",
            }

            response = requests.post(
                ZP_API_REQUEST,
                data=json.dumps(req_data),
                headers=headers,
                timeout=30,
            )

            if response.status_code == 200:
                data = response.json()

                if "data" in data and data["data"] and "authority" in data["data"]:
                    authority = data["data"]["authority"]
                    request.session[session_key]["authority"] = authority
                    request.session.modified = True
                    request.session["last_authority"] = authority

                    payment_url = request.build_absolute_uri(
                        reverse(
                            "peyment:payment_review",
                            kwargs={"session_key": session_key},
                        )
                    )

                    return JsonResponse({
                        "status": "success",
                        "message": "درخواست پرداخت با موفقیت ایجاد شد",
                        "payment_url": payment_url,
                        "authority": authority,
                        "amount": amount,
                    })

                peyment.statusCode = -2
                peyment.save()

                return JsonResponse({
                    "status": "error",
                    "message": "خطا از سمت درگاه پرداخت",
                }, status=500)

            return JsonResponse({
                "status": "error",
                "message": "خطا در ارتباط با درگاه پرداخت",
            }, status=500)

        except Exception as e:
            print(f"❌ خطا در MembershipPaymentAPIView: {str(e)}")
            return JsonResponse({
                "status": "error",
                "message": f"خطای غیرمنتظره: {str(e)}",
            }, status=500)

    def post(self, request):
        return self.get(request)


def check_membership_status(request):
    """API برای بررسی وضعیت حق عضویت کاربر"""

    try:
        if not request.user.is_authenticated:
            return JsonResponse({
                "status": "error",
                "message": "لطفا ابتدا وارد شوید",
            }, status=401)

        try:
            security = UserSecurity.objects.get(user=request.user)
            is_member = security.isPeymentuser
        except UserSecurity.DoesNotExist:
            is_member = False

        has_paid = Peyment.objects.filter(
            customer=request.user,
            amount=50000000,
            isFinaly=True,
        ).exists()

        return JsonResponse({
            "status": "success",
            "is_member": is_member or has_paid,
            "has_active_membership": is_member,
            "has_successful_payment": has_paid,
            "message": (
                "کاربر عضو است"
                if (is_member or has_paid)
                else "کاربر عضو نیست"
            ),
        })

    except Exception as e:
        return JsonResponse({
            "status": "error",
            "message": str(e),
        }, status=500)


# =============================== صفحه پرداخت حق عضویت ===============================

class MembershipPaymentView(LoginRequiredMixin, View):
    """نمایش صفحه پرداخت حق عضویت ۵ میلیون تومانی"""

    def get(self, request):
        try:
            try:
                security = UserSecurity.objects.get(user=request.user)
                is_member = security.isPeymentuser
            except UserSecurity.DoesNotExist:
                is_member = False

            has_successful_payment = Peyment.objects.filter(
                customer=request.user,
                amount=50000000,
                isFinaly=True,
            ).exists()

            if is_member or has_successful_payment:
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
                            isVerfiyByManager=True,
                        )

                context = {
                    "is_member": True,
                    "membership_amount": 50000000,
                    "membership_amount_toman": "۵,۰۰۰,۰۰۰",
                }
                return render(
                    request,
                    "peyment_app/membership_payment.html",
                    context,
                )

            pending_payment = Peyment.objects.filter(
                customer=request.user,
                amount=50000000,
                isFinaly=False,
            ).exclude(statusCode=0).first()

            context = {
                "is_member": False,
                "membership_amount": 50000000,
                "membership_amount_toman": "۵,۰۰۰,۰۰۰",
                "pending_payment": pending_payment,
            }

            return render(
                request,
                "peyment_app/membership_payment.html",
                context,
            )

        except Exception as e:
            print(f"❌ خطا در MembershipPaymentView: {str(e)}")
            messages.error(request, f"خطا در نمایش صفحه: {str(e)}")
            return redirect("main:index")


# =============================== شروع پرداخت حق عضویت ===============================

def membership_payment_redirect(request):
    """ایجاد پرداخت حق عضویت و هدایت به صفحه بررسی پرداخت"""

    if not request.user.is_authenticated:
        messages.error(request, "لطفا ابتدا وارد حساب کاربری خود شوید")
        return redirect("user:login")

    try:
        security = UserSecurity.objects.get(user=request.user)
        if security.isPeymentuser:
            messages.error(request, "شما قبلاً حق عضویت را پرداخت کرده‌اید")
            return redirect("main:index")
    except UserSecurity.DoesNotExist:
        pass

    existing_payment = Peyment.objects.filter(
        customer=request.user,
        amount=50000000,
        isFinaly=True,
    ).exists()

    if existing_payment:
        try:
            security = UserSecurity.objects.get(user=request.user)
            security.isPeymentuser = True
            security.isVerfiyByManager = True
            security.save()
        except UserSecurity.DoesNotExist:
            UserSecurity.objects.create(
                user=request.user,
                isPeymentuser=True,
                isVerfiyByManager=True,
            )

        messages.error(request, "شما قبلاً حق عضویت را پرداخت کرده‌اید")
        return redirect("main:index")

    try:
        amount = 50000000

        peyment = Peyment.objects.create(
            order=None,
            customer=request.user,
            amount=amount,
            description=f"پرداخت حق عضویت - کاربر {request.user.mobileNumber}",
            statusCode=0,
            isFinaly=False,
            payment_method=PaymentMethod.ONLINE.value,
        )

        session_key = f"membership_{request.user.id}_{int(time.time())}"
        request.session[session_key] = {
            "peyment_id": str(peyment.id),
            "amount": str(amount),
            "type": "membership",
            "membership_amount": amount,
            "timestamp": str(time.time()),
        }
        request.session["current_peyment_key"] = session_key
        request.session.set_expiry(3600)

        req_data = {
            "merchant_id": MERCHANT_ID,
            "amount": amount,
            "callback_url": CALLBACK_URL,
            "description": (
                f"پرداخت حق عضویت سایت دکو بی تو بی - کاربر "
                f"{request.user.mobileNumber}"
            ),
            "metadata": {
                "email": request.user.email if request.user.email else "",
                "mobile": request.user.mobileNumber,
            },
        }

        headers = {
            "accept": "application/json",
            "content-type": "application/json",
        }

        response = requests.post(
            ZP_API_REQUEST,
            data=json.dumps(req_data),
            headers=headers,
            timeout=30,
        )

        if response.status_code == 200:
            data = response.json()

            if "data" in data and data["data"] and "authority" in data["data"]:
                authority = data["data"]["authority"]
                request.session[session_key]["authority"] = authority
                request.session.modified = True
                request.session["last_authority"] = authority

                return redirect(
                    "peyment:payment_review",
                    session_key=session_key,
                )

            peyment.statusCode = -2
            peyment.save()
            messages.error(request, "خطا از سمت درگاه پرداخت")
            return redirect("main:index")

        messages.error(request, "خطا در ارتباط با درگاه پرداخت")
        return redirect("main:index")

    except Exception as e:
        print(f"❌ خطا در membership_payment_redirect: {str(e)}")
        messages.error(request, f"خطای غیرمنتظره: {str(e)}")
        return redirect("main:index")


# =============================== صفحه بررسی پرداخت ===============================
def payment_review(request, session_key):
    """نمایش اطلاعات پرداخت و انتقال امن به درگاه زرین‌پال"""

    if not request.user.is_authenticated:
        messages.error(request, "لطفاً ابتدا وارد حساب کاربری خود شوید.")
        return redirect("user:login")

    session_data = request.session.get(session_key)

    if not session_data:
        messages.error(request, "اطلاعات پرداخت معتبر نیست یا منقضی شده است.")
        return redirect("main:index")

    payment_id = session_data.get("peyment_id")
    authority = session_data.get("authority")
    amount = session_data.get("amount")

    if not payment_id or not authority or not amount:
        messages.error(request, "اطلاعات پرداخت ناقص است.")
        return redirect("main:index")

    try:
        payment = Peyment.objects.get(
            id=payment_id,
            customer=request.user,
            isFinaly=False,
            payment_method=PaymentMethod.ONLINE.value,
        )
    except Peyment.DoesNotExist:
        messages.error(request, "تراکنش پرداخت معتبر نیست.")
        return redirect("main:index")

    try:
        session_amount = int(amount)
    except (TypeError, ValueError):
        messages.error(request, "مبلغ پرداخت معتبر نیست.")
        return redirect("main:index")

    if session_amount <= 0 or session_amount != payment.amount:
        messages.error(request, "مبلغ پرداخت با تراکنش مطابقت ندارد.")
        return redirect("main:index")

    if not authority:
        messages.error(request, "شناسه پرداخت زرین‌پال معتبر نیست.")
        return redirect("main:index")

    context = {
        "payment": payment,
        "amount": payment.amount,
        "amount_toman": payment.amount // 10,
        "authority": authority,
        "payment_type": session_data.get("type", "order"),
        "order_id": session_data.get("order_id"),
        "gateway_url": ZP_API_STARTPAY.format(authority=authority),
    }

    response = render(
        request,
        "peyment_app/review.html",
        context,
    )

    response["Referrer-Policy"] = "no-referrer"

    return response

# =============================== تایید پرداخت زرین‌پال ===============================

@method_decorator(csrf_exempt, name="dispatch")
class Zarin_pal_view_verfiy(LoginRequiredMixin, View):

    def get(self, request):
        t_status = request.GET.get("Status")
        t_authority = request.GET.get("Authority")

        if not t_status or not t_authority:
            messages.error(request, "پارامترهای لازم ارسال نشده است")
            return redirect("main:index")

        session_data = None
        session_key = None

        for key in list(request.session.keys()):
            if (
                key.startswith("peyment_")
                or key.startswith("charge_wallet_")
                or key.startswith("membership_")
            ):
                data = request.session.get(key)
                if data and data.get("authority") == t_authority:
                    session_data = data
                    session_key = key
                    break

        if not session_data:
            try:
                payment = Peyment.objects.filter(
                    customer=request.user,
                    isFinaly=False,
                ).order_by("-createAt").first()

                if payment:
                    session_data = {
                        "peyment_id": str(payment.id),
                        "amount": str(payment.amount),
                        "type": "unknown",
                    }
            except Exception:
                pass

        if not session_data:
            messages.error(request, "اطلاعات پرداخت یافت نشد")
            return redirect("main:index")

        try:
            peyment_id = session_data.get("peyment_id")
            payment = Peyment.objects.get(
                id=peyment_id,
                customer=request.user,
            )
        except Peyment.DoesNotExist:
            messages.error(request, "اطلاعات پرداخت نامعتبر است")
            return redirect("main:index")

        if session_key and session_key in request.session:
            del request.session[session_key]

        if "current_peyment_key" in request.session:
            del request.session["current_peyment_key"]

        if "last_authority" in request.session:
            del request.session["last_authority"]

        request.session.modified = True

        if t_status == "OK":
            return self.verify_payment(
                request,
                payment,
                t_authority,
                session_data,
            )

        payment.statusCode = -10
        payment.save()
        return redirect(
            "peyment:show_verfiy_unmessage",
            message="پرداخت لغو شد",
        )

    def verify_payment(self, request, payment, authority, session_data):
        amount = session_data.get("amount")
        transaction_type = session_data.get("type", "order")

        req_data = {
            "merchant_id": MERCHANT_ID,
            "amount": int(amount),
            "authority": authority,
        }

        headers = {
            "accept": "application/json",
            "content-type": "application/json",
        }

        try:
            response = requests.post(
                ZP_API_VERIFY,
                data=json.dumps(req_data),
                headers=headers,
                timeout=30,
            )

            if response.status_code == 200:
                data = response.json()

                if "data" in data and data["data"]:
                    code = data["data"].get("code")

                    if code == 100:
                        payment.isFinaly = True
                        payment.statusCode = 100

                        if "ref_id" in data["data"]:
                            payment.refId = str(data["data"]["ref_id"])

                        payment.save()

                        if transaction_type == "charge_wallet":
                            return self.process_wallet_charge(
                                request,
                                payment,
                                session_data,
                            )

                        if transaction_type == "membership":
                            return self.process_membership_payment(
                                request,
                                payment,
                                session_data,
                            )

                        return self.process_order_payment(
                            request,
                            payment,
                            session_data,
                        )

                    if code == 101:
                        payment.isFinaly = True
                        payment.statusCode = 101

                        if "ref_id" in data["data"]:
                            payment.refId = str(data["data"]["ref_id"])

                        payment.save()

                        return redirect(
                            "peyment:show_sucess",
                            message="این تراکنش قبلا تایید شده است",
                        )

                    payment.statusCode = code
                    payment.save()

                    return redirect(
                        "peyment:show_verfiy_unmessage",
                        message="خطا در پرداخت",
                    )

                return redirect(
                    "peyment:show_verfiy_unmessage",
                    message="خطا در تایید پرداخت",
                )

            return redirect(
                "peyment:show_verfiy_unmessage",
                message="خطا در ارتباط با درگاه",
            )

        except Exception as e:
            return redirect(
                "peyment:show_verfiy_unmessage",
                message=f"خطا: {str(e)}",
            )

    def process_order_payment(self, request, payment, session_data):
        """پردازش پرداخت سفارش"""

        try:
            order_id = session_data.get("order_id")
            order = Order.objects.get(
                id=order_id,
                user=request.user,
            )

            order.status = "paid"
            order.paid_at = timezone.now()
            order.save(update_fields=["status", "paid_at"])

            from apps.order.signals import (
                deduct_product_stock,
                assign_coins_and_wallet_bonus,
            )

            deduct_product_stock(order)
            assign_coins_and_wallet_bonus(order)

            return redirect(
                "peyment:show_sucess",
                message="پرداخت با موفقیت انجام شد",
            )

        except Order.DoesNotExist:
            return redirect(
                "peyment:show_sucess",
                message="پرداخت موفق بود اما سفارش یافت نشد",
            )

    def process_wallet_charge(self, request, payment, session_data):
        """پردازش شارژ کیف پول"""

        try:
            amount_toman = session_data.get(
                "amount_toman",
                int(payment.amount) // 10,
            )

            wallet, created = Wallet.objects.get_or_create(
                user=request.user,
            )

            wallet.balance += int(amount_toman)
            wallet.save()

            WalletTransaction.objects.create(
                wallet=wallet,
                amount=amount_toman,
                transaction_type="deposit",
                status="completed",
                reference_id=payment.refId,
                description=(
                    "شارژ کیف پول از طریق درگاه پرداخت - "
                    f"مبلغ {amount_toman} تومان"
                ),
            )

            return redirect(
                "peyment:show_sucess",
                message=(
                    f"کیف پول شما به مبلغ {amount_toman} تومان شارژ شد"
                ),
            )

        except Exception as e:
            print(f"❌ خطا در شارژ کیف پول: {str(e)}")
            return redirect(
                "peyment:show_sucess",
                message="پرداخت موفق بود اما شارژ کیف پول با خطا مواجه شد",
            )

    def process_membership_payment(self, request, payment, session_data):
        """پردازش پرداخت حق عضویت"""

        try:
            from decimal import Decimal

            if payment.amount != 50000000:
                return redirect(
                    "peyment:show_verfiy_unmessage",
                    message=(
                        f"مبلغ پرداختی {payment.amount} تومان است در حالی که "
                        "مبلغ حق عضویت 5,000,000 تومان می‌باشد"
                    ),
                )

            security, created = UserSecurity.objects.get_or_create(
                user=request.user,
            )

            security.isPeymentuser = True
            security.isVerfiyByManager = True
            security.save()

            wallet, created = Wallet.objects.get_or_create(
                user=request.user,
            )

            amount_decimal = Decimal(payment.amount)
            wallet.balance += amount_decimal
            wallet.save()

            WalletTransaction.objects.create(
                wallet=wallet,
                amount=amount_decimal,
                transaction_type="deposit",
                status="completed",
                reference_id=payment.refId or f"MEMBERSHIP_{payment.id}",
                description=(
                    "شارژ کیف پول بابت پرداخت حق عضویت - "
                    f"کد پیگیری: {payment.refId or 'ندارد'}"
                ),
            )

            payment.description = (
                f"{payment.description} - حق عضویت تایید و کیف پول "
                f"به مبلغ {payment.amount} تومان شارژ شد"
            )
            payment.save(update_fields=["description"])

            return redirect(
                "peyment:show_sucess",
                message=(
                    "پرداخت حق عضویت با موفقیت انجام شد. "
                    f"کیف پول شما به مبلغ {payment.amount:,} تومان شارژ گردید."
                ),
            )

        except Exception as e:
            print(f"❌ خطا در process_membership_payment: {str(e)}")
            return redirect(
                "peyment:show_verfiy_unmessage",
                message=f"خطا در پردازش حق عضویت: {str(e)}",
            )


# =============================== ویوهای نمایش پیام ===============================

def show_verfiy_message(request, message):
    """نمایش صفحه پرداخت موفق با کد رهگیری"""

    try:
        latest_payment = Peyment.objects.filter(
            customer=request.user,
            isFinaly=True,
        ).order_by("-createAt").first()

        order = None
        if latest_payment and latest_payment.order:
            order = latest_payment.order

        context = {
            "message": message,
            "payment": latest_payment,
            "order": order,
            "ref_id": latest_payment.refId if latest_payment else None,
            "amount": latest_payment.amount if latest_payment else 0,
            "amount_toman": (
                latest_payment.amount // 10 if latest_payment else 0
            ),
            "payment_date": (
                latest_payment.createAt if latest_payment else None
            ),
        }

        return render(
            request,
            "peyment_app/peyment.html",
            context,
        )

    except Exception as e:
        print(f"❌ خطا در show_verfiy_message: {str(e)}")
        return render(
            request,
            "peyment_app/peyment.html",
            {"message": message},
        )


def show_verfiy_unmessage(request, message):
    """نمایش صفحه پرداخت ناموفق"""

    return render(
        request,
        "peyment_app/unpeyment.html",
        {"message": message},
    )
