from django.urls import path
from .views.auth import login,logout,verify
from .views.auth.dashboardapi import UserDashboardAPIView,UploadAvatarAPIView,DeleteAvatarAPIView
from .views.auth.addressapi import get_shop_name,DeleteAddressAPIView,AddAddressAPIView,ProvinceCityAPIView,UserAddressesAPIView,SetDefaultAddressAPIView

app_name = 'account'

urlpatterns = [
    path("login/", login.send_mobile, name="send_mobile"),
    path("verify/", verify.verify_code, name="verify_code"),
    path("logout/", logout.user_logout, name="logout"),
    path('api/user/dashboard/', UserDashboardAPIView.as_view(), name='user-dashboard-api'),
    path('api/user/addresses/', UserAddressesAPIView.as_view(), name='user-addresses-api'),
    path('api/provinces-cities/', ProvinceCityAPIView.as_view(), name='provinces-cities-api'),
    path('api/address/add/', AddAddressAPIView.as_view(), name='add-address-api'),
    path('api/address/set-default/', SetDefaultAddressAPIView.as_view(), name='set-default-address-api'),
    path('api/address/delete/', DeleteAddressAPIView.as_view(), name='delete-address-api'),
        # به urls.py اضافه کن:
    path('api/user/upload-avatar/', UploadAvatarAPIView.as_view(), name='upload-avatar-api'),
    path('api/user/delete-avatar/', DeleteAvatarAPIView.as_view(), name='delete-avatar-api'),
    path('api/shop_name/',get_shop_name,name='shop_name_get')
]
