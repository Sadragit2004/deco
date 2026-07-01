# apps/chat/models.py

from django.db import models
from django.conf import settings
import os


def message_file_path(instance, filename):
    """مسیر ذخیره فایل‌های پیام"""
    return f'chat/messages/user_{instance.sender.id}/{instance.chat.id}/{filename}'


class Chat(models.Model):
    """اتاق چت بین مشتری و ادمین"""
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='chat',
        verbose_name="مشتری"
    )
    admin = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='admin_chats',
        limit_choices_to={'is_staff': True},
        verbose_name="ادمین"
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="تاریخ ایجاد")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="آخرین بروزرسانی")
    is_active = models.BooleanField(default=True, verbose_name="فعال")
    has_unread = models.BooleanField(default=False, verbose_name="پیام نخوانده")

    class Meta:
        verbose_name = "چت"
        verbose_name_plural = "چت‌ها"
        ordering = ['-updated_at']

    def __str__(self):
        return f"چت {self.user.mobileNumber}"


class Message(models.Model):
    """هر پیام داخل چت"""
    class MessageType(models.TextChoices):
        TEXT = 'text', 'متن'
        IMAGE = 'image', 'تصویر'
        VIDEO = 'video', 'ویدیو'
        AUDIO = 'audio', 'صوت'
        FILE = 'file', 'فایل'
        DOCUMENT = 'document', 'سند'

    chat = models.ForeignKey(
        Chat,
        on_delete=models.CASCADE,
        related_name='messages',
        verbose_name="چت"
    )
    sender = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='sent_messages',
        verbose_name="فرستنده"
    )
    message_type = models.CharField(
        max_length=20,
        choices=MessageType.choices,
        default=MessageType.TEXT,
        verbose_name="نوع پیام"
    )
    content = models.TextField(
        max_length=1000,
        blank=True,
        null=True,
        verbose_name="متن پیام"
    )
    file = models.FileField(
        upload_to=message_file_path,
        blank=True,
        null=True,
        verbose_name="فایل پیوست"
    )
    file_name = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        verbose_name="نام فایل"
    )
    file_size = models.PositiveIntegerField(
        blank=True,
        null=True,
        verbose_name="حجم فایل (بایت)"
    )
    file_thumbnail = models.ImageField(
        upload_to='chat/thumbnails/',
        blank=True,
        null=True,
        verbose_name="تصویر بند انگشتی"
    )
    timestamp = models.DateTimeField(auto_now_add=True, verbose_name="زمان ارسال")
    is_read = models.BooleanField(default=False, verbose_name="خوانده شده")
    is_seen = models.BooleanField(default=False, verbose_name="دیده شده")  # 🔥 اضافه شد

    class Meta:
        verbose_name = "پیام"
        verbose_name_plural = "پیام‌ها"
        ordering = ['timestamp']

    def __str__(self):
        return f"{self.sender.mobileNumber}: {self.get_message_type_display()}"

    @property
    def is_file_message(self):
        """آیا پیام دارای فایل است؟"""
        return self.message_type != MessageType.TEXT and self.file

    @property
    def file_url(self):
        """دریافت URL فایل"""
        if self.file:
            return self.file.url
        return None

    @property
    def is_image(self):
        """آیا فایل تصویر است؟"""
        return self.message_type == MessageType.IMAGE

    @property
    def is_video(self):
        """آیا فایل ویدیو است؟"""
        return self.message_type == MessageType.VIDEO

    @property
    def is_audio(self):
        """آیا فایل صوتی است؟"""
        return self.message_type == MessageType.AUDIO

    @property
    def file_extension(self):
        """دریافت پسوند فایل"""
        if self.file_name:
            return os.path.splitext(self.file_name)[1].lower()
        return None

    @property
    def file_size_display(self):
        """نمایش حجم فایل به صورت خوانا"""
        if not self.file_size:
            return None
        size = self.file_size
        if size < 1024:
            return f"{size} B"
        elif size < 1024 * 1024:
            return f"{size / 1024:.1f} KB"
        elif size < 1024 * 1024 * 1024:
            return f"{size / (1024 * 1024):.1f} MB"
        else:
            return f"{size / (1024 * 1024 * 1024):.1f} GB"