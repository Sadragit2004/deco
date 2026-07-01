# apps/chat/consumers.py

import json
import base64
from django.core.files.base import ContentFile
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from .models import Chat, Message
from apps.user.models.user import CustomUser


class ChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.user = self.scope['user']

        if self.user.is_anonymous:
            await self.close()
            return

        self.user_group = f"user_{self.user.id}"
        await self.channel_layer.group_add(self.user_group, self.channel_name)

        if self.user.is_staff:
            self.admin_group = "admin_group"
            await self.channel_layer.group_add(self.admin_group, self.channel_name)
            print(f"✅ ادمین {self.user.mobileNumber} متصل شد")
        else:
            print(f"✅ کاربر {self.user.mobileNumber} متصل شد")

        await self.accept()

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(self.user_group, self.channel_name)
        if hasattr(self, 'admin_group'):
            await self.channel_layer.group_discard(self.admin_group, self.channel_name)
        print(f"🔴 کاربر {self.user.mobileNumber} قطع شد")

    # ================================================================
    # متد دریافت پیام
    # ================================================================
    async def receive(self, text_data):
        try:
            data = json.loads(text_data)

            # ========== نشانه‌گذاری دسته‌جمعی پیام‌ها به عنوان دیده شده ==========
            if data.get('action') == 'mark_chat_seen':
                chat_id = data.get('chat_id')
                if self.user.is_staff and chat_id:
                    await self.mark_chat_messages_as_seen(chat_id)
                    return

            message = data.get('message', '').strip()
            chat_id = data.get('chat_id')
            file_data = data.get('file')
            file_name = data.get('file_name')
            file_type = data.get('file_type', 'file')
            temp_id = data.get('temp_id')

            # ========== علامت‌گذاری پیام به عنوان دیده شده (SEEN) ==========
            message_id = data.get('message_id')
            if message_id and self.user.is_staff:
                await self.mark_message_as_seen(message_id)
                return

            if not message and not file_data:
                return

            print(f"📩 دریافت پیام از {self.user.mobileNumber}")

            # ============================================================
            # ارسال پیام توسط ادمین
            # ============================================================
            if self.user.is_staff and chat_id:
                try:
                    chat = await self.get_chat_by_id(chat_id)
                    if not chat:
                        await self.send(text_data=json.dumps({
                            'type': 'error',
                            'message': 'چت پیدا نشد'
                        }))
                        return

                    saved_message = await self.save_message_admin(
                        chat,
                        self.user,
                        message,
                        file_data,
                        file_name,
                        file_type
                    )

                    if not saved_message:
                        await self.send(text_data=json.dumps({
                            'type': 'error',
                            'message': 'خطا در ذخیره پیام'
                        }))
                        return

                    admin_message_data = {
                        'type': 'admin_message',
                        'message_id': str(saved_message.id),
                        'message': saved_message.content or '',
                        'sender_id': str(self.user.id),
                        'sender_name': 'ادمین',
                        'timestamp': saved_message.timestamp.isoformat(),
                        'chat_id': str(chat.id),
                        'user_id': str(chat.user.id),
                        'is_admin': True,
                        'message_type': saved_message.message_type,
                        'file_url': saved_message.file_url if saved_message.file else None,
                        'file_name': saved_message.file_name,
                        'file_size': saved_message.file_size_display,
                        'file_thumbnail': saved_message.file_thumbnail.url if saved_message.file_thumbnail else None,
                        'temp_id': temp_id,
                        'is_read': saved_message.is_read,
                        'is_seen': saved_message.is_seen,
                    }

                    user_message_data = {
                        'type': 'chat_message',
                        'message_id': str(saved_message.id),
                        'message': saved_message.content or '',
                        'sender_id': str(self.user.id),
                        'sender_name': 'ادمین',
                        'timestamp': saved_message.timestamp.isoformat(),
                        'is_admin': True,
                        'message_type': saved_message.message_type,
                        'file_url': saved_message.file_url if saved_message.file else None,
                        'file_name': saved_message.file_name,
                        'file_size': saved_message.file_size_display,
                        'file_thumbnail': saved_message.file_thumbnail.url if saved_message.file_thumbnail else None,
                        'temp_id': temp_id,
                        'is_read': saved_message.is_read,
                        'is_seen': saved_message.is_seen,
                    }

                    await self.channel_layer.group_send("admin_group", admin_message_data)

                    user_group = f"user_{chat.user.id}"
                    await self.channel_layer.group_send(user_group, user_message_data)

                    print(f"✅ پیام ادمین به کاربر {chat.user.mobileNumber} ارسال شد")
                    return

                except Exception as e:
                    print(f"❌ خطا در ارسال پیام ادمین: {e}")
                    await self.send(text_data=json.dumps({
                        'type': 'error',
                        'message': f'خطا در ارسال پیام: {str(e)}'
                    }))

            # ============================================================
            # ارسال پیام توسط کاربر
            # ============================================================
            else:
                try:
                    saved_message = await self.save_message(
                        self.user,
                        message,
                        file_data,
                        file_name,
                        file_type
                    )

                    if not saved_message:
                        await self.send(text_data=json.dumps({
                            'type': 'error',
                            'message': 'خطا در ذخیره پیام'
                        }))
                        return

                    # 🔥 مهم: temp_id را در پیام ارسال می‌کنیم تا فرانت‌اند پیام موقتی را جایگزین کند
                    user_message_data = {
                        'type': 'chat_message',
                        'message_id': str(saved_message.id),
                        'message': saved_message.content or '',
                        'sender_id': str(self.user.id),
                        'sender_name': self.user.name or self.user.mobileNumber,
                        'timestamp': saved_message.timestamp.isoformat(),
                        'is_admin': False,
                        'message_type': saved_message.message_type,
                        'file_url': saved_message.file_url if saved_message.file else None,
                        'file_name': saved_message.file_name,
                        'file_size': saved_message.file_size_display,
                        'file_thumbnail': saved_message.file_thumbnail.url if saved_message.file_thumbnail else None,
                        'temp_id': temp_id,
                        'is_read': saved_message.is_read,
                        'is_seen': saved_message.is_seen,
                    }

                    admin_message_data = {
                        'type': 'admin_message',
                        'message_id': str(saved_message.id),
                        'message': saved_message.content or '',
                        'sender_id': str(self.user.id),
                        'sender_name': self.user.name or self.user.mobileNumber,
                        'timestamp': saved_message.timestamp.isoformat(),
                        'chat_id': str(saved_message.chat.id),
                        'user_id': str(self.user.id),
                        'is_admin': False,
                        'message_type': saved_message.message_type,
                        'file_url': saved_message.file_url if saved_message.file else None,
                        'file_name': saved_message.file_name,
                        'file_size': saved_message.file_size_display,
                        'file_thumbnail': saved_message.file_thumbnail.url if saved_message.file_thumbnail else None,
                        'temp_id': temp_id,
                        'is_read': saved_message.is_read,
                        'is_seen': saved_message.is_seen,
                    }

                    # ارسال به کاربر (خودش)
                    await self.channel_layer.group_send(f"user_{self.user.id}", user_message_data)

                    # ارسال به ادمین‌ها
                    await self.channel_layer.group_send("admin_group", admin_message_data)

                    print(f"✅ پیام کاربر {self.user.mobileNumber} ارسال شد")

                except Exception as e:
                    print(f"❌ خطا در ارسال پیام کاربر: {e}")
                    await self.send(text_data=json.dumps({
                        'type': 'error',
                        'message': f'خطا در ارسال پیام: {str(e)}'
                    }))

        except json.JSONDecodeError:
            print("❌ خطا در دیکد کردن JSON")
            await self.send(text_data=json.dumps({
                'type': 'error',
                'message': 'داده نامعتبر'
            }))
        except Exception as e:
            print(f"❌ خطای ناشناخته: {e}")
            await self.send(text_data=json.dumps({
                'type': 'error',
                'message': f'خطا: {str(e)}'
            }))

    # ================================================================
    # متدهای دریافت پیام
    # ================================================================
    async def chat_message(self, event):
        await self.send(text_data=json.dumps({
            'type': 'chat_message',
            'message_id': event.get('message_id'),
            'message': event.get('message', ''),
            'sender_id': event.get('sender_id'),
            'sender_name': event.get('sender_name'),
            'timestamp': event.get('timestamp'),
            'is_admin': event.get('is_admin', False),
            'message_type': event.get('message_type', 'text'),
            'file_url': event.get('file_url'),
            'file_name': event.get('file_name'),
            'file_size': event.get('file_size'),
            'file_thumbnail': event.get('file_thumbnail'),
            'temp_id': event.get('temp_id'),
            'is_read': event.get('is_read', False),
            'is_seen': event.get('is_seen', False),
        }))

    async def admin_message(self, event):
        await self.send(text_data=json.dumps({
            'type': 'admin_message',
            'message_id': event.get('message_id'),
            'message': event.get('message', ''),
            'sender_id': event.get('sender_id'),
            'sender_name': event.get('sender_name'),
            'timestamp': event.get('timestamp'),
            'chat_id': event.get('chat_id'),
            'user_id': event.get('user_id'),
            'is_admin': event.get('is_admin', False),
            'message_type': event.get('message_type', 'text'),
            'file_url': event.get('file_url'),
            'file_name': event.get('file_name'),
            'file_size': event.get('file_size'),
            'file_thumbnail': event.get('file_thumbnail'),
            'temp_id': event.get('temp_id'),
            'is_read': event.get('is_read', False),
            'is_seen': event.get('is_seen', False),
        }))

    # ================================================================
    # هندلر بروزرسانی دیده شدن
    # ================================================================
    async def message_seen_update(self, event):
        """ارسال بروزرسانی دیده شدن یک پیام"""
        await self.send(text_data=json.dumps({
            'type': 'message_seen_update',
            'message_id': event.get('message_id'),
            'chat_id': event.get('chat_id'),
            'is_seen': event.get('is_seen', True),
        }))

    async def messages_seen_update(self, event):
        """ارسال بروزرسانی دیده شدن دسته‌جمعی"""
        await self.send(text_data=json.dumps({
            'type': 'messages_seen_update',
            'chat_id': event.get('chat_id'),
            'user_id': event.get('user_id'),
            'count': event.get('count', 0),
        }))

    # ================================================================
    # متدهای دیتابیس
    # ================================================================

    @database_sync_to_async
    def save_message(self, sender, content, file_data=None, file_name=None, file_type='text'):
        try:
            chat, created = Chat.objects.get_or_create(
                user=sender,
                defaults={'admin': CustomUser.objects.filter(is_staff=True).first()}
            )
            chat.has_unread = True
            chat.save()

            message = Message(
                chat=chat,
                sender=sender,
                message_type=file_type if file_data else 'text',
                content=content or '',
                is_read=False,
                is_seen=False,
            )

            if file_data:
                format, imgstr = file_data.split(';base64,')
                ext = format.split('/')[-1]
                file_content = ContentFile(base64.b64decode(imgstr), name=f"{file_name or 'file'}.{ext}")
                message.file = file_content
                message.file_name = file_name or f"file.{ext}"
                message.file_size = file_content.size

            message.save()
            return message

        except Exception as e:
            print(f"❌ خطا در save_message: {e}")
            raise

    @database_sync_to_async
    def save_message_admin(self, chat, admin, content, file_data=None, file_name=None, file_type='text'):
        try:
            message = Message(
                chat=chat,
                sender=admin,
                message_type=file_type if file_data else 'text',
                content=content or ''
            )
            message.is_read = True
            message.is_seen = True

            if file_data:
                format, imgstr = file_data.split(';base64,')
                ext = format.split('/')[-1]
                file_content = ContentFile(base64.b64decode(imgstr), name=f"{file_name or 'file'}.{ext}")
                message.file = file_content
                message.file_name = file_name or f"file.{ext}"
                message.file_size = file_content.size

            message.save()

            chat.has_unread = False
            chat.save()

            return message

        except Exception as e:
            print(f"❌ خطا در save_message_admin: {e}")
            raise

    @database_sync_to_async
    def get_chat_by_id(self, chat_id):
        try:
            return Chat.objects.select_related('user').get(id=chat_id)
        except Chat.DoesNotExist:
            return None
        except Exception as e:
            print(f"❌ خطا در get_chat_by_id: {e}")
            return None

    # ================================================================
    # علامت‌گذاری پیام به عنوان دیده شده
    # ================================================================

    @database_sync_to_async
    def mark_message_as_seen(self, message_id):
        """علامت‌گذاری یک پیام به عنوان دیده شده توسط ادمین"""
        try:
            message = Message.objects.get(id=message_id)
            if not message.is_seen:
                message.is_seen = True
                message.is_read = True
                message.save()
                print(f"✅ پیام {message_id} به عنوان دیده شده علامت‌گذاری شد")

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
                return True
            return True
        except Message.DoesNotExist:
            print(f"❌ پیام {message_id} پیدا نشد")
            return False
        except Exception as e:
            print(f"❌ خطا در mark_message_as_seen: {e}")
            return False

    # ================================================================
    # نشانه‌گذاری دسته‌جمعی پیام‌های چت
    # ================================================================

    @database_sync_to_async
    def mark_chat_messages_as_seen(self, chat_id):
        """نشانه‌گذاری تمام پیام‌های یک چت به عنوان دیده شده"""
        try:
            chat = Chat.objects.get(id=chat_id)

            updated_count = chat.messages.filter(
                is_read=True,
                is_seen=False
            ).exclude(sender=self.user).update(is_seen=True)

            read_count = chat.messages.filter(
                is_read=False
            ).exclude(sender=self.user).update(is_read=True, is_seen=True)

            total_updated = updated_count + read_count

            if total_updated > 0:
                chat.has_unread = False
                chat.save()

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

            return total_updated

        except Chat.DoesNotExist:
            print(f"❌ چت {chat_id} پیدا نشد")
            return 0
        except Exception as e:
            print(f"❌ خطا در mark_chat_messages_as_seen: {e}")
            return 0