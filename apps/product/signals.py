# product/signals.py
from django.db.models.signals import post_save, post_delete, m2m_changed
from django.dispatch import receiver
from django.core.cache import cache
from .models import Brand, Product, Catalog, Category
from .utils import safe_delete_pattern, clear_cache_keys


# ========== توابع کمکی ==========

def clear_brand_caches():
    """پاک کردن کش‌های مرتبط با برند"""
    clear_cache_keys([
        'popular_brands',
        'latest_catalogs',
        'catalogs_list'
    ])
    safe_delete_pattern('brand_*')
    safe_delete_pattern('category_brands_*')
    safe_delete_pattern('brand_catalogs_*')


def clear_product_caches():
    """پاک کردن کش‌های مرتبط با محصول"""
    clear_cache_keys([
        'latest_products',
        'popular_brands',
        'latest_catalogs'
    ])
    safe_delete_pattern('product_*')
    safe_delete_pattern('bestsellers_*')
    safe_delete_pattern('product_detail_*')


def clear_category_caches():
    """پاک کردن کش‌های مرتبط با دسته‌بندی"""
    clear_cache_keys([
        'main_categories',
        'latest_catalogs',
        'latest_products',
        'catalogs_list'
    ])
    safe_delete_pattern('category_*')
    safe_delete_pattern('category_menu_*')
    safe_delete_pattern('category_brands_*')
    safe_delete_pattern('category_children_*')


def clear_catalog_caches():
    """پاک کردن کش‌های مرتبط با کاتالوگ"""
    clear_cache_keys([
        'latest_catalogs',
        'catalogs_list',
        'catalogs_timestamp'
    ])
    safe_delete_pattern('catalog_*')
    safe_delete_pattern('brand_catalogs_*')


# ========== سیگنال‌های برند ==========

@receiver(post_save, sender=Brand)
def clear_brand_cache_on_save(sender, instance, **kwargs):
    """پاک کردن کش برندها هنگام ذخیره برند"""
    clear_brand_caches()
    clear_product_caches()
    clear_category_caches()
    cache.delete(f'brand_detail_{instance.id}')


@receiver(post_delete, sender=Brand)
def clear_brand_cache_on_delete(sender, instance, **kwargs):
    """پاک کردن کش برندها هنگام حذف برند"""
    clear_brand_caches()
    clear_product_caches()
    clear_category_caches()
    cache.delete(f'brand_detail_{instance.id}')


# ========== سیگنال‌های محصول ==========

@receiver(post_save, sender=Product)
def clear_product_cache_on_save(sender, instance, **kwargs):
    """پاک کردن کش محصولات هنگام تغییر محصول"""
    clear_product_caches()
    clear_brand_caches()
    clear_category_caches()

    if instance.brand:
        cache.delete(f'brand_detail_{instance.brand.id}')


@receiver(post_delete, sender=Product)
def clear_product_cache_on_delete(sender, instance, **kwargs):
    """پاک کردن کش محصولات هنگام حذف محصول"""
    clear_product_caches()
    clear_brand_caches()
    clear_category_caches()

    if instance.brand:
        cache.delete(f'brand_detail_{instance.brand.id}')


@receiver(m2m_changed, sender=Product.categories.through)
def clear_product_cache_on_category_change(sender, instance, action, **kwargs):
    """پاک کردن کش محصولات هنگام تغییر دسته‌بندی محصول"""
    if action in ['post_add', 'post_remove', 'post_clear']:
        clear_product_caches()
        clear_brand_caches()
        clear_category_caches()

        if instance.brand:
            cache.delete(f'brand_detail_{instance.brand.id}')


# ========== سیگنال‌های کاتالوگ ==========

@receiver(post_save, sender=Catalog)
def clear_catalog_cache_on_save(sender, instance, **kwargs):
    """پاک کردن کش کاتالوگ‌ها هنگام ذخیره کاتالوگ"""
    clear_catalog_caches()
    clear_category_caches()
    clear_brand_caches()

    if instance.brand:
        cache.delete(f'brand_detail_{instance.brand.id}')
    cache.delete(f'catalog_detail_{instance.id}')


