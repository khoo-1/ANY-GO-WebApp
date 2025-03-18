# filepath: /C:/Users/khoo_/Desktop/ANY-GO-WebApp/erp/views.py
from django.shortcuts import render, redirect, get_object_or_404
from django.db.models import Q
from django.core.paginator import Paginator
from django.http import HttpResponse, JsonResponse
from .forms import ProductForm, ShipmentOrderForm
from .models import Product, Inventory, PackingList, PackingListItem, ShipmentOrder, ShipmentItem, Shop
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
import datetime
import uuid
from django.db.models import Sum, F, DecimalField, Count, Case, When, Q, Value
from django.db.models.functions import Coalesce

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
            | Q(price__icontains=query)
            | Q(category__icontains=query)
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
    
    return render(request, "erp/product_list.html", {
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
            '价格': str(product.price),
            '类别': product.category,
            '重量': str(product.weight),
            '体积': product.volume,
            '在库数量': product.stock_in_warehouse,
            '到岸数量': product.stock_arrived,
            '在途数量': product.stock_in_transit,
            '总库存': product.stock,
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
    return render(request, "erp/product_detail.html", {"product": product})


def add_product(request):
    if request.method == "POST":
        form = ProductForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            return redirect("product_list")
    else:
        form = ProductForm()
    return render(request, "erp/add_product.html", {"form": form})


def bulk_upload(request):
    """批量上传视图"""
    if request.method == 'POST' and request.FILES.get('file'):
        try:
            # 保存上传的文件
            uploaded_file = request.FILES['file']
            file_path = handle_uploaded_file(uploaded_file)
            
            # 读取Excel文件
            df = pd.read_excel(file_path)
            
            # 检查必要的列是否存在
            required_columns = ['SKU', '中文名称', '价格', '类别', '重量', '体积', '店铺']
            if not all(col in df.columns for col in required_columns):
                if os.path.exists(file_path):
                    os.remove(file_path)
                messages.error(request, '文件格式不正确，缺少必要的列')
                return redirect('bulk_upload')
            
            # 去除空行
            df = df.dropna(subset=['SKU'], how='any')
            
            # 处理数据
            from decimal import Decimal
            total_records = 0
            
            # 获取或创建店铺
            shop_cache = {}  # 缓存店铺对象
            
            for _, row in df.iterrows():
                try:
                    # 获取店铺
                    shop_name = row['店铺'] if pd.notna(row['店铺']) else None
                    shop = None
                    
                    if shop_name:
                        if shop_name in shop_cache:
                            shop = shop_cache[shop_name]
                        else:
                            shop, _ = Shop.objects.get_or_create(name=shop_name)
                            shop_cache[shop_name] = shop
                    
                    # 获取或创建产品
                    sku = row['SKU']
                    price = Decimal(str(row['价格'])) if pd.notna(row['价格']) else Decimal('0.00')
                    
                    defaults = {
                        'chinese_name': row['中文名称'] if pd.notna(row['中文名称']) else '',
                        'price': price.quantize(Decimal('0.01'), rounding='ROUND_HALF_UP'),
                        'category': row['类别'] if pd.notna(row['类别']) else '普货',
                        'weight': Decimal(str(row['重量'])).quantize(Decimal('0.01'), rounding='ROUND_HALF_UP') if pd.notna(row['重量']) else Decimal('0.00'),
                        'volume': str(row['体积']) if pd.notna(row['体积']) else '',
                        'shop': shop
                    }
                    
                    # 查找或创建产品
                    product, created = Product.objects.get_or_create(sku=sku, defaults=defaults)
                    
                    # 如果产品已存在，更新字段
                    if not created:
                        for key, value in defaults.items():
                            setattr(product, key, value)
                        product.save()
                    
                    records_count = 1
                    total_records = total_records + records_count
                    
                except Exception as e:
                    messages.warning(request, f'处理SKU {row.get("SKU", "未知")}时出错: {str(e)}')
            
            # 删除临时文件
            if os.path.exists(file_path):
                os.remove(file_path)
            
            messages.success(request, f'成功导入/更新 {total_records} 个产品')
            return redirect('product_list')
            
        except Exception as e:
            messages.error(request, f'文件处理失败: {str(e)}')
    
    return render(request, 'erp/bulk_upload.html')


def clear_all_data(request):
    """清除所有数据"""
    if request.method == "POST":
        # 清除所有发货单项目
        ShipmentItem.objects.all().delete()
        # 清除所有发货单
        ShipmentOrder.objects.all().delete()
        # 清除所有装箱单项目
        PackingListItem.objects.all().delete()
        # 清除所有装箱单
        PackingList.objects.all().delete()
        # 清除所有产品
        Product.objects.all().delete()
        # 清除所有库存
        Inventory.objects.all().delete()

        messages.success(request, "所有数据已成功清除")
        return redirect("product_list")

    return render(request, "erp/clear_data.html")


# 为了保持向后兼容性，保留bulk_product_upload函数但复用bulk_upload的逻辑
def bulk_product_upload(request):
    return bulk_upload(request)


def save_bulk_upload(request):
    if request.method == "POST":
        data = json.loads(request.POST["data"])
        df = pd.DataFrame(data)

        # 装箱单名称
        packing_list_name = "批量上传装箱单"

        # 检查是否已存在同名的装箱单，如果存在则删除
        existing_packing_list = PackingList.objects.filter(name=packing_list_name)
        if existing_packing_list.exists():
            print(f"发现同名装箱单: {packing_list_name}，将删除旧数据")
            existing_packing_list.delete()
            print(f"已删除同名装箱单: {packing_list_name}")

        # 创建一个新的 PackingList 实例
        packing_list = PackingList.objects.create(
            name=packing_list_name,
            total_boxes=0,
            total_weight=0.0,
            total_volume=0.0,
            total_side_plus_one_volume=0.0,
            total_items=len(df),
            type="批量上传",
            total_price=0.0,
        )
        
        for index, row in df.iterrows():
            try:
                # 尝试获取现有产品
                product = Product.objects.get(sku=row["sku"])
                # 更新所有字段
                product.chinese_name = row["中文名称"]
                product.price = float(row["价格"]) if row["价格"] else 0.0
                product.category = row["类别"]
                product.weight = float(row["重量"]) if row["重量"] else 0.0
                product.volume = float(row["体积"]) if row["体积"] else 0.0
                product.stock = int(row["库存"]) if row["库存"] else 0
            except Product.DoesNotExist:
                # 如果产品不存在，创建新产品
                product = Product(
                    sku=row["sku"],
                    chinese_name=row["中文名称"],
                    price=float(row["价格"]) if row["价格"] else 0.0,
                    category=row["类别"],
                    weight=float(row["重量"]) if row["重量"] else 0.0,
                    volume=float(row["体积"]) if row["体积"] else 0.0,
                    stock=int(row["库存"]) if row["库存"] else 0,
                )
            
            # 保存产品
            product.save()

            # 创建装箱单项目
            PackingListItem.objects.create(
                packing_list=packing_list,
                product=product,
                quantity=int(row["数量"]) if row["数量"] else 0,
            )
        
        return redirect("packing_list")

    return HttpResponse("无效的请求方法")


def edit_product(request, pk):
    # 获取要编辑的产品对象，如果不存在则返回404错误
    product = get_object_or_404(Product, pk=pk)
    
    if request.method == "POST":
        # 如果请求方法是POST，表示表单已提交
        form = ProductForm(request.POST, request.FILES, instance=product)
        if form.is_valid():
            # 如果表单数据有效，保存表单数据
            form.save()
            # 保存成功后重定向到产品列表页面
            return redirect("product_list")
    else:
        # 如果请求方法不是POST，表示是GET请求，显示表单
        form = ProductForm(instance=product)
    
    # 渲染编辑产品页面，并传递表单对象
    return render(request, "erp/edit_product.html", {"form": form})


def delete_product(request, pk):
    product = get_object_or_404(Product, pk=pk)
    if request.method == "POST":
        product.delete()
        return redirect("product_list")
    return render(request, "erp/delete_product.html", {"product": product})


def inventory_list(request):
    """库存列表视图"""
    # 获取查询参数
    shop_id = request.GET.get('shop', '')
    sku = request.GET.get('sku', '')
    chinese_name = request.GET.get('chinese_name', '')
    category = request.GET.get('category', '')
    
    # 基础查询
    products = Product.objects.all().select_related('shop')
    
    # 应用筛选条件
    if shop_id:
        products = products.filter(shop_id=shop_id)
    if sku:
        products = products.filter(sku__icontains=sku)
    if chinese_name:
        products = products.filter(chinese_name__icontains=chinese_name)
    if category and category != 'all':
        products = products.filter(category=category)
    
    # 统计和汇总数据
    from decimal import Decimal
    
    # 初始化汇总变量
    total_in_warehouse_quantity = 0
    total_in_warehouse_value = Decimal('0.00')
    total_arrived_quantity = 0
    total_arrived_value = Decimal('0.00')
    total_in_transit_quantity = 0
    total_in_transit_value = Decimal('0.00')
    
    # 按库存状态统计
    in_stock_stats = {
        'total_quantity': sum(p.stock_in_warehouse for p in products),
        'total_value': sum(p.value_in_warehouse for p in products),
    }
    
    arrived_stats = {
        'total_quantity': sum(p.stock_arrived for p in products),
        'total_value': sum(p.value_arrived for p in products),
    }
    
    transit_stats = {
        'total_quantity': sum(p.stock_in_transit for p in products),
        'total_value': sum(p.value_in_transit for p in products),
    }
    
    # 汇总数据
    total_in_warehouse_quantity = total_in_warehouse_quantity + in_stock_stats['total_quantity']
    total_in_warehouse_value = total_in_warehouse_value + Decimal(str(in_stock_stats['total_value']))
    total_arrived_quantity = total_arrived_quantity + arrived_stats['total_quantity']
    total_arrived_value = total_arrived_value + Decimal(str(arrived_stats['total_value']))
    total_in_transit_quantity = total_in_transit_quantity + transit_stats['total_quantity']
    total_in_transit_value = total_in_transit_value + Decimal(str(transit_stats['total_value']))
    
    # 计算总量
    total_quantity = total_in_warehouse_quantity + total_arrived_quantity + total_in_transit_quantity
    total_value = total_in_warehouse_value + total_arrived_value + total_in_transit_value
    
    # 分页处理
    paginator = Paginator(products, 1000)  # 每页显示1000条
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)
    
    # 准备上下文数据
    context = {
        'page_obj': page_obj,
        'shops': Shop.objects.all(),
        'selected_shop': shop_id,
        'sku': sku,
        'chinese_name': chinese_name,
        'category': category,
        'categories': [('普货', '普货'), ('纺织', '纺织'), ('混装', '混装')],
        'stats': {
            'in_warehouse': {
                'quantity': total_in_warehouse_quantity,
                'value': total_in_warehouse_value,
            },
            'arrived': {
                'quantity': total_arrived_quantity,
                'value': total_arrived_value,
            },
            'in_transit': {
                'quantity': total_in_transit_quantity,
                'value': total_in_transit_value,
            },
            'total': {
                'quantity': total_quantity,
                'value': total_value,
            }
        }
    }
    
    return render(request, 'erp/inventory_list.html', context)


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


def process_packing_list(df):
    # 初始化变量
    total_boxes = 0
    total_weight = 0.0
    total_volume = 0.0
    total_side_volume = 0.0
    total_items = 0
    packing_type = "普货"  # 默认值
    total_price = 0.0

    try:
        # 读取基础信息
        total_boxes = int(df.iloc[0, 1]) if pd.notna(df.iloc[0, 1]) else 0  # B1: 总箱数
        
        # 读取类型 (D1)
        type_value = df.iloc[0, 3]  # D1: 类型
        if pd.notna(type_value):
            if isinstance(type_value, str):
                packing_type = type_value
            elif isinstance(type_value, (int, float)):
                # 如果是数字，尝试在其他位置查找类型信息
                for i in range(5):
                    for j in range(5):
                        cell_value = df.iloc[i, j]
                        if isinstance(cell_value, str) and cell_value in ["普货", "纺织", "混装"]:
                            packing_type = cell_value
                            break
        
        # 读取其他基础信息
        total_weight = float(df.iloc[1, 1]) if pd.notna(df.iloc[1, 1]) else 0.0  # B2: 总重量
        total_volume = float(df.iloc[2, 1]) if pd.notna(df.iloc[2, 1]) else 0.0  # B3: 总体积
        total_side_volume = float(df.iloc[3, 1]) if pd.notna(df.iloc[3, 1]) else 0.0  # B4: 总边加一体积
        
        # 读取总件数 (B6)
        # 首先尝试直接读取B6
        total_items_value = df.iloc[5, 1]
        if pd.notna(total_items_value):
            if isinstance(total_items_value, (int, float)):
                total_items = int(total_items_value)
            else:
                # 如果B6不是数字，尝试在周围单元格查找
                for i in range(4, 7):  # 搜索第5-7行
                    for j in range(1, 3):  # 搜索B-C列
                        cell_value = df.iloc[i, j]
                        if isinstance(cell_value, (int, float)) and cell_value > 0:
                            total_items = int(cell_value)
                            break
        
        # 读取总价格 (D2)
        total_price = float(df.iloc[1, 3]) if pd.notna(df.iloc[1, 3]) else 0.0  # D2: 总价格

        # 打印调试信息
        print(f"总箱数 (B1): {df.iloc[0, 1]}, 实际使用: {total_boxes}, 类型: {type(df.iloc[0, 1])}")
        print(f"类型 (D1): {type_value}, 实际使用: {packing_type}, 类型: {type(type_value)}")
        print(f"总重量 (B2): {df.iloc[1, 1]}, 实际使用: {total_weight}, 类型: {type(df.iloc[1, 1])}")
        print(f"总体积 (B3): {df.iloc[2, 1]}, 实际使用: {total_volume}, 类型: {type(df.iloc[2, 1])}")
        print(f"总边加一体积 (B4): {df.iloc[3, 1]}, 实际使用: {total_side_volume}, 类型: {type(df.iloc[3, 1])}")
        print(f"总件数 (B6): {total_items_value}, 实际使用: {total_items}, 类型: {type(total_items_value)}")
        print(f"总价格 (D2): {df.iloc[1, 3]}, 实际使用: {total_price}, 类型: {type(df.iloc[1, 3])}")

    except Exception as e:
        print(f"读取基础信息时出错: {str(e)}")
        # 使用默认值继续处理

    return {
        "total_boxes": total_boxes,
        "total_weight": total_weight,
        "total_volume": total_volume,
        "total_side_volume": total_side_volume,
        "total_items": total_items,
        "packing_type": packing_type,
        "total_price": total_price
    }


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
                            price=0.0,
                            category=packing_list.type,
                            weight=0.0,
                            volume=0.0,
                            stock=0,
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
                return render(request, 'erp/shipment_import.html', {
                    'shops': Shop.objects.all()
                })
            
            # 检查批次号是否已存在
            if ShipmentOrder.objects.filter(batch_number=batch_number).exists():
                messages.error(request, f'批次号 {batch_number} 已存在')
                return render(request, 'erp/shipment_import.html', {
                    'shops': Shop.objects.all()
                })
            
            # 验证上传的文件
            if not request.FILES.get('file'):
                messages.error(request, '请选择要上传的Excel文件')
                return render(request, 'erp/shipment_import.html', {
                    'shops': Shop.objects.all()
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
                return render(request, 'erp/shipment_import.html', {
                    'shops': Shop.objects.all()
                })
            
            # 验证必要的列是否存在
            required_columns = ['SKU', '数量', '采购成本', '体积']
            if not all(col in df.columns for col in required_columns):
                if os.path.exists(file_path):
                    os.remove(file_path)
                messages.error(request, '文件格式不正确，请使用正确的模板')
                return render(request, 'erp/shipment_import.html', {
                    'shops': Shop.objects.all()
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
        
            # 处理每一行数据
            for _, row in df.iterrows():
                sku = row['SKU']
                quantity = int(row['数量'])
                purchase_cost = Decimal(str(row['采购成本'])).quantize(Decimal('0.01'), rounding='ROUND_HALF_UP')
                volume = Decimal(str(row['体积'])).quantize(Decimal('0.01'), rounding='ROUND_HALF_UP')
                
                # 从缓存中获取产品或创建
                if sku in product_cache:
                    product = product_cache[sku]
                else:
                    # 获取或创建产品
                    product, created = Product.objects.get_or_create(
                        sku=sku,
                        defaults={
                            'chinese_name': row.get('中文名称', ''),
                            'price': purchase_cost,
                            'volume': str(volume),
                            'shop': shop  # 设置店铺关联
                        }
                    )
                    product_cache[sku] = product
                
                # 更新产品的在途库存和货值
                product.stock_in_transit = product.stock_in_transit + quantity
                
                # 确保使用Decimal进行计算
                quantity_decimal = Decimal(str(quantity))
                value_addition = purchase_cost * quantity_decimal
                product.value_in_transit = product.value_in_transit + value_addition
                product.value_in_transit = product.value_in_transit.quantize(Decimal('0.01'), rounding='ROUND_HALF_UP')
                
                if product not in updated_products:
                    updated_products.append(product)
                
                # 添加到批量创建列表
                shipment_items.append(
                    ShipmentItem(
                        shipment_order=shipment,
                        product=product,
                        quantity=quantity,
                        purchase_cost=purchase_cost,
                        volume=volume
                    )
                )
                
                # 每50个创建一次，减少内存占用
                if len(shipment_items) >= 50:
                    ShipmentItem.objects.bulk_create(shipment_items)
                    shipment_items = []
            
            # 创建剩余的项目
            if shipment_items:
                ShipmentItem.objects.bulk_create(shipment_items)
            
            # 更新产品的在途库存和货值
            for product in updated_products:
                product.save()
            
            # 删除临时文件
            if os.path.exists(file_path):
                os.remove(file_path)
            
            messages.success(request, f'发货单 {batch_number} 导入成功')
            return redirect('shipment_detail', pk=shipment.id)
            
        except Exception as e:
            # 确保临时文件被删除
            if 'file_path' in locals() and os.path.exists(file_path):
                os.remove(file_path)
            messages.error(request, f'导入失败: {str(e)}')
    
    return render(request, 'erp/shipment_import.html', {
        'shops': Shop.objects.all()
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
    
    return render(request, 'erp/shipment_list.html', {
        'page_obj': page_obj,
        'query': query
    })


def shipment_detail(request, pk):
    """发货单详情"""
    shipment = get_object_or_404(ShipmentOrder.objects.select_related('shop'), pk=pk)
    items = shipment.items.select_related('product').all()
    return render(request, 'erp/shipment_detail.html', {
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
                return render(request, 'erp/change_shipment_status.html', {'shipment': shipment})
            
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
    
    return render(request, 'erp/change_shipment_status.html', {'shipment': shipment})


def delete_shipment(request, pk):
    """删除发货单"""
    shipment = get_object_or_404(ShipmentOrder, pk=pk)
    if request.method == 'POST':
        shipment.delete()
        messages.success(request, '发货单已删除')
        return redirect('shipment_list')
    return render(request, 'erp/delete_shipment.html', {'shipment': shipment})


def inventory_edit(request, pk):
    """编辑库存视图"""
    inventory = get_object_or_404(Inventory, pk=pk)
    if request.method == "POST":
        inventory.stock = request.POST.get("stock")
        inventory.save()
        messages.success(request, "库存更新成功")
        return redirect("inventory_list")
    return render(request, "erp/inventory_edit.html", {"inventory": inventory})


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
    
    return render(request, 'erp/rollback_shipment_status.html', {'shipment': shipment})


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
    
    return render(request, 'erp/edit_shipment_item.html', {
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
                return render(request, 'erp/add_shipment_item.html', {'shipment': shipment})
            
            # 获取或创建产品
            product, created = Product.objects.get_or_create(
                sku=sku,
                defaults={
                    'chinese_name': chinese_name,
                    'price': purchase_cost,
                    'volume': str(volume)
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
    
    return render(request, 'erp/add_shipment_item.html', {'shipment': shipment})


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
    
    return render(request, 'erp/delete_shipment_item.html', {
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
                return render(request, 'erp/import_inventory.html')
            
            # 检查必要的列是否存在
            required_columns = ['SKU', '中文名称', '在库数量', '店铺']
            if not all(col in df.columns for col in required_columns):
                os.remove(file_path)
                messages.error(request, '文件格式不正确，必须包含SKU、中文名称、在库数量和店铺列')
                return render(request, 'erp/import_inventory.html')
            
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
                product.save()
            
            # 处理数据
            processed_products = []
            shop_cache = {}
            
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
                        if shop_name in shop_cache:
                            shop = shop_cache[shop_name]
                        else:
                            shop, _ = Shop.objects.get_or_create(name=shop_name)
                            shop_cache[shop_name] = shop
                    
                    # 获取或创建产品
                    product = None
                    try:
                        product = Product.objects.get(sku=sku)
                    except Product.DoesNotExist:
                        # 创建新产品
                        product = Product(
                            sku=sku,
                            chinese_name=row['中文名称'] if pd.notna(row['中文名称']) else '',
                            price=Decimal(str(row['价格'])).quantize(Decimal('0.01'), rounding='ROUND_HALF_UP') if pd.notna(row['价格']) else Decimal('0.00'),
                            category=row['类别'] if pd.notna(row['类别']) else '普货',
                            weight=Decimal(str(row['重量'])).quantize(Decimal('0.01'), rounding='ROUND_HALF_UP') if pd.notna(row['重量']) else Decimal('0.00'),
                            volume=str(row['体积']) if pd.notna(row['体积']) else '',
                            shop=shop
                        )
                        product.save()
                    
                    # 更新产品在库数量和货值
                    val = quantity
                    product.stock_in_warehouse = product.stock_in_warehouse + int(val)
                    
                    # 计算在库货值
                    product.value_in_warehouse = Decimal(str(row['价格'])) * product.stock_in_warehouse
                    
                    # 设置店铺
                    if shop and not product.shop:
                        product.shop = shop
                    
                    # 保存产品
                    product.save()
                    
                    # 添加到已处理列表
                    if product not in processed_products:
                        processed_products.append(product)
                    
                except Exception as e:
                    messages.warning(request, f'处理SKU {sku}时出错: {str(e)}')
            
            # 更新所有处理过的产品的总库存和总货值
            for product in processed_products:
                # 重新计算总库存
                product.stock = product.stock_in_warehouse + product.stock_arrived + product.stock_in_transit
                
                # 重新计算总货值，确保使用Decimal
                warehouse_value = Decimal(str(product.value_in_warehouse))
                arrived_value = Decimal(str(product.value_arrived))
                transit_value = Decimal(str(product.value_in_transit))
                
                product.total_value = warehouse_value + arrived_value + transit_value
                product.save()
            
            # 删除临时文件
            if os.path.exists(file_path):
                os.remove(file_path)
            
            messages.success(request, f'成功导入 {len(processed_products)} 个产品的在库数据')
            return redirect('inventory_list')
            
        except Exception as e:
            # 确保临时文件被删除
            if 'file_path' in locals() and os.path.exists(file_path):
                os.remove(file_path)
            messages.error(request, f'导入失败: {str(e)}')
    
    return render(request, 'erp/import_inventory.html')


def download_inventory_template(request):
    """下载库存导入模板"""
    # 创建样本数据
    sample_data = {
        'SKU': ['ABC123', 'ABC123', 'DEF456', 'GHI789', 'JKL012'],
        '中文名称': ['产品A', '产品A', '产品B', '产品C', '产品D'],
        '店铺': ['1号店', '9号店', '9号店', '12号店', '16号店'],
        '数量': [10, 5, 20, 30, 15],
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
            '价格': product.price,
            '类别': product.category,
            '重量': product.weight,
            '体积': product.volume,
            '店铺': product.shop.name if product.shop else '',
            '在库数量': product.stock_in_warehouse,
            '到岸数量': product.stock_arrived,
            '在途数量': product.stock_in_transit,
            '总库存': product.stock,
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
