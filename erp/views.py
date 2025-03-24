# filepath: /C:/Users/khoo_/Desktop/ANY-GO-WebApp/erp/views.py
from django.shortcuts import render, redirect, get_object_or_404
from django.db.models import Q
from django.core.paginator import Paginator
from django.http import HttpResponse, JsonResponse
from .forms import ProductForm, ShipmentOrderForm
from .models import Product, Inventory, ShipmentOrder, ShipmentItem, Shop
import subprocess
import os
import json
import pandas as pd
from django.contrib import messages
import openpyxl
from openpyxl.styles import Font, Alignment, PatternFill
from openpyxl.utils import get_column_letter
import traceback
from django.contrib.auth.decorators import login_required
from decimal import Decimal, InvalidOperation
from datetime import datetime
import uuid
from django.db.models import Sum, F, DecimalField, Count, Case, When, Q, Value
from django.db.models.functions import Coalesce
import logging
import csv

def index(request):
    """首页视图"""
    return render(request, 'erp/index.html')

def product_list(request):
    query = request.GET.get("q")
    shop_id = request.GET.get("shop")
    
    # 基础查询集合
    products = Product.objects.all().select_related('shop')
    
    # 应用搜索过滤
    if query:
        products = products.filter(
            Q(sku__icontains=query)
            | Q(chinese_name__icontains=query)
            | Q(weight__icontains=query)
            | Q(volume__icontains=query)
        )
    
    # 按店铺筛选
    if shop_id:
        try:
            shop_id = int(shop_id)
            products = products.filter(shop_id=shop_id)
        except (ValueError, TypeError):
            pass  # 忽略无效的shop_id值
    
    # 排序
    products = products.order_by("id")
    
    # 分页
    paginator = Paginator(products, 100)  # 每页显示100个产品
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)
    
    # 获取所有店铺，用于筛选
    shops = Shop.objects.all()
    
    return render(request, "erp/product/list.html", {
        "page_obj": page_obj,
        "shops": shops,
        "current_shop": shop_id
    })


def export_products(request):
    # 获取所有产品
    products = Product.objects.all().select_related('shop')
    
    # 创建Pandas数据框
    data = []
    for product in products:
        data.append({
            'SKU': product.sku,
            '中文名称': product.chinese_name,
            '店铺': product.shop.name if product.shop else '-',
            '重量': str(product.weight),
            '体积': product.volume,
            '在库数量': product.stock_in_warehouse,
            '到岸数量': product.stock_arrived,
            '在途数量': product.stock_in_transit,
            '总库存': product.stock,
            '采购成本': str(product.purchase_cost),
            '头程成本': str(product.shipping_cost),
            '在库货值': str(product.value_in_warehouse),
            '到岸货值': str(product.value_arrived),
            '在途货值': str(product.value_in_transit),
            '总货值': str(product.total_value)
        })
    
    # 转换为DataFrame
    df = pd.DataFrame(data)
    
    # 创建HTTP响应，并设置内容类型和附件文件名
    response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    response['Content-Disposition'] = 'attachment; filename=products.xlsx'
    
    # 使用ExcelWriter写入Excel
    with pd.ExcelWriter(response, engine='xlsxwriter') as writer:
        df.to_excel(writer, sheet_name='产品列表', index=False)
        
        # 获取workbook和worksheet对象
        workbook = writer.book
        worksheet = writer.sheets['产品列表']
        
        # 设置列宽
        for idx, col in enumerate(df.columns):
            # 获取列中最长的字符串长度
            max_len = max(df[col].astype(str).map(len).max(), len(col)) + 2 if not df.empty else len(col) + 2
            worksheet.set_column(idx, idx, max_len)
    
    return response


def product_detail(request, pk):
    product = get_object_or_404(Product, pk=pk)
    return render(request, "erp/product/detail.html", {"product": product})


def add_product(request):
    if request.method == "POST":
        form = ProductForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            return redirect("product_list")
    else:
        form = ProductForm()
    return render(request, "erp/product/add.html", {"form": form})


def clear_data(request):
    """清除所有数据的视图函数"""
    if request.method == 'POST':
        security_password = request.POST.get('security_password')
        
        if security_password == 'ANYGO1001':
            # 直接清除所有数据
            Product.objects.all().delete()
            Shop.objects.all().delete()
            
            messages.success(request, '所有数据已成功清除')
            return redirect('index')
        else:
            messages.error(request, '安全密码错误')
            return redirect(request.META.get('HTTP_REFERER', 'index'))
    
    return redirect('index')


def edit_product(request, pk):
    """编辑产品"""
    product = get_object_or_404(Product, pk=pk)
    
    if request.method == "POST":
        form = ProductForm(request.POST, instance=product)
        if form.is_valid():
            try:
                # 获取原始数据，用于比较变化
                old_stock_in_warehouse = product.stock_in_warehouse
                old_purchase_cost = product.purchase_cost
                old_shipping_cost = product.shipping_cost
                
                # 保存基本字段
                product = form.save(commit=False)
                
                # 如果在库数量、采购成本或头程成本发生变化，重新计算在库货值
                if (old_stock_in_warehouse != product.stock_in_warehouse or 
                    old_purchase_cost != product.purchase_cost or 
                    old_shipping_cost != product.shipping_cost):
                    product.value_in_warehouse = (
                        (product.purchase_cost + product.shipping_cost) * 
                        Decimal(str(product.stock_in_warehouse))
                    ).quantize(Decimal('0.01'), rounding='ROUND_HALF_UP')
                
                # 更新总库存
                product.stock = (
                    product.stock_in_warehouse + 
                    product.stock_arrived + 
                    product.stock_in_transit
                )
                
                # 更新总货值
                product.total_value = (
                    product.value_in_warehouse + 
                    product.value_arrived + 
                    product.value_in_transit
                ).quantize(Decimal('0.01'), rounding='ROUND_HALF_UP')
                
                # 保存更新后的产品
                product.save()
                
                messages.success(request, '产品更新成功')
                return redirect('product_list')
                
            except Exception as e:
                messages.error(request, f'保存失败：{str(e)}')
    else:
        form = ProductForm(instance=product)
    
    return render(request, 'erp/product/edit.html', {
        'form': form,
        'product': product
    })


def delete_product(request, pk):
    product = get_object_or_404(Product, pk=pk)
    if request.method == "POST":
        product.delete()
        return redirect("product_list")
    return render(request, "erp/product/delete.html", {"product": product})


