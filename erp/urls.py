# filepath: /C:/Users/khoo_/Desktop/ANY-GO-WebApp/erp/urls.py
from django.urls import path
from . import views

urlpatterns = [
    path('products/', views.product_list, name='product_list'),
    path('products/<int:pk>/', views.product_detail, name='product_detail'),
    path('products/add/', views.add_product, name='add_product'),
    path('products/<int:pk>/edit/', views.edit_product, name='edit_product'),
    path('products/<int:pk>/delete/', views.delete_product, name='delete_product'),
    path('products/export/', views.export_products, name='export_products'),  # 添加导出功能的 URL 路由
    path('inventory/', views.inventory_list, name='inventory_list'),
    path('packing/', views.packing_list, name='packing_list'),
    path('packing/<int:pk>/', views.packing_list_detail, name='packing_list_detail'),
    path('packing/<int:pk>/delete/', views.delete_packing_list, name='delete_packing_list'),
    path('bulk_upload/', views.bulk_upload, name='bulk_upload'),
    path('save_bulk_upload/', views.save_bulk_upload, name='save_bulk_upload'),
    path('bulk-product-upload/', views.bulk_product_upload, name='bulk_product_upload'),
    path('clear-all-data/', views.clear_all_data, name='clear_all_data'),
]