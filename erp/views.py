# filepath: /C:/Users/khoo_/Desktop/ANY-GO-WebApp/erp/views.py
from django.shortcuts import render, redirect, get_object_or_404
from django.db.models import Q
from django.core.paginator import Paginator
from django.http import HttpResponse
from .forms import ProductForm
from .models import Product, Inventory, PackingList, PackingListItem
import subprocess
import os
import json
import pandas as pd

def product_list(request):
    query = request.GET.get('q')
    if query:
        products = Product.objects.filter(
            Q(sku__icontains=query) |
            Q(chinese_name__icontains=query) |
            Q(price__icontains=query) |
            Q(category__icontains=query) |
            Q(weight__icontains=query) |
            Q(volume__icontains=query)
        ).order_by('id')  # 添加排序
    else:
        products = Product.objects.all().order_by('id')  # 添加排序
    
    paginator = Paginator(products, 100)  # 每页显示100个产品
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    return render(request, 'erp/product_list.html', {'page_obj': page_obj})

def export_products(request):
    # 获取所有产品
    products = Product.objects.all().values('sku', 'chinese_name', 'price', 'category', 'weight', 'volume', 'stock', 'created_at', 'updated_at')
    
    # 创建一个 DataFrame，并指定列名
    df = pd.DataFrame(products)
    df.columns = ['SKU', '中文名称', '价格', '类别', '重量', '体积', '库存', '创建时间', '更新时间']
    
    # 将日期时间字段转换为无时区的格式
    df['创建时间'] = df['创建时间'].dt.tz_localize(None)
    df['更新时间'] = df['更新时间'].dt.tz_localize(None)
    
    # 创建一个 HttpResponse 对象，并设置内容类型为 Excel 文件
    response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    response['Content-Disposition'] = 'attachment; filename=products.xlsx'
    
    # 将 DataFrame 写入 Excel 文件
    with pd.ExcelWriter(response, engine='xlsxwriter') as writer:
        df.to_excel(writer, sheet_name='Products', index=False)
    
    return response

def product_detail(request, pk):
    product = get_object_or_404(Product, pk=pk)
    return render(request, 'erp/product_detail.html', {'product': product})

def add_product(request):
    if request.method == 'POST':
        form = ProductForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            return redirect('product_list')
    else:
        form = ProductForm()
    return render(request, 'erp/add_product.html', {'form': form})

def bulk_upload(request, template_name='erp/bulk_upload.html'):
    if request.method == 'POST':
        excel_file = request.FILES['file']
        upload_dir = 'uploads'
        if not os.path.exists(upload_dir):
            os.makedirs(upload_dir)
        file_path = os.path.join(upload_dir, excel_file.name)
        
        with open(file_path, 'wb+') as destination:
            for chunk in excel_file.chunks():
                destination.write(chunk)

        # 读取Excel文件
        df = pd.read_excel(file_path)
        
        # 处理每一行数据
        for index, row in df.iterrows():
            try:
                product = Product.objects.get(sku=row['SKU'])
                # 更新现有产品
                product.chinese_name = row['中文名称']
                product.price = float(row['价格']) if pd.notna(row['价格']) else 0.0
                product.category = row['类别']
                product.weight = float(row['重量']) if pd.notna(row['重量']) else 0.0
                product.volume = float(row['体积']) if pd.notna(row['体积']) else 0.0
                product.stock = int(row['库存']) if pd.notna(row['库存']) else 0
            except Product.DoesNotExist:
                # 创建新产品
                product = Product(
                    sku=row['SKU'],
                    chinese_name=row['中文名称'],
                    price=float(row['价格']) if pd.notna(row['价格']) else 0.0,
                    category=row['类别'],
                    weight=float(row['重量']) if pd.notna(row['重量']) else 0.0,
                    volume=float(row['体积']) if pd.notna(row['体积']) else 0.0,
                    stock=int(row['库存']) if pd.notna(row['库存']) else 0
                )
            product.save()
        
        os.remove(file_path)  # 删除上传的文件
        return redirect('product_list')
        
    return render(request, template_name)

# 为了保持向后兼容性，保留bulk_product_upload函数但复用bulk_upload的逻辑
def bulk_product_upload(request):
    return bulk_upload(request, template_name='erp/bulk_product_upload.html')

