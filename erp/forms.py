# filepath: /C:/Users/khoo_/Desktop/ANY-GO-WebApp/erp/forms.py
from django import forms
from .models import Product

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