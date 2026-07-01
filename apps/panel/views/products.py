# apps/product/views.py

import os
import re
import json
import base64
import random
import string
from decimal import Decimal
from datetime import datetime
from django.db import models
from django.db.models import Q, Sum
from django.core.paginator import Paginator
from django.shortcuts import get_object_or_404
from django.http import JsonResponse
from django.views import View
from django.utils import timezone
from django.utils.text import slugify
from django.core.files.base import ContentFile
from django.contrib.admin.views.decorators import staff_member_required
from django.shortcuts import render

from apps.product.models import (
    Product, Category, Brand, Catalog, SalesUnit, PackageUnit,
    Attribute, ProductAttributeValue
)
from apps.discount.models import Discount, DiscountScope, DiscountType


def generate_random_slug(length=10):
    chars = string.ascii_lowercase + string.digits
    return ''.join(random.choices(chars, k=length))


def generate_unique_slug(model_class, base_slug=None):
    if base_slug:
        base_slug = re.sub(r'[^a-zA-Z0-9]', '', base_slug.lower())
        if base_slug and len(base_slug) >= 4:
            slug_candidate = base_slug[:20]
            if not model_class.objects.filter(slug=slug_candidate).exists():
                return slug_candidate

    while True:
        random_slug = generate_random_slug(10)
        if not model_class.objects.filter(slug=random_slug).exists():
            return random_slug


def save_base64_image_to_model(instance, base64_string, field_name='image'):
    """ذخیره تصویر از base64 به هر مدلی که فیلد image داشته باشد"""
    try:
        if not base64_string:
            return False

        if ';base64,' in base64_string:
            format, imgstr = base64_string.split(';base64,')
            ext = format.split('/')[-1]
        else:
            imgstr = base64_string
            ext = 'png'

        image_data = base64.b64decode(imgstr)
        filename = f"{instance.__class__.__name__.lower()}_{instance.id}_{int(timezone.now().timestamp())}.{ext}"

        old_file = getattr(instance, field_name)
        if old_file and old_file.name:
            try:
                old_file.delete(save=False)
            except:
                pass

        getattr(instance, field_name).save(filename, ContentFile(image_data), save=False)
        instance.save()
        return True
    except Exception as e:
        print(f"Error saving image: {e}")
        return False


def generate_random_name_en(length=8):
    """تولید نام انگلیسی تصادفی"""
    chars = string.ascii_lowercase
    return ''.join(random.choices(chars, k=length))


# ==================== صفحه پنل ====================
@staff_member_required
def product_admin_index(request):
    return render(request, 'panel_app/dashboard/products.html')


