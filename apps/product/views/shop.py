
import logging

from django.core.paginator import Page, Paginator
from django.db.models import F, Max, Min, Q
from django.http import JsonResponse
from django.shortcuts import render
from django.utils import timezone
from django.views import View

from apps.product.models import (
    Brand,
    Category,
    Product,
)

from apps.discount.models import  Discount,DiscountScope, DiscountType




from apps.product.service.shop_cache import (
    SHOP_CACHE_TTL,
    SHOP_PAGE_SIZE,
    get_or_build_shop_cache,
)

logger = logging.getLogger(__name__)


class ShopView(View):
    template_name = "product_app/products/shop.html"

    def get(self, request):
        params = {
            "search": request.GET.get("search", "").strip(),
            "sort": request.GET.get("sort", "newest").strip(),
            "min_price": request.GET.get("min_price", "").strip(),
            "max_price": request.GET.get("max_price", "").strip(),
            "brand": request.GET.get("brand", "").strip(),
            "category": request.GET.get("category", "").strip(),
            "catalog": request.GET.get("catalog", "").strip(),
            "page": request.GET.get("page", "1").strip(),
        }

        try:
            page_number = max(1, int(params["page"]))
        except (TypeError, ValueError):
            page_number = 1

        params["page"] = str(page_number)

        try:
            min_price = (
                int(params["min_price"])
                if params["min_price"]
                else None
            )
            max_price = (
                int(params["max_price"])
                if params["max_price"]
                else None
            )
        except (TypeError, ValueError):
            min_price = None
            max_price = None
            params["min_price"] = ""
            params["max_price"] = ""

        if min_price is not None and min_price < 0:
            min_price = None
            params["min_price"] = ""

        if max_price is not None and max_price < 0:
            max_price = None
            params["max_price"] = ""

        if (
            min_price is not None
            and max_price is not None
            and min_price > max_price
        ):
            min_price, max_price = max_price, min_price
            params["min_price"] = str(min_price)
            params["max_price"] = str(max_price)

        cache_params = {
            **params,
            "min_price": (
                str(min_price) if min_price is not None else ""
            ),
            "max_price": (
                str(max_price) if max_price is not None else ""
            ),
            "page_size": str(SHOP_PAGE_SIZE),
        }

        payload, cache_hit = get_or_build_shop_cache(
            cache_params,
            lambda: self.build_shop_payload(
                params=params,
                min_price=min_price,
                max_price=max_price,
                page_number=page_number,
            ),
            timeout=SHOP_CACHE_TTL,
        )

        logger.debug(
            "Shop cache status: %s",
            "HIT" if cache_hit else "MISS",
        )

        paginator = Paginator(
            range(payload["total_products"]),
            SHOP_PAGE_SIZE,
        )

        products_page = Page(
            payload["products"],
            payload["page_number"],
            paginator,
        )

        if request.headers.get("X-Requested-With") == "XMLHttpRequest":
            data = []

            for product in payload["products"]:
                image = product["image"]

                data.append({
                    "id": product["id"],
                    "title": product["title"],
                    "slug": product["slug"],
                    "price": product["final_price_display"],
                    "old_price": product["old_price_display"],
                    "discount_percent": product["discount_percent"],
                    "has_discount": product["has_discount"],
                    "image": image.url if image else None,
                    "brand": (
                        product["brand"].title
                        if product["brand"]
                        else ""
                    ),
                    "brand_slug": product["brand_slug"],
                    "code": product["code"] or "",
                    "has_next": products_page.has_next(),
                })

            return JsonResponse({
                "status": "success",
                "data": data,
                "has_next": products_page.has_next(),
                "current_page": payload["page_number"],
                "total_pages": paginator.num_pages,
                "total_products": payload["total_products"],
            })

        context = {
            "products": payload["products"],
            "products_page_obj": products_page,
            "total_products": payload["total_products"],
            "search_query": params["search"],
            "sort_by": params["sort"],
            "min_price": params["min_price"],
            "max_price": params["max_price"],
            "selected_brand": params["brand"],
            "selected_category": params["category"],
            "selected_catalog": params["catalog"],
            "brands": payload["brands"],
            "categories": payload["categories"],
            "price_min": payload["price_min"],
            "price_max": payload["price_max"],
        }

        return render(request, self.template_name, context)

    def build_shop_payload(
        self,
        params,
        min_price,
        max_price,
        page_number,
    ):
        products = (
            Product.objects
            .filter(status=True)
            .select_related("brand", "sales_unit")
            .prefetch_related("categories")
        )

        search_query = params["search"]

        if search_query:
            products = products.filter(
                Q(title__icontains=search_query)
                | Q(description__icontains=search_query)
                | Q(code__icontains=search_query)
                | Q(brand__title__icontains=search_query)
            )

        if params["brand"]:
            products = products.filter(
                brand__slug=params["brand"]
            )

        if params["category"]:
            products = products.filter(
                categories__slug=params["category"]
            )

        if params["catalog"]:
            products = products.filter(
                catalog__slug=params["catalog"]
            )

        if min_price is not None:
            products = products.filter(price__gte=min_price)

        if max_price is not None:
            products = products.filter(price__lte=max_price)

        products = products.distinct()

        sort_options = {
            "newest": ("-created_at", "-pk"),
            "expensive": ("-price", "-pk"),
            "cheapest": ("price", "pk"),
            "bestseller": ("-stock", "-pk"),
        }

        products = products.order_by(
            *sort_options.get(
                params["sort"],
                sort_options["newest"],
            )
        )

        total_products = products.count()

        price_range = products.aggregate(
            min_price=Min("price"),
            max_price=Max("price"),
        )

        paginator = Paginator(
            range(total_products),
            SHOP_PAGE_SIZE,
        )

        page_obj = paginator.get_page(page_number)
        page_number = page_obj.number

        start = page_obj.start_index() - 1
        end = page_obj.end_index()

        page_products = list(products[start:end])

        discounts = self.get_active_discounts()
        products_with_discount = []

        for product in page_products:
            discount_info = self.get_discount_info(
                product,
                discounts,
            )

            products_with_discount.append({
                "id": product.id,
                "title": product.title,
                "slug": product.slug,
                "code": product.code,
                "image": product.image,
                "brand": product.brand,
                "brand_slug": (
                    product.brand.slug if product.brand else ""
                ),
                "price": product.price,
                "sales_unit_symbol": product.get_sales_unit_symbol(),
                "has_discount": discount_info["has_discount"],
                "discount_percent": discount_info["discount_percent"],
                "final_price": discount_info["final_price"],
                "final_price_display": (
                    discount_info["final_price_display"]
                ),
                "old_price_display": (
                    discount_info["old_price_display"]
                ),
            })

        brands = list(
            Brand.objects
            .filter(status=True, products__isnull=False)
            .distinct()
            .order_by("title")
        )

        categories = list(
            Category.objects
            .filter(status=True, products__isnull=False)
            .distinct()
            .order_by("title")
        )

        return {
            "products": products_with_discount,
            "total_products": total_products,
            "page_number": page_number,
            "brands": brands,
            "categories": categories,
            "price_min": int(price_range["min_price"] or 0),
            "price_max": int(
                price_range["max_price"] or 10000000
            ),
        }

    @staticmethod
    def get_active_discounts():
        now = timezone.now()

        return list(
            Discount.objects
            .filter(
                is_active=True,
                start_date__lte=now,
                end_date__gte=now,
            )
            .filter(
                Q(usage_limit__isnull=True)
                | Q(usage_limit=0)
                | Q(used_count__lt=F("usage_limit"))
            )
            .prefetch_related(
                "categories",
                "brands",
                "products",
            )
            .order_by("-priority", "start_date")
        )

    @staticmethod
    def get_discount_info(product, discounts):
        try:
            price = float(product.price or 0)
            best_discount = None
            best_amount = 0.0

            product_category_ids = {
                category.id
                for category in product.categories.all()
            }

            product_brand_id = product.brand_id or None

            for discount in discounts:
                if (
                    discount.min_quantity
                    and float(discount.min_quantity) > 1
                ):
                    continue

                if (
                    discount.min_cart_amount
                    and float(discount.min_cart_amount) > 0
                ):
                    continue

                if discount.scope == DiscountScope.GLOBAL:
                    applies = True

                elif discount.scope == DiscountScope.PRODUCT:
                    applies = product.id in {
                        item.id
                        for item in discount.products.all()
                    }

                elif discount.scope == DiscountScope.BRAND:
                    applies = (
                        product_brand_id is not None
                        and product_brand_id in {
                            item.id
                            for item in discount.brands.all()
                        }
                    )

                elif discount.scope == DiscountScope.CATEGORY:
                    discount_category_ids = {
                        item.id
                        for item in discount.categories.all()
                    }
                    applies = bool(
                        product_category_ids & discount_category_ids
                    )

                else:
                    applies = False

                if not applies:
                    continue

                if discount.discount_type == DiscountType.PERCENT:
                    amount = price * float(discount.amount) / 100
                else:
                    amount = min(float(discount.amount), price)

                if amount > best_amount:
                    best_amount = amount
                    best_discount = discount

            has_discount = (
                best_discount is not None and best_amount > 0
            )

            final_price = (
                max(0, price - best_amount)
                if has_discount
                else price
            )

            discount_percent = (
                int((best_amount / price) * 100)
                if has_discount and price > 0
                else 0
            )

            return {
                "has_discount": has_discount,
                "discount_percent": discount_percent,
                "discount_amount": (
                    best_amount if has_discount else 0
                ),
                "final_price": final_price,
                "final_price_display": f"{int(final_price):,}",
                "old_price_display": (
                    f"{int(price):,}"
                    if has_discount and discount_percent > 0
                    else None
                ),
            }

        except (TypeError, ValueError, ArithmeticError):
            logger.exception(
                "Unable to calculate discount for product %s",
                product.pk,
            )

            price = float(product.price or 0)

            return {
                "has_discount": False,
                "discount_percent": 0,
                "discount_amount": 0,
                "final_price": price,
                "final_price_display": f"{int(price):,}",
                "old_price_display": None,
            }


