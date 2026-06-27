# apps/chat/views.py

from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.http import JsonResponse
from django.db.models import Q
from django.conf import settings
from .models import Chat, Message
from apps.user.models.user import CustomUser
from django.utils import timezone
import os


@login_required
def chat_room(request):
    return render(request, 'chat/chat.html')


@login_required
def get_chat_history(request):
    """دریافت تاریخچه پیام‌های چت کاربر"""
    user = request.user

    try:
        chat = Chat.objects.get(user=user)
        messages = chat.messages.all().order_by('timestamp')[:50]

        # علامت‌گذاری پیام‌های دریافتی به عنوان خوانده شده
        chat.messages.filter(is_read=False).exclude(sender=user).update(is_read=True)
        chat.has_unread = False
        chat.save()

        data = {
            'status': 'success',
            'messages': [
                {
                    'id': msg.id,
                    'content': msg.content,
                    'sender_id': str(msg.sender.id),
                    'sender_name': msg.sender.name or msg.sender.mobileNumber,
                    'timestamp': msg.timestamp.isoformat(),
                    'is_read': msg.is_read,
                    'is_mine': msg.sender == user,
                    'is_admin': msg.sender.is_staff,
                    # فیلدهای جدید فایل
                    'message_type': msg.message_type,
                    'file_url': msg.file.url if msg.file else None,
                    'file_name': msg.file_name,
                    'file_size': msg.file_size_display,
                    'file_thumbnail': msg.file_thumbnail.url if msg.file_thumbnail else None,
                }
                for msg in messages
            ]
        }
    except Chat.DoesNotExist:
        data = {
            'status': 'success',
            'messages': []
        }

    return JsonResponse(data)


@login_required
@user_passes_test(lambda u: u.is_staff)
def admin_dashboard(request):
    """داشبورد ادمین برای مدیریت چت‌ها"""
    return render(request, 'chat/admin_dashboard.html')


@login_required
@user_passes_test(lambda u: u.is_staff)
def get_admin_chats(request):
    """دریافت لیست تمام چت‌ها برای ادمین"""
    chats = Chat.objects.filter(is_active=True).select_related('user', 'admin').prefetch_related('messages')

    data = []
    for chat in chats:
        last_message = chat.messages.last()
        unread_count = chat.messages.filter(is_read=False).exclude(sender=request.user).count()

        # بررسی آخرین پیام
        last_msg_content = ''
        if last_message:
            if last_message.message_type == 'text':
                last_msg_content = last_message.content or 'بدون پیام'
            elif last_message.message_type == 'image':
                last_msg_content = '📷 تصویر'
            elif last_message.message_type == 'video':
                last_msg_content = '🎬 ویدیو'
            elif last_message.message_type == 'audio':
                last_msg_content = '🎵 صدا'
            elif last_message.message_type == 'document':
                last_msg_content = '📄 سند'
            else:
                last_msg_content = '📎 فایل'

        data.append({
            'id': chat.id,
            'user_id': chat.user.id,
            'user_name': chat.user.name or chat.user.mobileNumber,
            'user_mobile': chat.user.mobileNumber,
            'last_message': last_msg_content,
            'last_message_time': last_message.timestamp.isoformat() if last_message else None,
            'unread_count': unread_count,
            'has_unread': chat.has_unread,
            'created_at': chat.created_at.isoformat(),
            'is_active': chat.is_active
        })

    return JsonResponse({
        'status': 'success',
        'chats': data
    })


@login_required
@user_passes_test(lambda u: u.is_staff)
def get_admin_chat_detail(request, chat_id):
    """دریافت جزئیات یک چت خاص برای ادمین"""
    chat = get_object_or_404(Chat, id=chat_id)
    messages = chat.messages.all().order_by('timestamp')[:100]

    # علامت‌گذاری پیام‌های خوانده نشده
    chat.messages.filter(is_read=False).exclude(sender=request.user).update(is_read=True)
    chat.has_unread = False
    chat.save()

    data = {
        'status': 'success',
        'chat': {
            'id': chat.id,
            'user_id': chat.user.id,
            'user_name': chat.user.name or chat.user.mobileNumber,
            'user_mobile': chat.user.mobileNumber,
            'is_active': chat.is_active,
            'created_at': chat.created_at.isoformat()
        },
        'messages': [
            {
                'id': msg.id,
                'content': msg.content,
                'sender_id': str(msg.sender.id),
                'sender_name': msg.sender.name or msg.sender.mobileNumber,
                'timestamp': msg.timestamp.isoformat(),
                'is_read': msg.is_read,
                'is_admin': msg.sender.is_staff,
                # فیلدهای جدید فایل
                'message_type': msg.message_type,
                'file_url': msg.file.url if msg.file else None,
                'file_name': msg.file_name,
                'file_size': msg.file_size_display,
                'file_thumbnail': msg.file_thumbnail.url if msg.file_thumbnail else None,
            }
            for msg in messages
        ]
    }

    return JsonResponse(data)