# ==================== API محصولات ====================
class ProductAPIView(View):
    def get(self, request, product_id=None):
        if product_id:
            return self.get_product_detail(product_id)
        return self.get_product_list(request)

    def get_product_list(self, request):
        queryset = Product.objects.all()

        search = request.GET.get('search', '')
        if search:
            queryset = queryset.filter(
                Q(title__icontains=search) |
                Q(code__icontains=search) |
                Q(brand__title__icontains=search)
            )

        brand_id = request.GET.get('brand_id')
        if brand_id and brand_id.isdigit():
            queryset = queryset.filter(brand_id=int(brand_id))

        category_id = request.GET.get('category_id')
        if category_id and category_id.isdigit():
            queryset = queryset.filter(categories__id=int(category_id))

        catalog_id = request.GET.get('catalog_id')
        if catalog_id and catalog_id.isdigit():
            queryset = queryset.filter(catalog_id=int(catalog_id))

        status = request.GET.get('status')
        if status in ['true', 'false']:
            queryset = queryset.filter(status=status == 'true')

        sort_by = request.GET.get('sort_by', '-created_at')
        queryset = queryset.order_by(sort_by)

        page = int(request.GET.get('page', 1))
        page_size = int(request.GET.get('page_size', 20))

        paginator = Paginator(queryset, page_size)
        paginated = paginator.get_page(page)

        return JsonResponse({
            'success': True,
            'data': [self.serialize_product(p) for p in paginated],
            'pagination': {
                'current_page': paginated.number,
                'total_pages': paginator.num_pages,
                'total_items': paginator.count,
                'has_next': paginated.has_next(),
                'has_prev': paginated.has_previous(),
            }
        })

    def get_product_detail(self, product_id):
        try:
            product = Product.objects.get(id=product_id)
            return JsonResponse({
                'success': True,
                'data': self.serialize_product(product, detailed=True)
            })
        except Product.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'محصول یافت نشد'}, status=404)

    def serialize_product(self, product, detailed=False):
        data = {
            'id': product.id,
            'title': product.title or '',
            'slug': product.slug or '',
            'code': product.code or '',
            'price': float(product.price) if product.price else 0,
            'price_display': f"{int(product.price):,}" if product.price else "۰",
            'stock': float(product.stock) if product.stock else 0,
            'status': product.status,
            'image': product.image.url if product.image else None,
            'brand_id': product.brand_id,
            'brand_title': product.brand.title if product.brand else None,
            'catalog_id': product.catalog_id,
            'catalog_title': product.catalog.title if product.catalog else None,
            'sales_unit_id': product.sales_unit_id,
            'sales_unit_symbol': product.get_sales_unit_symbol(),
            'sales_unit_name': product.get_sales_unit_name(),
            'use_packaging': product.use_packaging,
            'package_unit_id': product.package_unit_id,
            'package_unit_symbol': product.get_package_unit_symbol(),
            'package_size': float(product.package_size) if product.package_size else None,
            'min_order': float(product.min_order) if product.min_order else 1,
            'step': float(product.step) if product.step else 1,
            'description': product.description or '',
            'created_at': product.created_at.isoformat() if product.created_at else None,
        }

        if detailed:
            data['categories'] = [
                {'id': c.id, 'title': c.title} for c in product.categories.all()
            ]

        return data

    def post(self, request, product_id=None):
        if product_id:
            return self.update_product(request, product_id)
        return self.create_product(request)

    def create_product(self, request):
        try:
            data = json.loads(request.body)
        except:
            return JsonResponse({'success': False, 'error': 'داده نامعتبر'}, status=400)

        if not data.get('title'):
            return JsonResponse({'success': False, 'error': 'عنوان محصول الزامی است'}, status=400)

        slug = generate_unique_slug(Product, data.get('title'))

        sales_unit_id = None
        if data.get('sales_unit_id') and data['sales_unit_id'] not in ['', 'null', 'None', 'ندارد']:
            try:
                sales_unit_id = int(data['sales_unit_id'])
            except (ValueError, TypeError):
                pass

        package_unit_id = None
        if data.get('package_unit_id') and data['package_unit_id'] not in ['', 'null', 'None', 'ندارد']:
            try:
                package_unit_id = int(data['package_unit_id'])
            except (ValueError, TypeError):
                pass

        product = Product.objects.create(
            title=data.get('title'),
            slug=slug,
            code=data.get('code') or f"PROD-{int(timezone.now().timestamp())}",
            price=Decimal(str(data['price'])) if data.get('price') and data['price'] not in ['', 'null', 'None'] else None,
            stock=Decimal(str(data.get('stock', 0))) if data.get('stock') is not None else Decimal(0),
            brand_id=int(data['brand_id']) if data.get('brand_id') and data['brand_id'] not in ['', 'null', 'None'] else None,
            catalog_id=int(data['catalog_id']) if data.get('catalog_id') and data['catalog_id'] not in ['', 'null', 'None'] else None,
            sales_unit_id=sales_unit_id,
            status=data.get('status', True) in [True, 'true', 'True', 1, '1'],
            use_packaging=data.get('use_packaging', False) in [True, 'true', 'True', 1, '1'],
            package_unit_id=package_unit_id,
            package_size=Decimal(str(data.get('package_size', 1))) if data.get('package_size') else Decimal(1),
            min_order=Decimal(str(data.get('min_order', 1))) if data.get('min_order') else Decimal(1),
            step=Decimal(str(data.get('step', 1))) if data.get('step') else Decimal(1),
            description=data.get('description', ''),
        )

        if data.get('categories'):
            try:
                category_ids = [int(c) for c in data['categories'] if c and c not in ['', 'null', 'None']]
                if category_ids:
                    product.categories.set(category_ids)
            except (ValueError, TypeError):
                pass

        if data.get('image_base64'):
            save_base64_image_to_model(product, data['image_base64'], 'image')

        return JsonResponse({
            'success': True,
            'message': 'محصول با موفقیت ایجاد شد',
            'product_id': product.id
        })

    def update_product(self, request, product_id):
        try:
            product = Product.objects.get(id=product_id)
        except Product.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'محصول یافت نشد'}, status=404)

        try:
            data = json.loads(request.body)
        except:
            return JsonResponse({'success': False, 'error': 'داده نامعتبر'}, status=400)

        updatable_fields = [
            'title', 'slug', 'code', 'price', 'stock', 'brand_id', 'catalog_id',
            'sales_unit_id', 'status', 'use_packaging', 'package_unit_id',
            'package_size', 'min_order', 'step', 'description'
        ]

        for field in updatable_fields:
            if field in data and data[field] is not None and data[field] != '' and data[field] != 'null':
                value = data[field]

                if field in ['price', 'stock', 'package_size', 'min_order', 'step']:
                    try:
                        value = Decimal(str(value))
                    except:
                        value = Decimal(0) if field != 'price' else None

                elif field == 'status':
                    value = value in [True, 'true', 'True', 1, '1']
                elif field == 'use_packaging':
                    value = value in [True, 'true', 'True', 1, '1']

                elif field in ['brand_id', 'catalog_id', 'sales_unit_id', 'package_unit_id']:
                    if value and value not in ['', 'null', 'None', 'ندارد']:
                        try:
                            value = int(value)
                        except:
                            value = None
                    else:
                        value = None

                setattr(product, field, value)

        if not product.slug:
            product.slug = generate_unique_slug(Product, product.title)

        product.save()

        if 'categories' in data and data['categories']:
            try:
                category_ids = [int(c) for c in data['categories'] if c and c not in ['', 'null', 'None']]
                if category_ids:
                    product.categories.set(category_ids)
                else:
                    product.categories.clear()
            except (ValueError, TypeError):
                pass

        if data.get('image_base64'):
            save_base64_image_to_model(product, data['image_base64'], 'image')

        return JsonResponse({
            'success': True,
            'message': 'محصول با موفقیت بروزرسانی شد'
        })

    def delete(self, request, product_id):
        try:
            product = Product.objects.get(id=product_id)
            product.delete()
            return JsonResponse({'success': True, 'message': 'محصول با موفقیت حذف شد'})
        except Product.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'محصول یافت نشد'}, status=404)


