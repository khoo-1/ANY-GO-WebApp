# Generated by Django 5.1.7 on 2025-03-18 13:14

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='PackingList',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=200)),
                ('total_boxes', models.IntegerField()),
                ('total_weight', models.DecimalField(decimal_places=2, max_digits=10)),
                ('total_volume', models.DecimalField(decimal_places=2, max_digits=10)),
                ('total_side_plus_one_volume', models.DecimalField(decimal_places=2, max_digits=10)),
                ('total_items', models.IntegerField()),
                ('type', models.CharField(max_length=100)),
                ('total_price', models.DecimalField(decimal_places=2, max_digits=10)),
            ],
        ),
        migrations.CreateModel(
            name='Product',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('sku', models.CharField(max_length=100, unique=True, verbose_name='SKU')),
                ('chinese_name', models.CharField(max_length=200, verbose_name='中文名称')),
                ('price', models.DecimalField(decimal_places=2, default=0.0, max_digits=10, verbose_name='价格')),
                ('category', models.CharField(choices=[('普货', '普货'), ('纺织', '纺织'), ('混装', '混装')], default='普货', max_length=50, verbose_name='类别')),
                ('weight', models.DecimalField(decimal_places=2, default=0.0, max_digits=10, verbose_name='重量')),
                ('volume', models.CharField(blank=True, max_length=100, verbose_name='体积')),
                ('stock', models.IntegerField(default=0, verbose_name='库存')),
                ('shipping_cost', models.DecimalField(decimal_places=2, default=0.0, max_digits=10, verbose_name='头程成本')),
                ('total_value', models.DecimalField(decimal_places=2, default=0.0, max_digits=10, verbose_name='总货值')),
            ],
            options={
                'verbose_name': '产品',
                'verbose_name_plural': '产品',
            },
        ),
        migrations.CreateModel(
            name='ShipmentOrder',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('batch_number', models.CharField(max_length=50, unique=True, verbose_name='批次号')),
                ('total_price', models.DecimalField(decimal_places=2, max_digits=10, verbose_name='总价格')),
                ('status', models.CharField(choices=[('在途', '在途'), ('到岸', '到岸')], default='在途', max_length=10, verbose_name='状态')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='创建时间')),
            ],
            options={
                'verbose_name': '发货单',
                'verbose_name_plural': '发货单',
            },
        ),
        migrations.CreateModel(
            name='Shop',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=50, verbose_name='店铺名称')),
            ],
            options={
                'verbose_name': '店铺',
                'verbose_name_plural': '店铺',
            },
        ),
        migrations.CreateModel(
            name='Warehouse',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=100)),
                ('location', models.CharField(max_length=100)),
            ],
        ),
        migrations.CreateModel(
            name='PackingListItem',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('quantity', models.IntegerField()),
                ('packing_list', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='items', to='erp.packinglist')),
                ('product', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='erp.product')),
            ],
        ),
        migrations.CreateModel(
            name='ShipmentItem',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('quantity', models.IntegerField(verbose_name='数量')),
                ('purchase_cost', models.DecimalField(decimal_places=2, max_digits=10, verbose_name='采购成本')),
                ('volume', models.DecimalField(decimal_places=2, max_digits=10, verbose_name='体积')),
                ('shipping_cost', models.DecimalField(decimal_places=2, default=0, max_digits=10, verbose_name='头程成本')),
                ('product', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='erp.product', verbose_name='产品')),
                ('shipment_order', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='items', to='erp.shipmentorder', verbose_name='发货单')),
            ],
            options={
                'verbose_name': '发货单项目',
                'verbose_name_plural': '发货单项目',
            },
        ),
        migrations.AddField(
            model_name='shipmentorder',
            name='shop',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='erp.shop', verbose_name='店铺'),
        ),
        migrations.CreateModel(
            name='Inventory',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('stock', models.IntegerField()),
                ('product', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='erp.product')),
                ('warehouse', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='erp.warehouse')),
            ],
        ),
    ]
