# apps/chat/urls.py
from django.urls import path
from . import views

app_name = 'chat'

urlpatterns = [
    # مسیرهای کاربر
    path('', views.chat_room, name='chat_room'),
    path('api/history/', views.get_chat_history, name='chat_history'),

    # مسیرهای ادمین
    path('admin/dashboard/', views.admin_dashboard, name='admin_dashboard'),
    path('api/admin/chats/', views.get_admin_chats, name='admin_chats'),
    path('api/admin/chat/<int:chat_id>/', views.get_admin_chat_detail, name='admin_chat_detail'),
    path('api/admin/chat/<int:chat_id>/close/', views.close_chat, name='close_chat'),
    path('api/admin/unread/', views.get_unread_count, name='unread_count'),

    # مسیرهای فایل
    path('api/upload/', views.upload_file, name='upload_file'),
    path('api/delete/<int:message_id>/', views.delete_file, name='delete_file'),

    # ========== 🔥 مسیرهای دیده شدن (SEEN) ==========
    path('api/admin/chat/<int:chat_id>/seen/', views.mark_messages_as_seen, name='mark_messages_seen'),
    path('api/message/<int:message_id>/seen/', views.mark_single_message_seen, name='mark_single_message_seen'),
    path('api/message/<int:message_id>/status/', views.get_message_seen_status, name='message_seen_status'),

    # ========== 🔥 مسیر جدید: اطلاعات کامل مشتری ==========
    path('api/customer/<uuid:user_id>/info/', views.get_customer_info, name='customer_info'),
]