# ==================== API برندها ====================
class BrandAPIView(View):
    def get(self, request, brand_id=None):
        if brand_id:
            return self.get_brand_detail(brand_id)
        return self.get_brand_list(request)

    def get_brand_list(self, request):
        queryset = Brand.objects.all()
        search = request.GET.get('search', '')
        if search:
            queryset = queryset.filter(title__icontains=search)

        page_size = int(request.GET.get('page_size', 100))
        page = int(request.GET.get('page', 1))

        paginator = Paginator(queryset, page_size)
        paginated = paginator.get_page(page)

        return JsonResponse({
            'success': True,
            'data': [
                {
                    'id': b.id,
                    'title': b.title or str(b.id),
                    'slug': b.slug,
                    'status': b.status,
                    'is_catalog': b.isCatalog,
                    'description': b.description or '',
                    'image': b.image.url if b.image else None,
                }
                for b in paginated
            ],
            'pagination': {
                'current_page': paginated.number,
                'total_pages': paginator.num_pages,
                'total_items': paginator.count,
            }
        })

    def get_brand_detail(self, brand_id):
        try:
            brand = Brand.objects.get(id=brand_id)
            return JsonResponse({
                'success': True,
                'data': {
                    'id': brand.id,
                    'title': brand.title,
                    'slug': brand.slug,
                    'status': brand.status,
                    'is_catalog': brand.isCatalog,
                    'description': brand.description or '',
                    'image': brand.image.url if brand.image else None,
                }
            })
        except Brand.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'برند یافت نشد'}, status=404)

    def post(self, request, brand_id=None):
        if brand_id:
            return self.update_brand(request, brand_id)
        return self.create_brand(request)

    def create_brand(self, request):
        try:
            data = json.loads(request.body)
        except:
            data = request.POST.dict()

        title = data.get('title')
        if not title:
            return JsonResponse({'success': False, 'error': 'عنوان برند الزامی است'}, status=400)

        slug = generate_unique_slug(Brand, title)

        brand = Brand.objects.create(
            title=title,
            slug=slug,
            isCatalog=data.get('is_catalog', True) in [True, 'true', 'True', 1, '1'],
            status=True,
            description=data.get('description', '')
        )

        if data.get('image_base64'):
            save_base64_image_to_model(brand, data['image_base64'], 'image')

        return JsonResponse({'success': True, 'message': 'برند با موفقیت ایجاد شد', 'id': brand.id})

    def update_brand(self, request, brand_id):
        try:
            brand = Brand.objects.get(id=brand_id)
        except Brand.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'برند یافت نشد'}, status=404)

        try:
            data = json.loads(request.body)
        except:
            data = request.POST.dict()

        if 'title' in data:
            brand.title = data['title']
            brand.slug = generate_unique_slug(Brand, data['title'])
        if 'is_catalog' in data:
            brand.isCatalog = data['is_catalog'] in [True, 'true', 'True', 1, '1']
        if 'status' in data:
            brand.status = data['status'] in [True, 'true', 'True', 1, '1']
        if 'description' in data:
            brand.description = data['description']

        if data.get('image_base64'):
            save_base64_image_to_model(brand, data['image_base64'], 'image')

        brand.save()
        return JsonResponse({'success': True, 'message': 'برند با موفقیت بروزرسانی شد'})

    def delete(self, request, brand_id):
        try:
            brand = Brand.objects.get(id=brand_id)
            brand.delete()
            return JsonResponse({'success': True, 'message': 'برند با موفقیت حذف شد'})
        except Brand.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'برند یافت نشد'}, status=404)


