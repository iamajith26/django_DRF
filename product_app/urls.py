from django.urls import path, include
from .views import ProductView, CategoryView
from . import views

urlpatterns = [

    path('categories', CategoryView.as_view(), name='category_list'),
    path('create_category', CategoryView.as_view(), name='create_category'),
    path('get_category/<int:pk>', CategoryView.as_view(), name='get_category'),
    path('update_category/<int:pk>', CategoryView.as_view(), name='update_category'),
    path('delete_category/<int:pk>', CategoryView.as_view(), name='delete_category'),
    path('activate_category/<int:pk>', CategoryView.as_view(), name='activate_category'),
    
    path('products', ProductView.as_view(), name='product_list'),
    path('create_product', ProductView.as_view(), name='create_product'),
    path('get_product/<int:pk>', ProductView.as_view(), name='get_product'),
    path('update_product/<int:pk>', ProductView.as_view(), name='update_product'),
    path('delete_product/<int:pk>', ProductView.as_view(), name='delete_product'),
    path('activate_product/<int:pk>', ProductView.as_view(), name='activate_product'),
    
    path('users', views.fetch_users, name='fetch_users'),
]