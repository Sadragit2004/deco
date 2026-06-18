# models.py - نسخه نهایی با تمام فیلدهای nullable

import math
from django.db import models
from django.conf import settings
from django.utils.translation import gettext_lazy as _
import utils


class BaseModel(models.Model):
    """مدل پایه برای تمام مدل‌ها"""
    title = models.CharField(max_length=255, null=True, blank=True, verbose_name=_("عنوان"))
    slug = models.SlugField(max_length=255, unique=True, allow_unicode=True, null=True, blank=True, verbose_name=_("اسلاگ"))
    image = models.ImageField(
        upload_to=utils.FileUpload('uploads/images', 'img').upload_to,
        null=True, blank=True, verbose_name=_("عکس شاخص/تصویر")
    )
    status = models.BooleanField(default=True, null=True, blank=True, verbose_name=_("وضعیت/فعال"))
    sort_order = models.IntegerField(default=0, null=True, blank=True, verbose_name=_("ترتیب نمایش"))
    created_at = models.DateTimeField(auto_now_add=True, null=True, blank=True, verbose_name=_("تاریخ ایجاد"))
    updated_at = models.DateTimeField(auto_now=True, null=True, blank=True, verbose_name=_("تاریخ ویرایش"))
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="%(class)s_created", verbose_name=_("ایجاد کننده")
    )
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="%(class)s_updated", verbose_name=_("ویرایش کننده")
    )

    class Meta:
        abstract = True


class SalesUnit(BaseModel):
    """
    واحد فروش محصول (متر مربع، عدد، رول، شاخه، کیلوگرم، بسته، کارتن و ...)
    """
    name = models.CharField(max_length=100, null=True, blank=True, verbose_name=_("نام واحد"))
    name_en = models.CharField(max_length=50, blank=True, null=True, verbose_name=_("نام انگلیسی"))
    symbol = models.CharField(max_length=20, blank=True, null=True, verbose_name=_("نماد (مثل: m², عدد, رول)"))

    class Meta:
        verbose_name = _("واحد فروش")
        verbose_name_plural = _("واحدهای فروش")
        ordering = ['sort_order']

    def __str__(self):
        return self.name or str(self.id)


class PackageUnit(BaseModel):
    """
    واحد بسته‌بندی (کارتن، بسته، پالت، رول، شاخه و ...)
    """
    name = models.CharField(max_length=100, null=True, blank=True, verbose_name=_("نام واحد بسته‌بندی"))
    name_en = models.CharField(max_length=50, blank=True, null=True, verbose_name=_("نام انگلیسی"))
    symbol = models.CharField(max_length=20, blank=True, null=True, verbose_name=_("نماد"))
    icon = models.CharField(max_length=50, default='fa-box', blank=True, null=True, verbose_name=_("آیکون FontAwesome"))

    class Meta:
        verbose_name = _("واحد بسته‌بندی")
        verbose_name_plural = _("واحدهای بسته‌بندی")
        ordering = ['sort_order']

    def __str__(self):
        return self.name or str(self.id)


class Brand(BaseModel):
    description = models.TextField(null=True, blank=True, verbose_name=_("توضیحات برند"))
    isCatalog = models.BooleanField(default=True,verbose_name='ایا کاتالوگ هست ؟')

    class Meta:
        verbose_name = _("برند")
        verbose_name_plural = _("برندها")

    def __str__(self):
        return self.title or str(self.id)


class Category(BaseModel):
    parent = models.ForeignKey('self', on_delete=models.SET_NULL, null=True, blank=True, related_name='children', verbose_name=_("دسته بندی والد"))
    brands = models.ManyToManyField(Brand, blank=True, related_name="categories", verbose_name=_("برندهای این دسته"))

    class Meta:
        verbose_name = _("دسته بندی")
        verbose_name_plural = _("دسته بندی ها")

    def __str__(self):
        return self.title or str(self.id)