# ==================== API دسته‌بندی ====================
class CategoryAPIView(View):
    def get(self, request, category_id=None):
        if category_id:
            return self.get_category_detail(category_id)
        return self.get_category_list(request)

    def get_category_list(self, request):
        queryset = Category.objects.all()
        search = request.GET.get('search', '')
        if search:
            queryset = queryset.filter(title__icontains=search)

        page_size = int(request.GET.get('page_size', 100))
        page = int(request.GET.get('page', 1))

        paginator = Paginator(queryset, page_size)
        paginated = paginator.get_page(page)

        return JsonResponse({
            'success': True,
            'data': [
                {
                    'id': c.id,
                    'title': c.title or str(c.id),
                    'slug': c.slug,
                    'parent_id': c.parent_id,
                    'parent_title': c.parent.title if c.parent else None,
                    'status': c.status,
                    'brands': [{'id': b.id, 'title': b.title} for b in c.brands.all()],
                    'image': c.image.url if c.image else None,
                }
                for c in paginated
            ],
            'pagination': {
                'current_page': paginated.number,
                'total_pages': paginator.num_pages,
                'total_items': paginator.count,
            }
        })

    def get_category_detail(self, category_id):
        try:
            category = Category.objects.get(id=category_id)
            return JsonResponse({
                'success': True,
                'data': {
                    'id': category.id,
                    'title': category.title,
                    'slug': category.slug,
                    'parent_id': category.parent_id,
                    'status': category.status,
                    'brands': list(category.brands.values_list('id', flat=True)),
                    'image': category.image.url if category.image else None,
                }
            })
        except Category.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'دسته‌بندی یافت نشد'}, status=404)

    def post(self, request, category_id=None):
        if category_id:
            if request.path.endswith('/update-brands/'):
                return self.update_brands(request, category_id)
            return self.update_category(request, category_id)
        return self.create_category(request)

    def create_category(self, request):
        try:
            data = json.loads(request.body)
        except:
            data = request.POST.dict()

        title = data.get('title')
        if not title:
            return JsonResponse({'success': False, 'error': 'عنوان دسته‌بندی الزامی است'}, status=400)

        slug = generate_unique_slug(Category, title)

        category = Category.objects.create(
            title=title,
            slug=slug,
            parent_id=int(data['parent_id']) if data.get('parent_id') and data['parent_id'] not in ['', 'null'] else None,
            status=True
        )

        brands = data.get('brands', [])
        if brands:
            category.brands.set(brands)

        if data.get('image_base64'):
            save_base64_image_to_model(category, data['image_base64'], 'image')

        return JsonResponse({'success': True, 'message': 'دسته‌بندی با موفقیت ایجاد شد', 'id': category.id})

    def update_category(self, request, category_id):
        try:
            category = Category.objects.get(id=category_id)
        except Category.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'دسته‌بندی یافت نشد'}, status=404)

        try:
            data = json.loads(request.body)
        except:
            data = request.POST.dict()

        if 'title' in data:
            category.title = data['title']
            category.slug = generate_unique_slug(Category, data['title'])
        if 'parent_id' in data:
            category.parent_id = int(data['parent_id']) if data['parent_id'] and data['parent_id'] not in ['', 'null'] else None
        if 'status' in data:
            category.status = data['status'] in [True, 'true', 'True', 1, '1']
        if 'brands' in data:
            category.brands.set(data['brands'])

        if data.get('image_base64'):
            save_base64_image_to_model(category, data['image_base64'], 'image')

        category.save()
        return JsonResponse({'success': True, 'message': 'دسته‌بندی با موفقیت بروزرسانی شد'})

    def update_brands(self, request, category_id):
        try:
            category = Category.objects.get(id=category_id)
        except Category.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'دسته‌بندی یافت نشد'}, status=404)

        try:
            data = json.loads(request.body)
        except:
            return JsonResponse({'success': False, 'error': 'داده نامعتبر'}, status=400)

        brands = data.get('brands', [])
        if brands:
            category.brands.set(brands)
        else:
            category.brands.clear()

        return JsonResponse({'success': True, 'message': 'برندهای دسته‌بندی بروزرسانی شد'})

    def delete(self, request, category_id):
        try:
            category = Category.objects.get(id=category_id)
            category.delete()
            return JsonResponse({'success': True, 'message': 'دسته‌بندی با موفقیت حذف شد'})
        except Category.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'دسته‌بندی یافت نشد'}, status=404)


