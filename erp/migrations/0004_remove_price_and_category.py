from django.db import migrations

class Migration(migrations.Migration):

    dependencies = [
        ('erp', '0003_product_shop_product_stock_arrived_and_more'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='product',
            name='price',
        ),
        migrations.RemoveField(
            model_name='product',
            name='category',
        ),
    ] 