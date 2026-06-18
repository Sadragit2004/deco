from django.urls import path, include
from .views import category
from .views import products
from .views import brands
from .views import catalog
from .views import ProductDetail
from .views import shop
from . import wishview

app_name = 'product'

urlpatterns = [
    # ========== مسیرهای API و دیتا (بدون slug عمومی) ==========
    path('noneParentCategory/', category.CategoryListView.as_view(), name='categorynoneParent'),
    path('lastedProduct/', products.LatestProductsView.as_view(), name='lastedProduct'),
    path('popularBrands/', brands.PopularBrandsView.as_view(), name='popularBrands'),
    path('latest-catalogs/', catalog.latest_catalogs, name='latest_catalogs'),
    path('api/bestsellers/', products.BestsellersAPIView.as_view(), name='bestsellers-api'),
    path('search-suggestions/', shop.SearchSuggestionsView.as_view(), name='search_suggestions'),
    path('category-mega-menu/<slug:slug>/', category.CategoryMegaMenuView.as_view(), name='category_mega_menu'),

    # ========== مسیرهای فروشگاه و شاپ ==========
    path('shop/', shop.ShopView.as_view(), name='shop'),

    # ========== مسیرهای دسته‌بندی و برند ==========
    path('category/<slug:slug>/brands/', category.CategoryBrandsView.as_view(), name='category_brands'),
    path('brand/<slug:slug>/catalogs/', category.BrandCatalogsView.as_view(), name='brand_catalogs'),

    # ========== مسیر عمومی محصول (حتماً در آخر باشد) ==========
    path('<slug:slug>/', ProductDetail.ProductDetailView.as_view(), name='product_detail'),
     path('wishlist/check/<int:product_id>/', wishview.check_in_wishlist, name='wishlist_check'),
    path('wishlist/toggle/', wishview.toggle_wishlist, name='wishlist_toggle'),
    path('wishlist/active', wishview.wishlist_page, name='wishlist'),
    path('wishlist/remove/<int:item_id>/', wishview.remove_wishlist_item, name='wishlist_remove'),  # این مسیر مهمه
    path('wishlist/clear/', wishview.clear_wishlist, name='wishlist_clear'),
    path('wishlist/count/', wishview.get_wishlist_count, name='wishlist_count'),
]