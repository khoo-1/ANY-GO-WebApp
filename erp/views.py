# filepath: /C:/Users/khoo_/Desktop/ANY-GO-WebApp/erp/views.py
from django.shortcuts import render, redirect, get_object_or_404
from django.db.models import Q
from django.core.paginator import Paginator
from django.http import HttpResponse, JsonResponse
from .forms import ProductForm
from .models import Product, Inventory, PackingList, PackingListItem
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


def product_list(request):
    query = request.GET.get("q")
    if query:
        products = Product.objects.filter(
            Q(sku__icontains=query)
            | Q(chinese_name__icontains=query)
            | Q(price__icontains=query)
            | Q(category__icontains=query)
            | Q(weight__icontains=query)
            | Q(volume__icontains=query)
        ).order_by(
            "id"
        )  # 添加排序
    else:
        products = Product.objects.all().order_by("id")  # 添加排序
    
    paginator = Paginator(products, 100)  # 每页显示100个产品
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)
    
    return render(request, "erp/product_list.html", {"page_obj": page_obj})


def export_products(request):
    # 获取所有产品
    products = Product.objects.all().values(
        "sku",
        "chinese_name",
        "price",
        "category",
        "weight",
        "volume",
        "stock",
        "shipping_cost",
        "total_value"
    )
    
    # 创建一个 DataFrame，并指定列名
    df = pd.DataFrame(products)
    df.columns = [
        "SKU",
        "中文名称",
        "价格",
        "类别",
        "重量",
        "体积",
        "库存",
        "头程成本",
        "总货值"
    ]
    
    # 创建一个 HttpResponse 对象，并设置内容类型为 Excel 文件
    response = HttpResponse(
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
    response["Content-Disposition"] = "attachment; filename=products.xlsx"
    
    # 将 DataFrame 写入 Excel 文件
    with pd.ExcelWriter(response, engine="xlsxwriter") as writer:
        df.to_excel(writer, sheet_name="Products", index=False)
    
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
    if request.method == "POST" and request.FILES.get("file"):
        try:
            # 保存上传的文件
            uploaded_file = request.FILES["file"]
            file_path = handle_uploaded_file(uploaded_file)
            
            # 读取Excel文件
            xls = pd.ExcelFile(file_path)
            
            # 获取所有sheet名称
            sheet_names = [name for name in xls.sheet_names if name != "常用箱规"]
            
            total_records = 0
            
            # 处理每个sheet
            for sheet_name in sheet_names:
                try:
                    # 读取当前sheet
                    df = pd.read_excel(file_path, sheet_name=sheet_name)
                    
                    # 使用新的函数处理装箱单基础信息
                    packing_info = process_packing_list(df)
                    
                    # 从文件名中提取店铺信息
                    shop_info = extract_shop_info_from_filename(uploaded_file.name)
                    
                    # 生成装箱单名称
                    packing_list_name = generate_packing_list_name(shop_info, packing_info["packing_type"])
                    
                    print("原始数据:")
                    print(f"  总箱数 (B1): {packing_info['total_boxes']}")
                    print(f"  类型 (D1): {packing_info['packing_type']}")
                    print(f"  总重量 (B2): {packing_info['total_weight']}")
                    print(f"  总体积 (B3): {packing_info['total_volume']}")
                    print(f"  总边加一体积 (B4): {packing_info['total_side_volume']}")
                    print(f"  总件数 (B6): {packing_info['total_items']}")
                    print(f"  总价格 (D2): {packing_info['total_price']}")
                    
                    print("创建装箱单，数据如下:")
                    print(f"  名称: {packing_list_name}")
                    print(f"  总箱数: {packing_info['total_boxes']}")
                    print(f"  总重量: {packing_info['total_weight']}")
                    print(f"  总体积: {packing_info['total_volume']}")
                    print(f"  总边加一体积: {packing_info['total_side_volume']}")
                    print(f"  总件数: {packing_info['total_items']}")
                    print(f"  类型: {packing_info['packing_type']}")
                    print(f"  总价格: {packing_info['total_price']}")
                    
                    # 创建装箱单
                    packing_list = PackingList.objects.create(
                        name=packing_list_name,
                        total_boxes=packing_info["total_boxes"],
                        total_weight=packing_info["total_weight"],
                        total_volume=packing_info["total_volume"],
                        total_side_volume=packing_info["total_side_volume"],
                        total_items=packing_info["total_items"],
                        type=packing_info["packing_type"],
                        total_price=packing_info["total_price"]
                    )
                    
                    print(f"创建装箱单成功: {packing_list_name}")
                    
                    # 处理SKU数据
                    records = process_sku_data(df, packing_list)
                    total_records += records
                    
                    print(f"成功创建装箱单: {packing_list_name}，包含{records}个产品")
                    
                except Exception as e:
                    print(f"处理sheet {sheet_name}时出错: {str(e)}")
                    continue
            
            # 删除临时文件
            os.remove(file_path)
            print(f"删除临时文件: {file_path}")
            
            messages.success(request, f"导入成功：共导入{total_records}条记录")
            return redirect("packing_list")
            
        except Exception as e:
            messages.error(request, f"导入失败：{str(e)}")
            return redirect("packing_list")
    
    return render(request, "erp/bulk_upload.html")


# 添加清除所有数据库的函数
def clear_all_data(request):
    if request.method == "POST":
        # 清除所有装箱单项目
        PackingListItem.objects.all().delete()
        # 清除所有装箱单
        PackingList.objects.all().delete()
        # 清除所有产品
        Product.objects.all().delete()
        # 清除所有库存
        Inventory.objects.all().delete()

        messages.success(request, "所有数据已成功清除")
        return redirect("packing_list")

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
    inventories = Inventory.objects.all()
    return render(request, "erp/inventory_list.html", {"inventories": inventories})


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
