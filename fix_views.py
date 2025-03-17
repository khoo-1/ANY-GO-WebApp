import re

# 读取文件
with open('erp/views.py', 'r', encoding='utf-8') as f:
    content = f.read()

# 修复总箱数读取位置
content = re.sub(r'total_boxes = df\.iloc\[(\d+), (\d+)\]', r'total_boxes = df.iloc[0, 1]', content)

# 修复类型读取位置
content = re.sub(r'packing_type = df\.iloc\[(\d+), (\d+)\]', r'packing_type = df.iloc[0, 3]', content)

# 修复总件数读取位置
content = re.sub(r'total_items = df\.iloc\[(\d+), (\d+)\]', r'total_items = df.iloc[5, 1]', content)

# 修复总价格读取位置
content = re.sub(r'total_price = df\.iloc\[(\d+), (\d+)\]', r'total_price = df.iloc[1, 3]', content)

# 写入文件
with open('erp/views.py', 'w', encoding='utf-8') as f:
    f.write(content)

print("文件修复完成！") 