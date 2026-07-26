# product/signals.py
from django.db.models.signals import post_save, post_delete, m2m_changed
from django.dispatch import receiver
from django.core.cache import cache
from .models import Brand, Product, Catalog, Category
from .utils import safe_delete_pattern, clear_cache_keys


# ========== فقط کلیدهای ضروری ==========

@receiver(post_save, sender=Brand)
def clear_brand_cache_on_save(sender, instance, **kwargs):
    """پاک کردن فقط کش برند"""
    cache.delete(f'brand_detail_{instance.id}')
    cache.delete('popular_brands')
    safe_delete_pattern('brand_*')


@receiver(post_delete, sender=Brand)
def clear_brand_cache_on_delete(sender, instance, **kwargs):
    cache.delete(f'brand_detail_{instance.id}')
    cache.delete('popular_brands')
    safe_delete_pattern('brand_*')


# ========== محصول ==========

@receiver(post_save, sender=Product)
def clear_product_cache_on_save(sender, instance, **kwargs):
    """پاک کردن فقط کش محصول"""
    cache.delete(f'product_detail_{instance.id}')
    cache.delete('latest_products')
    safe_delete_pattern('product_*')

    # فقط اگه برند تغییر کرده
    if instance.brand:
        cache.delete(f'brand_detail_{instance.brand.id}')


@receiver(post_delete, sender=Product)
def clear_product_cache_on_delete(sender, instance, **kwargs):
    cache.delete(f'product_detail_{instance.id}')
    cache.delete('latest_products')
    safe_delete_pattern('product_*')

    if instance.brand:
        cache.delete(f'brand_detail_{instance.brand.id}')


@receiver(m2m_changed, sender=Product.categories.through)
def clear_product_cache_on_category_change(sender, instance, action, **kwargs):
    if action in ['post_add', 'post_remove', 'post_clear']:
        cache.delete(f'product_detail_{instance.id}')
        cache.delete('latest_products')
        safe_delete_pattern('product_*')


# ========== کاتالوگ ==========

@receiver(post_save, sender=Catalog)
def clear_catalog_cache_on_save(sender, instance, **kwargs):
    """پاک کردن فقط کش کاتالوگ"""
    cache.delete(f'catalog_detail_{instance.id}')
    cache.delete('latest_catalogs')
    safe_delete_pattern('catalog_*')
    safe_delete_pattern('brand_catalogs_*')


@receiver(post_delete, sender=Catalog)
def clear_catalog_cache_on_delete(sender, instance, **kwargs):
    cache.delete(f'catalog_detail_{instance.id}')
    cache.delete('latest_catalogs')
    safe_delete_pattern('catalog_*')
    safe_delete_pattern('brand_catalogs_*')


@receiver(m2m_changed, sender=Catalog.categories.through)
def clear_catalog_cache_on_categories_change(sender, instance, action, **kwargs):
    if action in ['post_add', 'post_remove', 'post_clear']:
        cache.delete(f'catalog_detail_{instance.id}')
        safe_delete_pattern('catalog_*')


# ========== دسته‌بندی ==========

@receiver(post_save, sender=Category)
def clear_category_cache_on_save(sender, instance, **kwargs):
    """پاک کردن فقط کش دسته‌بندی"""
    if instance.slug:
        cache.delete(f'category_detail_{instance.slug}')
    if instance.parent:
        cache.delete(f'category_children_{instance.parent.id}')

    cache.delete('main_categories')
    safe_delete_pattern('category_*')


@receiver(post_delete, sender=Category)
def clear_category_cache_on_delete(sender, instance, **kwargs):
    cache.delete('main_categories')
    safe_delete_pattern('category_*')


# ========== سفارش (برای پرفروش‌ها) ==========

try:
    from apps.order.models import OrderItem, Order

    @receiver(post_save, sender=OrderItem)
    def clear_bestsellers_cache_on_order(sender, instance, **kwargs):
        safe_delete_pattern('bestsellers_*')

    @receiver(post_save, sender=Order)
    def clear_bestsellers_cache_on_order_status(sender, instance, **kwargs):
        if instance.status in ['paid', 'delivered']:
            safe_delete_pattern('bestsellers_*')

except ImportError:
    pass


# ========== تخفیف ==========

try:
    from apps.discount.models import Discount

    @receiver(post_save, sender=Discount)
    def clear_discount_cache_on_save(sender, instance, **kwargs):
        safe_delete_pattern('product_*')
        cache.delete('latest_products')

    @receiver(post_delete, sender=Discount)
    def clear_discount_cache_on_delete(sender, instance, **kwargs):
        safe_delete_pattern('product_*')
        cache.delete('latest_products')

except ImportError:
    pass