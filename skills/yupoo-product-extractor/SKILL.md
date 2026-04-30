# Skill: yupoo-product-extractor

Yupoo 产品采集器 - 从 Yupoo 相册批量采集产品信息并导出 Excel

## 功能

- 按日期采集 Yupoo 相册产品
- 提取产品名称、图片链接（最多14张）
- 自动生成英文产品名称
- 支持颜色识别（基于图片或产品名称）
- 导出 Excel 文件

## 触发场景

- 用户需要从 Yupoo 采集产品数据
- 用户需要批量导出产品信息到 Excel
- 用户提到"采集产品"、"提取产品"、"导出产品"

## 使用方法

### 基本用法

```bash
# 采集昨天的产品
python skills/yupoo-product-extractor/scripts/extract_products.py --date yesterday

# 采集指定日期的产品
python skills/yupoo-product-extractor/scripts/extract_products.py --date 2026-04-21

# 采集最近N天的产品
python skills/yupoo-product-extractor/scripts/extract_products.py --days 7
```

### 输出文件

- JSON 数据：`inputs/yupoo_products_{date}.json`
- Excel 文件：`inputs/yupoo_products_{date}.xlsx`

### Excel 列结构

| 列 | 内容 |
|---|---|
| A | No.（序号） |
| B | Product Name（产品名称） |
| C | English Product Name（英文产品名称，唯一） |
| D | Album ID（相册ID） |
| E | Image Count（图片数量） |
| F | First Image（首图链接） |
| G | Second Image（第二张图链接） |
| H | Image Links (Max 12)（剩余图片链接） |

## 依赖

- playwright-cli（浏览器自动化）
- openpyxl（Excel 生成）
- baidu-content-parser（图片识别，可选）

## 注意事项

1. 需要先在浏览器中登录 Yupoo 并保存会话状态
2. 图片 URL 格式：`http://pic.yupoo.com/{user_id}/{image_id}/{hash}.jpeg`
3. 英文产品名称自动确保唯一，重复的添加序号后缀
4. 颜色识别基于产品名称关键词，准确率有限

## 文件结构

```
skills/yupoo-product-extractor/
├── SKILL.md                          # 本文件
└── scripts/
    └── extract_products.py           # 主脚本
```

## 示例

```bash
# 采集昨天上架的所有产品
python skills/yupoo-product-extractor/scripts/extract_products.py --date yesterday

# 输出示例
# Loaded 96 products from Yupoo
# Total images: 1559
# Excel file created: inputs/yupoo_products_2026-04-21.xlsx
```
