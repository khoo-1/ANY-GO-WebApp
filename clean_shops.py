import os
import django
import re

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ecommerce_project.settings')
django.setup()

from erp.models import Shop, Product

def clean_shops():
    """清理店铺数据，只保留标准命名的店铺（如1号店、2号店等）"""
    # 获取所有店铺
    shops = Shop.objects.all()
    
    # 存储标准店铺映射
    standard_shops = {}
    
    for shop in shops:
        # 检查是否是标准命名（数字+号店）
        match = re.match(r'^(\d+)号店.*$', shop.name)
        if match:
            shop_number = match.group(1)
            standard_name = f"{shop_number}号店"
            
            # 如果这是一个非标准名称的店铺
            if shop.name != standard_name:
                # 获取或创建标准名称的店铺
                standard_shop, created = Shop.objects.get_or_create(name=standard_name)
                standard_shops[shop_number] = standard_shop
                
                # 更新关联的产品到标准店铺
                Product.objects.filter(shop=shop).update(shop=standard_shop)
                
                # 删除非标准店铺
                shop.delete()
                print(f"已将店铺 '{shop.name}' 的产品迁移到 '{standard_name}'")
            else:
                standard_shops[shop_number] = shop
                print(f"保留标准店铺 '{shop.name}'")

if __name__ == '__main__':
    clean_shops()
    print("店铺清理完成！") 