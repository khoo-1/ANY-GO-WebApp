# filepath: /C:/Users/khoo_/Desktop/ANY-GO-WebApp/erp/urls.py
from django.urls import path
from . import views

urlpatterns = [
    path('', views.index, name='index'),
    path('products/', views.product_list, name='product_list'),
    path('products/add/', views.add_product, name='add_product'),
    path('products/edit/<int:pk>/', views.edit_product, name='edit_product'),
    path('products/delete/<int:pk>/', views.delete_product, name='delete_product'),
    path('products/export/', views.export_products, name='export_products'),
    path('products/<int:pk>/', views.product_detail, name='product_detail'),
    path('inventory/', views.inventory_list, name='inventory_list'),
    path('inventory/edit/<int:pk>/', views.inventory_edit, name='inventory_edit'),
    path('packing-lists/', views.packing_list, name='packing_list'),
    path('packing-lists/<int:pk>/', views.packing_list_detail, name='packing_list_detail'),
    path('packing-lists/delete/<int:pk>/', views.delete_packing_list, name='delete_packing_list'),
    path('bulk-upload/', views.bulk_upload, name='bulk_upload'),
    path('bulk-product-upload/', views.bulk_product_upload, name='bulk_product_upload'),
    path('save-bulk-upload/', views.save_bulk_upload, name='save_bulk_upload'),
    path('clear-data/', views.clear_all_data, name='clear_data'),
    # 发货单相关URL
    path('shipment/import/', views.shipment_import, name='shipment_import'),
    path('shipment/template/', views.download_shipment_template, name='download_shipment_template'),
    path('shipment/', views.shipment_list, name='shipment_list'),
    path('shipment/<int:pk>/', views.shipment_detail, name='shipment_detail'),
    path('shipment/<int:pk>/delete/', views.delete_shipment, name='delete_shipment'),
    path('shipment/<int:shipment_id>/change-status/', views.change_shipment_status, name='change_shipment_status'),
    path('shipment/<int:shipment_id>/rollback-status/', views.rollback_shipment_status, name='rollback_shipment_status'),
    path('shipment/<int:pk>/export/', views.export_shipment_detail, name='export_shipment_detail'),
    path('shipment/<int:shipment_id>/item/<int:item_id>/edit/', views.edit_shipment_item, name='edit_shipment_item'),
    path('shipment/<int:shipment_id>/item/add/', views.add_shipment_item, name='add_shipment_item'),
    path('shipment/<int:shipment_id>/item/<int:item_id>/delete/', views.delete_shipment_item, name='delete_shipment_item'),
]