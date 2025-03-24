# filepath: /C:/Users/khoo_/Desktop/ANY-GO-WebApp/erp/forms.py
from django import forms
from .models import Product, ShipmentOrder, Shop
from decimal import Decimal

class ProductForm(forms.ModelForm):
    class Meta:
        model = Product
        fields = [
            'sku',
            'chinese_name',
            'purchase_cost',
            'shipping_cost',
            'weight',
            'volume',
            'shop',
            'stock_in_warehouse',
            'stock_arrived',
            'stock_in_transit',
            'value_in_warehouse',
            'value_arrived',
            'value_in_transit',
            'stock',
            'total_value'
        ]
        widgets = {
            'sku': forms.TextInput(attrs={'class': 'form-control'}),
            'chinese_name': forms.TextInput(attrs={'class': 'form-control'}),
            'purchase_cost': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'shipping_cost': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'weight': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'volume': forms.TextInput(attrs={'class': 'form-control'}),
            'shop': forms.Select(attrs={'class': 'form-select'}),
            'stock_in_warehouse': forms.NumberInput(attrs={'class': 'form-control'}),
            'stock_arrived': forms.NumberInput(attrs={'class': 'form-control', 'readonly': 'readonly'}),
            'stock_in_transit': forms.NumberInput(attrs={'class': 'form-control', 'readonly': 'readonly'}),
            'value_in_warehouse': forms.NumberInput(attrs={'class': 'form-control', 'readonly': 'readonly'}),
            'value_arrived': forms.NumberInput(attrs={'class': 'form-control', 'readonly': 'readonly'}),
            'value_in_transit': forms.NumberInput(attrs={'class': 'form-control', 'readonly': 'readonly'}),
            'stock': forms.NumberInput(attrs={'class': 'form-control', 'readonly': 'readonly'}),
            'total_value': forms.NumberInput(attrs={'class': 'form-control', 'readonly': 'readonly'})
        }
    
    def clean_purchase_cost(self):
        purchase_cost = self.cleaned_data.get('purchase_cost')
        if purchase_cost < 0:
            raise forms.ValidationError("采购成本不能为负数")
        return Decimal(str(purchase_cost)).quantize(Decimal('0.01'))
    
    def clean_shipping_cost(self):
        shipping_cost = self.cleaned_data.get('shipping_cost')
        if shipping_cost < 0:
            raise forms.ValidationError("头程成本不能为负数")
        return Decimal(str(shipping_cost)).quantize(Decimal('0.01'))
    
    def clean_weight(self):
        weight = self.cleaned_data.get('weight')
        if weight < 0:
            raise forms.ValidationError("重量不能为负数")
        return Decimal(str(weight)).quantize(Decimal('0.01'))
    
    def clean_stock_in_warehouse(self):
        stock = self.cleaned_data.get('stock_in_warehouse')
        if stock < 0:
            raise forms.ValidationError("在库数量不能为负数")
        return stock

class ShipmentOrderForm(forms.ModelForm):
    class Meta:
        model = ShipmentOrder
        fields = ['batch_number', 'shop']
        widgets = {
            'batch_number': forms.TextInput(attrs={'class': 'form-control'}),
            'shop': forms.Select(attrs={'class': 'form-select'}),
        }