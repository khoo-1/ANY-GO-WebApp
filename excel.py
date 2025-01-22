import pandas as pd
import os
import django
from django.conf import settings

# 设置 Django 环境
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ecommerce_project.settings')
django.setup()

from erp.models import Product, PackingList, PackingListItem

# 加载 Excel 文件
file_path = 'c:/Users/khoo_/Desktop/ANY-GO-WebApp/16号店海运ERP.xlsx'

# 检查文件是否存在
if not os.path.exists(file_path):
    print(f"文件 {file_path} 不存在，请检查路径。")
else:
    try:
        # 使用 pandas 读取 Excel 文件，从第5行开始读取表头
        df = pd.read_excel(file_path, header=None)
        print("Headers:", df.iloc[4].tolist())  # 打印第5行作为表头
        df.columns = df.iloc[4]  # 将第5行设置为列名
        df = df.drop([0, 1, 2, 3, 4, 5])  # 删除前6行（包括原来的表头行）
        df = df.reset_index(drop=True)  # 重置索引
        print(df)  # 打印所有数据

        # 从第6列开始，每隔3列检查一次
        for col in range(5, df.shape[1], 3):
            if col < df.shape[1] and col + 2 < df.shape[1]:
                # 如果第6列有数据，则第7、8列的 NaN 值自动补充第6列的值
                df.iloc[:, col + 1].fillna(df.iloc[:, col], inplace=True)
                df.iloc[:, col + 2].fillna(df.iloc[:, col], inplace=True)

        print("处理后的数据:")
        print(df)  # 打印处理后的数据

        # 从第7行开始检索数据
        start_row = 1  # 第7行的索引是1（因为前面已经删除了前6行）
        end_row = start_row

        # 找到第2列中第一个没有数据的行
        for i in range(start_row, len(df)):
            if pd.isna(df.iloc[i, 1]):
                end_row = i
                break
        else:
            end_row = len(df)

        # 提取第2、3、5列的数据，并另存为一个新的 DataFrame
        df_upload = df.iloc[start_row:end_row, [1, 2, 4]].copy()
        df_upload.columns = ['sku', '中文名称', '数量']  # 重命名列

        print("用于批量上传的数据:")
        print(df_upload)  # 打印用于批量上传的数据

        # 创建一个新的 PackingList 实例
        packing_list = PackingList.objects.create(
            total_boxes=10,  # 示例值
            total_weight=100.0,  # 示例值
            total_volume=200.0,  # 示例值
            total_side_plus_one_volume=210.0,  # 示例值
            total_items=len(df_upload),  # 总件数
            type='海运',  # 示例值
            total_price=1000.0  # 示例值
        )

        # 将 df_upload 中的数据保存到数据库中
        for index, row in df_upload.iterrows():
            product, created = Product.objects.get_or_create(
                sku=row['sku'],
                defaults={'chinese_name': row['中文名称']}
            )
            PackingListItem.objects.create(
                packing_list=packing_list,
                product=product,
                quantity=row['数量']
            )

        print("数据已成功保存到数据库中。")

    except Exception as e:
        print(f"加载文件时出错: {e}")