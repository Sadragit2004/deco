# apps/chat/urls.py

from django.urls import path
from . import views

app_name = 'chat'

urlpatterns = [
    # کاربر عادی
    path('', views.chat_room, name='chat_room'),
    path('api/history/', views.get_chat_history, name='chat_history'),
    path('api/upload/', views.upload_file, name='upload_file'),
    path('api/delete/<int:message_id>/', views.delete_file, name='delete_file'),

    # ادمین
    path('admin/', views.admin_dashboard, name='admin_dashboard'),
    path('api/admin/chats/', views.get_admin_chats, name='admin_chats'),
    path('api/admin/chat/<int:chat_id>/', views.get_admin_chat_detail, name='admin_chat_detail'),
    path('api/admin/chat/<int:chat_id>/close/', views.close_chat, name='close_chat'),
    path('api/admin/unread/', views.get_unread_count, name='unread_count'),
]