def inventory_list(request):
    """库存列表视图"""
    logger = logging.getLogger(__name__)
    
    try:
        # 检查是否有店铺数据
        shops_count = Shop.objects.count()
        logger.info(f"店铺总数: {shops_count}")
        
        # 检查是否有产品数据
        products_count = Product.objects.count()
        logger.info(f"产品总数: {products_count}")
        
        # 检查未关联店铺的产品
        no_shop_products = Product.objects.filter(shop__isnull=True).count()
        logger.info(f"未关联店铺的产品数: {no_shop_products}")
        
        if no_shop_products > 0:
            # 列出未关联店铺的产品
            for product in Product.objects.filter(shop__isnull=True)[:5]:  # 只显示前5个
                logger.info(f"未关联店铺的产品: SKU={product.sku}, 名称={product.chinese_name}")
        
        # 检查各类型库存数量
        in_warehouse_count = Product.objects.filter(stock_in_warehouse__gt=0).count()
        arrived_count = Product.objects.filter(stock_arrived__gt=0).count()
        in_transit_count = Product.objects.filter(stock_in_transit__gt=0).count()
        
        logger.info(f"在库产品数: {in_warehouse_count}")
        logger.info(f"到岸产品数: {arrived_count}")
        logger.info(f"在途产品数: {in_transit_count}")
        
        # 检查库存值异常的产品
        abnormal_products = Product.objects.filter(
            Q(stock_in_warehouse__lt=0) |
            Q(stock_arrived__lt=0) |
            Q(stock_in_transit__lt=0) |
            Q(value_in_warehouse__lt=0) |
            Q(value_arrived__lt=0) |
            Q(value_in_transit__lt=0)
        )
        
        if abnormal_products.exists():
            logger.warning("发现库存值异常的产品:")
            for product in abnormal_products[:5]:  # 只显示前5个
                logger.warning(f"SKU={product.sku}, 在库={product.stock_in_warehouse}(¥{product.value_in_warehouse}), "
                             f"到岸={product.stock_arrived}(¥{product.value_arrived}), "
                             f"在途={product.stock_in_transit}(¥{product.value_in_transit})")
        
        # 使用annotate和values优化查询
        from django.db.models import Sum, Value, F, DecimalField
        from django.db.models.functions import Coalesce
        from decimal import Decimal
        
        # 按店铺分组统计
        shop_stats = Shop.objects.filter(name__regex=r'^[0-9]+号店$').annotate(
            stock_in_warehouse=Coalesce(Sum('product__stock_in_warehouse'), Value(0)),
            value_in_warehouse=Coalesce(Sum('product__value_in_warehouse'), Value(Decimal('0.00'), output_field=DecimalField())),
            stock_arrived=Coalesce(Sum('product__stock_arrived'), Value(0)),
            value_arrived=Coalesce(Sum('product__value_arrived'), Value(Decimal('0.00'), output_field=DecimalField())),
            stock_in_transit=Coalesce(Sum('product__stock_in_transit'), Value(0)),
            value_in_transit=Coalesce(Sum('product__value_in_transit'), Value(Decimal('0.00'), output_field=DecimalField()))
        ).values('id', 'name', 'stock_in_warehouse', 'value_in_warehouse', 
                'stock_arrived', 'value_arrived', 'stock_in_transit', 'value_in_transit')
        
        # 记录每个店铺的统计数据
        for shop in shop_stats:
            logger.info(f"店铺 {shop['name']} 统计:")
            logger.info(f"  在库: {shop['stock_in_warehouse']} 件, {shop['value_in_warehouse']:.2f} 元")
            logger.info(f"  到岸: {shop['stock_arrived']} 件, {shop['value_arrived']:.2f} 元")
            logger.info(f"  在途: {shop['stock_in_transit']} 件, {shop['value_in_transit']:.2f} 元")
        
        # 计算总体统计
        total_stats = Product.objects.aggregate(
            total_in_warehouse_quantity=Coalesce(Sum('stock_in_warehouse'), Value(0)),
            total_in_warehouse_value=Coalesce(Sum('value_in_warehouse'), Value(Decimal('0.00'), output_field=DecimalField())),
            total_arrived_quantity=Coalesce(Sum('stock_arrived'), Value(0)),
            total_arrived_value=Coalesce(Sum('value_arrived'), Value(Decimal('0.00'), output_field=DecimalField())),
            total_in_transit_quantity=Coalesce(Sum('stock_in_transit'), Value(0)),
            total_in_transit_value=Coalesce(Sum('value_in_transit'), Value(Decimal('0.00'), output_field=DecimalField()))
        )
        
        logger.info(f"总体统计: {total_stats}")
        
        # 格式化店铺统计数据
        formatted_shop_stats = []
        for shop in shop_stats:
            formatted_shop_stats.append({
                'id': shop['id'],
                'name': shop['name'],
                'stats': {
                    'stock_in_warehouse': shop['stock_in_warehouse'],
                    'value_in_warehouse': shop['value_in_warehouse'],
                    'stock_arrived': shop['stock_arrived'],
                    'value_arrived': shop['value_arrived'],
                    'stock_in_transit': shop['stock_in_transit'],
                    'value_in_transit': shop['value_in_transit']
                }
            })
        
        context = {
            'stats': total_stats,
            'shop_stats': formatted_shop_stats,
            'debug_info': {
                'shops_count': shops_count,
                'products_count': products_count,
                'no_shop_products': no_shop_products,
                'in_warehouse_count': in_warehouse_count,
                'arrived_count': arrived_count,
                'in_transit_count': in_transit_count,
            }
        }
        
        return render(request, 'erp/inventory/list.html', context)
        
    except Exception as e:
        logger.error(f"发生错误: {str(e)}")
        logger.error(traceback.format_exc())
        return render(request, 'erp/inventory/list.html', {'error': str(e)})


def packing_list(request):
    packing_lists = PackingList.objects.all()
    return render(request, "erp/packing_list.html", {"packing_lists": packing_lists})


def packing_list_detail(request, pk):
    packing_list = get_object_or_404(PackingList, pk=pk)
    items = PackingListItem.objects.filter(packing_list=packing_list)
    return render(
        request,
        "erp/packing_list_detail.html",
        {"packing_list": packing_list, "items": items},
    )


def delete_packing_list(request, pk):
    packing_list = get_object_or_404(PackingList, pk=pk)
    if request.method == "POST":
        packing_list.delete()
        return redirect("packing_list")
    return render(
        request, "erp/delete_packing_list.html", {"packing_list": packing_list}
    )



def handle_uploaded_file(uploaded_file):
    """处理上传的文件，保存到临时目录并返回文件路径"""
    import uuid
    import time
    import os

    # 检查文件类型
    if not uploaded_file.name.endswith((".xls", ".xlsx")):
        raise ValueError("请上传Excel文件(.xls或.xlsx格式)")

    # 生成唯一的临时文件名
    unique_filename = f"{uuid.uuid4().hex}_{int(time.time())}_{uploaded_file.name}"
    
    # 创建上传目录
    upload_dir = "uploads"
    if not os.path.exists(upload_dir):
        os.makedirs(upload_dir)
    
    # 保存文件
    file_path = os.path.join(upload_dir, unique_filename)
    with open(file_path, "wb+") as destination:
        for chunk in uploaded_file.chunks():
            destination.write(chunk)

    return file_path


def extract_shop_info_from_filename(filename):
    """从文件名中提取店铺信息"""
    if filename.endswith(".xlsx") or filename.endswith(".xls"):
        file_name = filename[:-5] if filename.endswith(".xlsx") else filename[:-4]
        print(f"处理文件名: {file_name}")

        # 检查文件名是否包含特定格式的信息
        parts = file_name.split("-")
        print(f"文件名分割后的部分: {parts}")

        # 如果文件名中包含"号店"，则提取店铺信息
        if "号店" in file_name:
            shop_info = file_name.split("号店")[0] + "号店"
            print(f"从文件名解析到店铺信息: {shop_info}")
            return shop_info
        
        # 如果文件名符合特定格式
        if len(parts) >= 1:
            shop_info = parts[0]
            print(f"从文件名解析到店铺信息: {shop_info}")
            return shop_info
    
    return ""


def generate_packing_list_name(shop_info, packing_type):
    """生成装箱单名称"""
    import time
    
    # 生成时间戳
    timestamp = time.strftime("%y%m%d%H%M")
    
    # 生成类型后缀
    type_suffix = ""
    if packing_type == "普货":
        type_suffix = "ph"
    elif packing_type == "纺织":
        type_suffix = "fz"
    elif packing_type == "混装":
        type_suffix = "hz"
    
    # 生成装箱单名称
    return f"{shop_info}_S{timestamp}-{type_suffix}"


