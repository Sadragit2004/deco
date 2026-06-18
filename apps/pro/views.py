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
from decimal import Decimal

from .models import Installation, InstallationMaterial, MaterialPDF, ReadyTemplate, OrderMaterial
from apps.order.models import Order, OrderItem, OrderStatusHistory, OrderStatus, OrderType


# ==================== صفحه اصلی ====================

def proorder_page(request):
    return render(request, 'pro_app/proorder.html')


# ==================== API های مرحله به مرحله ====================

def get_installations(request):
    """مرحله 1: لیست نصبیات"""
    installations = Installation.objects.filter(is_active=True)
    data = [{
        'id': ins.id,
        'title': ins.title,
        'description': ins.description,
        'image': ins.main_image.url if ins.main_image else '',
        'order': ins.order,
        'price': str(ins.price) if ins.price else '0'
    } for ins in installations]
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


def get_pdfs_by_material(request, material_id):
    """مرحله 3: PDFهای مخصوص یک جنس"""
    pdfs = MaterialPDF.objects.filter(material_id=material_id)
    data = [{
        'id': p.id,
        'title': p.title,
        'code': p.code,
        'file_url': p.pdf_file.url if p.pdf_file else '',
        'download_count': p.download_count
    } for p in pdfs]
    return JsonResponse({'status': 'success', 'data': data})


@csrf_exempt
@require_http_methods(["POST"])
def verify_pdf_code(request):
    """تایید کد PDF"""
    try:
        body = json.loads(request.body)
        code = body.get('code', '')
        material_id = body.get('material_id')

        pdf = MaterialPDF.objects.filter(code=code, material_id=material_id).first()
        if pdf:
            return JsonResponse({
                'status': 'success',
                'valid': True,
                'id': pdf.id,
                'title': pdf.title,
                'file_url': pdf.pdf_file.url if pdf.pdf_file else ''
            })
        return JsonResponse({'status': 'error', 'valid': False, 'message': 'کد معتبر نیست'})
    except:
        return JsonResponse({'status': 'error', 'valid': False, 'message': 'خطا'})


def get_templates_by_installation(request, installation_id):
    """مرحله 4: طرح‌های آماده یک نصبیات"""
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

        # محاسبه مساحت به متر مربع
        area = length * width

        # گرفتن قیمت نصبیات (قیمت پایه برای هر متر مربع)
        installation_price = Decimal('0')
        if body.get('installation_id'):
            installation = Installation.objects.filter(id=body.get('installation_id')).first()
            if installation:
                installation_price = Decimal(str(installation.price))

        # گرفتن ضریب جنس
        material_multiplier = Decimal('1.0')
        if body.get('material_id'):
            material = InstallationMaterial.objects.filter(id=body.get('material_id')).first()
            if material:
                material_multiplier = Decimal(str(material.price_multiplier))

        # فرمول محاسبه قیمت نهایی:
        # قیمت نهایی = (قیمت نصبیات × ضریب جنس) × مساحت (متر مربع)
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
        return JsonResponse({
            'status': 'error',
            'message': str(e)
        })


# ==================== ثبت سفارش قدیمی (submit_order) ====================

@csrf_exempt
@require_http_methods(["POST"])
def submit_order(request):
    """مرحله نهایی: ثبت سفارش (نسخه قدیمی)"""
    try:
        body = json.loads(request.body)

        order = OrderMaterial.objects.create(
            user=request.user if request.user.is_authenticated else None,
            installation_id=body.get('installation_id'),
            material_id=body.get('material_id'),
            pdf_document_id=body.get('pdf_id'),
            ready_template_id=body.get('template_id'),
            design_type=body.get('design_type', 'custom'),
            length=body.get('length', 0),
            width=body.get('width', 0),
            notes=body.get('notes', '')
        )

        # ذخیره عکس پلن اگه باشه
        if body.get('plan_image'):
            format, imgstr = body.get('plan_image').split(';base64,')
            ext = format.split('/')[-1]
            order.plan_image.save(f"plan_{order.id}.{ext}", ContentFile(base64.b64decode(imgstr)), save=True)

        return JsonResponse({
            'status': 'success',
            'message': 'سفارش ثبت شد',
            'order_id': str(order.id)
        })
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)})


# ==================== ثبت سفارش جدید با ادغام در سیستم اصلی Order ====================

@csrf_exempt
@require_http_methods(["POST"])
def create_pro_order(request):
    """ایجاد سفارش نصبیات و ادغام با سیستم اصلی Order"""
    try:
        body = json.loads(request.body)

        # ==================== محاسبه مساحت و قیمت ====================
        length = Decimal(str(body.get('length', 0)))
        width = Decimal(str(body.get('width', 0)))
        area = length * width  # مساحت به متر مربع

        # گرفتن نصبیات و قیمت آن (قیمت هر متر مربع)
        installation_price = Decimal('0')
        installation_title = "نصبیات"
        if body.get('installation_id'):
            installation = Installation.objects.filter(id=body.get('installation_id')).first()
            if installation:
                installation_price = Decimal(str(installation.price))
                installation_title = installation.title

        # گرفتن جنس و ضریب آن
        material_multiplier = Decimal('1.0')
        material_title = ""
        if body.get('material_id'):
            material = InstallationMaterial.objects.filter(id=body.get('material_id')).first()
            if material:
                material_multiplier = Decimal(str(material.price_multiplier))
                material_title = material.title

        # ==================== فرمول محاسبه قیمت نهایی ====================
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
        product_title = f"{installation_title} - {material_title}".strip()
        if not product_title or product_title == "-":
            product_title = "سفارش چاپی"

        dimensions_text = f"ابعاد: {length} × {width} متر | مساحت: {area:,.2f} متر مربع"

        order_item = OrderItem.objects.create(
            order=order,
            product=None,
            product_title=product_title,
            product_code=f"PRINT-{timezone.now().strftime('%Y%m%d')}-{order.order_number}",
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
        if body.get('plan_image'):
            format, imgstr = body.get('plan_image').split(';base64,')
            ext = format.split('/')[-1]
            pro_order_material.plan_image.save(
                f"plan_{pro_order_material.id}.{ext}",
                ContentFile(base64.b64decode(imgstr)),
                save=True
            )

        # اتصال OrderMaterial به Order
        order.printing = pro_order_material
        order.save(update_fields=['printing'])

        # ==================== ثبت تاریخچه وضعیت ====================
        OrderStatusHistory.objects.create(
            order=order,
            status=OrderStatus.PENDING.value,
            note=f"سفارش چاپی: {product_title} | {dimensions_text} | مبلغ: {total_price:,.0f} تومان"
        )

        return JsonResponse({
            'status': 'success',
            'message': 'سفارش با موفقیت ایجاد شد',
            'order_id': str(order.id),
            'order_number': order.order_number,
            'total_price': f"{total_price:,.0f}",
            'redirect_url': f'/order/checkout/{str(order.id)}/'
        })

    except Exception as e:
        import traceback
        traceback.print_exc()
        return JsonResponse({
            'status': 'error',
            'message': str(e)
        })

