# apps/chat/views.py

from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.http import JsonResponse
from django.db.models import Q, Count, Max
from django.conf import settings
from .models import Chat, Message
from apps.user.models.user import CustomUser
from apps.user.models.profile import UserAddress, Province, City
from apps.user.models.profile import Wallet, WalletTransaction
from apps.user.models.profile import CustomerLoyalty, LoyaltyTransaction
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
                    'message_type': msg.message_type,
                    'file_url': msg.file.url if msg.file else None,
                    'file_name': msg.file_name,
                    'file_size': msg.file_size_display,
                    'file_thumbnail': msg.file_thumbnail.url if msg.file_thumbnail else None,
                    'is_seen': msg.is_seen,
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
    """دریافت لیست تمام چت‌ها برای ادمین - مرتب شده بر اساس آخرین پیام"""
    chats = Chat.objects.filter(is_active=True).select_related('user', 'admin').prefetch_related('messages').annotate(
        last_msg_time=Max('messages__timestamp')
    ).order_by('-last_msg_time')

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
            'user_id': str(chat.user.id),
            'user_name': chat.user.name or chat.user.mobileNumber,
            'user_mobile': chat.user.mobileNumber,
            'last_message': last_msg_content,
            'last_message_time': last_message.timestamp.isoformat() if last_message else None,
            'unread_count': unread_count,
            'has_unread': chat.has_unread,
            'created_at': chat.created_at.isoformat(),
            'is_active': chat.is_active,
            'user_avatar': chat.user.avatar.url if chat.user.avatar else None,
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

    # ============================================================
    # 🔥 علامت‌گذاری پیام‌ها به عنوان دیده شده (SEEN)
    # ============================================================
    unseen_count = chat.messages.filter(is_seen=False).exclude(sender=request.user).update(is_seen=True)

    if unseen_count > 0:
        try:
            from channels.layers import get_channel_layer
            from asgiref.sync import async_to_sync

            channel_layer = get_channel_layer()

            async_to_sync(channel_layer.group_send)(
                f"user_{chat.user.id}",
                {
                    'type': 'messages_seen_update',
                    'chat_id': str(chat.id),
                    'user_id': str(chat.user.id),
                    'count': unseen_count,
                }
            )

            async_to_sync(channel_layer.group_send)(
                "admin_group",
                {
                    'type': 'messages_seen_update',
                    'chat_id': str(chat.id),
                    'user_id': str(chat.user.id),
                    'count': unseen_count,
                }
            )
            print(f"✅ {unseen_count} پیام در چت {chat_id} به عنوان دیده شده علامت‌گذاری شد")
        except Exception as e:
            print(f"❌ خطا در ارسال بروزرسانی دیده شدن: {e}")

    data = {
        'status': 'success',
        'chat': {
            'id': chat.id,
            'user_id': str(chat.user.id),
            'user_name': chat.user.name or chat.user.mobileNumber,
            'user_mobile': chat.user.mobileNumber,
            'is_active': chat.is_active,
            'created_at': chat.created_at.isoformat(),
            'user_avatar': chat.user.avatar.url if chat.user.avatar else None,
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
                'message_type': msg.message_type,
                'file_url': msg.file.url if msg.file else None,
                'file_name': msg.file_name,
                'file_size': msg.file_size_display,
                'file_thumbnail': msg.file_thumbnail.url if msg.file_thumbnail else None,
                'is_seen': msg.is_seen,
            }
            for msg in messages
        ]
    }

    return JsonResponse(data)


