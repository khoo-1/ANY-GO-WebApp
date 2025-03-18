import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ecommerce_project.settings')
django.setup()

from erp.models import Shop

# 店铺列表
shops = ['1号店', '2号店', '8号店', '9号店', '12号店', '13号店', '16号店', '20号店']

# 创建店铺
for shop_name in shops:
    Shop.objects.get_or_create(name=shop_name)
    print(f'创建店铺：{shop_name}') 