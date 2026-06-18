# apps/pro/panel.py

from django.shortcuts import render
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views import View
from django.views.decorators.http import require_http_methods
from django.http import JsonResponse
from django.db.models import Q, Sum
from django.core.paginator import Paginator, EmptyPage

from .models import OrderMaterial, OrderDesignStatus, OrderReviewHistory

import json
import logging

logger = logging.getLogger(__name__)


# ==================== صفحه اصلی پنل کاربری ====================
class ProUserOrdersPanelView(LoginRequiredMixin, View):
    def get(self, request):
        return render(request, 'pro_app/panel.html')


# ==================== API لیست سفارشات ====================
class UserProOrdersListAPIView(LoginRequiredMixin, View):
    def get(self, request):
        user = request.user
        orders = OrderMaterial.objects.filter(user=user)

        # فیلترها
        status = request.GET.get('status', '')
        if status:
            orders = orders.filter(status=status)

        design_status = request.GET.get('design_status', '')
        if design_status:
            orders = orders.filter(design_status__status=design_status)

        search = request.GET.get('search', '')
        if search:
            orders = orders.filter(
                Q(id__icontains=search) |
                Q(installation__title__icontains=search)
            )

        sort_by = request.GET.get('sort_by', '-created_at')
        orders = orders.order_by(sort_by)

        # صفحه‌بندی
        page = request.GET.get('page', 1)
        page_size = int(request.GET.get('page_size', 20))
        paginator = Paginator(orders, page_size)

        try:
            orders_page = paginator.page(page)
        except EmptyPage:
            orders_page = paginator.page(paginator.num_pages)

        # محاسبه مجموع مبلغ
        total_amount = 0
        for order in orders:
            if order.total_price:
                total_amount += order.total_price

        # آمار
        stats = {
            'total': orders.count(),
            'pending': orders.filter(status='pending').count(),
            'confirmed': orders.filter(status='confirmed').count(),
            'processing': orders.filter(status='processing').count(),
            'ready': orders.filter(status='ready').count(),
            'delivered': orders.filter(status='delivered').count(),
            'cancelled': orders.filter(status='cancelled').count(),
            'total_amount': float(total_amount),
            'ready_for_review': OrderMaterial.objects.filter(user=user, design_status__status='ready_for_review').count(),
        }

        # ساخت لیست سفارشات
        orders_list = []
        for order in orders_page:
            design_status_obj = getattr(order, 'design_status', None)
            design_status_data = None
            if design_status_obj:
                design_status_data = {
                    'status': design_status_obj.status,
                    'status_display': design_status_obj.get_status_display(),
                    'final_design_image': design_status_obj.final_design_image.url if design_status_obj.final_design_image else None,
                    'operator_message': design_status_obj.operator_message,
                }

            orders_list.append({
                'id': str(order.id),
                'order_number': str(order.id)[:8],
                'installation': {
                    'title': order.installation.title if order.installation else None,
                    'image': order.installation.main_image.url if order.installation and order.installation.main_image else None,
                } if order.installation else None,
                'material': {
                    'title': order.material.title if order.material else None,
                } if order.material else None,
                'length': float(order.length) if order.length else 0,
                'width': float(order.width) if order.width else 0,
                'area': order.area,
                'total_price': int(order.total_price) if order.total_price else 0,
                'total_price_display': f"{int(order.total_price):,}" if order.total_price else '۰',
                'status': order.status,
                'status_display': dict(OrderMaterial.STATUS_CHOICES).get(order.status, ''),
                'design_status': design_status_data,
                'reject_count': order.review_history.filter(action='user_reject').count(),
                'created_at': order.created_at.isoformat(),
            })

        return JsonResponse({
            'status': 'success',
            'orders': orders_list,
            'pagination': {
                'current_page': orders_page.number,
                'total_pages': paginator.num_pages,
                'total_items': paginator.count,
                'has_next': orders_page.has_next(),
                'has_previous': orders_page.has_previous(),
            },
            'stats': stats,
        })


