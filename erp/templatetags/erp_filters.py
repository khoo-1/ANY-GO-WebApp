from django import template

register = template.Library()

@register.filter
def multiply(value, arg):
    """乘法运算过滤器"""
    try:
        return float(value) * float(arg)
    except (ValueError, TypeError):
        return 0 