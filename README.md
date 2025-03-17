# ANY-GO 办公系统

ANY-GO 办公系统是一个基于Django的企业资源规划(ERP)系统，用于管理产品、库存和装箱单等信息。

## 功能特点

- 产品管理：添加、编辑、删除和查看产品信息
- 库存管理：跟踪产品库存情况
- 装箱单管理：创建和管理装箱单
- 批量导入：支持通过Excel文件批量导入产品数据

## 安装与设置

1. 克隆仓库
```
git clone <repository-url>
cd ANY-GO-WebApp
```

2. 创建并激活虚拟环境
```
python -m venv venv
# Windows
venv\Scripts\activate
# Linux/Mac
source venv/bin/activate
```

3. 安装依赖
```
pip install -r requirements.txt
```

4. 运行数据库迁移
```
python manage.py migrate
```

5. 启动开发服务器
```
python manage.py runserver
```

## 使用指南

### 产品管理

- 产品列表：访问 `/erp/products/` 查看所有产品
- 添加产品：点击"添加产品"按钮，填写产品信息
- 编辑产品：在产品列表中点击"编辑"按钮
- 删除产品：在产品列表中点击"删除"按钮

### 批量导入产品

1. 访问 `/erp/bulk_upload/` 页面
2. 下载Excel模板
3. 按照模板格式填写产品数据
4. 上传填写好的Excel文件

**注意事项：**
- Excel文件必须包含以下列：SKU、中文名称、价格、类别、重量、体积、库存
- SKU是唯一标识符，如果系统中已存在相同SKU的产品，将会更新该产品信息
- 如果SKU不存在，将创建新产品

### 装箱单管理

- 装箱单列表：访问 `/erp/packing/` 查看所有装箱单
- 装箱单详情：点击装箱单名称查看详情
- 删除装箱单：在装箱单列表中点击"删除"按钮

## 技术栈

- 后端：Django 5.1.7
- 前端：Bootstrap 4.5.2
- 数据库：SQLite (开发环境)
- 数据处理：Pandas, Openpyxl

## 贡献指南

1. Fork 仓库
2. 创建功能分支 (`git checkout -b feature/amazing-feature`)
3. 提交更改 (`git commit -m 'Add some amazing feature'`)
4. 推送到分支 (`git push origin feature/amazing-feature`)
5. 创建 Pull Request

## 许可证

[MIT License](LICENSE) 