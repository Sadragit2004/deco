
from django.urls import path
from . import views
from . import slider
from . import sample

app_name = 'main'

urlpatterns = [

    path('',views.main,name='index'),
    path('wait/',views.waitPage,name='wait'),
    path('api/sliders/', slider.slider_list_api, name='slider_list_api'),
    path('api/sliders/create/', slider.slider_create_api, name='slider_create_api'),
    path('api/sliders/<int:slider_id>/', slider.slider_detail_api, name='slider_detail_api'),
    path('api/sliders/<int:slider_id>/update/', slider.slider_update_api, name='slider_update_api'),
    path('api/sliders/<int:slider_id>/delete/', slider.slider_delete_api, name='slider_delete_api'),

    path('portfolio/', sample.portfolio_page, name='portfolio_page'),
    path('api/portfolios/', sample.portfolio_list_api, name='portfolio_list_api'),
    path('api/my-portfolios/', sample.my_portfolio_list_api, name='my_portfolio_list_api'),
    path('api/portfolios/create/', sample.create_portfolio_api, name='create_portfolio_api'),
    path('api/portfolios/<int:portfolio_id>/upload-image/', sample.upload_portfolio_image_api, name='upload_portfolio_image_api'),
    path('api/portfolios/<int:portfolio_id>/delete/', sample.delete_portfolio_api, name='delete_portfolio_api'),
]

