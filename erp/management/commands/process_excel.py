import pandas as pd
from django.core.management.base import BaseCommand
from erp.models import Product, PackingList, PackingListItem
from django.core.exceptions import ValidationError

class Command(BaseCommand):
    help = '处理上传的Excel文件并将数据存储到数据库中'

    def add_arguments(self, parser):
        # 添加命令行参数，用于指定Excel文件的路径
        parser.add_argument('file_path', type=str, help='要处理的Excel文件的路径')

    def handle(self, *args, **kwargs):
        file_path = kwargs['file_path']
        try:
            # 尝试读取Excel文件
            excel_file = pd.ExcelFile(file_path)
        except Exception as e:
            # 如果读取文件时出错，输出错误信息并返回
            self.stdout.write(self.style.ERROR(f"读取Excel文件时出错: {e}"))
            return

        # 遍历每个sheet的名称
        for sheet_name in excel_file.sheet_names:
            # 检查sheet名称是否已存在于装箱单的列表名称中，或名称为"常用箱规"
            if PackingList.objects.filter(name=sheet_name).exists() or sheet_name == "常用箱规":
                self.stdout.write(self.style.WARNING(f"装箱单名称 '{sheet_name}' 已存在或为'常用箱规'，跳过该sheet"))
                continue

            # 读取当前sheet的数据
            df = excel_file.parse(sheet_name, header=None)

            # 从指定的单元格中读取值，并处理NaN值
            try:
                total_boxes = df.iloc[0, 1] if pd.notna(df.iloc[0, 1]) else 0
                total_weight = df.iloc[1, 1] if pd.notna(df.iloc[1, 1]) else 0
                total_volume = df.iloc[2, 1] if pd.notna(df.iloc[2, 1]) else 0
                total_side_plus_one_volume = df.iloc[3, 1] if pd.notna(df.iloc[3, 1]) else 0
                total_items = df.iloc[5, 1] if pd.notna(df.iloc[5, 1]) else 0
                packing_type = df.iloc[0, 3] if pd.notna(df.iloc[0, 3]) else ''
                total_price = df.iloc[1, 3] if pd.notna(df.iloc[1, 3]) else 0
            except IndexError as e:
                self.stdout.write(self.style.ERROR(f"读取单元格时出错: {e}"))
                continue

            
            # 创建一个新的PackingList实例
            try:
                packing_list = PackingList.objects.create(
                    name=sheet_name,  # 使用sheet名称作为装箱单的名称
                    total_boxes=total_boxes,
                    total_weight=total_weight,
                    total_volume=total_volume,
                    total_side_plus_one_volume=total_side_plus_one_volume,
                    total_items=total_items,
                    type=packing_type,
                    total_price=total_price
                )
            except ValidationError as e:
                self.stdout.write(self.style.ERROR(f"创建PackingList实例时出错: {e}"))
                continue

            # 遍历Excel文件中的每一行，从第8行开始读取产品数据
            for index, row in df.iterrows():
                if index < 7:  # 跳过前7行
                    continue
                try:
                    # 获取或创建Product实例
                    product, created = Product.objects.get_or_create(
                        sku=str(row[1]),  # B列
                        defaults={'chinese_name': str(row[2])}  # C列
                    )
                    # 创建PackingListItem实例
                    PackingListItem.objects.create(
                        packing_list=packing_list,
                        product=product,
                        quantity=int(row[4])  # E列
                    )
                except KeyError as e:
                    self.stdout.write(self.style.ERROR(f"处理行 {index} 时出错: 缺少列 {e}"))
                    continue
                except ValueError as e:
                    self.stdout.write(self.style.ERROR(f"处理行 {index} 时出错: 数量列不是有效的整数: {e}"))
                    continue

        # 输出成功信息
        self.stdout.write(self.style.SUCCESS("Excel文件处理成功并存储到数据库"))