# ==================== API کاتالوگ ====================
class CatalogAPIView(View):
    def get(self, request, catalog_id=None):
        if catalog_id:
            return self.get_catalog_detail(catalog_id)
        return self.get_catalog_list(request)

    def get_catalog_list(self, request):
        queryset = Catalog.objects.all()
        search = request.GET.get('search', '')
        if search:
            queryset = queryset.filter(title__icontains=search)

        page_size = int(request.GET.get('page_size', 100))
        page = int(request.GET.get('page', 1))

        paginator = Paginator(queryset, page_size)
        paginated = paginator.get_page(page)

        return JsonResponse({
            'success': True,
            'data': [
                {
                    'id': c.id,
                    'title': c.title or str(c.id),
                    'slug': c.slug,
                    'brand_id': c.brand_id,
                    'brand_title': c.brand.title if c.brand else None,
                    'status': c.status,
                    'image': c.image.url if c.image else None,
                }
                for c in paginated
            ],
            'pagination': {
                'current_page': paginated.number,
                'total_pages': paginator.num_pages,
                'total_items': paginator.count,
            }
        })

    def get_catalog_detail(self, catalog_id):
        try:
            catalog = Catalog.objects.get(id=catalog_id)
            return JsonResponse({
                'success': True,
                'data': {
                    'id': catalog.id,
                    'title': catalog.title,
                    'slug': catalog.slug,
                    'brand_id': catalog.brand_id,
                    'status': catalog.status,
                    'image': catalog.image.url if catalog.image else None,
                }
            })
        except Catalog.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'کاتالوگ یافت نشد'}, status=404)

    def post(self, request, catalog_id=None):
        if catalog_id:
            return self.update_catalog(request, catalog_id)
        return self.create_catalog(request)

    def create_catalog(self, request):
        try:
            data = json.loads(request.body)
        except:
            data = request.POST.dict()

        title = data.get('title')
        if not title:
            return JsonResponse({'success': False, 'error': 'عنوان کاتالوگ الزامی است'}, status=400)

        slug = generate_unique_slug(Catalog, title)

        catalog = Catalog.objects.create(
            title=title,
            slug=slug,
            brand_id=int(data['brand_id']) if data.get('brand_id') and data['brand_id'] not in ['', 'null'] else None,
            status=True
        )

        if data.get('image_base64'):
            save_base64_image_to_model(catalog, data['image_base64'], 'image')

        return JsonResponse({'success': True, 'message': 'کاتالوگ با موفقیت ایجاد شد', 'id': catalog.id})

    def update_catalog(self, request, catalog_id):
        try:
            catalog = Catalog.objects.get(id=catalog_id)
        except Catalog.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'کاتالوگ یافت نشد'}, status=404)

        try:
            data = json.loads(request.body)
        except:
            data = request.POST.dict()

        if 'title' in data:
            catalog.title = data['title']
            catalog.slug = generate_unique_slug(Catalog, data['title'])
        if 'brand_id' in data:
            catalog.brand_id = int(data['brand_id']) if data['brand_id'] and data['brand_id'] not in ['', 'null'] else None
        if 'status' in data:
            catalog.status = data['status'] in [True, 'true', 'True', 1, '1']

        if data.get('image_base64'):
            save_base64_image_to_model(catalog, data['image_base64'], 'image')

        catalog.save()
        return JsonResponse({'success': True, 'message': 'کاتالوگ با موفقیت بروزرسانی شد'})

    def delete(self, request, catalog_id):
        try:
            catalog = Catalog.objects.get(id=catalog_id)
            catalog.delete()
            return JsonResponse({'success': True, 'message': 'کاتالوگ با موفقیت حذف شد'})
        except Catalog.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'کاتالوگ یافت نشد'}, status=404)


# ==================== API واحد فروش (اصلاح شده با کپی کردن) ====================
class SalesUnitAPIView(View):
    def get(self, request):
        queryset = SalesUnit.objects.all()
        return JsonResponse({
            'success': True,
            'data': [
                {
                    'id': u.id,
                    'title': u.name or str(u.id),
                    'name': u.name,
                    'name_en': u.name_en,
                    'symbol': u.symbol
                }
                for u in queryset
            ]
        })

    def post(self, request):
        try:
            data = json.loads(request.body)
        except:
            data = request.POST.dict()

        # دریافت نام واحد (اجباری)
        name = data.get('title') or data.get('name')
        if not name:
            return JsonResponse({'success': False, 'error': 'نام واحد الزامی است'}, status=400)

        # ====== تولید نام انگلیسی تصادفی ======
        name_en = generate_random_name_en(8)

        # ====== symbol = همان name کپی شود ======
        symbol = name

        # ایجاد واحد فروش
        unit = SalesUnit.objects.create(
            name=name,
            name_en=name_en,
            symbol=symbol,
            status=True
        )

        return JsonResponse({
            'success': True,
            'message': 'واحد فروش با موفقیت ایجاد شد',
            'id': unit.id,
            'data': {
                'id': unit.id,
                'name': unit.name,
                'name_en': unit.name_en,
                'symbol': unit.symbol
            }
        })


# ==================== API واحد بسته‌بندی (اصلاح شده با کپی کردن) ====================
class PackageUnitAPIView(View):
    def get(self, request):
        queryset = PackageUnit.objects.all()
        return JsonResponse({
            'success': True,
            'data': [
                {
                    'id': u.id,
                    'title': u.name or str(u.id),
                    'name': u.name,
                    'name_en': u.name_en,
                    'symbol': u.symbol,
                    'icon': u.icon
                }
                for u in queryset
            ]
        })

    def post(self, request):
        try:
            data = json.loads(request.body)
        except:
            data = request.POST.dict()

        # دریافت نام واحد (اجباری)
        name = data.get('title') or data.get('name')
        if not name:
            return JsonResponse({'success': False, 'error': 'نام واحد بسته‌بندی الزامی است'}, status=400)

        # ====== تولید نام انگلیسی تصادفی ======
        name_en = generate_random_name_en(8)

        # ====== symbol = همان name کپی شود ======
        symbol = name

        # آیکون پیش‌فرض
        icon = 'fa-box'

        # ایجاد واحد بسته‌بندی
        unit = PackageUnit.objects.create(
            name=name,
            name_en=name_en,
            symbol=symbol,
            icon=icon,
            status=True
        )

        return JsonResponse({
            'success': True,
            'message': 'واحد بسته‌بندی با موفقیت ایجاد شد',
            'id': unit.id,
            'data': {
                'id': unit.id,
                'name': unit.name,
                'name_en': unit.name_en,
                'symbol': unit.symbol,
                'icon': unit.icon
            }
        })


