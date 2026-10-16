
from django.db import transaction
from django.db.models.signals import post_delete, post_save, m2m_changed
from django.dispatch import receiver

from apps.product.models import (
    Product,
    Brand,
    Category,
    Catalog,
    SalesUnit,
    PackageUnit,
    ProductGallery,
    Attribute,
    ProductAttributeValue,
)
from apps.discount.models import Discount
from apps.product.service.shop_cache import invalidate_shop_cache


def schedule_shop_cache_invalidation(sender=None, **kwargs):
    using = kwargs.get("using", "default")
    transaction.on_commit(
        invalidate_shop_cache,
        using=using,
    )


PRODUCT_RELATED_MODELS = (
    Product,
    Brand,
    Category,
    Catalog,
    SalesUnit,
    PackageUnit,
    ProductGallery,
    Attribute,
    ProductAttributeValue,
    Discount,
)


def register_model_invalidation(model):
    dispatch_uid = f"shop_cache_invalidation_{model._meta.label_lower}"

    post_save.connect(
        schedule_shop_cache_invalidation,
        sender=model,
        weak=False,
        dispatch_uid=f"{dispatch_uid}_save",
    )

    post_delete.connect(
        schedule_shop_cache_invalidation,
        sender=model,
        weak=False,
        dispatch_uid=f"{dispatch_uid}_delete",
    )


for model in PRODUCT_RELATED_MODELS:
    register_model_invalidation(model)


M2M_THROUGH_MODELS = (
    Product.categories.through,
    Category.brands.through,
    Catalog.categories.through,
    Discount.categories.through,
    Discount.brands.through,
    Discount.products.through,
)


def register_m2m_invalidation(through_model):
    dispatch_uid = (
        f"shop_cache_m2m_invalidation_{through_model._meta.label_lower}"
    )

    @receiver(
        m2m_changed,
        sender=through_model,
        weak=False,
        dispatch_uid=dispatch_uid,
    )
    def invalidate_on_m2m_change(sender, instance, action, using, **kwargs):
        if action in {"post_add", "post_remove", "post_clear"}:
            transaction.on_commit(
                invalidate_shop_cache,
                using=using,
            )


for through_model in M2M_THROUGH_MODELS:
    register_m2m_invalidation(through_model)
