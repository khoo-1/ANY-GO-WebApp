# filepath: /C:/Users/khoo_/Desktop/ANY-GO-WebApp/erp/forms.py
from django import forms
from .models import Product, ShipmentOrder, Shop

class ProductForm(forms.ModelForm):
    class Meta:
        model = Product
        fields = [
            'sku',
            'chinese_name',
            'purchase_cost',
            'weight',
            'volume',
            'shop',
            'stock_in_warehouse',
            'stock_arrived',
            'stock_in_transit',
            'stock',
            'shipping_cost',
            'value_in_warehouse',
            'value_arrived',
            'value_in_transit',
            'total_value'
        ]

class ShipmentOrderForm(forms.ModelForm):
    class Meta:
        model = ShipmentOrder
        fields = ['batch_number', 'shop']
        widgets = {
            'batch_number': forms.TextInput(attrs={'class': 'form-control'}),
            'shop': forms.Select(attrs={'class': 'form-select'}),
        }