# ==================== API ویژگی‌ها ====================
class AttributeAPIView(View):
    def get(self, request, attr_id=None):
        if attr_id:
            return self.get_attribute_detail(attr_id)

        queryset = Attribute.objects.all()
        return JsonResponse({
            'success': True,
            'data': [
                {'id': a.id, 'name': a.name, 'code': a.code, 'icon': a.icon}
                for a in queryset
            ]
        })

    def get_attribute_detail(self, attr_id):
        try:
            attr = Attribute.objects.get(id=attr_id)
            return JsonResponse({
                'success': True,
                'data': {'id': attr.id, 'name': attr.name, 'code': attr.code, 'icon': attr.icon}
            })
        except Attribute.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'ویژگی یافت نشد'}, status=404)

    def post(self, request, attr_id=None):
        if attr_id:
            return self.update_attribute(request, attr_id)
        return self.create_attribute(request)

    def create_attribute(self, request):
        try:
            data = json.loads(request.body)
        except:
            data = request.POST.dict()

        name = data.get('name')
        if not name:
            return JsonResponse({'success': False, 'error': 'نام ویژگی الزامی است'}, status=400)

        code = generate_unique_slug(Attribute, name)

        attr = Attribute.objects.create(
            name=name,
            code=code,
            icon=data.get('icon')
        )

        return JsonResponse({'success': True, 'message': 'ویژگی با موفقیت ایجاد شد', 'id': attr.id})

    def update_attribute(self, request, attr_id):
        try:
            attr = Attribute.objects.get(id=attr_id)
        except Attribute.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'ویژگی یافت نشد'}, status=404)

        try:
            data = json.loads(request.body)
        except:
            data = request.POST.dict()

        if 'name' in data:
            attr.name = data['name']
            attr.code = generate_unique_slug(Attribute, data['name'])
        if 'icon' in data:
            attr.icon = data['icon']

        attr.save()
        return JsonResponse({'success': True, 'message': 'ویژگی با موفقیت بروزرسانی شد'})

    def delete(self, request, attr_id):
        try:
            attr = Attribute.objects.get(id=attr_id)
            attr.delete()
            return JsonResponse({'success': True, 'message': 'ویژگی با موفقیت حذف شد'})
        except Attribute.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'ویژگی یافت نشد'}, status=404)