def process_sku_data(df, packing_list):
    """处理SKU数据并返回处理的记录数"""
    # 查找SKU表头行
    sku_start_row = None
    for row_idx in range(5, min(15, df.shape[0])):
        if row_idx < df.shape[0] and df.shape[1] > 1:
            cell_value = df.iloc[row_idx, 1]
            if isinstance(cell_value, str) and "sku" in str(cell_value).lower():
                sku_start_row = row_idx + 1
                print(f"在第{row_idx+1}行找到SKU表头，数据从第{sku_start_row+1}行开始")
                break
    
    # 如果没找到表头，默认从第8行开始
    if sku_start_row is None:
        sku_start_row = 7
    
    processed_skus = []
    records_count = 0
    
    # 处理每一行SKU数据
    for row_idx in range(sku_start_row, df.shape[0]):
        if row_idx < df.shape[0] and df.shape[1] > 1:
            sku_value = df.iloc[row_idx, 1]  # B列
            
            if pd.notna(sku_value) and str(sku_value).strip():
                sku = str(sku_value).strip()
                
                # 跳过重复的SKU
                if sku in processed_skus:
                    continue
                
                processed_skus.append(sku)
                print(f"处理SKU: {sku}")
                
                # 获取中文名称
                chinese_name = "待补充"
                if df.shape[1] > 2 and pd.notna(df.iloc[row_idx, 2]):
                    chinese_name = str(df.iloc[row_idx, 2])
                
                # 创建或更新产品
                try:
                    product = Product.objects.get(sku=sku)
                    product.chinese_name = chinese_name
                except Product.DoesNotExist:
                    product = Product(
                            sku=sku,
                            chinese_name=chinese_name,
                            purchase_cost=Decimal('0.00'),
                            shipping_cost=Decimal('0.00'),
                            weight=Decimal('0.00'),
                            volume='0',
                            stock=0,
                            stock_in_warehouse=0,
                            stock_arrived=0,
                            stock_in_transit=0,
                            value_in_warehouse=Decimal('0.00'),
                            value_arrived=Decimal('0.00'),
                            value_in_transit=Decimal('0.00'),
                            total_value=Decimal('0.00')
                    )
                product.save()
            
                # 计算数量
                quantity = 0
                for col_idx in range(5, df.shape[1]):  # 从F列开始
                    if col_idx < df.shape[1] and pd.notna(df.iloc[row_idx, col_idx]):
                        try:
                            val = df.iloc[row_idx, col_idx]
                            print(f"检查列 {col_idx+1} 的值: {val}, 类型: {type(val)}")
                            
                            if isinstance(val, (int, float)) and val > 0:
                                quantity += int(val)
                                print(f"从列索引{col_idx}找到数量: {int(val)}")
                        except (ValueError, TypeError) as e:
                            print(f"处理列 {col_idx+1} 时出错: {str(e)}")
                
                # 创建PackingListItem
                if quantity > 0:
                    PackingListItem.objects.create(
                        packing_list=packing_list,
                        product=product,
                        quantity=quantity,
                    )
                    print(f"添加产品到装箱单: {sku}, 数量: {quantity}")
                    records_count += 1
    
    return records_count