class SearchSuggestionsView(View):
    """پیشنهادات جستجو با AJAX"""

    def get(self, request):
        query = request.GET.get('q', '').strip()

        if len(query) < 2:
            return JsonResponse({'status': 'success', 'data': []})

        products = Product.objects.filter(
            Q(title__icontains=query) | Q(brand__title__icontains=query),
            status=True
        )[:8]

        brands = Brand.objects.filter(title__icontains=query, status=True)[:4]

        data = []
        for p in products:
            # محاسبه تخفیف با مدیریت خطا
            price_display = f"{int(p.price):,}" if p.price else '0'
            try:
                if hasattr(p, 'get_best_discount'):
                    result = p.get_best_discount(1, 0)
                    if result and isinstance(result, tuple) and len(result) == 2:
                        best_discount, _ = result
                        if best_discount and hasattr(best_discount, 'discount_type') and best_discount.discount_type == 'percent':
                            final_price = float(p.price) * (1 - float(best_discount.amount) / 100) if p.price else 0
                            price_display = f"{int(final_price):,}"
            except Exception as e:
                print(f"Error in suggestion discount: {e}")

            data.append({
                'type': 'product',
                'type_name': 'محصول',
                'title': p.title,
                'url': f'/product/{p.slug}/',
                'image': p.image.url if p.image else None,
                'price': price_display,
                'brand': p.brand.title if p.brand else ''
            })

        for b in brands:
            data.append({
                'type': 'brand',
                'type_name': 'برند',
                'title': b.title,
                'url': f'/brand/{b.slug}/',
                'image': b.image.url if b.image else None,
            })

        return JsonResponse({'status': 'success', 'data': data})