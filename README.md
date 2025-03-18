# ANY-GO WebApp

基于Django的ERP系统，用于管理产品、发货单和装箱单等信息。

## 主要功能

### 产品管理
- SKU管理
- 产品信息维护
- 批量导入导出
- 自动创建缺失SKU

### 发货单管理
- 发货单导入功能
  - 支持Excel文件导入
  - 自动将产品价格设置为采购成本
  - 支持多家店铺选择
- 发货单列表显示
- 变更状态功能
  - 将发货单状态从"在途"变更为"到岸"
  - 填写头程总价格并自动按体积比例分摊头程成本
  - 更新产品的头程成本信息
- 回退态功能
  - 将发货单状态从"到岸"回退为"在途" 
  - 删去头程成本，货值计算恢复为仅采购成本
- 删除功能

### 在库数据管理
- 导入在库数据
  - 支持Excel文件导入
  - 导入时会清空现有在库数据（到岸和在途数据不受影响）
  - 使用标准店铺名称
  - 自动计算总货值
- 查看库存统计
- 按店铺查看统计

### 数据管理
- 清除所有数据功能（便于测试和重置系统）

## 技术栈
- Python 3.9+
- Django 4.2+
- Pandas
- Bootstrap 4
- jQuery

## 开发说明
1. 克隆仓库
2. 安装依赖: `pip install -r requirements.txt`
3. 运行迁移: `python manage.py migrate`
4. 启动服务器: `python manage.py runserver`
5. 访问: http://127.0.0.1:8000/erp/

## 数据规则
- 所有金额和价格字段保留两位小数
- 采用四舍五入进位规则
- 头程成本按体积比例分摊

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

## ANY-GO ERP系统

### 核心功能

- 产品管理：录入、查询、编辑和删除产品信息
- 库存管理：跟踪不同店铺的产品库存（在库、到岸、在途）
- 发货管理：创建发货单，跟踪发货状态，自动计算头程成本
- 数据导入导出：支持Excel文件导入导出各类数据
- 报表功能：查看库存总览和各店铺库存情况

### 最新更新

- 产品模型增加店铺关联，清晰区分不同店铺的产品
- 将产品库存和价值分为三类：在库、到岸、在途，更准确地反映货物状态
- 在产品列表页面增加店铺筛选功能
- 改进库存总览页面，显示各店铺的库存状态和价值
- 更新发货状态变更逻辑，正确更新产品的在途和到岸状态
- 导入库存数据时移除了正则表达式匹配，直接使用标准店铺名称

### 使用方法

1. 添加店铺：先在系统中添加您的店铺
2. 添加产品：为每个店铺添加产品信息
3. 导入库存：通过Excel导入库存数据
4. 创建发货单：记录产品发货信息
5. 更新发货状态：当货物到岸时更新状态，系统会自动计算头程成本

### 数据导入格式

#### 库存数据

- 必须包含字段：SKU、数量、店铺
- 导入时会自动关联到对应店铺的产品
- 可选择清除现有库存数据（"到岸"和"在途"状态不受影响）

#### 发货单数据

- 必须包含字段：SKU、数量、采购成本、体积
- 导入成功后会自动更新产品的在途库存和价值

### 技术栈

- 后端：Django
- 前端：Bootstrap 5
- 数据库：SQLite (开发) / PostgreSQL (生产)
- 数据处理：Pandas

## 贡献指南

1. Fork 仓库
2. 创建功能分支 (`git checkout -b feature/amazing-feature`)
3. 提交更改 (`git commit -m 'Add some amazing feature'`)
4. 推送到分支 (`git push origin feature/amazing-feature`)
5. 创建 Pull Request

## 许可证

[MIT License](LICENSE) 