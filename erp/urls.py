# filepath: /C:/Users/khoo_/Desktop/ANY-GO-WebApp/erp/urls.py
from django.urls import path
from . import views

urlpatterns = [
    # 主页
    path('', views.index, name='index'),
    
    # 产品管理
    path('products/', views.product_list, name='product_list'),
    path('products/export/', views.export_products, name='export_products'),
    path('products/<int:pk>/', views.product_detail, name='product_detail'),
    path('products/add/', views.add_product, name='add_product'),
    path('products/<int:pk>/edit/', views.edit_product, name='edit_product'),
    path('products/<int:pk>/delete/', views.delete_product, name='delete_product'),
    
    # 库存管理
    path('inventory/', views.inventory_list, name='inventory_list'),
    path('inventory/import/', views.import_inventory, name='import_inventory'),
    path('inventory/export/', views.export_inventory, name='export_inventory'),
    path('inventory/template/', views.download_inventory_template, name='download_inventory_template'),
    path('inventory/<int:pk>/edit/', views.inventory_edit, name='inventory_edit'),
    path('inventory/export-stats/', views.export_inventory_stats, name='export_inventory_stats'),
    
    # 装箱单管理

    
    # 批量上传
    
    
    # 发货单管理
    path('shipment/', views.shipment_list, name='shipment_list'),
    path('shipment/<int:pk>/', views.shipment_detail, name='shipment_detail'),
    path('shipment/<int:pk>/delete/', views.delete_shipment, name='delete_shipment'),
    path('shipment/<int:shipment_id>/change-status/', views.change_shipment_status, name='change_shipment_status'),
    path('shipment/<int:shipment_id>/rollback-status/', views.rollback_shipment_status, name='rollback_shipment_status'),
    path('shipment/import/', views.shipment_import, name='shipment_import'),
    path('shipment/template/', views.download_shipment_template, name='download_shipment_template'),
    path('shipment/<int:pk>/export/', views.export_shipment_detail, name='export_shipment_detail'),
    
    # 发货单商品管理
    path('shipment/<int:shipment_id>/item/<int:item_id>/edit/', views.edit_shipment_item, name='edit_shipment_item'),
    path('shipment/<int:shipment_id>/item/add/', views.add_shipment_item, name='add_shipment_item'),
    path('shipment/<int:shipment_id>/item/<int:item_id>/delete/', views.delete_shipment_item, name='delete_shipment_item'),
    
    # 数据管理
    path('clear-data/', views.clear_data, name='clear_data'),
]