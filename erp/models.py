from django.db import models
from django.utils import timezone

# 创建你的模型

class Warehouse(models.Model):
    name = models.CharField(max_length=100)  # 仓库名称，最大长度为100个字符
    location = models.CharField(max_length=100)  # 仓库位置，最大长度为100个字符

    def __str__(self):
        return self.name  # 返回仓库名称作为字符串表示

class Product(models.Model):
    sku = models.CharField(max_length=100, unique=True)  # SKU（库存单位），最大长度为100个字符，唯一
    chinese_name = models.CharField(max_length=200)  # 中文名称，最大长度为200个字符，非空
    price = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)  # 产品价格，最多10位数字，小数点后保留2位，可以为空
    category = models.CharField(max_length=100, blank=True, null=True)  # 产品类别，最大长度为100个字符，可以为空
    weight = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)  # 产品重量，最多10位数字，小数点后保留2位，可以为空
    volume = models.CharField(max_length=100, blank=True, null=True)  # 产品体积，最大长度为100个字符，可以为空
    image = models.ImageField(upload_to='products/', null=True, blank=True)  # 产品图片，上传路径为'products/'，允许为空
    stock = models.IntegerField(blank=True, null=True)  # 库存数量，使用整数字段，可以为空
    created_at = models.DateTimeField(default=timezone.now)  # 创建时间，默认值为当前时间
    updated_at = models.DateTimeField(auto_now=True)  # 更新时间，自动设置为当前时间

    def __str__(self):
        return self.chinese_name  # 返回中文名称作为字符串表示

class Inventory(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE)  # 关联的产品，外键，级联删除
    warehouse = models.ForeignKey(Warehouse, on_delete=models.CASCADE)  # 关联的仓库，外键，级联删除
    stock = models.IntegerField()  # 库存数量，使用整数字段

    def __str__(self):
        return f"{self.product.sku} in {self.warehouse.name}"  # 返回产品SKU和仓库名称作为字符串表示


class PackingList(models.Model):
    name = models.CharField(max_length=200)  # 装箱单名称
    total_boxes = models.IntegerField()  # 总箱数
    total_weight = models.DecimalField(max_digits=10, decimal_places=2)  # 总箱重
    total_volume = models.DecimalField(max_digits=10, decimal_places=2)  # 总体积
    total_side_plus_one_volume = models.DecimalField(max_digits=10, decimal_places=2)  # 总单边+1体积
    total_items = models.IntegerField()  # 总件数
    type = models.CharField(max_length=100)  # 类型
    total_price = models.DecimalField(max_digits=10, decimal_places=2)  # 总价格
    created_at = models.DateTimeField(default=timezone.now)  # 创建时间
    updated_at = models.DateTimeField(auto_now=True)  # 更新时间

    def __str__(self):
        return self.name  # 返回装箱单名称作为字符串表示

class PackingListItem(models.Model):
    packing_list = models.ForeignKey(PackingList, related_name='items', on_delete=models.CASCADE)  # 关联到 PackingList
    product = models.ForeignKey(Product, on_delete=models.CASCADE)  # 关联到 Product
    quantity = models.IntegerField()  # 数量

    def __str__(self):
        return f"{self.product.chinese_name} - {self.quantity}"