# ================================================================
# 🔥 ویو جدید: دریافت اطلاعات کامل مشتری
# ================================================================
@login_required
@user_passes_test(lambda u: u.is_staff)
def get_customer_info(request, user_id):
    """
    دریافت اطلاعات کامل یک مشتری برای نمایش در داشبورد ادمین
    شامل: اطلاعات شخصی، آدرس‌ها، کیف پول، امتیازات، تاریخچه سفارشات
    """
    try:
        user = get_object_or_404(CustomUser, id=user_id)

        # اطلاعات شخصی
        user_data = {
            'id': str(user.id),
            'mobile': user.mobileNumber,
            'name': user.name or '',
            'family': user.family or '',
            'full_name': f"{user.name or ''} {user.family or ''}".strip() or user.mobileNumber,
            'email': user.email or '',
            'gender': dict(user.GENDER_CHOICES).get(user.gender, ''),
            'birth_date': user.birth_date.isoformat() if user.birth_date else None,
            'age': user.age,
            'shop_name': user.shop_name or '',
            'is_online': user.is_online,
            'last_activity': user.last_activity.isoformat() if user.last_activity else None,
            'created_at': user.createAt.isoformat() if user.createAt else None,
            'avatar': user.avatar.url if user.avatar else None,
        }

        # آدرس‌ها
        addresses = []
        for addr in user.addresses.filter(is_active=True):
            addresses.append({
                'id': addr.id,
                'type': addr.get_address_type_display(),
                'province': addr.province.name,
                'city': addr.city.name,
                'address': addr.address_text,
                'postal_code': addr.postal_code or '',
                'is_default': addr.is_default,
            })

        # کیف پول
        wallet_data = None
        try:
            wallet = user.wallet
            wallet_data = {
                'balance': wallet.balance,
                'frozen_balance': wallet.frozen_balance,
                'total_balance': wallet.balance + wallet.frozen_balance,
                'created_at': wallet.created_at.isoformat(),
            }
        except Wallet.DoesNotExist:
            wallet_data = {
                'balance': 0,
                'frozen_balance': 0,
                'total_balance': 0,
                'created_at': None,
            }

        # امتیازات وفاداری
        loyalty_data = None
        try:
            loyalty = user.loyalty
            tier_map = {
                'select': 'انتخاب شده',
                'premium': 'پریمیوم',
                'elite': 'الیت',
                'private': 'پرایویت',
            }
            loyalty_data = {
                'total_points': loyalty.total_points,
                'total_coins': loyalty.total_coins,
                'current_tier': tier_map.get(loyalty.current_tier, loyalty.current_tier),
                'lifetime_purchase': loyalty.lifetime_purchase,
                'created_at': loyalty.created_at.isoformat(),
            }
        except CustomerLoyalty.DoesNotExist:
            loyalty_data = {
                'total_points': 0,
                'total_coins': 0,
                'current_tier': 'انتخاب شده',
                'lifetime_purchase': 0,
                'created_at': None,
            }

        # آمار چت
        try:
            chat = Chat.objects.get(user=user)
            chat_data = {
                'total_messages': chat.messages.count(),
                'user_messages': chat.messages.filter(sender=user).count(),
                'admin_messages': chat.messages.filter(sender__is_staff=True).count(),
                'last_message': chat.messages.last().timestamp.isoformat() if chat.messages.last() else None,
                'created_at': chat.created_at.isoformat(),
            }
        except Chat.DoesNotExist:
            chat_data = {
                'total_messages': 0,
                'user_messages': 0,
                'admin_messages': 0,
                'last_message': None,
                'created_at': None,
            }

        return JsonResponse({
            'status': 'success',
            'data': {
                'user': user_data,
                'addresses': addresses,
                'wallet': wallet_data,
                'loyalty': loyalty_data,
                'chat': chat_data,
            }
        })

    except CustomUser.DoesNotExist:
        return JsonResponse({
            'status': 'error',
            'message': 'کاربر پیدا نشد'
        }, status=404)
    except Exception as e:
        return JsonResponse({
            'status': 'error',
            'message': f'خطا: {str(e)}'
        }, status=500)


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


# ======================== API برای آپلود فایل ========================
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

    if file.size > 10 * 1024 * 1024:
        return JsonResponse({
            'status': 'error',
            'message': 'حجم فایل بیشتر از 10 مگابایت است'
        }, status=400)

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

        if message.sender != request.user and not request.user.is_staff:
            return JsonResponse({
                'status': 'error',
                'message': 'شما دسترسی به این پیام ندارید'
            }, status=403)

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


# ======================== 🔥 API برای نشانه‌گذاری دیده شده (SEEN) ========================

