from django import template
from decimal import Decimal
import decimal

register = template.Library()

@register.filter
def multiply(value1, value2):
    """将两个数相乘"""
    try:
        return Decimal(str(value1)) * Decimal(str(value2))
    except (ValueError, TypeError, decimal.InvalidOperation):
        return 0

@register.filter
def sum_quantity(items):
    """计算总数量"""
    return sum(item.quantity for item in items)

@register.filter
def sum_volume(items):
    """计算总体积"""
    return sum(Decimal(str(item.volume)) * Decimal(str(item.quantity)) for item in items)

@register.filter
def sum_total_value(items):
    """计算总货值（仅采购成本）"""
    return sum(Decimal(str(item.purchase_cost)) * Decimal(str(item.quantity)) for item in items)

@register.filter
def sum_total_value_with_shipping(items):
    """计算总货值（采购成本 + 头程成本）"""
    total = Decimal('0.00')
    for item in items:
        item_cost = Decimal(str(item.purchase_cost)) + Decimal(str(item.shipping_cost))
        item_value = item_cost * Decimal(str(item.quantity))
        total += item_value
    return total.quantize(Decimal('0.01'), rounding='ROUND_HALF_UP') 