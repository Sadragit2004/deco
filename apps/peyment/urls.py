
from django.urls import path

from .views import (
    send_request,
    Zarin_pal_view_verfiy,
    show_verfiy_message,
    show_verfiy_unmessage,
    MembershipPaymentAPIView,
    check_membership_status,
    membership_payment_redirect,
    MembershipPaymentView,
    payment_review,
)
from .panel_view import PaymentListView, PaymentDetailView


app_name = "peyment"

urlpatterns = [
    path(
        "request/<uuid:order_id>/",
        send_request,
        name="request",
    ),
    path(
        "review/<str:session_key>/",
        payment_review,
        name="payment_review",
    ),
    path(
        "verify/",
        Zarin_pal_view_verfiy.as_view(),
        name="verify",
    ),
    path(
        "show_sucess/<str:message>/",
        show_verfiy_message,
        name="show_sucess",
    ),
    path(
        "show_verfiy_unmessage/<str:message>/",
        show_verfiy_unmessage,
        name="show_verfiy_unmessage",
    ),
    path(
        "payments/",
        PaymentListView.as_view(),
        name="payment_list",
    ),
    path(
        "payments/<int:payment_id>/",
        PaymentDetailView.as_view(),
        name="payment_detail",
    ),
    path(
        "api/membership/pay/",
        MembershipPaymentAPIView.as_view(),
        name="membership_payment_api",
    ),
    path(
        "api/membership/status/",
        check_membership_status,
        name="check_membership_status",
    ),
    path(
        "membership/pay/",
        membership_payment_redirect,
        name="membership_payment_redirect",
    ),
    path(
        "membership/pay/page/",
        MembershipPaymentView.as_view(),
        name="membership_payment_page",
    ),
]
