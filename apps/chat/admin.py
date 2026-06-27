# apps/chat/admin.py

from django.contrib import admin
from django.utils.html import format_html
from .models import Chat, Message


@admin.register(Chat)
class ChatAdmin(admin.ModelAdmin):
    list_display = ('user_display', 'admin_display', 'message_count', 'created_at', 'is_active', 'has_unread')
    list_filter = ('is_active', 'has_unread', 'created_at')
    search_fields = ('user__mobileNumber', 'user__name', 'user__family', 'admin__mobileNumber')
    readonly_fields = ('created_at', 'updated_at')
    ordering = ('-updated_at',)

    def user_display(self, obj):
        return f"{obj.user.name or ''} {obj.user.family or ''} - {obj.user.mobileNumber}"
    user_display.short_description = "مشتری"

    def admin_display(self, obj):
        return f"{obj.admin.name or ''} {obj.admin.family or ''} - {obj.admin.mobileNumber}"
    admin_display.short_description = "ادمین"

    def message_count(self, obj):
        return obj.messages.count()
    message_count.short_description = "تعداد پیام‌ها"


@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ('sender_display', 'chat_link', 'content_preview', 'timestamp', 'is_read')
    list_filter = ('is_read', 'timestamp')
    search_fields = ('sender__mobileNumber', 'sender__name', 'sender__family', 'content')
    readonly_fields = ('timestamp',)
    ordering = ('-timestamp',)

    def sender_display(self, obj):
        return f"{obj.sender.name or ''} {obj.sender.family or ''} - {obj.sender.mobileNumber}"
    sender_display.short_description = "فرستنده"

    def chat_link(self, obj):
        url = f"/admin/chat/chat/{obj.chat.id}/change/"
        return format_html('<a href="{}">مشاهده چت</a>', url)
    chat_link.short_description = "چت"

    def content_preview(self, obj):
        return obj.content[:50] + ('...' if len(obj.content) > 50 else '')
    content_preview.short_description = "متن پیام"