@login_required
@user_passes_test(lambda u: u.is_staff)
def mark_messages_as_seen(request, chat_id):
    """نشانه‌گذاری تمام پیام‌های یک چت به عنوان دیده شده"""
    if request.method != 'POST':
        return JsonResponse({
            'status': 'error',
            'message': 'روش نامعتبر'
        }, status=405)

    try:
        chat = get_object_or_404(Chat, id=chat_id)

        updated_count = chat.messages.filter(
            is_read=True,
            is_seen=False
        ).exclude(sender=request.user).update(is_seen=True)

        read_count = chat.messages.filter(
            is_read=False
        ).exclude(sender=request.user).update(is_read=True, is_seen=True)

        total_updated = updated_count + read_count

        chat.has_unread = False
        chat.save()

        if total_updated > 0:
            try:
                from channels.layers import get_channel_layer
                from asgiref.sync import async_to_sync

                channel_layer = get_channel_layer()

                async_to_sync(channel_layer.group_send)(
                    "admin_group",
                    {
                        'type': 'messages_seen_update',
                        'chat_id': str(chat.id),
                        'user_id': str(chat.user.id),
                        'count': total_updated,
                    }
                )

                async_to_sync(channel_layer.group_send)(
                    f"user_{chat.user.id}",
                    {
                        'type': 'messages_seen_update',
                        'chat_id': str(chat.id),
                        'user_id': str(chat.user.id),
                        'count': total_updated,
                    }
                )

                print(f"✅ {total_updated} پیام در چت {chat_id} به عنوان دیده شده علامت‌گذاری شد")
            except Exception as e:
                print(f"❌ خطا در ارسال بروزرسانی دیده شدن: {e}")

        return JsonResponse({
            'status': 'success',
            'message': f'{total_updated} پیام به عنوان دیده شده علامت‌گذاری شد',
            'updated_count': total_updated
        })

    except Chat.DoesNotExist:
        return JsonResponse({
            'status': 'error',
            'message': 'چت پیدا نشد'
        }, status=404)
    except Exception as e:
        return JsonResponse({
            'status': 'error',
            'message': f'خطا: {str(e)}'
        }, status=500)


@login_required
def mark_single_message_seen(request, message_id):
    """نشانه‌گذاری یک پیام خاص به عنوان دیده شده"""
    if request.method != 'POST':
        return JsonResponse({
            'status': 'error',
            'message': 'روش نامعتبر'
        }, status=405)

    try:
        message = Message.objects.get(id=message_id)

        if request.user.is_staff or message.sender == request.user:
            if not message.is_seen:
                message.is_seen = True
                message.is_read = True
                message.save()

                try:
                    from channels.layers import get_channel_layer
                    from asgiref.sync import async_to_sync

                    channel_layer = get_channel_layer()

                    async_to_sync(channel_layer.group_send)(
                        "admin_group",
                        {
                            'type': 'message_seen_update',
                            'message_id': str(message.id),
                            'chat_id': str(message.chat.id),
                            'is_seen': True,
                        }
                    )

                    async_to_sync(channel_layer.group_send)(
                        f"user_{message.sender.id}",
                        {
                            'type': 'message_seen_update',
                            'message_id': str(message.id),
                            'chat_id': str(message.chat.id),
                            'is_seen': True,
                        }
                    )

                    print(f"✅ پیام {message_id} به عنوان دیده شده علامت‌گذاری شد")
                except Exception as e:
                    print(f"❌ خطا در ارسال بروزرسانی دیده شدن: {e}")

                return JsonResponse({
                    'status': 'success',
                    'message': 'پیام به عنوان دیده شده علامت‌گذاری شد'
                })

        return JsonResponse({
            'status': 'error',
            'message': 'شما دسترسی به این عملیات ندارید'
        }, status=403)

    except Message.DoesNotExist:
        return JsonResponse({
            'status': 'error',
            'message': 'پیام پیدا نشد'
        }, status=404)
    except Exception as e:
        return JsonResponse({
            'status': 'error',
            'message': f'خطا: {str(e)}'
        }, status=500)


@login_required
def get_message_seen_status(request, message_id):
    """دریافت وضعیت دیده شدن یک پیام"""
    try:
        message = Message.objects.get(id=message_id)

        return JsonResponse({
            'status': 'success',
            'message_id': str(message.id),
            'is_seen': message.is_seen,
            'is_read': message.is_read,
        })

    except Message.DoesNotExist:
        return JsonResponse({
            'status': 'error',
            'message': 'پیام پیدا نشد'
        }, status=404)