def download_shipment_template(request):
    """下载发货单导入模板"""
    # 创建一个新的DataFrame
    df = pd.DataFrame({
        'SKU': ['示例SKU'],
        '中文名称': ['示例产品'],
        '采购成本': [0.00],
        '体积': [0.00],
        '数量': [0]
    })
    
    # 创建一个 HttpResponse 对象
    response = HttpResponse(
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    response['Content-Disposition'] = 'attachment; filename=shipment_template.xlsx'
    
    # 将DataFrame写入Excel
    with pd.ExcelWriter(response, engine='xlsxwriter') as writer:
        df.to_excel(writer, sheet_name='发货单', index=False)
        
        # 获取工作表
        worksheet = writer.sheets['发货单']
        
        # 设置列宽
        worksheet.set_column('A:A', 15)  # SKU
        worksheet.set_column('B:B', 20)  # 中文名称
        worksheet.set_column('C:C', 12)  # 采购成本
        worksheet.set_column('D:D', 12)  # 体积
        worksheet.set_column('E:E', 10)  # 数量
    
    return response


def shipment_import(request):
    """导入发货单"""
    if request.method == 'POST':
        try:
            # 获取表单信息
            shop_id = request.POST.get('shop')
            batch_number = request.POST.get('batch_number')
            
            # 验证表单信息
            if not shop_id or not batch_number:
                messages.error(request, '请选择店铺并填写批次号')
                return render(request, 'erp/shipment/import.html', {
                    'shops': Shop.objects.filter(name__regex=r'^[0-9]+号店$')
                })
            
            # 检查批次号是否已存在
            if ShipmentOrder.objects.filter(batch_number=batch_number).exists():
                messages.error(request, f'批次号 {batch_number} 已存在')
                return render(request, 'erp/shipment/import.html', {
                    'shops': Shop.objects.filter(name__regex=r'^[0-9]+号店$')
                })
            
            # 验证上传的文件
            if not request.FILES.get('file'):
                messages.error(request, '请选择要上传的Excel文件')
                return render(request, 'erp/shipment/import.html', {
                    'shops': Shop.objects.filter(name__regex=r'^[0-9]+号店$')
                })
            
            # 保存上传的文件
            uploaded_file = request.FILES['file']
            file_path = handle_uploaded_file(uploaded_file)
            
            # 读取Excel文件
            try:
                df = pd.read_excel(file_path)
            except Exception as e:
                if os.path.exists(file_path):
                    os.remove(file_path)  # 删除临时文件
                messages.error(request, f'Excel文件读取失败: {str(e)}')
                return render(request, 'erp/shipment/import.html', {
                    'shops': Shop.objects.filter(name__regex=r'^[0-9]+号店$')
                })
            
            # 验证必要的列是否存在
            required_columns = ['SKU', '数量', '采购成本', '体积']
            if not all(col in df.columns for col in required_columns):
                if os.path.exists(file_path):
                    os.remove(file_path)
                messages.error(request, '文件格式不正确，请使用正确的模板')
                return render(request, 'erp/shipment/import.html', {
                    'shops': Shop.objects.filter(name__regex=r'^[0-9]+号店$')
                })
            
            # 创建发货单
            shop = get_object_or_404(Shop, pk=shop_id)
            shipment = ShipmentOrder.objects.create(
                batch_number=batch_number,
                shop=shop
            )
            
            # 导入必要模块
            from decimal import Decimal
            
            # 准备批量创建的列表
            shipment_items = []
            product_cache = {}  # 缓存已获取的产品，避免重复查询
            updated_products = []  # 需要更新在途库存和货值的产品
            
            success_count = 0
            error_count = 0
            
            # 处理每一行数据
            for _, row in df.iterrows():
                try:
                    sku = str(row['SKU']).strip()
                    quantity = int(row['数量'])
                    purchase_cost = Decimal(str(row['采购成本'])).quantize(Decimal('0.01'), rounding='ROUND_HALF_UP')
                    volume = Decimal(str(row['体积'])).quantize(Decimal('0.01'), rounding='ROUND_HALF_UP')
                    chinese_name = str(row['中文名称']).strip() if pd.notna(row.get('中文名称')) else ''
                    
                    # 获取或创建产品
                    try:
                        product = Product.objects.get(sku=sku)
                        # 更新现有产品信息
                        if chinese_name:
                            product.chinese_name = chinese_name
                        if not product.shop:
                            product.shop = shop
                        product.purchase_cost = purchase_cost
                        product.volume = str(volume)
                        product.save()
                    except Product.DoesNotExist:
                        product = Product.objects.create(
                            sku=sku,
                            chinese_name=chinese_name,
                            purchase_cost=purchase_cost,
                            shipping_cost=Decimal('0.00'),
                            volume=str(volume),
                            shop=shop,
                            stock_in_warehouse=0,
                            stock_arrived=0,
                            stock_in_transit=0,
                            stock=0,
                            value_in_warehouse=Decimal('0.00'),
                            value_arrived=Decimal('0.00'),
                            value_in_transit=Decimal('0.00'),
                            total_value=Decimal('0.00')
                        )
                    
                    # 创建发货单项目
                    shipment_item = ShipmentItem.objects.create(
                        shipment_order=shipment,
                        product=product,
                        quantity=quantity,
                        purchase_cost=purchase_cost,
                        volume=volume,
                        shipping_cost=Decimal('0.00')  # 头程成本在变更状态时计算
                    )
                    
                    # 更新产品在途库存和货值
                    product.stock_in_transit = product.stock_in_transit + quantity
                    product.value_in_transit = product.value_in_transit + (purchase_cost * Decimal(str(quantity)))
                    product.stock = product.stock_in_warehouse + product.stock_arrived + product.stock_in_transit
                    product.total_value = product.value_in_warehouse + product.value_arrived + product.value_in_transit
                    product.save()
                    
                    success_count += 1
                    
                except Exception as e:
                    error_count += 1
                    messages.error(request, f'处理SKU {sku} 时出错: {str(e)}')
            
            # 删除临时文件
            if os.path.exists(file_path):
                os.remove(file_path)
            
            if error_count > 0:
                messages.warning(request, f'导入完成，成功: {success_count} 条，失败: {error_count} 条')
            else:
                messages.success(request, f'导入成功，共处理 {success_count} 条数据')
            
            return redirect('shipment_detail', pk=shipment.id)
            
        except Exception as e:
            messages.error(request, f'导入失败: {str(e)}')
    
    return render(request, 'erp/shipment/import.html', {
        'shops': Shop.objects.filter(name__regex=r'^[0-9]+号店$')
    })


def shipment_list(request):
    """发货单列表"""
    query = request.GET.get('q', '')
    
    if query:
        shipments = ShipmentOrder.objects.filter(
            Q(batch_number__icontains=query) | 
            Q(shop__name__icontains=query) |
            Q(status__icontains=query)
        ).select_related('shop').order_by('-created_at')
    else:
        shipments = ShipmentOrder.objects.all().select_related('shop').order_by('-created_at')
    
    # 使用Django的内置分页
    paginator = Paginator(shipments, 20)  # 每页显示20个发货单
    page_number = request.GET.get('page', 1)
    
    try:
        page_obj = paginator.get_page(page_number)
    except (ValueError, TypeError):
        page_obj = paginator.get_page(1)
    
    return render(request, 'erp/shipment/list.html', {
        'page_obj': page_obj,
        'query': query
    })


def shipment_detail(request, pk):
    """发货单详情"""
    shipment = get_object_or_404(ShipmentOrder.objects.select_related('shop'), pk=pk)
    items = shipment.items.select_related('product').all()
    return render(request, 'erp/shipment/detail.html', {
        'shipment': shipment,
        'items': items
    })


def change_shipment_status(request, shipment_id):
    """变更发货单状态为到岸，并分摊头程成本"""
    shipment = get_object_or_404(ShipmentOrder.objects.select_related('shop'), pk=shipment_id)
    
    if request.method == 'POST':
        try:
            # 获取总价格
            total_price = Decimal(request.POST.get('total_price', '0'))
            
            if total_price <= 0:
                messages.error(request, '总价格必须大于0')
                return render(request, 'erp/shipment/change_status.html', {'shipment': shipment})
            
            # 更新发货单状态和总价格
            shipment.status = '到岸'
            shipment.total_price = total_price
            shipment.save()
            
            # 获取所有相关的物品
            items = list(ShipmentItem.objects.filter(shipment_order=shipment).select_related('product'))
            
            if items:
                # 计算总体积
                total_volume = sum(Decimal(str(item.volume)) * Decimal(str(item.quantity)) for item in items)
                
                if total_volume > 0:
                    # 提前计算单位价格系数以减少除法操作
                    price_factor = total_price / total_volume
                    
                    # 批量更新头程成本
                    updated_items = []
                    updated_products = []
                    
                    # 先将相关产品的在途数量和货值减去，准备转为到岸数量和货值
                    for item in items:
                        try:
                            product = item.product
                            
                            # 更新在途库存和货值
                            item_quantity = Decimal(str(item.quantity))
                            item_purchase_cost = Decimal(str(item.purchase_cost))
                            
                            product.stock_in_transit = product.stock_in_transit - item.quantity
                            transit_value_reduction = item_purchase_cost * item_quantity
                            product.value_in_transit = product.value_in_transit - transit_value_reduction
                            
                            # 确保不会出现负值
                            if product.stock_in_transit < 0:
                                product.stock_in_transit = 0
                            if product.value_in_transit < 0:
                                product.value_in_transit = Decimal('0.00')
                                
                            updated_products.append(product)
                        except Exception as e:
                            messages.error(request, f"更新产品 {item.product.sku} 在途数据时出错：{str(e)}")
                    
                    # 更新物品的头程成本和产品的到岸库存货值
                    for item in items:
                        try:
                            # 计算这个物品占总体积的比例
                            item_volume = Decimal(str(item.volume)) * Decimal(str(item.quantity))
                            
                            # 计算单个物品的头程成本
                            if item.quantity > 0:  # 防止除以零
                                per_item_shipping_cost = (price_factor * item_volume) / Decimal(str(item.quantity))
                                # 保留两位小数
                                per_item_shipping_cost = per_item_shipping_cost.quantize(Decimal('0.01'), rounding='ROUND_HALF_UP')
                            else:
                                per_item_shipping_cost = Decimal('0.00')
                            
                            # 更新物品的头程成本
                            if item.shipping_cost != per_item_shipping_cost:
                                item.shipping_cost = per_item_shipping_cost
                                updated_items.append(item)
                            
                            # 更新产品的头程成本和到岸库存货值
                            product = item.product
                            
                            # 设置产品店铺关联（如果没有）
                            if not product.shop:
                                product.shop = shipment.shop
                            
                            # 更新头程成本
                            if product.shipping_cost != per_item_shipping_cost:
                                product.shipping_cost = per_item_shipping_cost.quantize(Decimal('0.01'), rounding='ROUND_HALF_UP')
                            
                            # 更新到岸库存和货值
                            product.stock_arrived = product.stock_arrived + item.quantity
                            
                            item_quantity = Decimal(str(item.quantity))
                            item_purchase_cost = Decimal(str(item.purchase_cost))
                            item_shipping_cost = Decimal(str(item.shipping_cost))
                            
                            arrived_value_addition = (item_purchase_cost + item_shipping_cost) * item_quantity
                            product.value_arrived = product.value_arrived + arrived_value_addition
                            product.value_arrived = product.value_arrived.quantize(Decimal('0.01'), rounding='ROUND_HALF_UP')
                            
                            # 更新总库存和总货值
                            product.stock = product.stock_in_warehouse + product.stock_arrived + product.stock_in_transit
                            product.total_value = (
                                product.value_in_warehouse + 
                                product.value_arrived + 
                                product.value_in_transit
                            ).quantize(Decimal('0.01'), rounding='ROUND_HALF_UP')
                            
                            if product not in updated_products:
                                updated_products.append(product)
                                
                        except Exception as e:
                            messages.error(request, f"处理物品 {item.product.sku} 时出错：{str(e)}")
                            continue
                    
                    # 批量保存以减少数据库操作
                    if updated_items:
                        for item in updated_items:
                            item.save()
                    
                    if updated_products:
                        for product in updated_products:
                            product.save()
                            
                    messages.success(request, '发货单状态已更新为到岸，头程成本已分摊')
                else:
                    messages.warning(request, '发货单状态已更新为到岸，但总体积为0，无法分摊头程成本')
            else:
                messages.warning(request, '发货单状态已更新为到岸，但没有相关物品，无法分摊头程成本')
            
            return redirect('shipment_detail', pk=shipment_id)
            
        except (ValueError, TypeError) as e:
            messages.error(request, f'更新失败：{str(e)}')
    
    return render(request, 'erp/shipment/change_status.html', {'shipment': shipment})


def delete_shipment(request, shipment_id):
    """删除发货单及其关联的物品"""
    try:
        shipment = get_object_or_404(ShipmentOrder, pk=shipment_id)
        
        # 获取所有关联的物品
        items = shipment.items.select_related('product').all()
        
        # 根据发货单状态更新产品数据
        for item in items:
            product = item.product
            item_quantity = Decimal(str(item.quantity))
            item_purchase_cost = Decimal(str(item.purchase_cost))
            item_shipping_cost = Decimal(str(item.shipping_cost))
            
            if shipment.status == '在途':
                # 减少在途数量和货值
                product.stock_in_transit = max(0, product.stock_in_transit - item.quantity)
                transit_value_reduction = item_purchase_cost * item_quantity
                product.value_in_transit = max(Decimal('0.00'), 
                    product.value_in_transit - transit_value_reduction)
                
            elif shipment.status == '到岸':
                # 减少到岸数量和货值
                product.stock_arrived = max(0, product.stock_arrived - item.quantity)
                arrived_value_reduction = (item_purchase_cost + item_shipping_cost) * item_quantity
                product.value_arrived = max(Decimal('0.00'), 
                    product.value_arrived - arrived_value_reduction)
            
            # 更新总库存和总货值
            product.stock = (product.stock_in_warehouse + 
                           product.stock_arrived + 
                           product.stock_in_transit)
            
            product.total_value = (product.value_in_warehouse + 
                                 product.value_arrived + 
                                 product.value_in_transit)
            
            # 确保货值不会出现负数，并保留两位小数
            product.total_value = max(Decimal('0.00'), 
                product.total_value).quantize(Decimal('0.01'), rounding='ROUND_HALF_UP')
            
            product.save()
        
        # 删除发货单（会级联删除关联的物品）
        shipment.delete()
        messages.success(request, '发货单及其关联物品已成功删除')
        
    except Exception as e:
        messages.error(request, f'删除发货单时出错：{str(e)}')
    
    return redirect('shipment_list')


def inventory_edit(request, pk):
    """编辑库存视图"""
    inventory = get_object_or_404(Inventory, pk=pk)
    if request.method == "POST":
        inventory.stock = request.POST.get("stock")
        inventory.save()
        messages.success(request, "库存更新成功")
        return redirect("inventory_list")
    return render(request, "erp/inventory/edit.html", {"inventory": inventory})


def export_shipment_detail(request, pk):
    """导出发货单详情"""
    shipment = get_object_or_404(ShipmentOrder, pk=pk)
    items = ShipmentItem.objects.filter(shipment_order=shipment).select_related('product')
    
    # 创建DataFrame
    data = []
    for item in items:
        # 确保所有数值计算都使用Decimal类型
        purchase_cost = Decimal(str(item.purchase_cost))
        quantity = Decimal(str(item.quantity))
        shipping_cost = Decimal(str(item.shipping_cost))
        
        # 计算货值
        if shipment.status == '到岸':
            item_value = (purchase_cost + shipping_cost) * quantity
        else:
            item_value = purchase_cost * quantity
            
        # 将计算结果四舍五入到两位小数
        item_value = item_value.quantize(Decimal('0.01'), rounding='ROUND_HALF_UP')
        
        data.append({
            'SKU': item.product.sku,
            '中文名称': item.product.chinese_name,
            '数量': item.quantity,
            '采购成本': item.purchase_cost,
            '体积': item.volume,
            '头程成本': item.shipping_cost,
            '货值': str(item_value)  # 转换为字符串避免pandas中的类型问题
        })
    
    df = pd.DataFrame(data)
    
    # 创建Excel响应
    response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    response['Content-Disposition'] = f'attachment; filename=shipment_{shipment.batch_number}.xlsx'
    
    # 使用xlsxwriter引擎写入Excel
    with pd.ExcelWriter(response, engine='xlsxwriter') as writer:
        # 写入发货单基本信息
        info_df = pd.DataFrame([{
            '批次号': shipment.batch_number,
            '店铺': shipment.shop.name,
            '状态': shipment.status,
            '创建时间': shipment.created_at.strftime('%Y-%m-%d %H:%M'),
            '总价格': str(shipment.total_price) if shipment.total_price else '0.00',
            '总货值': str(shipment.calculate_total_value())
        }])
        info_df.to_excel(writer, sheet_name='基本信息', index=False)
        
        # 写入商品明细
        df.to_excel(writer, sheet_name='商品明细', index=False)
        
        # 获取workbook和worksheet对象
        workbook = writer.book
        info_sheet = writer.sheets['基本信息']
        detail_sheet = writer.sheets['商品明细']
        
        # 设置列宽
        for sheet in [info_sheet, detail_sheet]:
            for idx, col in enumerate(df.columns):
                sheet.set_column(idx, idx, 15)
    
    return response


def rollback_shipment_status(request, shipment_id):
    """回退发货单状态为在途"""
    shipment = get_object_or_404(ShipmentOrder, pk=shipment_id)
    
    if request.method == 'POST':
        try:
            # 先获取发货单所有物品，以便更新产品库存和货值
            items = ShipmentItem.objects.filter(shipment_order=shipment).select_related('product')
            
            # 更新物品和产品状态
            for item in items:
                try:
                    product = item.product
                    from decimal import Decimal
                    
                    # 转换为Decimal类型进行计算
                    item_quantity = Decimal(str(item.quantity))
                    purchase_cost = Decimal(str(item.purchase_cost))
                    shipping_cost = Decimal(str(item.shipping_cost))
                    
                    # 减少到岸库存和货值
                    product.stock_arrived = product.stock_arrived - item.quantity
                    arrived_value_reduction = (purchase_cost + shipping_cost) * item_quantity
                    product.value_arrived = product.value_arrived - arrived_value_reduction
                    
                    # 确保不会出现负值
                    if product.stock_arrived < 0:
                        product.stock_arrived = 0
                    if product.value_arrived < 0:
                        product.value_arrived = Decimal('0.00')
                    
                    # 增加在途库存和货值
                    product.stock_in_transit = product.stock_in_transit + item.quantity
                    transit_value_addition = purchase_cost * item_quantity  # 在途状态只计算采购成本
                    product.value_in_transit = product.value_in_transit + transit_value_addition
                    
                    # 重置物品头程成本
                    item.shipping_cost = Decimal('0.00')  # 重置头程成本为0
                    item.save()
                    
                    # 保存产品状态
                    product.save()
                except Exception as e:
                    messages.error(request, f"处理物品 {item.product.sku} 时出错：{str(e)}")
                    continue
            
            # 更新发货单状态和总价格
            shipment.status = '在途'
            shipment.total_price = None  # 回退状态时清空总价格字段
            shipment.save()
            
            messages.success(request, '发货单状态已回退为在途')
            return redirect('shipment_detail', pk=shipment_id)
            
        except Exception as e:
            messages.error(request, f'回退失败：{str(e)}')
    
    return render(request, 'erp/shipment/rollback_status.html', {'shipment': shipment})


def edit_shipment_item(request, shipment_id, item_id):
    """编辑发货单商品明细"""
    shipment = get_object_or_404(ShipmentOrder, pk=shipment_id)
    item = get_object_or_404(ShipmentItem.objects.select_related('product'), pk=item_id, shipment_order=shipment)
    
    if request.method == 'POST':
        try:
            # 获取表单数据
            quantity = int(request.POST.get('quantity', 0))
            purchase_cost = Decimal(request.POST.get('purchase_cost', '0'))
            volume = Decimal(request.POST.get('volume', '0'))
            
            # 保存修改
            item.quantity = quantity
            item.purchase_cost = purchase_cost.quantize(Decimal('0.01'), rounding='ROUND_HALF_UP')
            item.volume = volume.quantize(Decimal('0.01'), rounding='ROUND_HALF_UP')
            
            # 如果发货单状态是到岸，重新计算头程成本
            if shipment.status == '到岸' and shipment.total_price:
                # 首先保存当前项目的更改
                item.save()
                
                # 一次性获取所有商品及其产品信息
                all_items = list(ShipmentItem.objects.filter(shipment_order=shipment).select_related('product'))
                
                # 计算总体积
                total_volume = sum(Decimal(str(i.volume)) * Decimal(str(i.quantity)) for i in all_items)
                
                if total_volume > 0:
                    # 提前计算单位价格系数以减少除法操作
                    price_factor = shipment.total_price / total_volume
                    
                    # 批量更新头程成本
                    for i in all_items:
                        item_volume = Decimal(str(i.volume)) * Decimal(str(i.quantity))
                        
                        if i.quantity > 0:
                            per_item_shipping_cost = (price_factor * item_volume) / Decimal(str(i.quantity))
                            per_item_shipping_cost = per_item_shipping_cost.quantize(Decimal('0.01'), rounding='ROUND_HALF_UP')
                        else:
                            per_item_shipping_cost = Decimal('0.00')
                        
                        # 只在需要更新时才更新，避免不必要的数据库写入
                        if i.shipping_cost != per_item_shipping_cost:
                            i.shipping_cost = per_item_shipping_cost
                            i.save()
                            
                            # 更新产品的头程成本
                            product = i.product
                            if product.shipping_cost != per_item_shipping_cost:
                                product.shipping_cost = per_item_shipping_cost.quantize(Decimal('0.01'), rounding='ROUND_HALF_UP')
                                product.save()
            else:
                # 非到岸状态，直接保存项目
                item.save()
            
            messages.success(request, '商品明细已更新')
            return redirect('shipment_detail', pk=shipment_id)
            
        except (ValueError, TypeError) as e:
            messages.error(request, f'更新失败：{str(e)}')
    
    return render(request, 'erp/shipment/item/edit.html', {
        'shipment': shipment,
        'item': item
    })


def add_shipment_item(request, shipment_id):
    """向发货单添加新商品"""
    shipment = get_object_or_404(ShipmentOrder.objects.select_related('shop'), pk=shipment_id)
    
    if request.method == 'POST':
        try:
            # 获取表单数据
            sku = request.POST.get('sku', '').strip()
            quantity = int(request.POST.get('quantity', 0))
            purchase_cost = Decimal(request.POST.get('purchase_cost', '0'))
            volume = Decimal(request.POST.get('volume', '0'))
            chinese_name = request.POST.get('chinese_name', '').strip()
            
            if not sku or quantity <= 0:
                messages.error(request, '请输入有效的SKU和数量')
                return render(request, 'erp/shipment/item/add.html', {'shipment': shipment})
            
            # 获取或创建产品
            product, created = Product.objects.get_or_create(
                sku=sku,
                defaults={
                    'chinese_name': chinese_name,
                    'volume': str(volume),
                    'purchase_cost': purchase_cost,
                    'shipping_cost': Decimal('0.00'),
                    'stock_in_warehouse': 0,
                    'stock_arrived': 0,
                    'stock_in_transit': 0,
                    'stock': 0,
                    'value_in_warehouse': Decimal('0.00'),
                    'value_arrived': Decimal('0.00'),
                    'value_in_transit': Decimal('0.00'),
                    'total_value': Decimal('0.00')
                }
            )
            
            # 如果产品已存在但中文名为空，更新中文名
            if not created and not product.chinese_name and chinese_name:
                product.chinese_name = chinese_name
            product.save()
        
            # 创建发货单项目
            item = ShipmentItem.objects.create(
                shipment_order=shipment,
                product=product,
                quantity=quantity,
                purchase_cost=purchase_cost.quantize(Decimal('0.01'), rounding='ROUND_HALF_UP'),
                volume=volume.quantize(Decimal('0.01'), rounding='ROUND_HALF_UP')
            )
            
            # 如果发货单状态是到岸，重新计算头程成本
            if shipment.status == '到岸' and shipment.total_price:
                # 一次性获取所有商品及其产品信息
                all_items = list(ShipmentItem.objects.filter(shipment_order=shipment).select_related('product'))
                
                # 计算总体积
                total_volume = sum(Decimal(str(i.volume)) * Decimal(str(i.quantity)) for i in all_items)
                
                if total_volume > 0:
                    # 提前计算单位价格系数以减少除法操作
                    price_factor = shipment.total_price / total_volume
                    
                    # 批量更新头程成本
                    for i in all_items:
                        item_volume = Decimal(str(i.volume)) * Decimal(str(i.quantity))
                        
                        if i.quantity > 0:
                            per_item_shipping_cost = (price_factor * item_volume) / Decimal(str(i.quantity))
                            per_item_shipping_cost = per_item_shipping_cost.quantize(Decimal('0.01'), rounding='ROUND_HALF_UP')
                        else:
                            per_item_shipping_cost = Decimal('0.00')
                        
                        # 只在需要更新时才更新，避免不必要的数据库写入
                        if i.shipping_cost != per_item_shipping_cost:
                            i.shipping_cost = per_item_shipping_cost
                            i.save()
                            
                            # 更新产品的头程成本
                            product = i.product
                            if product.shipping_cost != per_item_shipping_cost:
                                product.shipping_cost = per_item_shipping_cost.quantize(Decimal('0.01'), rounding='ROUND_HALF_UP')
                                product.save()
            
            messages.success(request, f'成功添加商品 {sku}')
            return redirect('shipment_detail', pk=shipment_id)
            
        except (ValueError, TypeError) as e:
            messages.error(request, f'添加失败：{str(e)}')
    
    return render(request, 'erp/shipment/item/add.html', {'shipment': shipment})


def delete_shipment_item(request, shipment_id, item_id):
    """删除发货单商品明细"""
    shipment = get_object_or_404(ShipmentOrder, pk=shipment_id)
    item = get_object_or_404(ShipmentItem.objects.select_related('product'), pk=item_id, shipment_order=shipment)
    
    if request.method == 'POST':
        try:
            # 删除商品明细
            item.delete()
            
            # 如果发货单状态是到岸，重新计算头程成本
            if shipment.status == '到岸' and shipment.total_price:
                # 一次性获取剩余的商品明细
                all_items = list(ShipmentItem.objects.filter(shipment_order=shipment).select_related('product'))
                
                if all_items:
                    # 计算总体积
                    total_volume = sum(Decimal(str(i.volume)) * Decimal(str(i.quantity)) for i in all_items)
                    
                    if total_volume > 0:
                        # 提前计算单位价格系数以减少除法操作
                        price_factor = shipment.total_price / total_volume
                        
                        # 批量更新头程成本
                        for i in all_items:
                            item_volume = Decimal(str(i.volume)) * Decimal(str(i.quantity))
                            
                            if i.quantity > 0:
                                per_item_shipping_cost = (price_factor * item_volume) / Decimal(str(i.quantity))
                            else:
                                per_item_shipping_cost = Decimal('0.00')
                            
                            # 只在需要更新时才更新，避免不必要的数据库写入
                            if i.shipping_cost != per_item_shipping_cost:
                                i.shipping_cost = per_item_shipping_cost
                                i.save()
                                
                                # 更新产品的头程成本
                                product = i.product
                                if product.shipping_cost != per_item_shipping_cost:
                                    product.shipping_cost = per_item_shipping_cost.quantize(Decimal('0.01'), rounding='ROUND_HALF_UP')
                                    product.save()
            
            messages.success(request, '商品明细已删除')
            return redirect('shipment_detail', pk=shipment_id)
            
        except Exception as e:
            messages.error(request, f'删除失败：{str(e)}')
    
    return render(request, 'erp/shipment/item/delete.html', {
        'shipment': shipment,
        'item': item
    })


def import_inventory(request):
    """导入在库数据"""
    if request.method == 'POST' and request.FILES.get('file'):
        try:
            # 保存上传的文件
            uploaded_file = request.FILES['file']
            file_path = handle_uploaded_file(uploaded_file)
            
            # 读取Excel文件
            try:
                df = pd.read_excel(file_path)
            except Exception as e:
                os.remove(file_path)  # 删除临时文件
                messages.error(request, f'Excel文件读取失败: {str(e)}')
                return render(request, 'erp/inventory/import.html')
            
            # 检查必要的列是否存在
            required_columns = ['SKU', '中文名称', '店铺', '在库数量', '采购成本', '头程成本']
            if not all(col in df.columns for col in required_columns):
                os.remove(file_path)
                messages.error(request, '文件格式不正确，必须包含SKU、中文名称、在库数量、店铺、采购成本和头程成本列')
                return render(request, 'erp/inventory/import.html')
            
            # 清除现有在库数据，但保留到岸和在途数据
            preserve_query = Q(status='到岸') | Q(status='在途')
            shipment_orders_to_preserve = ShipmentOrder.objects.filter(preserve_query)
            
            # 获取所有产品
            products = Product.objects.all()
            from decimal import Decimal
            
            # 清除在库数量和货值
            for product in products:
                product.stock_in_warehouse = 0
                product.value_in_warehouse = Decimal('0.00')
                # 更新总库存和总货值
                product.stock = product.stock_arrived + product.stock_in_transit
                product.total_value = (
                    product.value_arrived + 
                    product.value_in_transit
                ).quantize(Decimal('0.01'), rounding='ROUND_HALF_UP')
                product.save()
            
            # 处理数据
            processed_products = []
            shop_cache = {}
            error_count = 0
            success_count = 0
            
            for _, row in df.iterrows():
                try:
                    sku = str(row['SKU']).strip()
                    quantity = int(row['在库数量']) if pd.notna(row['在库数量']) else 0
                    
                    if not sku or quantity <= 0:
                        continue
                    
                    # 获取店铺
                    shop_name = row['店铺'] if pd.notna(row['店铺']) else None
                    shop = None
                    
                    if shop_name:
                        # 标准化店铺名称
                        import re
                        match = re.match(r'^(\d+)号店.*$', shop_name)
                        if match:
                            standard_shop_name = f"{match.group(1)}号店"
                            if standard_shop_name in shop_cache:
                                shop = shop_cache[standard_shop_name]
                            else:
                                shop, _ = Shop.objects.get_or_create(name=standard_shop_name)
                                shop_cache[standard_shop_name] = shop
                    
                    # 处理采购成本和头程成本
                    purchase_cost = Decimal('0.00')
                    if pd.notna(row.get('采购成本')):
                        try:
                            purchase_cost = Decimal(str(row['采购成本'])).quantize(Decimal('0.01'), rounding='ROUND_HALF_UP')
                        except (ValueError, TypeError, InvalidOperation):
                            purchase_cost = Decimal('0.00')
                    
                    shipping_cost = Decimal('0.00')
                    if pd.notna(row.get('头程成本')):
                        try:
                            shipping_cost = Decimal(str(row['头程成本'])).quantize(Decimal('0.01'), rounding='ROUND_HALF_UP')
                        except (ValueError, TypeError, InvalidOperation):
                            shipping_cost = Decimal('0.00')
                    
                    # 获取或创建产品
                    try:
                        product = Product.objects.get(sku=sku)
                        
                        # 更新产品的基本信息
                        if pd.notna(row.get('中文名称')) and row['中文名称']:
                            product.chinese_name = str(row['中文名称'])
                        if shop:
                            product.shop = shop
                        
                        # 更新采购成本和头程成本
                        product.purchase_cost = purchase_cost
                        product.shipping_cost = shipping_cost
                        
                        # 更新在库数量和货值
                        product.stock_in_warehouse = quantity
                        product.value_in_warehouse = (purchase_cost + shipping_cost) * Decimal(str(quantity))
                        product.value_in_warehouse = product.value_in_warehouse.quantize(Decimal('0.01'), rounding='ROUND_HALF_UP')
                        
                        # 更新总库存和总货值
                        product.stock = product.stock_in_warehouse + product.stock_arrived + product.stock_in_transit
                        product.total_value = (
                            product.value_in_warehouse + 
                            product.value_arrived + 
                            product.value_in_transit
                        ).quantize(Decimal('0.01'), rounding='ROUND_HALF_UP')
                        
                        product.save()
                        success_count += 1
                        
                    except Product.DoesNotExist:
                        # 创建新产品
                        product = Product.objects.create(
                            sku=sku,
                            chinese_name=str(row['中文名称']) if pd.notna(row['中文名称']) else '',
                            purchase_cost=purchase_cost,
                            shipping_cost=shipping_cost,
                            shop=shop,
                            stock_in_warehouse=quantity,
                            value_in_warehouse=(purchase_cost + shipping_cost) * Decimal(str(quantity)),
                            stock=quantity,
                            total_value=(purchase_cost + shipping_cost) * Decimal(str(quantity))
                        )
                        success_count += 1
                    
                except Exception as e:
                    error_count += 1
                    messages.error(request, f'处理SKU {sku} 时出错: {str(e)}')
            
            # 删除临时文件
            if os.path.exists(file_path):
                os.remove(file_path)
            
            if error_count > 0:
                messages.warning(request, f'导入完成，成功: {success_count} 条，失败: {error_count} 条')
            else:
                messages.success(request, f'导入成功，共处理 {success_count} 条数据')
            
            return redirect('inventory_list')
            
        except Exception as e:
            messages.error(request, f'导入失败: {str(e)}')
    
    return render(request, 'erp/inventory/import.html')


def download_inventory_template(request):
    """下载库存导入模板"""
    # 创建样本数据
    sample_data = {
        'SKU': ['ABC123', 'ABC123', 'DEF456', 'GHI789', 'JKL012'],
        '中文名称': ['产品A', '产品A', '产品B', '产品C', '产品D'],
        '店铺': ['1号店', '9号店', '9号店', '12号店', '16号店'],
        '在库数量': [10, 5, 20, 30, 15],
        '采购成本': [100.00, 100.00, 200.00, 300.00, 150.00],
        '头程成本': [20.00, 20.00, 30.00, 40.00, 25.00]
    }
    
    df = pd.DataFrame(sample_data)
    
    # 创建一个HttpResponse对象，并设置内容类型为Excel文件
    response = HttpResponse(
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    response['Content-Disposition'] = 'attachment; filename=inventory_import_template.xlsx'
    
    # 将DataFrame写入Excel文件
    with pd.ExcelWriter(response, engine='xlsxwriter') as writer:
        df.to_excel(writer, sheet_name='导入模板', index=False)
        
        # 获取工作表和工作簿对象
        workbook = writer.book
        worksheet = writer.sheets['导入模板']
        
        # 添加单元格格式
        header_format = workbook.add_format({
            'bold': True,
            'bg_color': '#D9EAD3',
            'border': 1
        })
        
        # 设置列宽并应用标题格式
        for col_num, value in enumerate(df.columns.values):
            worksheet.write(0, col_num, value, header_format)
            
        worksheet.set_column('A:A', 15)  # SKU
        worksheet.set_column('B:B', 20)  # 中文名称
        worksheet.set_column('C:C', 15)  # 店铺
        worksheet.set_column('D:D', 10)  # 数量
        worksheet.set_column('E:E', 12)  # 采购成本
        worksheet.set_column('F:F', 12)  # 头程成本
        
        # 添加说明信息到新的工作表
        info_sheet = workbook.add_worksheet('说明')
        title_format = workbook.add_format({'bold': True, 'font_size': 14})
        header_format = workbook.add_format({'bold': True, 'bg_color': '#D9EAD3'})
        
        info_sheet.write('A1', '库存导入说明', title_format)
        info_sheet.write('A3', '字段', header_format)
        info_sheet.write('B3', '说明', header_format)
        info_sheet.write('A4', 'SKU')
        info_sheet.write('B4', '必填，产品的唯一标识符')
        info_sheet.write('A5', '中文名称')
        info_sheet.write('B5', '必填，产品的中文名称')
        info_sheet.write('A6', '店铺')
        info_sheet.write('B6', '必填，产品所属的店铺名称（1号店/2号店/8号店/9号店/12号店/13号店/16号店/20号店）')
        info_sheet.write('A7', '数量')
        info_sheet.write('B7', '必填，整数，导入的数量。注意：导入前会清空现有在库数据')
        info_sheet.write('A8', '采购成本')
        info_sheet.write('B8', '必填，数字，产品的采购单价')
        info_sheet.write('A9', '头程成本')
        info_sheet.write('B9', '必填，数字，产品的头程单价')
        
        info_sheet.write('A11', '特别说明:', header_format)
        info_sheet.write('A12', '1. 同一个SKU如果在多个店铺都有库存，请在Excel中分多行录入，每行对应一个店铺（如示例中的ABC123）')
        info_sheet.write('A13', '2. 导入后系统会先清空现有在库数据（到岸和在途数据不会受影响）')
        info_sheet.write('A14', '3. 确保店铺名称正确，系统将为每个店铺创建对应的库存关联')
        info_sheet.write('A15', '4. 在库货值将自动计算为: (采购成本 + 头程成本) × 数量')
        info_sheet.write('A16', '5. 请不要修改列名，保持与模板一致')
        
        # 设置说明页列宽
        info_sheet.set_column('A:A', 20)
        info_sheet.set_column('B:B', 60)
    
    return response


def export_inventory(request):
    """导出库存数据"""
    # 获取所有产品
    products = Product.objects.all().select_related('shop')
    
    # 创建Excel数据
    data = []
    for product in products:
        data.append({
            'SKU': product.sku,
            '中文名称': product.chinese_name,
            '重量': product.weight,
            '体积': product.volume,
            '店铺': product.shop.name if product.shop else '',
            '在库数量': product.stock_in_warehouse,
            '到岸数量': product.stock_arrived,
            '在途数量': product.stock_in_transit,
            '总库存': product.stock,
            '采购成本': product.purchase_cost,
            '头程成本': product.shipping_cost,
            '在库货值': product.value_in_warehouse,
            '到岸货值': product.value_arrived,
            '在途货值': product.value_in_transit,
            '总货值': product.total_value,
        })
    
    # 创建DataFrame
    df = pd.DataFrame(data)
    
    # 创建Excel响应
    response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    response['Content-Disposition'] = 'attachment; filename=inventory_export.xlsx'
    
    # 导出Excel
    df.to_excel(response, index=False)
    
    return response


def export_inventory_stats(request):
    """导出库存统计表"""
    from django.db.models import Sum, Value, F, DecimalField
    from django.db.models.functions import Coalesce
    from decimal import Decimal
    
    # 创建响应对象
    response = HttpResponse(content_type='text/csv')
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    response['Content-Disposition'] = f'attachment; filename="库存统计表_{timestamp}.csv"'
    
    # 设置CSV写入器，指定UTF-8编码并添加BOM头
    response.write(u'\ufeff'.encode('utf-8'))
    writer = csv.writer(response)
    
    # 写入表头
    writer.writerow([
        '店铺',
        '在库数量',
        '在库货值',
        '到岸数量',
        '到岸货值',
        '在途数量',
        '在途货值',
        '总数量',
        '总货值'
    ])
    
    # 获取所有店铺的统计数据
    shops = Shop.objects.filter(name__regex=r'^[0-9]+号店$').annotate(
        stock_in_warehouse=Coalesce(Sum('product__stock_in_warehouse'), Value(0)),
        value_in_warehouse=Coalesce(Sum('product__value_in_warehouse'), Value(Decimal('0.00'), output_field=DecimalField())),
        stock_arrived=Coalesce(Sum('product__stock_arrived'), Value(0)),
        value_arrived=Coalesce(Sum('product__value_arrived'), Value(Decimal('0.00'), output_field=DecimalField())),
        stock_in_transit=Coalesce(Sum('product__stock_in_transit'), Value(0)),
        value_in_transit=Coalesce(Sum('product__value_in_transit'), Value(Decimal('0.00'), output_field=DecimalField()))
    )
    
    # 初始化总计
    total_stats = {
        'warehouse_qty': 0,
        'warehouse_value': Decimal('0.00'),
        'arrived_qty': 0,
        'arrived_value': Decimal('0.00'),
        'transit_qty': 0,
        'transit_value': Decimal('0.00')
    }
    
    # 写入每个店铺的数据
    for shop in shops:
        # 计算店铺总数和总值
        total_qty = shop.stock_in_warehouse + shop.stock_arrived + shop.stock_in_transit
        total_value = shop.value_in_warehouse + shop.value_arrived + shop.value_in_transit
        
        writer.writerow([
            shop.name,
            shop.stock_in_warehouse,
            f"¥ {shop.value_in_warehouse:.2f}",
            shop.stock_arrived,
            f"¥ {shop.value_arrived:.2f}",
            shop.stock_in_transit,
            f"¥ {shop.value_in_transit:.2f}",
            total_qty,
            f"¥ {total_value:.2f}"
        ])
        
        # 累加到总计
        total_stats['warehouse_qty'] += shop.stock_in_warehouse
        total_stats['warehouse_value'] += shop.value_in_warehouse
        total_stats['arrived_qty'] += shop.stock_arrived
        total_stats['arrived_value'] += shop.value_arrived
        total_stats['transit_qty'] += shop.stock_in_transit
        total_stats['transit_value'] += shop.value_in_transit
    
    # 写入合计行
    total_qty = total_stats['warehouse_qty'] + total_stats['arrived_qty'] + total_stats['transit_qty']
    total_value = total_stats['warehouse_value'] + total_stats['arrived_value'] + total_stats['transit_value']
    
    writer.writerow([
        '合计',
        total_stats['warehouse_qty'],
        f"¥ {total_stats['warehouse_value']:.2f}",
        total_stats['arrived_qty'],
        f"¥ {total_stats['arrived_value']:.2f}",
        total_stats['transit_qty'],
        f"¥ {total_stats['transit_value']:.2f}",
        total_qty,
        f"¥ {total_value:.2f}"
    ])
    
    return response
