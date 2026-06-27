
from django.contrib import admin
from django.urls import path,include
import web.settings as sett
from django.conf.urls.static import static


urlpatterns = [

    path('admin/', admin.site.urls),
    path('',include('apps.main.urls',namespace='main')),
    path('accounts/',include('apps.user.urls',namespace='account')),
    path('product/',include('apps.product.urls',namespace='product')),
    path('discount/',include('apps.discount.urls',namespace='discount')),
    path('order/',include('apps.order.urls',namespace='order')),
    path('peyment/',include('apps.peyment.urls',namespace='peyment')),
    path('search/',include('apps.search.urls',namespace='search')),
    path('notification/',include('apps.Notification.urls')),
    path('pro/',include('apps.pro.urls',namespace='pro')),
    path('panel/',include('apps.panel.urls',namespace='panel')),
    path('check/',include('apps.check.urls',namespace='check')),
    path('chat/',include('apps.chat.urls',namespace='chat'))




]+static(sett.MEDIA_URL,document_root = sett.MEDIA_ROOT)
