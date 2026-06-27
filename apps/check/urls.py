from django.urls import path
from . import views

app_name = 'check'

urlpatterns = [

    path('checks/', views.UserCheckPaymentListView.as_view(), name='user_checks'),

    # جزئیات یک چک خاص با شماره پیگیری
    path('checks/<str:tracking_number>/', views.UserCheckPaymentDetailView.as_view(), name='user_check_detail'),

    # لغو چک (AJAX)
    path('checks/<str:tracking_number>/cancel/', views.check_payment_cancel, name='check_cancel'),
]