# ==================== API تخفیف‌ها ====================
class DiscountAPIView(View):
    def get(self, request, discount_id=None):
        if discount_id:
            return self.get_discount_detail(discount_id)
        return self.get_discount_list(request)

    def get_discount_list(self, request):
        queryset = Discount.objects.all().order_by('-priority', '-created_at')
        return JsonResponse({
            'success': True,
            'data': [
                {
                    'id': d.id,
                    'title': d.title,
                    'discount_type': d.discount_type,
                    'discount_type_display': d.get_discount_type_display(),
                    'amount': float(d.amount),
                    'amount_display': f"{int(d.amount):,} تومان" if d.discount_type == 'fixed' else f"{int(d.amount)}%",
                    'scope': d.scope,
                    'scope_display': d.get_scope_display(),
                    'min_quantity': float(d.min_quantity) if d.min_quantity else 0,
                    'min_cart_amount': float(d.min_cart_amount) if d.min_cart_amount else 0,
                    'start_date': d.start_date.isoformat(),
                    'end_date': d.end_date.isoformat(),
                    'priority': d.priority,
                    'usage_limit': d.usage_limit,
                    'used_count': d.used_count,
                    'is_active': d.is_active,
                    'products': [p.id for p in d.products.all()] if d.scope == 'product' else [],
                    'brands': [b.id for b in d.brands.all()] if d.scope == 'brand' else [],
                    'categories': [c.id for c in d.categories.all()] if d.scope == 'category' else [],
                }
                for d in queryset
            ]
        })

    def get_discount_detail(self, discount_id):
        try:
            discount = Discount.objects.get(id=discount_id)
            return JsonResponse({'success': True, 'data': {'id': discount.id, 'title': discount.title}})
        except Discount.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'تخفیف یافت نشد'}, status=404)

    def post(self, request, discount_id=None):
        if discount_id:
            return self.toggle_discount(request, discount_id)
        return self.create_discount(request)

    def create_discount(self, request):
        try:
            data = json.loads(request.body)
        except:
            return JsonResponse({'success': False, 'error': 'داده نامعتبر'}, status=400)

        required = ['title', 'discount_type', 'amount', 'start_date', 'end_date']
        for field in required:
            if not data.get(field):
                return JsonResponse({'success': False, 'error': f'فیلد {field} الزامی است'}, status=400)

        slug = generate_unique_slug(Discount, data['title'])

        discount = Discount.objects.create(
            title=data['title'],
            slug=slug,
            discount_type=data['discount_type'],
            amount=Decimal(str(data['amount'])),
            scope=data.get('scope', 'global'),
            min_quantity=Decimal(str(data.get('min_quantity', 0))),
            min_cart_amount=Decimal(str(data.get('min_cart_amount', 0))) if data.get('min_cart_amount') else None,
            start_date=data['start_date'],
            end_date=data['end_date'],
            priority=int(data.get('priority', 0)),
            usage_limit=int(data.get('usage_limit', 0)) if data.get('usage_limit') else 0,
            is_active=data.get('is_active', True),
        )

        if discount.scope == 'product' and data.get('products'):
            discount.products.set(data['products'])
        elif discount.scope == 'brand' and data.get('brands'):
            discount.brands.set(data['brands'])
        elif discount.scope == 'category' and data.get('categories'):
            discount.categories.set(data['categories'])

        return JsonResponse({
            'success': True,
            'message': 'تخفیف با موفقیت ایجاد شد',
            'id': discount.id
        })

    def toggle_discount(self, request, discount_id):
        try:
            discount = Discount.objects.get(id=discount_id)
            discount.is_active = not discount.is_active
            discount.save()
            return JsonResponse({'success': True, 'is_active': discount.is_active, 'message': 'وضعیت تخفیف تغییر کرد'})
        except Discount.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'تخفیف یافت نشد'}, status=404)

    def delete(self, request, discount_id):
        try:
            discount = Discount.objects.get(id=discount_id)
            discount.delete()
            return JsonResponse({'success': True, 'message': 'تخفیف با موفقیت حذف شد'})
        except Discount.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'تخفیف یافت نشد'}, status=404)


# ==================== API آمار ====================
class StatsAPIView(View):
    def get(self, request):
        total_products = Product.objects.count()
        total_brands = Brand.objects.count()
        total_categories = Category.objects.count()
        total_catalogs = Catalog.objects.count()

        now = timezone.now()
        active_discounts = Discount.objects.filter(
            is_active=True,
            start_date__lte=now,
            end_date__gte=now
        ).count()

        total_value = Product.objects.aggregate(
            total=models.Sum(models.F('price') * models.F('stock'))
        )['total'] or 0

        return JsonResponse({
            'success': True,
            'data': {
                'total_products': total_products,
                'total_brands': total_brands,
                'total_categories': total_categories,
                'total_catalogs': total_catalogs,
                'active_discounts': active_discounts,
                'total_value': float(total_value),
            }
        })


