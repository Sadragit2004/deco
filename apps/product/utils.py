# product/utils/cache_utils.py
from django.core.cache import cache
import logging

logger = logging.getLogger(__name__)


def safe_delete_pattern(pattern):
    """
    پاک کردن کش بر اساس الگو به صورت امن
    برای تمام Backendها کار می‌کند
    """
    try:
        # اگر delete_pattern وجود داشت
        if hasattr(cache, 'delete_pattern'):
            cache.delete_pattern(pattern)
            return True
    except AttributeError:
        pass

    # برای LocMemCache و سایر Backendها
    try:
        # روش جایگزین: حذف کلیدهای خاص
        if pattern.endswith('_*'):
            # برای الگوهای خاص مثل 'product_*'
            prefix = pattern[:-2]
            # کلیدهای معروف رو حذف می‌کنیم
            if prefix == 'product_':
                cache.delete('latest_products')
                cache.delete_pattern('product_detail_*')
            elif prefix == 'brand_':
                cache.delete('popular_brands')
                cache.delete('latest_catalogs')
            elif prefix == 'catalog_':
                cache.delete('latest_catalogs')
                cache.delete('catalogs_list')
            elif prefix == 'category_':
                cache.delete('main_categories')
            elif prefix == 'bestsellers_':
                cache.delete_pattern('bestsellers_*')
    except Exception as e:
        logger.warning(f"Could not delete pattern {pattern}: {e}")

    return False


def clear_cache_keys(keys):
    """پاک کردن لیستی از کلیدهای کش"""
    for key in keys:
        try:
            cache.delete(key)
        except Exception as e:
            logger.warning(f"Could not delete key {key}: {e}")