class Catalog(BaseModel):
    brand = models.ForeignKey(Brand, on_delete=models.SET_NULL, null=True, blank=True, related_name="catalogs", verbose_name=_("برند کاتالوگ"))
    categories = models.ManyToManyField(Category, blank=True, related_name="catalogs", verbose_name=_("دسته بندی های کاتالوگ"))
    files = models.FileField(
        upload_to=utils.FileUpload('uploads/catalogs', 'pdf').upload_to,
        null=True, blank=True, verbose_name=_("فایل کاتالوگ (PDF)")
    )

    class Meta:
        verbose_name = _("کاتالوگ")
        verbose_name_plural = _("کاتالوگ ها")

    def __str__(self):
        return self.title or str(self.id)


class Product(BaseModel):
    brand = models.ForeignKey(Brand, on_delete=models.SET_NULL, null=True, blank=True, related_name="products", verbose_name=_("برند محصول"))
    categories = models.ManyToManyField(Category, blank=True, related_name="products", verbose_name=_("دسته بندی ها"))
    catalog = models.ForeignKey(Catalog, on_delete=models.SET_NULL, null=True, blank=True, related_name="products", verbose_name=_("کاتالوگ مرتبط"))

    # قیمت و موجودی
    price = models.DecimalField(max_digits=15, decimal_places=0, null=True, blank=True, verbose_name=_("قیمت (تومان)"))
    stock = models.DecimalField(max_digits=15, decimal_places=2, default=0, null=True, blank=True, verbose_name=_("موجودی (بر حسب واحد فروش)"))

    # واحد فروش (پویا)
    sales_unit = models.ForeignKey(
        SalesUnit,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="products",
        verbose_name=_("واحد فروش اصلی")
    )

    # توضیحات
    description = models.TextField(null=True, blank=True, verbose_name=_("توضیحات کامل"))
    code = models.CharField(max_length=100, blank=True, null=True, verbose_name=_("کد محصول"))
    product_pdf = models.FileField(
        upload_to=utils.FileUpload('uploads/products/pdfs', 'product_pdf').upload_to,
        null=True, blank=True, verbose_name=_("فایل PDF محصول")
    )

    # ========== سیستم بسته‌بندی پویا ==========
    use_packaging = models.BooleanField(
        default=False,
        null=True, blank=True,
        verbose_name=_("فعال کردن فروش بسته‌بندی شده")
    )
    package_unit = models.ForeignKey(
        PackageUnit,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="products",
        verbose_name=_("واحد بسته‌بندی")
    )
    package_size = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True, default=1,
        verbose_name=_("اندازه هر بسته (بر حسب واحد فروش)")
    )
    min_order = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True, default=1,
        verbose_name=_("حداقل سفارش (بر حسب واحد فروش)")
    )
    step = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True, default=1,
        verbose_name=_("گام افزایش (بر حسب واحد فروش)")
    )

    class Meta:
        verbose_name = _("محصول")
        verbose_name_plural = _("محصولات")

    def __str__(self):
        return self.title or str(self.id)

    def get_sales_unit_symbol(self):
        return self.sales_unit.symbol if self.sales_unit and self.sales_unit.symbol else "واحد"

    def get_sales_unit_name(self):
        return self.sales_unit.name if self.sales_unit and self.sales_unit.name else "واحد"

    def get_package_unit_symbol(self):
        return self.package_unit.symbol if self.package_unit and self.package_unit.symbol else "بسته"

    def get_package_unit_name(self):
        return self.package_unit.name if self.package_unit and self.package_unit.name else "بسته"

    def calculate_packages(self, quantity):
        """محاسبه تعداد بسته بر اساس مقدار درخواستی"""
        if not self.use_packaging or not self.package_size or self.package_size <= 0:
            return 0
        try:
            return math.ceil(float(quantity) / float(self.package_size))
        except (TypeError, ValueError):
            return 0

    def calculate_quantity_from_packages(self, packages):
        """محاسبه مقدار واقعی از تعداد بسته"""
        if not self.use_packaging or not self.package_size:
            return packages
        try:
            return float(packages) * float(self.package_size)
        except (TypeError, ValueError):
            return 0

    def get_valid_quantity(self, quantity):
        """دریافت مقدار معتبر (گرد شده به گام و حداقل)"""
        try:
            qty = float(quantity)
        except (TypeError, ValueError):
            qty = 1

        min_qty = float(self.min_order) if self.min_order else 1
        step_qty = float(self.step) if self.step else 1

        if qty < min_qty:
            qty = min_qty

        # گرد کردن به گام
        if step_qty > 0:
            qty = math.ceil(qty / step_qty) * step_qty

        return round(qty, 2)


    def get_ui_discount_data(self, quantity=1, cart_amount=0):

        price = float(self.price) if self.price else 0
        total_original = price * quantity

        # دریافت بهترین تخفیف
        best_discount, discount_amount = self.get_best_discount(quantity, cart_amount)

        # محاسبه قیمت نهایی
        final_price = total_original - discount_amount if discount_amount > 0 else total_original

        # اطلاعات پایه
        data = {
            'has_discount': discount_amount > 0,
            'original_price': total_original,
            'original_price_display': f"{int(total_original):,}",
            'final_price': final_price,
            'final_price_display': f"{int(final_price):,}",
            'discount_amount': discount_amount,
            'discount_amount_display': f"{int(discount_amount):,}",
            'saved_percent': 0,
            'badge_text': None,
            'badge_color': 'gray',
            'price_class': '',
            'show_badge': False,
            'discount_type': None,
            'discount_title': None,
        }

        # اگر تخفیف داریم، اطلاعات کامل رو پر کن
        if discount_amount > 0 and best_discount:
            # محاسبه درصد تخفیف
            if total_original > 0:
                saved_percent = int((discount_amount / total_original) * 100)
                data['saved_percent'] = saved_percent

            # تنظیم متن و رنگ badge بر اساس نوع تخفیف
            if best_discount.discount_type == 'percent':
                data['badge_text'] = f"{int(best_discount.amount)}٪ تخفیف"
                data['badge_color'] = 'red'
                data['badge_class'] = 'bg-red-500 text-white px-2 py-1 rounded text-xs font-bold'
            else:
                data['badge_text'] = f"{int(best_discount.amount):,} تومان تخفیف"
                data['badge_color'] = 'orange'
                data['badge_class'] = 'bg-orange-500 text-white px-2 py-1 rounded text-xs font-bold'

            data['show_badge'] = True
            data['discount_type'] = best_discount.discount_type
            data['discount_title'] = best_discount.title
            data['price_class'] = 'line-through text-gray-400 text-sm'

            # اگر تخفیف بیشتر از 30% بود، یه کلاس ویژه برای برجسته‌سازی
            if data['saved_percent'] > 30:
                data['badge_class'] = 'bg-red-600 text-white px-2 py-1 rounded text-xs font-bold animate-pulse'
                data['price_class'] = 'line-through text-gray-400 text-sm'

        return data


    def get_order_summary(self, requested_quantity):
        """دریافت خلاصه کامل سفارش"""
        try:
            requested = float(requested_quantity)
        except (TypeError, ValueError):
            requested = 1

        min_qty = float(self.min_order) if self.min_order else 1

        if requested < min_qty:
            requested = min_qty

        # گرد کردن به گام
        step_qty = float(self.step) if self.step else 1
        if step_qty > 0 and step_qty != 1:
            requested = math.ceil(requested / step_qty) * step_qty

        # بررسی محدودیت موجودی
        stock_val = float(self.stock) if self.stock else 0
        if stock_val > 0 and requested > stock_val:
            requested = stock_val

        price_val = float(self.price) if self.price else 0

        if self.use_packaging and self.package_size:
            packages = self.calculate_packages(requested)
            actual_quantity = self.calculate_quantity_from_packages(packages)

            # دوباره محدودیت موجودی
            if stock_val > 0 and actual_quantity > stock_val:
                actual_quantity = stock_val
                packages = self.calculate_packages(actual_quantity)

            total_price = price_val * actual_quantity

            return {
                'requested_quantity': round(requested, 2),
                'actual_quantity': round(actual_quantity, 2),
                'packages': packages,
                'package_size': float(self.package_size) if self.package_size else 0,
                'package_unit_symbol': self.get_package_unit_symbol(),
                'package_unit_name': self.get_package_unit_name(),
                'sales_unit_symbol': self.get_sales_unit_symbol(),
                'sales_unit_name': self.get_sales_unit_name(),
                'total_price': total_price,
                'total_price_display': f"{int(total_price):,}" if total_price > 0 else "۰",
                'quantity_display': f"{actual_quantity:,.2f}",
                'is_packaging': True
            }
        else:
            actual_quantity = requested
            total_price = price_val * actual_quantity

            return {
                'requested_quantity': round(requested, 2),
                'actual_quantity': round(actual_quantity, 2),
                'packages': 0,
                'package_size': 0,
                'package_unit_symbol': '',
                'package_unit_name': '',
                'sales_unit_symbol': self.get_sales_unit_symbol(),
                'sales_unit_name': self.get_sales_unit_name(),
                'total_price': total_price,
                'total_price_display': f"{int(total_price):,}" if total_price > 0 else "۰",
                'quantity_display': f"{actual_quantity:,.2f}",
                'is_packaging': False
            }

    def get_discounts(self, quantity=1, cart_amount=0):
            """دریافت تمام تخفیف‌های معتبر برای این محصول"""
            from apps.discount.models import Discount, DiscountScope

            # فقط تخفیف‌های فعال و معتبر
            all_discounts = Discount.objects.filter(is_active=True)
            valid_discounts = []

            for discount in all_discounts:
                # بررسی اعتبار زمانی
                if not discount.is_valid_now():
                    continue

                # بررسی اعمال روی این محصول
                if not discount.applies_to_product(self):
                    continue

                # بررسی حداقل تعداد
                if discount.min_quantity and quantity < discount.min_quantity:
                    continue

                # بررسی حداقل مبلغ سبد
                if discount.min_cart_amount and cart_amount < discount.min_cart_amount:
                    continue

                valid_discounts.append(discount)

            # مرتب‌سازی بر اساس اولویت (بیشترین اولویت اول)
            valid_discounts.sort(key=lambda x: x.priority, reverse=True)
            return valid_discounts

    def get_best_discount(self, quantity=1, cart_amount=0):
        """بهترین تخفیف موجود را برمی‌گرداند (بیشترین مبلغ تخفیف)"""
        discounts = self.get_discounts(quantity, cart_amount)
        if not discounts:
            return None, 0

        price = float(self.price) if self.price else 0
        best_discount = None
        best_amount = 0

        for discount in discounts:
            amount = discount.calculate_discount(price, quantity, cart_amount)
            if amount > best_amount:
                best_amount = amount
                best_discount = discount

        return best_discount, best_amount

    def get_final_price_info(self, quantity=1, cart_amount=0):
        """
        دریافت اطلاعات کامل قیمت نهایی بعد از تخفیف
        برگرداندن دیکشنری شامل:
        - original_price: قیمت اصلی کل
        - discount_amount: مبلغ تخفیف
        - final_price: قیمت نهایی کل
        - has_discount: آیا تخفیف دارد
        - discount_title: عنوان تخفیف
        - discount_type: نوع تخفیف (percent/fixed)
        - discount_percent: درصد تخفیف (اگر از نوع درصدی باشد)
        """
        price = float(self.price) if self.price else 0
        total_original = price * quantity

        best_discount, discount_amount = self.get_best_discount(quantity, cart_amount)

        if best_discount and discount_amount > 0:
            final_price = total_original - discount_amount

            # محاسبه درصد تخفیف
            discount_percent = 0
            if best_discount.discount_type == 'percent' and total_original > 0:
                discount_percent = int((discount_amount / total_original) * 100)

            return {
                'original_price': total_original,
                'original_price_display': f"{int(total_original):,}",
                'discount_amount': discount_amount,
                'discount_amount_display': f"{int(discount_amount):,}",
                'final_price': final_price,
                'final_price_display': f"{int(final_price):,}",
                'has_discount': True,
                'discount_title': best_discount.title,
                'discount_type': best_discount.discount_type,
                'discount_percent': discount_percent,
            }

        return {
            'original_price': total_original,
            'original_price_display': f"{int(total_original):,}",
            'discount_amount': 0,
            'discount_amount_display': "۰",
            'final_price': total_original,
            'final_price_display': f"{int(total_original):,}",
            'has_discount': False,
            'discount_title': None,
            'discount_type': None,
            'discount_percent': 0,
        }

    def get_final_price(self, quantity=1, cart_amount=0):
        """قیمت نهایی هر واحد محصول (بعد از تخفیف)"""
        info = self.get_final_price_info(quantity, cart_amount)
        if quantity > 0:
            return info['final_price'] / quantity
        return float(self.price) if self.price else 0

    def get_discount_percent(self, quantity=1, cart_amount=0):
        """درصد تخفیف محصول"""
        info = self.get_final_price_info(quantity, cart_amount)
        return info['discount_percent']

    def has_discount(self, quantity=1, cart_amount=0):
        """آیا محصول تخفیف دارد"""
        info = self.get_final_price_info(quantity, cart_amount)
        return info['has_discount']


