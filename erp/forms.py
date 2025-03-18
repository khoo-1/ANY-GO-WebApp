# filepath: /C:/Users/khoo_/Desktop/ANY-GO-WebApp/erp/forms.py
from django import forms
from .models import Product, ShipmentOrder, Shop

class ProductForm(forms.ModelForm):
    class Meta:
        model = Product
        fields = [
            'sku',
            'chinese_name',
            'price',
            'category',
            'weight',
            'volume',
            'stock',
            'shipping_cost',
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