@receiver(post_delete, sender=Catalog)
def clear_catalog_cache_on_delete(sender, instance, **kwargs):
    """پاک کردن کش کاتالوگ‌ها هنگام حذف کاتالوگ"""
    clear_catalog_caches()
    clear_category_caches()
    clear_brand_caches()

    if instance.brand:
        cache.delete(f'brand_detail_{instance.brand.id}')
    cache.delete(f'catalog_detail_{instance.id}')


@receiver(m2m_changed, sender=Catalog.categories.through)
def clear_catalog_cache_on_categories_change(sender, instance, action, **kwargs):
    """پاک کردن کش کاتالوگ‌ها هنگام تغییر دسته‌بندی‌های کاتالوگ"""
    if action in ['post_add', 'post_remove', 'post_clear']:
        clear_catalog_caches()
        clear_category_caches()
        clear_brand_caches()
        cache.delete(f'catalog_detail_{instance.id}')


# ========== سیگنال‌های دسته‌بندی ==========

@receiver(post_save, sender=Category)
def clear_category_cache_on_save(sender, instance, **kwargs):
    """پاک کردن کش دسته‌بندی‌ها هنگام تغییر دسته‌بندی"""
    clear_category_caches()
    clear_product_caches()
    clear_catalog_caches()

    if instance.parent:
        cache.delete(f'category_children_{instance.parent.id}')
    if instance.slug:
        cache.delete(f'category_detail_{instance.slug}')


@receiver(post_delete, sender=Category)
def clear_category_cache_on_delete(sender, instance, **kwargs):
    """پاک کردن کش دسته‌بندی‌ها هنگام حذف دسته‌بندی"""
    clear_category_caches()
    clear_product_caches()
    clear_catalog_caches()


# ========== سیگنال‌های سفارش (برای بهترین فروش‌ها) ==========

try:
    from apps.order.models import OrderItem, Order

    @receiver(post_save, sender=OrderItem)
    def clear_bestsellers_cache_on_order(sender, instance, **kwargs):
        """پاک کردن کش پرفروش‌ها هنگام ثبت سفارش"""
        safe_delete_pattern('bestsellers_*')
        safe_delete_pattern('category_menu_*')
        safe_delete_pattern('product_*')
        cache.delete('latest_products')

    @receiver(post_delete, sender=OrderItem)
    def clear_bestsellers_cache_on_order_delete(sender, instance, **kwargs):
        """پاک کردن کش پرفروش‌ها هنگام حذف سفارش"""
        safe_delete_pattern('bestsellers_*')
        safe_delete_pattern('category_menu_*')
        cache.delete('latest_products')

    @receiver(post_save, sender=Order)
    def clear_bestsellers_cache_on_order_status(sender, instance, **kwargs):
        """پاک کردن کش پرفروش‌ها هنگام تغییر وضعیت سفارش"""
        if instance.status in ['paid', 'delivered', 'cancelled']:
            safe_delete_pattern('bestsellers_*')
            safe_delete_pattern('category_menu_*')
            cache.delete('latest_products')

except ImportError:
    pass


# ========== سیگنال‌های تخفیف ==========

try:
    from apps.discount.models import Discount

    @receiver(post_save, sender=Discount)
    def clear_discount_cache_on_save(sender, instance, **kwargs):
        """پاک کردن کش تخفیف‌ها هنگام تغییر تخفیف"""
        safe_delete_pattern('product_*')
        safe_delete_pattern('bestsellers_*')
        cache.delete('latest_products')
        safe_delete_pattern('category_menu_*')

    @receiver(post_delete, sender=Discount)
    def clear_discount_cache_on_delete(sender, instance, **kwargs):
        """پاک کردن کش تخفیف‌ها هنگام حذف تخفیف"""
        safe_delete_pattern('product_*')
        safe_delete_pattern('bestsellers_*')
        cache.delete('latest_products')
        safe_delete_pattern('category_menu_*')

except ImportError:
    pass