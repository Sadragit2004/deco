# apps/pro/views.py

import json
import base64
import uuid
from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.contrib.auth.decorators import login_required
from django.core.files.base import ContentFile
from django.utils import timezone
from django.db import transaction
from decimal import Decimal, InvalidOperation

from .models import Installation, InstallationMaterial, MaterialPDF, ReadyTemplate, OrderMaterial
from apps.order.models import Order, OrderItem, OrderStatusHistory, OrderStatus, OrderType


# ==================== صفحه اصلی ====================

def proorder_page(request):
    return render(request, 'pro_app/proorder.html')


# ==================== API های مرحله به مرحله ====================

def get_installations(request):
    """مرحله 1: لیست نصبیات همراه با PDFهای هر کدام"""
    installations = Installation.objects.filter(is_active=True).prefetch_related(
        'materials__pdfs'
    )

    data = []
    for ins in installations:
        # جمع‌آوری PDFها از طریق materials
        pdfs = []
        for material in ins.materials.filter(is_active=True):
            for pdf in material.pdfs.all():
                pdfs.append({
                    'id': pdf.id,
                    'title': pdf.title,
                    'code': pdf.code,
                    'material_id': material.id,
                    'material_title': material.title,
                    'file_url': pdf.pdf_file.url if pdf.pdf_file else '',
                    'download_count': pdf.download_count,
                })

        data.append({
            'id': ins.id,
            'title': ins.title,
            'description': ins.description,
            'image': ins.main_image.url if ins.main_image else '',
            'order': ins.order,
            'price': str(ins.price) if ins.price else '0',
            'pdfs': pdfs,
        })

    return JsonResponse({'status': 'success', 'data': data})


def get_materials_by_installation(request, installation_id):
    """مرحله 2: جنس‌های یک نصبیات"""
    materials = InstallationMaterial.objects.filter(
        installation_id=installation_id,
        is_active=True
    )
    data = [{
        'id': m.id,
        'title': m.title,
        'description': m.description,
        'image': m.image.url if m.image else '',
        'price_multiplier': str(m.price_multiplier)
    } for m in materials]
    return JsonResponse({'status': 'success', 'data': data})


@csrf_exempt
@require_http_methods(["POST"])
def verify_pdf_code(request):
    """تایید کد PDF (بدون وابستگی به material_id)"""
    try:
        body = json.loads(request.body)
        code = (body.get('code') or '').strip()

        if not code:
            return JsonResponse({
                'status': 'error', 'valid': False,
                'message': 'کد را وارد کنید'
            })

        pdf = MaterialPDF.objects.filter(code=code).select_related('material').first()
        if pdf:
            return JsonResponse({
                'status': 'success',
                'valid': True,
                'id': pdf.id,
                'title': pdf.title,
                'material_id': pdf.material_id,
                'material_title': pdf.material.title if pdf.material else '',
                'file_url': pdf.pdf_file.url if pdf.pdf_file else ''
            })
        return JsonResponse({'status': 'error', 'valid': False, 'message': 'کد معتبر نیست'})
    except Exception as e:
        return JsonResponse({'status': 'error', 'valid': False, 'message': str(e)})


def get_templates_by_installation(request, installation_id):
    """مرحله 3 (قبلاً 4): طرح‌های آماده یک نصبیات"""
    templates = ReadyTemplate.objects.filter(installation_id=installation_id, is_active=True)
    data = [{
        'id': t.id,
        'title': t.title,
        'description': t.description,
        'image': t.image.url if t.image else '',
        'width': t.width,
        'height': t.height,
        'gallery': [{'image': g.image.url} for g in t.gallery.all()]
    } for t in templates]
    return JsonResponse({'status': 'success', 'data': data})


# ==================== محاسبه قیمت ====================

@csrf_exempt
@require_http_methods(["POST"])
def calculate_price(request):
    """محاسبه قیمت نهایی بر اساس مساحت (متر مربع)"""
    try:
        body = json.loads(request.body)

        length = Decimal(str(body.get('length', 0)))
        width = Decimal(str(body.get('width', 0)))
        area = length * width

        installation_price = Decimal('0')
        if body.get('installation_id'):
            installation = Installation.objects.filter(id=body.get('installation_id')).first()
            if installation:
                installation_price = Decimal(str(installation.price))

        material_multiplier = Decimal('1.0')
        if body.get('material_id'):
            material = InstallationMaterial.objects.filter(id=body.get('material_id')).first()
            if material:
                material_multiplier = Decimal(str(material.price_multiplier))

        base_price_per_meter = installation_price * material_multiplier
        total_price = base_price_per_meter * area

        return JsonResponse({
            'status': 'success',
            'data': {
                'length': str(length),
                'width': str(width),
                'area': str(area),
                'area_display': f"{area:,.2f} متر مربع",
                'installation_price': f"{installation_price:,.0f}",
                'material_multiplier': str(material_multiplier),
                'base_price_per_meter': f"{base_price_per_meter:,.0f}",
                'total_price': f"{total_price:,.0f}",
                'total_price_raw': str(total_price)
            }
        })

    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)})