# ==================== API جزئیات سفارش (کامل با طرح و پلن) ====================
class UserProOrderDetailAPIView(LoginRequiredMixin, View):
    def get(self, request, order_id):
        try:
            order = OrderMaterial.objects.select_related(
                'installation', 'material', 'ready_template', 'pdf_document'
            ).prefetch_related('design_status', 'review_history').get(id=order_id)

            if order.user != request.user:
                return JsonResponse({'status': 'error', 'message': 'شما دسترسی ندارید'}, status=403)

            design_status_obj = getattr(order, 'design_status', None)
            design_status_data = None
            if design_status_obj:
                design_status_data = {
                    'status': design_status_obj.status,
                    'status_display': design_status_obj.get_status_display(),
                    'final_design_image': design_status_obj.final_design_image.url if design_status_obj.final_design_image else None,
                    'final_design_psd': design_status_obj.final_design_psd.url if design_status_obj.final_design_psd else None,
                    'operator_message': design_status_obj.operator_message,
                }

            review_history = []
            for review in order.review_history.all():
                review_history.append({
                    'action': review.action,
                    'action_display': review.get_action_display(),
                    'message': review.message,
                    'created_at': review.created_at.isoformat(),
                })

            return JsonResponse({
                'status': 'success',
                'order': {
                    'id': str(order.id),
                    'order_number': str(order.id)[:8],
                    'installation': {
                        'title': order.installation.title if order.installation else None,
                        'image': order.installation.main_image.url if order.installation and order.installation.main_image else None,
                        'price': int(order.installation.price) if order.installation else 0,
                    } if order.installation else None,
                    'material': {
                        'title': order.material.title if order.material else None,
                        'price_multiplier': float(order.material.price_multiplier) if order.material else 1,
                    } if order.material else None,
                    'ready_template': {
                        'title': order.ready_template.title if order.ready_template else None,
                        'image': order.ready_template.image.url if order.ready_template and order.ready_template.image else None,
                        'width': order.ready_template.width if order.ready_template else None,
                        'height': order.ready_template.height if order.ready_template else None,
                    } if order.ready_template else None,
                    'pdf_document': {
                        'title': order.pdf_document.title if order.pdf_document else None,
                        'code': order.pdf_document.code if order.pdf_document else None,
                        'pdf_url': order.pdf_document.pdf_file.url if order.pdf_document and order.pdf_document.pdf_file else None,
                        'thumbnail': order.pdf_document.thumbnail.url if order.pdf_document and order.pdf_document.thumbnail else None,
                    } if order.pdf_document else None,
                    'design_type': order.design_type,
                    'design_type_display': dict(OrderMaterial.DESIGN_TYPES).get(order.design_type, ''),
                    'length': float(order.length) if order.length else 0,
                    'width': float(order.width) if order.width else 0,
                    'area': order.area,
                    'plan_image': order.plan_image.url if order.plan_image else None,
                    'total_price': int(order.total_price) if order.total_price else 0,
                    'total_price_display': f"{int(order.total_price):,}" if order.total_price else '۰',
                    'status': order.status,
                    'status_display': dict(OrderMaterial.STATUS_CHOICES).get(order.status, ''),
                    'notes': order.notes,
                    'design_status': design_status_data,
                    'review_history': review_history,
                    'reject_count': order.review_history.filter(action='user_reject').count(),
                    'created_at': order.created_at.isoformat(),
                }
            })
        except OrderMaterial.DoesNotExist:
            return JsonResponse({'status': 'error', 'message': 'سفارش یافت نشد'}, status=404)


# ==================== API تایید طراحی ====================
class UserApproveDesignAPIView(LoginRequiredMixin, View):
    @require_http_methods(['POST'])
    def post(self, request):
        try:
            data = json.loads(request.body)
            order_id = data.get('order_id')

            order = OrderMaterial.objects.get(id=order_id)
            if order.user != request.user:
                return JsonResponse({'status': 'error', 'message': 'شما دسترسی ندارید'}, status=403)

            design_status, _ = OrderDesignStatus.objects.get_or_create(order=order)

            if design_status.status != 'ready_for_review':
                return JsonResponse({'status': 'error', 'message': 'سفارش در وضعیت قابل تایید نیست'}, status=400)

            design_status.status = 'approved'
            design_status.save()

            OrderReviewHistory.objects.create(
                order=order,
                action='user_approve',
                message='کاربر طرح را تایید کرد',
                created_by=request.user
            )

            return JsonResponse({'status': 'success', 'message': 'طراحی با موفقیت تایید شد'})
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=400)


# ==================== API رد طراحی ====================
class UserRejectDesignAPIView(LoginRequiredMixin, View):
    @require_http_methods(['POST'])
    def post(self, request):
        try:
            data = json.loads(request.body)
            order_id = data.get('order_id')
            message = data.get('message', '')

            if not message:
                return JsonResponse({'status': 'error', 'message': 'لطفاً دلیل رد را وارد کنید'}, status=400)

            order = OrderMaterial.objects.get(id=order_id)
            if order.user != request.user:
                return JsonResponse({'status': 'error', 'message': 'شما دسترسی ندارید'}, status=403)

            reject_count = order.review_history.filter(action='user_reject').count()

            if reject_count >= 3:
                return JsonResponse({'status': 'error', 'message': 'شما بیش از ۳ بار اجازه رد ندارید'}, status=400)

            design_status, _ = OrderDesignStatus.objects.get_or_create(order=order)

            if design_status.status != 'ready_for_review':
                return JsonResponse({'status': 'error', 'message': 'سفارش در وضعیت قابل رد نیست'}, status=400)

            design_status.status = 'rejected'
            design_status.save()

            OrderReviewHistory.objects.create(
                order=order,
                action='user_reject',
                message=message,
                reject_round=reject_count + 1,
                created_by=request.user
            )

            return JsonResponse({'status': 'success', 'message': f'طراحی رد شد (مرتبه {reject_count + 1} از ۳)'})
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=400)


# ==================== API لغو سفارش ====================
class UserCancelOrderAPIView(LoginRequiredMixin, View):
    @require_http_methods(['POST'])
    def post(self, request):
        try:
            data = json.loads(request.body)
            order_id = data.get('order_id')
            reason = data.get('reason', '')

            order = OrderMaterial.objects.get(id=order_id)
            if order.user != request.user:
                return JsonResponse({'status': 'error', 'message': 'شما دسترسی ندارید'}, status=403)

            if order.status not in ['pending', 'confirmed']:
                return JsonResponse({'status': 'error', 'message': 'این سفارش قابل لغو نیست'}, status=400)

            order.status = 'cancelled'
            order.save()

            OrderReviewHistory.objects.create(
                order=order,
                action='user_reject',
                message=reason or 'کاربر سفارش را لغو کرد',
                created_by=request.user
            )

            return JsonResponse({'status': 'success', 'message': 'سفارش با موفقیت لغو شد'})
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=400)