@login_required
@user_passes_test(lambda u: u.is_staff)
def close_chat(request, chat_id):
    """بستن یک چت توسط ادمین"""
    chat = get_object_or_404(Chat, id=chat_id)
    chat.is_active = False
    chat.save()

    return JsonResponse({
        'status': 'success',
        'message': 'چت با موفقیت بسته شد'
    })


@login_required
@user_passes_test(lambda u: u.is_staff)
def get_unread_count(request):
    """دریافت تعداد پیام‌های خوانده نشده برای ادمین"""
    unread_chats = Chat.objects.filter(
        is_active=True,
        has_unread=True
    ).count()

    return JsonResponse({
        'status': 'success',
        'unread_count': unread_chats
    })


# ======================== API جدید برای آپلود فایل ========================
@login_required
def upload_file(request):
    """آپلود فایل برای پیام"""
    if request.method != 'POST':
        return JsonResponse({
            'status': 'error',
            'message': 'روش نامعتبر'
        }, status=405)

    if not request.FILES.get('file'):
        return JsonResponse({
            'status': 'error',
            'message': 'فایلی ارسال نشده است'
        }, status=400)

    file = request.FILES['file']

    # بررسی حجم فایل (حداکثر 10 مگابایت)
    if file.size > 10 * 1024 * 1024:
        return JsonResponse({
            'status': 'error',
            'message': 'حجم فایل بیشتر از 10 مگابایت است'
        }, status=400)

    # بررسی نوع فایل
    allowed_types = ['image/jpeg', 'image/png', 'image/gif', 'image/webp',
                     'video/mp4', 'video/webm', 'audio/mpeg', 'audio/wav',
                     'application/pdf', 'application/msword',
                     'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
                     'application/zip', 'text/plain']

    if file.content_type not in allowed_types:
        return JsonResponse({
            'status': 'error',
            'message': 'نوع فایل مجاز نیست'
        }, status=400)

    # تعیین نوع فایل
    content_type = file.content_type
    if content_type.startswith('image/'):
        file_type = 'image'
    elif content_type.startswith('video/'):
        file_type = 'video'
    elif content_type.startswith('audio/'):
        file_type = 'audio'
    elif content_type in ['application/pdf', 'application/msword',
                         'application/vnd.openxmlformats-officedocument.wordprocessingml.document']:
        file_type = 'document'
    else:
        file_type = 'file'

    return JsonResponse({
        'status': 'success',
        'file_type': file_type,
        'file_name': file.name,
        'file_size': file.size,
        'content_type': content_type
    })


@login_required
def delete_file(request, message_id):
    """حذف فایل یک پیام"""
    if request.method != 'DELETE':
        return JsonResponse({
            'status': 'error',
            'message': 'روش نامعتبر'
        }, status=405)

    try:
        message = Message.objects.get(id=message_id)

        # بررسی دسترسی
        if message.sender != request.user and not request.user.is_staff:
            return JsonResponse({
                'status': 'error',
                'message': 'شما دسترسی به این پیام ندارید'
            }, status=403)

        # حذف فایل
        if message.file:
            if os.path.isfile(message.file.path):
                os.remove(message.file.path)
            message.file = None
            message.file_name = None
            message.file_size = None
            message.message_type = 'text'
            message.save()

        return JsonResponse({
            'status': 'success',
            'message': 'فایل با موفقیت حذف شد'
        })

    except Message.DoesNotExist:
        return JsonResponse({
            'status': 'error',
            'message': 'پیام پیدا نشد'
        }, status=404)
    except Exception as e:
        return JsonResponse({
            'status': 'error',
            'message': f'خطا در حذف فایل: {str(e)}'
        }, status=500)