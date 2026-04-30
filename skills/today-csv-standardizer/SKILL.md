# Skill: today-csv-standardizer

把“多图片列”合并为 E 列（换行分隔），并基于 C 列中文名 + D 列首图做颜色识别生成英文名，回填到 B 列。

## 触发场景

- 用户要求“把 E 列之后图片合并到 E 列”
- 用户要求“按 C 中文名 + D 首图做图像识别后填 B 英文名”
- 用户要求“输出标准：A~E 五列（A序号/B英文/C中文/D首图/E其他图换行）”

## 输入与输出

### 输入（CSV）

支持两类输入：

1) 含 `pic_01..pic_14` 的 CSV（例如 today_*.csv）
- 首图 = `pic_01`
- 其他图 = `pic_02..pic_14` 合并到 E 列

2) 含列名 `B/C/D/E/F/...` 的 CSV（从 Excel 导出的平铺表）
- C=中文名、D=首图
- E 及之后的图片列合并到 E

### 输出（CSV 标准）

固定 5 列：

| 列 | 含义 |
|---|---|
| A | 序号 |
| B | 产品英文名（必须英文、不能为空、不可重复） |
| C | 产品中文名 |
| D | 产品首图（URL） |
| E | 产品其他图片（换行分隔） |

## 使用方法

```bash
python skills/today-csv-standardizer/scripts/standardize_today_csv.py ^
  --input inputs/today_2026-04-25_35.csv ^
  --output inputs/today_2026-04-25_35_standard.csv
```

## 规则说明

- 英文名生成：颜色识别（从 D 首图计算主色）+ 中文关键词映射（如 短袖/T恤→T-Shirt，刺绣→Embroidered 等）
- 英文名去重：若 B 列出现重复，则从第 2 个开始在末尾追加空格 + 序号（如 `xxx 2`、`xxx 3`）
- 标题格式：用空格拼接，禁止带 ` - ` 这种分隔
