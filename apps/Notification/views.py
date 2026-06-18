# notifications/views.py
from django.http import JsonResponse
from django.views import View
from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator
from apps.order.models import Order, OrderStatus
from .models import OrderStatusNotification
import json
from django.utils import timezone


@method_decorator(login_required, name='dispatch')
class OrderNotificationsAPI(View):

    def get(self, request):
        # گرفتن آخرین 50 اعلان
        notifications = OrderStatusNotification.objects.filter(
            user=request.user
        ).order_by('-created_at')[:50]

        data = []
        for n in notifications:
            data.append({
                'id': n.id,
                'order_number': n.order.order_number,
                'old_status': n.old_status,
                'new_status': n.new_status,
                'message': n.message,
                'status_changed_at': n.status_changed_at.strftime('%Y-%m-%d %H:%M:%S'),
                'created_at': n.created_at.strftime('%Y-%m-%d %H:%M:%S'),
                'is_sent': n.is_sent
            })

        # شمارنده اعلان‌های نخوانده
        unread_count = OrderStatusNotification.objects.filter(
            user=request.user,
            is_sent=False
        ).count()

        # آخرین سفارش در انتظار پرداخت
        pending_order = Order.objects.filter(
            user=request.user,
            status=OrderStatus.PENDING.value  # حتماً .value
        ).order_by('-created_at').first()

        pending_data = None
        if pending_order:
            pending_data = {
                'order_id': str(pending_order.id),
                'order_number': pending_order.order_number,
                'total_amount': int(pending_order.total),
                'total_amount_display': f"{int(pending_order.total):,}",
                'created_at': pending_order.created_at.strftime('%Y-%m-%d %H:%M:%S')
            }

        return JsonResponse({
            'success': True,
            'unread_count': unread_count,
            'notifications': data,
            'pending_order': pending_data
        })


class MarkNotificationReadAPI(View):
    """علامت زدن اعلان به عنوان خوانده شده"""

    @method_decorator(login_required)
    def post(self, request):
        try:
            body = json.loads(request.body)
            notification_id = body.get('notification_id')

            notification = OrderStatusNotification.objects.get(
                id=notification_id,
                user=request.user
            )
            notification.is_sent = True
            notification.sent_at = timezone.now()
            notification.save()

            return JsonResponse({'success': True})
        except OrderStatusNotification.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'اعلان یافت نشد'}, status=404)
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)}, status=400)


class MarkAllNotificationsReadAPI(View):
    """علامت زدن همه اعلان‌ها به عنوان خوانده شده"""

    @method_decorator(login_required)
    def post(self, request):
        OrderStatusNotification.objects.filter(
            user=request.user,
            is_sent=False
        ).update(is_sent=True, sent_at=timezone.now())

        return JsonResponse({'success': True})