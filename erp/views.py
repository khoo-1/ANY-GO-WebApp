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
        excel_file = request.FILES["file"]

        # 检查文件类型
        if not excel_file.name.endswith((".xls", ".xlsx")):
            messages.error(request, "请上传Excel文件(.xls或.xlsx格式)")
            return render(request, "erp/bulk_upload.html")

        # 生成唯一的临时文件名，避免文件名冲突
        import uuid
        import time

        unique_filename = f"{uuid.uuid4().hex}_{int(time.time())}_{excel_file.name}"

        upload_dir = "uploads"
        if not os.path.exists(upload_dir):
            os.makedirs(upload_dir)
        file_path = os.path.join(upload_dir, unique_filename)
        
        # 保存上传的文件
        with open(file_path, "wb+") as destination:
            for chunk in excel_file.chunks():
                destination.write(chunk)

        try:
            # 读取Excel文件
            xl = None
            df_dict = {}
            try:
                xl = pd.ExcelFile(file_path)
                # 跳过"常用箱规"sheet
                sheet_names = [sheet for sheet in xl.sheet_names if sheet != "常用箱规"]

                if not sheet_names:
                    messages.error(request, "Excel文件中没有有效的sheet")
                    return render(request, "erp/bulk_upload.html")

                # 预先读取所有sheet到字典中，然后关闭ExcelFile对象
                for sheet_name in sheet_names:
                    df_dict[sheet_name] = pd.read_excel(
                        file_path, sheet_name=sheet_name
                    )
            finally:
                # 确保ExcelFile对象被关闭
                if xl is not None:
                    xl.close()

            success_count = 0
            error_count = 0

            # 处理每个sheet（每个sheet代表一个装箱单）
            for sheet_name, df in df_dict.items():
                try:
                    # 获取B1单元格（总箱数）- 确保正确读取
                    total_boxes = 0
                    if df.shape[0] > 0 and df.shape[1] > 1:
                        # 从图片看，B1单元格是总箱数，值为6
                        total_boxes_value = df.iloc[0, 1]
                        if pd.notna(total_boxes_value):
                            if isinstance(total_boxes_value, (int, float)):
                                total_boxes = int(total_boxes_value)
                            elif (
                                isinstance(total_boxes_value, str)
                                and total_boxes_value.strip().isdigit()
                            ):
                                total_boxes = int(total_boxes_value.strip())

                        # 如果读取失败或值为0，尝试查找包含"总箱数"的单元格
                        if total_boxes == 0:
                            for row_idx in range(0, min(5, df.shape[0])):
                                for col_idx in range(0, min(5, df.shape[1])):
                                    if row_idx < df.shape[0] and col_idx < df.shape[1]:
                                        cell_value = df.iloc[row_idx, col_idx]
                                        if (
                                            isinstance(cell_value, str)
                                            and "总箱数" in cell_value
                                        ):
                                            # 找到了"总箱数"字样，检查右侧单元格
                                            if col_idx + 1 < df.shape[1]:
                                                val = df.iloc[row_idx, col_idx + 1]
                                                if (
                                                    isinstance(val, (int, float))
                                                    and val > 0
                                                ):
                                                    total_boxes = int(val)
                                                    print(
                                                        f"在第{row_idx+1}行第{col_idx+2}列找到总箱数: {total_boxes}"
                                                    )
                                                    break
                                if total_boxes > 0:
                                    break

                        print(
                            f"总箱数 (B1): {total_boxes_value}, 实际使用: {total_boxes}, 类型: {type(total_boxes_value)}"
                        )

                    # 获取D1单元格（类型）- 确保正确读取
                    packing_type = "普货"  # 默认值
                    if df.shape[0] > 0 and df.shape[1] > 3:
                        # 从图片看，D1单元格是"纺织"
                        type_value = df.iloc[0, 3]
                        if pd.notna(type_value):
                            type_str = str(type_value).strip()
                            # 直接检查是否为标准类型
                            if type_str in ["普货", "纺织", "混装"]:
                                packing_type = type_str
                            # 检查是否包含关键字
                            elif "纺" in type_str or "织" in type_str:
                                packing_type = "纺织"
                            elif "混" in type_str:
                                packing_type = "混装"

                        # 如果仍未找到，尝试查找包含"类型"的单元格
                        if packing_type == "普货":
                            # 从图片看，类型在C1单元格，值为"类型"
                            if df.shape[0] > 0 and df.shape[1] > 2:
                                cell_value = df.iloc[0, 2]
                                if isinstance(cell_value, str) and "类型" in cell_value:
                                    # 找到了"类型"字样，检查右侧单元格
                                    if 3 < df.shape[1]:
                                        val = df.iloc[0, 3]
                                        if isinstance(val, str):
                                            val_str = str(val).strip()
                                            if val_str in ["普货", "纺织", "混装"]:
                                                packing_type = val_str
                                                print(
                                                    f"在第1行D列找到类型: {packing_type}"
                                                )
                                            elif "纺" in val_str or "织" in val_str:
                                                packing_type = "纺织"
                                                print(
                                                    f"在第1行D列找到类型关键字: {packing_type}"
                                                )
                                            elif "混" in val_str:
                                                packing_type = "混装"
                                                print(
                                                    f"在第1行D列找到类型关键字: {packing_type}"
                                                )

                            # 如果仍未找到，尝试查找A列中的"类型"
                            if packing_type == "普货":
                                for row_idx in range(0, min(5, df.shape[0])):
                                    if row_idx < df.shape[0] and df.shape[1] > 0:
                                        cell_value = df.iloc[row_idx, 0]
                                        if (
                                            isinstance(cell_value, str)
                                            and "类型" in cell_value
                                        ):
                                            # 找到了"类型"字样，检查右侧单元格
                                            if 1 < df.shape[1]:
                                                val = df.iloc[row_idx, 1]
                                                if isinstance(val, str):
                                                    val_str = str(val).strip()
                                                    if val_str in [
                                                        "普货",
                                                        "纺织",
                                                        "混装",
                                                    ]:
                                                        packing_type = val_str
                                                        print(
                                                            f"在第{row_idx+1}行B列找到类型: {packing_type}"
                                                        )
                                                        break
                                                    elif (
                                                        "纺" in val_str
                                                        or "织" in val_str
                                                    ):
                                                        packing_type = "纺织"
                                                        print(
                                                            f"在第{row_idx+1}行B列找到类型关键字: {packing_type}"
                                                        )
                                                        break
                                                    elif "混" in val_str:
                                                        packing_type = "混装"
                                                        print(
                                                            f"在第{row_idx+1}行B列找到类型关键字: {packing_type}"
                                                        )
                                                        break

                        # 如果文件名中包含"fz"，则认为是纺织类型
                        if packing_type == "普货" and sheet_name.lower().endswith(
                            "-fz"
                        ):
                            packing_type = "纺织"
                            print(f"从sheet名称 {sheet_name} 判断为纺织类型")

                        print(
                            f"类型 (D1): {type_value}, 实际使用: {packing_type}, 类型: {type(type_value)}"
                        )

                    # 获取B2单元格（总重量）
                    total_weight = 0.0
                    if df.shape[0] > 1 and df.shape[1] > 1:
                        # 从图片看，B2单元格是总重量，值为120
                        total_weight_value = df.iloc[1, 1]
                        if pd.notna(total_weight_value):
                            if isinstance(total_weight_value, (int, float)):
                                total_weight = float(total_weight_value)
                            elif isinstance(total_weight_value, str):
                                try:
                                    total_weight = float(
                                        total_weight_value.strip().replace(",", ".")
                                    )
                                except (ValueError, TypeError):
                                    pass

                        # 如果读取失败或值为0，尝试查找包含"总重量"的单元格
                        if total_weight == 0.0:
                            for row_idx in range(0, min(5, df.shape[0])):
                                for col_idx in range(0, min(5, df.shape[1])):
                                    if row_idx < df.shape[0] and col_idx < df.shape[1]:
                                        cell_value = df.iloc[row_idx, col_idx]
                                        if (
                                            isinstance(cell_value, str)
                                            and "总重量" in cell_value
                                        ):
                                            # 找到了"总重量"字样，检查右侧单元格
                                            if col_idx + 1 < df.shape[1]:
                                                val = df.iloc[row_idx, col_idx + 1]
                                                if isinstance(val, (int, float)):
                                                    total_weight = float(val)
                                                    print(
                                                        f"在第{row_idx+1}行第{col_idx+2}列找到总重量: {total_weight}"
                                                    )
                                                    break
                                                elif isinstance(val, str):
                                                    try:
                                                        total_weight = float(
                                                            val.strip().replace(
                                                                ",", "."
                                                            )
                                                        )
                                                        print(
                                                            f"在第{row_idx+1}行第{col_idx+2}列找到总重量: {total_weight}"
                                                        )
                                                        break
                                                    except (ValueError, TypeError):
                                                        pass
                                if total_weight > 0:
                                    break

                        print(
                            f"总重量 (B2): {total_weight_value}, 实际使用: {total_weight}, 类型: {type(total_weight_value)}"
                        )

                    # 获取B3单元格（总体积）
                    total_volume = 0.0
                    if df.shape[0] > 2 and df.shape[1] > 1:
                        # 从图片看，B3单元格是总体积，值为0.61
                        total_volume_value = df.iloc[2, 1]
                        if pd.notna(total_volume_value):
                            if isinstance(total_volume_value, (int, float)):
                                total_volume = float(total_volume_value)
                            elif isinstance(total_volume_value, str):
                                try:
                                    total_volume = float(
                                        total_volume_value.strip().replace(",", ".")
                                    )
                                except (ValueError, TypeError):
                                    pass

                        # 如果读取失败或值为0，尝试查找包含"总体积"的单元格
                        if total_volume == 0.0:
                            for row_idx in range(0, min(5, df.shape[0])):
                                for col_idx in range(0, min(5, df.shape[1])):
                                    if row_idx < df.shape[0] and col_idx < df.shape[1]:
                                        cell_value = df.iloc[row_idx, col_idx]
                                        if (
                                            isinstance(cell_value, str)
                                            and "总体积" in cell_value
                                        ):
                                            # 找到了"总体积"字样，检查右侧单元格
                                            if col_idx + 1 < df.shape[1]:
                                                val = df.iloc[row_idx, col_idx + 1]
                                                if isinstance(val, (int, float)):
                                                    total_volume = float(val)
                                                    print(
                                                        f"在第{row_idx+1}行第{col_idx+2}列找到总体积: {total_volume}"
                                                    )
                                                    break
                                                elif isinstance(val, str):
                                                    try:
                                                        total_volume = float(
                                                            val.strip().replace(
                                                                ",", "."
                                                            )
                                                        )
                                                        print(
                                                            f"在第{row_idx+1}行第{col_idx+2}列找到总体积: {total_volume}"
                                                        )
                                                        break
                                                    except (ValueError, TypeError):
                                                        pass
                                if total_volume > 0:
                                    break

                        print(
                            f"总体积 (B3): {total_volume_value}, 实际使用: {total_volume}, 类型: {type(total_volume_value)}"
                        )

                    # 获取B4单元格（总边加一体积）
                    total_side_plus_one_volume = 0.0
                    if df.shape[0] > 3 and df.shape[1] > 1:
                        # 从图片看，B4单元格是总边加一体积，值为0.65
                        total_side_plus_one_volume_value = df.iloc[3, 1]
                        if pd.notna(total_side_plus_one_volume_value):
                            if isinstance(
                                total_side_plus_one_volume_value, (int, float)
                            ):
                                total_side_plus_one_volume = float(
                                    total_side_plus_one_volume_value
                                )
                            elif isinstance(total_side_plus_one_volume_value, str):
                                try:
                                    total_side_plus_one_volume = float(
                                        total_side_plus_one_volume_value.strip().replace(
                                            ",", "."
                                        )
                                    )
                                except (ValueError, TypeError):
                                    pass

                        # 如果读取失败或值为0，尝试查找包含"总边加一体积"的单元格
                        if total_side_plus_one_volume == 0.0:
                            for row_idx in range(0, min(5, df.shape[0])):
                                for col_idx in range(0, min(5, df.shape[1])):
                                    if row_idx < df.shape[0] and col_idx < df.shape[1]:
                                        cell_value = df.iloc[row_idx, col_idx]
                                        if isinstance(cell_value, str) and (
                                            "总边加一" in cell_value
                                            or "总边加1" in cell_value
                                        ):
                                            # 找到了相关字样，检查右侧单元格
                                            if col_idx + 1 < df.shape[1]:
                                                val = df.iloc[row_idx, col_idx + 1]
                                                if isinstance(val, (int, float)):
                                                    total_side_plus_one_volume = float(
                                                        val
                                                    )
                                                    print(
                                                        f"在第{row_idx+1}行第{col_idx+2}列找到总边加一体积: {total_side_plus_one_volume}"
                                                    )
                                                    break
                                                elif isinstance(val, str):
                                                    try:
                                                        total_side_plus_one_volume = (
                                                            float(
                                                                val.strip().replace(
                                                                    ",", "."
                                                                )
                                                            )
                                                        )
                                                        print(
                                                            f"在第{row_idx+1}行第{col_idx+2}列找到总边加一体积: {total_side_plus_one_volume}"
                                                        )
                                                        break
                                                    except (ValueError, TypeError):
                                                        pass
                                if total_side_plus_one_volume > 0:
                                    break

                        print(
                            f"总边加一体积 (B4): {total_side_plus_one_volume_value}, 实际使用: {total_side_plus_one_volume}, 类型: {type(total_side_plus_one_volume_value)}"
                        )

                    # 获取B6单元格（总件数）
                    total_items = 0
                    if df.shape[0] > 5 and df.shape[1] > 1:
                        # 从图片看，B6单元格是"总件数"，值为410
                        total_items_value = df.iloc[5, 1]
                        if pd.notna(total_items_value):
                            if isinstance(total_items_value, (int, float)):
                                total_items = int(total_items_value)
                            elif isinstance(total_items_value, str):
                                # 如果是字符串，尝试转换为数字
                                try:
                                    if total_items_value.strip().isdigit():
                                        total_items = int(total_items_value.strip())
                                except (ValueError, TypeError):
                                    pass

                        # 如果读取失败或值为0，尝试查找包含"总件数"的单元格
                        if total_items == 0:
                            for row_idx in range(0, min(10, df.shape[0])):
                                for col_idx in range(0, min(5, df.shape[1])):
                                    if row_idx < df.shape[0] and col_idx < df.shape[1]:
                                        cell_value = df.iloc[row_idx, col_idx]
                                        if (
                                            isinstance(cell_value, str)
                                            and "总件数" in cell_value
                                        ):
                                            # 找到了"总件数"字样，检查右侧单元格
                                            if col_idx + 1 < df.shape[1]:
                                                val = df.iloc[row_idx, col_idx + 1]
                                                if (
                                                    isinstance(val, (int, float))
                                                    and val > 0
                                                ):
                                                    total_items = int(val)
                                                    print(
                                                        f"在第{row_idx+1}行第{col_idx+2}列找到总件数: {total_items}"
                                                    )
                                                    break
                                                elif isinstance(val, str):
                                                    try:
                                                        if val.strip().isdigit():
                                                            total_items = int(
                                                                val.strip()
                                                            )
                                                            print(
                                                                f"在第{row_idx+1}行第{col_idx+2}列找到总件数: {total_items}"
                                                            )
                                                            break
                                                    except (ValueError, TypeError):
                                                        pass
                                if total_items > 0:
                                    break

                        print(
                            f"总件数 (B6): {total_items_value}, 实际使用: {total_items}, 类型: {type(total_items_value)}"
                        )

                    # 获取D2单元格（总价格）
                    total_price = 0.0
                    if df.shape[0] > 1 and df.shape[1] > 3:
                        # 从图片看，D2单元格可能是总价格，值为3300
                        total_price_value = df.iloc[1, 3]
                        if pd.notna(total_price_value):
                            if isinstance(total_price_value, (int, float)):
                                total_price = float(total_price_value)
                            elif isinstance(total_price_value, str):
                                try:
                                    total_price = float(
                                        total_price_value.strip().replace(",", ".")
                                    )
                                except (ValueError, TypeError):
                                    pass

                        # 如果读取失败或值为0，尝试查找包含"总价格"的单元格
                        if total_price == 0.0:
                            for row_idx in range(0, min(5, df.shape[0])):
                                for col_idx in range(0, min(5, df.shape[1])):
                                    if row_idx < df.shape[0] and col_idx < df.shape[1]:
                                        cell_value = df.iloc[row_idx, col_idx]
                                        if isinstance(cell_value, str) and (
                                            "总价格" in cell_value
                                            or "总价" in cell_value
                                        ):
                                            # 找到了相关字样，检查右侧单元格
                                            if col_idx + 1 < df.shape[1]:
                                                val = df.iloc[row_idx, col_idx + 1]
                                                if isinstance(val, (int, float)):
                                                    total_price = float(val)
                                                    print(
                                                        f"在第{row_idx+1}行第{col_idx+2}列找到总价格: {total_price}"
                                                    )
                                                    break
                                                elif isinstance(val, str):
                                                    try:
                                                        total_price = float(
                                                            val.strip().replace(
                                                                ",", "."
                                                            )
                                                        )
                                                        print(
                                                            f"在第{row_idx+1}行第{col_idx+2}列找到总价格: {total_price}"
                                                        )
                                                        break
                                                    except (ValueError, TypeError):
                                                        pass
                                if total_price > 0:
                                    break

                        print(
                            f"总价格 (D2): {total_price_value}, 实际使用: {total_price}, 类型: {type(total_price_value)}"
                        )

                    # 创建一个新的PackingList实例
                    # 从文件名中提取信息
                    shop_info = ""
                    total_boxes_from_filename = 0
                    total_weight_from_filename = 0.0
                    total_volume_from_filename = 0.0
                    packing_type_from_filename = "普货"

                    if excel_file.name.endswith(".xlsx") or excel_file.name.endswith(
                        ".xls"
                    ):
                        file_name = (
                            excel_file.name[:-5]
                            if excel_file.name.endswith(".xlsx")
                            else excel_file.name[:-4]
                        )
                        print(f"处理文件名: {file_name}")

                        # 检查文件名是否包含特定格式的信息
                        # 例如：910749250100438-1.7-1.0-fz
                        parts = file_name.split("-")
                        print(f"文件名分割后的部分: {parts}")

                        if len(parts) >= 3:
                            # 第一部分可能是订单号或店铺信息
                            shop_info = parts[0]
                            print(f"从文件名解析到店铺/订单信息: {shop_info}")

                            # 第二部分可能是总重量
                            try:
                                total_weight_from_filename = float(parts[1])
                                print(
                                    f"从文件名解析到总重量: {total_weight_from_filename}"
                                )
                            except (ValueError, IndexError) as e:
                                print(f"解析总重量时出错: {str(e)}")
                                pass

                            # 第三部分可能是总体积
                            try:
                                total_volume_from_filename = float(parts[2])
                                print(
                                    f"从文件名解析到总体积: {total_volume_from_filename}"
                                )
                            except (ValueError, IndexError) as e:
                                print(f"解析总体积时出错: {str(e)}")
                                pass

                            # 第四部分可能是类型
                            if len(parts) >= 4:
                                if parts[3].lower() == "fz":
                                    packing_type_from_filename = "纺织"
                                    print(
                                        f"从文件名解析到类型: {packing_type_from_filename}"
                                    )
                                else:
                                    print(f"文件名第四部分不是'fz': {parts[3]}")
                        else:
                            print(f"文件名格式不符合预期，无法解析: {file_name}")

                        # 如果文件名中包含"号店"，则提取店铺信息
                        if "号店" in file_name:
                            shop_info = file_name.split("号店")[0] + "号店"
                            print(f"从文件名解析到店铺信息: {shop_info}")

                    # 创建装箱单名称
                    packing_list_name = (
                        f"{shop_info}_{sheet_name}" if shop_info else sheet_name
                    )
                    print(f"生成的装箱单名称: {packing_list_name}")

                    # 检查是否已存在同名的装箱单，如果存在则删除
                    existing_packing_list = PackingList.objects.filter(
                        name=packing_list_name
                    )
                    if existing_packing_list.exists():
                        print(f"发现同名装箱单: {packing_list_name}，将删除旧数据")
                        existing_packing_list.delete()
                        print(f"已删除同名装箱单: {packing_list_name}")

                    # 使用文件名中的信息补充或覆盖从Excel中读取的信息
                    if total_weight_from_filename > 0:
                        print(
                            f"使用文件名中的总重量 {total_weight_from_filename} 替换Excel中读取的总重量 {total_weight}"
                        )
                        total_weight = total_weight_from_filename
                    else:
                        print(f"保留Excel中读取的总重量: {total_weight}")

                    if total_volume_from_filename > 0:
                        print(
                            f"使用文件名中的总体积 {total_volume_from_filename} 替换Excel中读取的总体积 {total_volume}"
                        )
                        total_volume = total_volume_from_filename
                    else:
                        print(f"保留Excel中读取的总体积: {total_volume}")

                    if packing_type_from_filename != "普货":
                        print(
                            f"使用文件名中的类型 {packing_type_from_filename} 替换Excel中读取的类型 {packing_type}"
                        )
                        packing_type = packing_type_from_filename
                    else:
                        print(f"保留Excel中读取的类型: {packing_type}")

                    # 转换数据类型
                    try:
                        total_boxes = (
                            int(float(total_boxes)) if pd.notna(total_boxes) else 0
                        )
                    except (ValueError, TypeError):
                        total_boxes = 0

                    try:
                        total_weight = (
                            float(total_weight) if pd.notna(total_weight) else 0.0
                        )
                    except (ValueError, TypeError):
                        total_weight = 0.0

                    try:
                        total_volume = (
                            float(total_volume) if pd.notna(total_volume) else 0.0
                        )
                    except (ValueError, TypeError):
                        total_volume = 0.0

                    try:
                        total_side_plus_one_volume = (
                            float(total_side_plus_one_volume)
                            if pd.notna(total_side_plus_one_volume)
                            else 0.0
                        )
                    except (ValueError, TypeError):
                        total_side_plus_one_volume = 0.0

                    try:
                        total_items = (
                            int(float(total_items)) if pd.notna(total_items) else 0
                        )
                    except (ValueError, TypeError):
                        total_items = 0

                    try:
                        total_price = (
                            float(total_price) if pd.notna(total_price) else 0.0
                        )
                    except (ValueError, TypeError):
                        total_price = 0.0

                    # 打印原始数据和处理后的数据，用于调试
                    print(f"原始数据:")
                    print(
                        f"  总箱数 (B1): {df.iloc[0, 1] if df.shape[0] > 0 and df.shape[1] > 1 else 'N/A'}"
                    )
                    print(
                        f"  类型 (D1): {df.iloc[0, 3] if df.shape[0] > 0 and df.shape[1] > 3 else 'N/A'}"
                    )
                    print(
                        f"  总重量 (B2): {df.iloc[1, 1] if df.shape[0] > 1 and df.shape[1] > 1 else 'N/A'}"
                    )
                    print(
                        f"  总体积 (B3): {df.iloc[2, 1] if df.shape[0] > 2 and df.shape[1] > 1 else 'N/A'}"
                    )
                    print(
                        f"  总边加一体积 (B4): {df.iloc[3, 1] if df.shape[0] > 3 and df.shape[1] > 1 else 'N/A'}"
                    )
                    print(
                        f"  总件数 (B6): {df.iloc[5, 1] if df.shape[0] > 5 and df.shape[1] > 1 else 'N/A'}"
                    )
                    print(
                        f"  总价格 (D2): {df.iloc[1, 3] if df.shape[0] > 1 and df.shape[1] > 3 else 'N/A'}"
                    )

                    print(f"创建装箱单，数据如下:")
                    print(f"  名称: {packing_list_name}")
                    print(f"  总箱数: {total_boxes}")
                    print(f"  总重量: {total_weight}")
                    print(f"  总体积: {total_volume}")
                    print(f"  总边加一体积: {total_side_plus_one_volume}")
                    print(f"  总件数: {total_items}")
                    print(f"  类型: {packing_type}")
                    print(f"  总价格: {total_price}")

                    # 创建PackingList对象
                    packing_list = PackingList.objects.create(
                        name=packing_list_name,
                        total_boxes=total_boxes,
                        total_weight=total_weight,
                        total_volume=total_volume,
                        total_side_plus_one_volume=total_side_plus_one_volume,
                        total_items=total_items,
                        type=str(packing_type) if pd.notna(packing_type) else "普货",
                        total_price=total_price,
                    )
                    print(f"创建装箱单成功: {packing_list_name}")

                    # 处理SKU数据
                    valid_sku_count = 0
                    processed_skus = []  # 用于跟踪已处理的SKU

                    # 从图片看，SKU数据从第8行开始，B列是SKU，C列是中文名称
                    # 但实际上可能从第7行或第9行开始，需要灵活处理
                    sku_start_row = None

                    # 查找包含"sku"的行，这通常是表头行
                    for row_idx in range(5, min(15, df.shape[0])):
                        if row_idx < df.shape[0] and df.shape[1] > 1:
                            cell_value = df.iloc[row_idx, 1]
                            if (
                                isinstance(cell_value, str)
                                and "sku" in str(cell_value).lower()
                            ):
                                sku_start_row = row_idx + 1  # SKU数据从下一行开始
                                print(
                                    f"在第{row_idx+1}行找到SKU表头，数据从第{sku_start_row+1}行开始"
                                )
                                break

                    # 如果没有找到包含"sku"的行，默认从第8行开始
                    if sku_start_row is None:
                        sku_start_row = 7  # 索引7对应第8行
                        print(f"未找到SKU表头，默认从第{sku_start_row+1}行开始")

                    # 处理SKU数据
                    for row_idx in range(
                        sku_start_row, min(sku_start_row + 100, df.shape[0])
                    ):
                        if row_idx < df.shape[0] and df.shape[1] > 1:
                            sku_value = df.iloc[row_idx, 1]  # B列
                            print(
                                f"第{row_idx+1}行B列值: {sku_value}, 类型: {type(sku_value)}"
                            )

                            if pd.notna(sku_value) and str(sku_value).strip() != "":
                                sku = str(sku_value).strip()

                                # 跳过重复的SKU
                                if sku in processed_skus:
                                    print(f"跳过重复的SKU: {sku}")
                                    continue

                                processed_skus.append(sku)
                                print(f"处理SKU: {sku}")

                                # 获取中文名称（C列）
                                chinese_name = "待补充"
                                if df.shape[1] > 2 and pd.notna(df.iloc[row_idx, 2]):
                                    chinese_name = str(df.iloc[row_idx, 2])

                                # 创建或更新产品
                                try:
                                    product = Product.objects.get(sku=sku)
                                    # 更新现有产品
                                    product.chinese_name = chinese_name
                                except Product.DoesNotExist:
                                    # 创建新产品
                                    product = Product(
                                        sku=sku,
                                        chinese_name=chinese_name,
                                        price=0.0,
                                        category=packing_type,  # 使用装箱单类型作为产品类别
                                        weight=0.0,
                                        volume="",
                                        stock=0,
                                    )
                                product.save()

                                # 计算数量
                                quantity = 0
                                quantity_found = False

                                # 从图片看，数量信息从F列开始，每个箱子占用3列
                                # 遍历所有可能包含数量的列
                                for col_idx in range(5, df.shape[1]):  # 从F列开始查找
                                    if col_idx < df.shape[1] and pd.notna(
                                        df.iloc[row_idx, col_idx]
                                    ):
                                        try:
                                            val = df.iloc[row_idx, col_idx]
                                            print(
                                                f"检查列 {col_idx+1} 的值: {val}, 类型: {type(val)}"
                                            )

                                            # 尝试将值转换为数字
                                            if isinstance(val, (int, float)):
                                                num_val = val
                                            elif (
                                                isinstance(val, str)
                                                and val.strip()
                                                .replace(".", "", 1)
                                                .isdigit()
                                            ):
                                                num_val = float(val)
                                            else:
                                                continue

                                            if num_val > 0:
                                                quantity += int(num_val)
                                                quantity_found = True
                                                print(
                                                    f"从列索引{col_idx}找到数量: {int(num_val)}"
                                                )
                                        except (ValueError, TypeError) as e:
                                            print(
                                                f"处理列 {col_idx+1} 时出错: {str(e)}"
                                            )

                                # 如果没有找到数量，尝试从第5列（E列）获取
                                if (
                                    not quantity_found
                                    and df.shape[1] > 4
                                    and pd.notna(df.iloc[row_idx, 4])
                                ):
                                    try:
                                        val = df.iloc[row_idx, 4]
                                        if isinstance(val, (int, float)) and val > 0:
                                            quantity = int(val)
                                            quantity_found = True
                                            print(f"从E列找到数量: {quantity}")
                                    except (ValueError, TypeError) as e:
                                        print(f"处理E列时出错: {str(e)}")

                                # 如果仍然没有找到数量，使用总件数或默认为1
                                if not quantity_found:
                                    if total_items > 0 and len(processed_skus) == 1:
                                        # 如果只有一个SKU且有总件数，使用总件数
                                        quantity = total_items
                                        print(f"使用总件数作为数量: {quantity}")
                                    else:
                                        quantity = 1
                                        print(f"未找到数量，默认设置为1: SKU={sku}")

                                # 创建PackingListItem
                                if quantity > 0:
                                    PackingListItem.objects.create(
                                        packing_list=packing_list,
                                        product=product,
                                        quantity=quantity,
                                    )
                                    print(f"添加产品到装箱单: {sku}, 数量: {quantity}")
                                    valid_sku_count += 1
                                    success_count += 1

                    # 如果没有有效的SKU，也标记为错误
                    if valid_sku_count == 0:
                        # 检查是否有任何PackingListItem
                        items_count = PackingListItem.objects.filter(
                            packing_list=packing_list
                        ).count()
                        if items_count == 0:
                            messages.warning(
                                request,
                                f'Sheet "{sheet_name}" 未能添加任何产品到装箱单，但装箱单基本信息已保存',
                            )
                            print(
                                f"装箱单 {packing_list_name} 没有任何产品，但基本信息已保存"
                            )
                        else:
                            # 如果有PackingListItem，则保留装箱单
                            messages.success(
                                request,
                                f'Sheet "{sheet_name}" 成功创建装箱单，包含{items_count}个产品',
                            )
                            print(
                                f"保留装箱单: {packing_list_name}，包含{items_count}个产品"
                            )
                    else:
                        messages.success(
                            request,
                            f'Sheet "{sheet_name}" 成功创建装箱单，包含{valid_sku_count}个产品',
                        )
                        print(
                            f"成功创建装箱单: {packing_list_name}，包含{valid_sku_count}个产品"
                        )
                except Exception as e:
                    print(f"处理Sheet时出错: {str(e)}")
                    traceback.print_exc()  # 打印详细的错误堆栈
                    messages.warning(
                        request, f'处理Sheet "{sheet_name}" 时出错: {str(e)}'
                    )
                    continue

            # 使用延迟删除，确保所有文件句柄都已关闭
            try:
                import gc
                gc.collect()  # 强制垃圾回收，释放文件句柄
                time.sleep(0.5)  # 短暂延迟，确保文件句柄已释放

                if os.path.exists(file_path):
                    os.remove(file_path)  # 删除上传的文件
                    print(f"删除临时文件: {file_path}")
            except Exception as e:
                # 如果删除失败，记录错误但不中断流程
                print(f"警告：无法删除临时文件 {file_path}: {str(e)}")

            # 显示处理结果
            if error_count > 0 and success_count > 0:
                messages.warning(
                    request,
                    f"部分导入成功：{success_count}条记录导入成功，{error_count}条记录导入失败",
                )
                print(
                    f"部分导入成功：{success_count}条记录导入成功，{error_count}条记录导入失败"
                )
            elif error_count > 0 and success_count == 0:
                messages.error(request, f"导入失败：所有记录均导入失败")
                print(f"导入失败：所有记录均导入失败")
            else:
                messages.success(request, f"导入成功：共导入{success_count}条记录")
                print(f"导入成功：共导入{success_count}条记录")

            # 重定向到装箱单列表页面，而不是产品列表页面
            return redirect("packing_list")

        except Exception as e:
            print(f"处理Excel文件时出错: {str(e)}")
            traceback.print_exc()  # 打印详细的错误堆栈
            messages.error(request, f"处理Excel文件时出错: {str(e)}")
            # 尝试删除临时文件
            try:
                import gc
                gc.collect()
                time.sleep(0.5)

                if os.path.exists(file_path):
                    os.remove(file_path)
                    print(f"删除临时文件: {file_path}")
            except Exception as ex:
                print(f"删除临时文件时出错: {str(ex)}")
            return render(request, "erp/bulk_upload.html")

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
