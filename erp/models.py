from django.db import models
from django.utils import timezone

# 创建你的模型

class Warehouse(models.Model):
    name = models.CharField(max_length=100)  # 仓库名称，最大长度为100个字符
    location = models.CharField(max_length=100)  # 仓库位置，最大长度为100个字符

    def __str__(self):
        return self.name  # 返回仓库名称作为字符串表示

class Product(models.Model):
    sku = models.CharField(max_length=100, unique=True, verbose_name="SKU")
    chinese_name = models.CharField(max_length=200, verbose_name="中文名称")
    price = models.DecimalField(max_digits=10, decimal_places=2, default=0.00, verbose_name="价格")
    category = models.CharField(max_length=50, choices=[('普货', '普货'), ('纺织', '纺织'), ('混装', '混装')], default='普货', verbose_name="类别")
    weight = models.DecimalField(max_digits=10, decimal_places=2, default=0.00, verbose_name="重量")
    volume = models.CharField(max_length=100, blank=True, verbose_name="体积")
    stock = models.IntegerField(default=0, verbose_name="库存")
    shipping_cost = models.DecimalField(max_digits=10, decimal_places=2, default=0.00, verbose_name="头程成本")
    total_value = models.DecimalField(max_digits=10, decimal_places=2, default=0.00, verbose_name="总货值")

    def __str__(self):
        return f"{self.sku} - {self.chinese_name}"

    class Meta:
        verbose_name = "产品"
        verbose_name_plural = "产品"

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

    def __str__(self):
        return self.name  # 返回装箱单名称作为字符串表示

class PackingListItem(models.Model):
    packing_list = models.ForeignKey(PackingList, related_name='items', on_delete=models.CASCADE)  # 关联到 PackingList
    product = models.ForeignKey(Product, on_delete=models.CASCADE)  # 关联到 Product
    quantity = models.IntegerField()  # 数量

    def __str__(self):
        return f"{self.product.chinese_name} - {self.quantity}"