# ==================== ثبت سفارش (ادغام در سیستم اصلی Order) ====================

@csrf_exempt
@require_http_methods(["POST"])
@transaction.atomic
def create_pro_order(request):
    """ایجاد سفارش نصبیات و ادغام با سیستم اصلی Order"""
    try:
        body = json.loads(request.body)

        # ==================== محاسبه مساحت و قیمت ====================
        try:
            length = Decimal(str(body.get('length', 0)))
            width = Decimal(str(body.get('width', 0)))
        except (InvalidOperation, ValueError, TypeError):
            return JsonResponse({'status': 'error', 'message': 'ابعاد نامعتبر است'})

        if length <= 0 or width <= 0:
            return JsonResponse({'status': 'error', 'message': 'طول و عرض باید مثبت باشند'})

        area = length * width

        installation_price = Decimal('0')
        installation_title = "نصبیات"
        if body.get('installation_id'):
            installation = Installation.objects.filter(id=body.get('installation_id')).first()
            if installation:
                installation_price = Decimal(str(installation.price))
                installation_title = installation.title

        material_multiplier = Decimal('1.0')
        material_title = ""
        if body.get('material_id'):
            material = InstallationMaterial.objects.filter(id=body.get('material_id')).first()
            if material:
                material_multiplier = Decimal(str(material.price_multiplier))
                material_title = material.title

        base_price_per_meter = installation_price * material_multiplier
        total_price = base_price_per_meter * area

        # ==================== ایجاد Order اصلی ====================
        order = Order.objects.create(
            user=request.user if request.user.is_authenticated else None,
            order_type=OrderType.PRINT.value,
            status=OrderStatus.PENDING.value,
            subtotal=total_price,
            discount_amount=0,
            coupon_discount=0,
            shipping_cost=0,
            total=total_price,
            description=body.get('notes', '')
        )

        # ==================== ایجاد OrderItem ====================
        product_title = f"{installation_title} - {material_title}".strip(" -")
        if not product_title:
            product_title = "سفارش چاپی"

        order_item = OrderItem.objects.create(
            order=order,
            product=None,
            product_title=product_title,
            product_code=f"PRINT-{timezone.now().strftime('%Y%m%d%H%M%S')}-{str(order.id)[:8]}",
            quantity=1,
            unit_price=total_price,
            unit_price_before_discount=total_price,
            discount_amount=0,
            discount_percent=0,
            total=total_price,
            sales_unit_name="متر مربع",
            use_packaging=False
        )

        # ==================== ایجاد OrderMaterial ====================
        pro_order_material = OrderMaterial.objects.create(
            user=request.user if request.user.is_authenticated else None,
            installation_id=body.get('installation_id'),
            material_id=body.get('material_id'),
            pdf_document_id=body.get('pdf_id'),
            ready_template_id=body.get('template_id'),
            design_type=body.get('design_type', 'custom'),
            length=length,
            width=width,
            total_price=total_price,
            notes=body.get('notes', ''),
            status='pending'
        )

        # ذخیره عکس پلن اگر وجود داشته باشد
        plan_image_data = body.get('plan_image')
        if plan_image_data and isinstance(plan_image_data, str) and ';base64,' in plan_image_data:
            try:
                fmt, imgstr = plan_image_data.split(';base64,', 1)
                ext = fmt.split('/')[-1].split(';')[0] or 'png'
                filename = f"plan_{pro_order_material.id}.{ext}"
                pro_order_material.plan_image.save(
                    filename,
                    ContentFile(base64.b64decode(imgstr)),
                    save=False
                )
                pro_order_material.save(update_fields=['plan_image'])
            except Exception as img_err:
                # اگر عکس خراب بود، حداقل بقیه سفارش ذخیره شود
                print(f"Plan image save error: {img_err}")

        # اتصال OrderMaterial به Order
        order.printing = pro_order_material
        order.save(update_fields=['printing'])

        # ==================== ثبت تاریخچه وضعیت ====================
        OrderStatusHistory.objects.create(
            order=order,
            status=OrderStatus.PENDING.value,
            note=f"سفارش چاپی: {product_title} | ابعاد: {length}×{width} متر | مبلغ: {total_price:,.0f} تومان"
        )

        return JsonResponse({
            'status': 'success',
            'message': 'سفارش با موفقیت ایجاد شد',
            'order_id': str(order.id),
            'order_number': getattr(order, 'order_number', str(order.id)[:8]),
            'total_price': f"{total_price:,.0f}",
            'redirect_url': f'/order/checkout/{str(order.id)}/'
        })

    except Exception as e:
        import traceback
        traceback.print_exc()
        return JsonResponse({
            'status': 'error',
            'message': f'خطا در ثبت سفارش: {str(e)}'
        })