def save_bulk_upload(request):
    if request.method == 'POST':
        data = json.loads(request.POST['data'])
        df = pd.DataFrame(data)

        # 创建一个新的 PackingList 实例
        packing_list = PackingList.objects.create(
            name='批量上传装箱单',
            total_boxes=0,
            total_weight=0.0,
            total_volume=0.0,
            total_side_plus_one_volume=0.0,
            total_items=len(df),
            type='批量上传',
            total_price=0.0
        )
        
        for index, row in df.iterrows():
            try:
                # 尝试获取现有产品
                product = Product.objects.get(sku=row['sku'])
                # 更新所有字段
                product.chinese_name = row['中文名称']
                product.price = float(row['价格']) if row['价格'] else 0.0
                product.category = row['类别']
                product.weight = float(row['重量']) if row['重量'] else 0.0
                product.volume = float(row['体积']) if row['体积'] else 0.0
                product.stock = int(row['库存']) if row['库存'] else 0
            except Product.DoesNotExist:
                # 如果产品不存在，创建新产品
                product = Product(
                    sku=row['sku'],
                    chinese_name=row['中文名称'],
                    price=float(row['价格']) if row['价格'] else 0.0,
                    category=row['类别'],
                    weight=float(row['重量']) if row['重量'] else 0.0,
                    volume=float(row['体积']) if row['体积'] else 0.0,
                    stock=int(row['库存']) if row['库存'] else 0
                )
            
            # 保存产品
            product.save()

            # 创建装箱单项目
            PackingListItem.objects.create(
                packing_list=packing_list,
                product=product,
                quantity=int(row['数量']) if row['数量'] else 0
            )
        
        return redirect('packing_list')

    return HttpResponse("无效的请求方法")

def edit_product(request, pk):
    # 获取要编辑的产品对象，如果不存在则返回404错误
    product = get_object_or_404(Product, pk=pk)
    
    if request.method == 'POST':
        # 如果请求方法是POST，表示表单已提交
        form = ProductForm(request.POST, request.FILES, instance=product)
        if form.is_valid():
            # 如果表单数据有效，保存表单数据
            form.save()
            # 保存成功后重定向到产品列表页面
            return redirect('product_list')
    else:
        # 如果请求方法不是POST，表示是GET请求，显示表单
        form = ProductForm(instance=product)
    
    # 渲染编辑产品页面，并传递表单对象
    return render(request, 'erp/edit_product.html', {'form': form})

def delete_product(request, pk):
    product = get_object_or_404(Product, pk=pk)
    if request.method == 'POST':
        product.delete()
        return redirect('product_list')
    return render(request, 'erp/delete_product.html', {'product': product})

def inventory_list(request):
    inventories = Inventory.objects.all()
    return render(request, 'erp/inventory_list.html', {'inventories': inventories})

def packing_list(request):
    packing_lists = PackingList.objects.all()
    return render(request, 'erp/packing_list.html', {'packing_lists': packing_lists})

def packing_list_detail(request, pk):
    packing_list = get_object_or_404(PackingList, pk=pk)
    items = PackingListItem.objects.filter(packing_list=packing_list)
    return render(request, 'erp/packing_list_detail.html', {'packing_list': packing_list, 'items': items})

def delete_packing_list(request, pk):
    packing_list = get_object_or_404(PackingList, pk=pk)
    if request.method == 'POST':
        packing_list.delete()
        return redirect('packing_list')
    return render(request, 'erp/delete_packing_list.html', {'packing_list': packing_list})

def bulk_upload(request):
    if request.method == 'POST':
        excel_file = request.FILES['file']
        upload_dir = 'uploads'
        if not os.path.exists(upload_dir):
            os.makedirs(upload_dir)
        file_path = os.path.join(upload_dir, excel_file.name)
        with open(file_path, 'wb+') as destination:
            for chunk in excel_file.chunks():
                destination.write(chunk)

        # 读取Excel文件
        df = pd.read_excel(file_path)
        
        # 处理每一行数据
        for index, row in df.iterrows():
            try:
                product = Product.objects.get(sku=row['SKU'])
                # 更新现有产品
                product.chinese_name = row['中文名称']
                product.price = float(row['价格']) if pd.notna(row['价格']) else 0.0
                product.category = row['类别']
                product.weight = float(row['重量']) if pd.notna(row['重量']) else 0.0
                product.volume = float(row['体积']) if pd.notna(row['体积']) else 0.0
                product.stock = int(row['库存']) if pd.notna(row['库存']) else 0
            except Product.DoesNotExist:
                # 创建新产品
                product = Product(
                    sku=row['SKU'],
                    chinese_name=row['中文名称'],
                    price=float(row['价格']) if pd.notna(row['价格']) else 0.0,
                    category=row['类别'],
                    weight=float(row['重量']) if pd.notna(row['重量']) else 0.0,
                    volume=float(row['体积']) if pd.notna(row['体积']) else 0.0,
                    stock=int(row['库存']) if pd.notna(row['库存']) else 0
                )
            product.save()
        
        os.remove(file_path)  # 删除上传的文件
        return redirect('product_list')
        
    return render(request, 'erp/bulk_upload.html')
