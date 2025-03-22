import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ecommerce_project.settings')
django.setup()

from django.db import connection

# 删除price和category列
with connection.cursor() as cursor:
    try:
        cursor.execute("ALTER TABLE erp_product DROP COLUMN price")
    except:
        print("price列已经不存在")
        
    try:
        cursor.execute("ALTER TABLE erp_product DROP COLUMN category")
    except:
        print("category列已经不存在") 