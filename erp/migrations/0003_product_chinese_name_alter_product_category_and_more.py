# Generated by Django 4.2.17 on 2024-12-26 10:11

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("erp", "0002_warehouse_product_image_inventory"),
    ]

    operations = [
        migrations.AddField(
            model_name="product",
            name="chinese_name",
            field=models.CharField(default=1, max_length=200),
            preserve_default=False,
        ),
        migrations.AlterField(
            model_name="product",
            name="category",
            field=models.CharField(blank=True, max_length=100, null=True),
        ),
        migrations.AlterField(
            model_name="product",
            name="description",
            field=models.TextField(blank=True, null=True),
        ),
        migrations.AlterField(
            model_name="product",
            name="name",
            field=models.CharField(blank=True, max_length=200, null=True),
        ),
        migrations.AlterField(
            model_name="product",
            name="price",
            field=models.DecimalField(
                blank=True, decimal_places=2, max_digits=10, null=True
            ),
        ),
        migrations.AlterField(
            model_name="product",
            name="sku",
            field=models.CharField(max_length=100, unique=True),
        ),
        migrations.AlterField(
            model_name="product",
            name="spu",
            field=models.CharField(blank=True, max_length=100, null=True),
        ),
        migrations.AlterField(
            model_name="product",
            name="stock",
            field=models.IntegerField(blank=True, null=True),
        ),
        migrations.AlterField(
            model_name="product",
            name="supplier",
            field=models.CharField(blank=True, max_length=100, null=True),
        ),
    ]
