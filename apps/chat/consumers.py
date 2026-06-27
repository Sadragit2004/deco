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

        # گروه اختصاصی برای هر کاربر
        self.user_group = f"user_{self.user.id}"
        await self.channel_layer.group_add(self.user_group, self.channel_name)

        # اگر ادمین است، به گروه ادمین‌ها اضافه شود
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

    async def receive(self, text_data):
        try:
            data = json.loads(text_data)

            # ========== پیام متنی ==========
            message = data.get('message', '').strip()
            chat_id = data.get('chat_id')

            # ========== پیام فایل ==========
            file_data = data.get('file')
            file_name = data.get('file_name')
            file_type = data.get('file_type', 'file')

            # اگر پیام متنی داریم یا فایل داریم
            if not message and not file_data:
                return

            print(f"📩 دریافت پیام از {self.user.mobileNumber}")
            if message:
                print(f"📝 متن: {message[:30]}...")
            if file_data:
                print(f"📎 فایل: {file_name} (نوع: {file_type})")

            # ========== ادمین در حال ارسال پیام ==========
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

                    # داده برای ادمین‌ها (با chat_id)
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
                    }

                    # داده برای کاربر
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
                    }

                    # ارسال به همه ادمین‌ها
                    await self.channel_layer.group_send("admin_group", admin_message_data)

                    # ارسال به کاربر
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

            # ========== کاربر عادی در حال ارسال پیام ==========
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

                    # داده برای خود کاربر (chat_message)
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
                    }

                    # داده برای ادمین‌ها (admin_message با chat_id)
                    admin_message_data = {
                        'type': 'admin_message',
                        'message_id': str(saved_message.id),
                        'message': saved_message.content or '',
                        'sender_id': str(self.user.id),
                        'sender_name': self.user.name or self.user.mobileNumber,
                        'timestamp': saved_message.timestamp.isoformat(),
                        'chat_id': str(saved_message.chat.id),
                        'user_id': str(self.user.id),
                        'is_admin': False,  # کاربر عادی = False
                        'message_type': saved_message.message_type,
                        'file_url': saved_message.file_url if saved_message.file else None,
                        'file_name': saved_message.file_name,
                        'file_size': saved_message.file_size_display,
                        'file_thumbnail': saved_message.file_thumbnail.url if saved_message.file_thumbnail else None,
                    }

                    # ارسال به خود کاربر
                    await self.channel_layer.group_send(f"user_{self.user.id}", user_message_data)

                    # ارسال به همه ادمین‌ها
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

    # ========== متدهای دریافت پیام ==========
    async def chat_message(self, event):
        """هندلر برای پیام‌های چت (کاربر عادی)"""
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
        }))

    async def admin_message(self, event):
        """هندلر برای پیام‌های ادمین"""
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
        }))

    # ========== متدهای دیتابیس ==========
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
                content=content or ''
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