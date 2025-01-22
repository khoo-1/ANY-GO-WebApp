# filepath: /C:/Users/khoo_/Desktop/ANY-GO-WebApp/erp/forms.py
from django import forms
from .models import Product

class ProductForm(forms.ModelForm):
    class Meta:
        model = Product
        fields = [
            'sku', 'name', 'chinese_name', 'description', 'price', 'spu',
            'category', 'supplier', 'brand', 'weight', 'volume', 'status',
            'image', 'stock'
        ]