class ProductGallery(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, null=True, blank=True, related_name="gallery", verbose_name=_("محصول"))
    image = models.ImageField(
        upload_to=utils.FileUpload('uploads/products/gallery', 'gallery').upload_to,
        null=True, blank=True, verbose_name=_("تصویر")
    )
    alt_text = models.CharField(max_length=255, blank=True, null=True, verbose_name=_("متن جایگزین"))
    sort_order = models.IntegerField(default=0, null=True, blank=True, verbose_name=_("ترتیب"))

    class Meta:
        ordering = ['sort_order']
        verbose_name = _("گالری محصول")
        verbose_name_plural = _("گالری محصولات")

    def __str__(self):
        return f"{self.product.title if self.product else 'بدون محصول'} - {self.sort_order}"


class Attribute(models.Model):
    name = models.CharField(max_length=255, null=True, blank=True, verbose_name=_("نام ویژگی"))
    code = models.SlugField(max_length=255, unique=True, null=True, blank=True, verbose_name=_("کد ویژگی"))
    icon = models.CharField(max_length=50, blank=True, null=True, verbose_name=_("آیکون FontAwesome"))

    class Meta:
        verbose_name = _("ویژگی")
        verbose_name_plural = _("ویژگی‌ها")

    def __str__(self):
        return self.name or str(self.id)

    def save(self, *args, **kwargs):
        if not self.code and self.name:
            import re
            self.code = re.sub(r'[\s\u200c]+', '_', self.name.strip())
        super().save(*args, **kwargs)


class ProductAttributeValue(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, null=True, blank=True, related_name="attributes", verbose_name=_("محصول"))
    attribute = models.ForeignKey(Attribute, on_delete=models.CASCADE, null=True, blank=True, related_name="values", verbose_name=_("ویژگی"))
    value = models.CharField(max_length=255, null=True, blank=True, verbose_name=_("مقدار ویژگی"))

    class Meta:
        verbose_name = _("مقدار ویژگی محصول")
        verbose_name_plural = _("مقادیر ویژگی محصولات")
        unique_together = ('product', 'attribute')

    def __str__(self):
        return f"{self.product} - {self.attribute}: {self.value}"