# ==================== تولید انبوه محصولات ====================
class BulkProductCreateView(View):
    def post(self, request):
        try:
            data = json.loads(request.body)
        except:
            return JsonResponse({'success': False, 'error': 'داده نامعتبر'}, status=400)

        brand_id = data.get('brand_id')
        code_start = data.get('code_start')
        code_end = data.get('code_end')

        if not brand_id:
            return JsonResponse({'success': False, 'error': 'برند الزامی است'}, status=400)

        if not code_start or not code_end:
            return JsonResponse({'success': False, 'error': 'کد شروع و پایان الزامی است'}, status=400)

        # پردازش sales_unit_id
        sales_unit_id = None
        if data.get('sales_unit_id') and data['sales_unit_id'] not in ['', 'null', 'None', 'ندارد']:
            try:
                sales_unit_id = int(data['sales_unit_id'])
            except (ValueError, TypeError):
                pass

        # پردازش package_unit_id
        package_unit_id = None
        if data.get('package_unit_id') and data['package_unit_id'] not in ['', 'null', 'None', 'ندارد']:
            try:
                package_unit_id = int(data['package_unit_id'])
            except (ValueError, TypeError):
                pass

        start_match = re.search(r'(\D*)(\d+)(\D*)', code_start)
        end_match = re.search(r'(\d+)', code_end)

        if not start_match or not end_match:
            return JsonResponse({'success': False, 'error': 'فرمت کد نامعتبر است. مثال: PROD-001'}, status=400)

        prefix = start_match.group(1)
        start_num = int(start_match.group(2))
        suffix = start_match.group(3) or ''
        end_num = int(end_match.group(1))

        if end_num < start_num:
            start_num, end_num = end_num, start_num

        created_count = 0
        created_ids = []
        errors = []

        brand_obj = Brand.objects.filter(id=int(brand_id)).first()
        brand_name = brand_obj.title if brand_obj else ""

        for num in range(start_num, end_num + 1):
            code = f"{prefix}{num}{suffix}"

            if Product.objects.filter(code=code).exists():
                errors.append(f"کد {code} قبلاً وجود دارد - رد شد")
                continue

            product_slug = generate_unique_slug(Product)

            product_title = f"{code}"
            if brand_name:
                product_title = f"{product_title} - {brand_name}"

            try:
                price_value = data.get('base_price', 0)
                if price_value in ['', 'null', 'None', 'ندارد']:
                    price_value = 0
                price = Decimal(str(price_value)) if price_value is not None else None

                stock_value = data.get('stock', 0)
                if stock_value in ['', 'null', 'None', 'ندارد']:
                    stock_value = 0
                stock = Decimal(str(stock_value)) if stock_value is not None else Decimal(0)

                package_size = data.get('package_size', 1)
                if package_size in ['', 'null', 'None']:
                    package_size = 1
                package_size = Decimal(str(package_size))

                min_order = data.get('min_order', 1)
                if min_order in ['', 'null', 'None']:
                    min_order = 1
                min_order = Decimal(str(min_order))

                step = data.get('step', 1)
                if step in ['', 'null', 'None']:
                    step = 1
                step = Decimal(str(step))

                use_packaging = data.get('use_packaging', False)
                if isinstance(use_packaging, str):
                    use_packaging = use_packaging in ['true', 'True', '1']

                product = Product.objects.create(
                    title=product_title,
                    slug=product_slug,
                    code=code,
                    brand_id=int(brand_id),
                    catalog_id=int(data['catalog_id']) if data.get('catalog_id') and data['catalog_id'] not in ['', 'null', 'None'] else None,
                    price=price,
                    stock=stock,
                    sales_unit_id=sales_unit_id,
                    use_packaging=use_packaging,
                    package_unit_id=package_unit_id,
                    package_size=package_size,
                    min_order=min_order,
                    step=step,
                    description=data.get('description', ''),
                    status=True
                )

                if data.get('categories'):
                    try:
                        category_ids = [int(c) for c in data['categories'] if c and c not in ['', 'null', 'None']]
                        if category_ids:
                            product.categories.set(category_ids)
                    except (ValueError, TypeError):
                        pass

                created_count += 1
                created_ids.append(product.id)

            except Exception as e:
                errors.append(f"خطا در ایجاد محصول {code}: {str(e)}")

        return JsonResponse({
            'success': True,
            'message': f'{created_count} محصول با موفقیت ایجاد شد',
            'product_ids': created_ids,
            'created_count': created_count,
            'errors': errors if errors else None
        })


# ==================== تغییر قیمت دسته‌جمعی ====================
class BulkPriceUpdateView(View):
    def post(self, request):
        try:
            data = json.loads(request.body)
        except:
            return JsonResponse({'success': False, 'error': 'داده نامعتبر'}, status=400)

        scope = data.get('scope')
        scope_id = data.get('scope_id')
        operation = data.get('operation', 'increase')
        change_type = data.get('change_type', 'percent')
        amount = Decimal(str(data.get('amount', 0)))
        preview = data.get('preview', True)

        if not scope_id:
            return JsonResponse({'success': False, 'error': 'هدف را انتخاب کنید'}, status=400)

        if amount <= 0:
            return JsonResponse({'success': False, 'error': 'مقدار معتبر وارد کنید'}, status=400)

        queryset = Product.objects.filter(price__isnull=False)

        if scope == 'brand':
            queryset = queryset.filter(brand_id=int(scope_id))
        elif scope == 'catalog':
            queryset = queryset.filter(catalog_id=int(scope_id))
        elif scope == 'category':
            queryset = queryset.filter(categories__id=int(scope_id))
        elif scope == 'product':
            queryset = queryset.filter(id=int(scope_id))
        else:
            return JsonResponse({'success': False, 'error': 'محدوده نامعتبر'}, status=400)

        products = list(queryset)
        updated_products = []

        for product in products:
            old_price = float(product.price)
            new_price = old_price

            if change_type == 'percent':
                if operation == 'increase':
                    new_price = old_price * (1 + float(amount) / 100)
                else:
                    new_price = old_price * (1 - float(amount) / 100)
            else:
                if operation == 'increase':
                    new_price = old_price + float(amount)
                else:
                    new_price = old_price - float(amount)

            new_price = max(0, round(new_price))

            updated_products.append({
                'id': product.id,
                'code': product.code,
                'old_price': old_price,
                'old_price_display': f"{int(old_price):,}",
                'new_price': new_price,
                'new_price_display': f"{int(new_price):,}",
            })

            if not preview:
                product.price = Decimal(str(new_price))
                product.save()

        return JsonResponse({
            'success': True,
            'updated_count': len(updated_products),
            'updated_products': updated_products[:20],
            'message': f'قیمت {len(updated_products)} محصول با موفقیت تغییر یافت' if not preview else None,
            'preview': preview
        })