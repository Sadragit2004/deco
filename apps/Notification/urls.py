
from django.urls import path
from . import views

app_name = 'Notification '

urlpatterns = [
    path('', views.OrderNotificationsAPI.as_view(), name='notifications'),
    path('mark-read/', views.MarkNotificationReadAPI.as_view(), name='mark_notification_read'),
    path('mark-all-read/', views.MarkAllNotificationsReadAPI.as_view(), name='mark_all_notifications_read'),
]