# ERP MVP 执行手册 v3.0

> 版本：v3.0 | 日期：2026-04-15 | 基于双架构验证

---

## ⚠️ 当前状态（必读）

**双架构并行验证成功：架构A(Playwright) + 架构B(Excel中转)**

| 架构 | 脚本 | 状态 | 适用场景 |
|------|------|------|----------|
| **A: Playwright流水线** | `sync_pipeline.py` | ✅ 生产可用 | 单商品全自动，约2分钟 |
| **B: Excel中转批量导入** | `generate_saint_excel*.py` | ✅ DESCENTE/SAINT验证通过 | 批量导入，支持多规格 |

---

## 执行方式一：架构A - Playwright 6阶段流水线

### 前置准备

**1. 启动Chrome（CDP模式）**
```bash
"C:\Program Files\Google\Chrome\Application\chrome.exe" --remote-debugging-port=9222
```

**2. 手动登录**（保持两个Tab打开）

| 平台 | URL | 账号 |
|------|-----|------|
| Yupoo | https://lol2024.x.yupoo.com | lol2024 / 9longt#3 |
| MrShopPlus | https://www.mrshopplus.com | zhiqiang / 123qazwsx |

### 执行命令

```bash
cd C:\Users\Administrator\Documents\GitHub\ERP

# 每个商品单独执行（约2分钟/个）
python scripts/sync_pipeline.py --album-id 230251075 \
  --brand-name "BAPE" --product-name "Shark Hoodie" --use-cdp
```

### 成功标志

```
Pipeline Execution Success (流水线执行成功)
Evidence saved: screenshots/verify_HHMMSS.png
```

---

## 执行方式二：架构B - Excel中转批量导入

### Step 1: 生成Excel填充数据

```bash
# DESCENTE品牌（已验证 ✅）
python scripts/generate_saint_excel_v2.py --brand DESCENTE --album-id 232338513

# SAINT品牌（已验证 ✅）
python scripts/generate_saint_excel.py --album-id 527345264973337
```

### Step 2: ERP后台批量导入

1. 打开 ERP 后台: https://www.mrshopplus.com
2. 导航到商品管理 → 批量导入
3. 上传生成的 Excel 文件（如 `DESCENTE_232338513_商品导入模板.xlsx`）
4. 点击确认导入
5. 验证导入结果

### 验证通过的模板文件

| 品牌 | Excel文件 | 状态 |
|------|----------|------|
| DESCENTE | `DESCENTE_232338513_商品导入模板.xlsx` | ✅ |
| DESCENTE | `logs/商品导入模板_DESCENTE_232338513.xlsx` | ✅ |
| SAINT | `SAINT_商品导入模板.xlsx` | ✅ |
| SAINT | `logs/SAINT_商品导入模板_填充.xlsx` | ✅ |
| 其他 | `logs/商品导入结果_527345264973337.xlsx` | ✅ |

---

## Excel模板字段说明（架构B）

### 必填字段（P0级）

| 列 | 字段 | 值 | 说明 |
|----|------|-----|------|
| B | 商品标题* | 商品标题 | 最多255字符 |
| E | 商品首图* | URL | 单URL |
| I | 商品上架* | **N** | **强制下架！禁止Y** |
| J | 物流模板* | 默认模板 | 系统配置 |
| O | 不记库存* | N | 记库存 |
| P | 商品重量* | 0.8 | kg, 3位小数 |
| AD | 售价* | 88.99 | 2位小数 |

### 可选字段

| 列 | 字段 | 示例 |
|----|------|------|
| C | 副标题 | DESCENTE 联名系列 男子防风防水夹克 |
| H | 属性 | `品牌|DESCENTE\n款号|22-0975-91` |
| K | 类别名称 | 男装,外套 |
| L | 标签 | DESCENTE,ALLTERRAIN,防水夹克 |
| X/Y | 规格1/2 | `Color\nBlack` / `Size\nM: 肩宽46cm...` |
| AB | SKU值 | `Color:Black\nSize:M` |
| AD | 售价 | 88.99 |
| AE | 原价 | 149.99 |

---

## 吞吐计算

| 架构 | 方式 | 每商品耗时 | 每小时产出 |
|------|------|-----------|-----------|
| A: Playwright | 全自动 | ~2分钟 | ~30款/小时 |
| B: Excel中转 | 批量 | 手动导入 | 取决于批量大小 |

---

## 并发踩踏问题说明

**根因**：所有worker共享同一个CDP Chrome session，点击ERP"复制"按钮后页面SPA路由跳转互相覆盖。

**修复方向**：每个worker需要独立Chrome实例 + 独立CDP端口（9222/9223/9224...）

**当前状态**：单worker顺序执行是唯一稳定方案

---

## 关键约束（P0级）

| 规则 | 说明 | 违规后果 |
|------|------|----------|
| **强制下架** | I列=必须填写N | 违反业务合规/误发 |
| **图片≤14张** | 单商品最多14张 | 商品无法上架 |
| **独立浏览器** | Yupoo/MrShopPlus各自独立上下文 | SPA踩踏/会话混淆 |
| **CDP页面清理** | 只能关闭自己创建的page | 关闭Chrome导致CDP断开 |

---

## 文件清单

| 文件 | 说明 |
|------|------|
| `scripts/sync_pipeline.py` | ✅ 架构A主脚本 (~1425行) |
| `scripts/generate_saint_excel*.py` | ✅ 架构B Excel生成脚本 |
| `DESCENTE_232338513_商品导入模板.xlsx` | ✅ DESCENTE模板 |
| `SAINT_商品导入模板.xlsx` | ✅ SAINT模板 |
| `logs/` | 凭证、日志、填充结果 |
| `screenshots/` | 截图留证 |
| `docs/pipeline_flowchart.html` | ✅ 流水线流程图 v8.0 |
| `docs/yupoo_to_erp_excel_flow.html` | ✅ Excel中转流程图 v2.0 |

---

## 流程图文档

| 文档 | 内容 | 版本 |
|------|------|------|
| `docs/pipeline_flowchart.html` | 6阶段Playwright流水线流程图 | v8.0 ✅ |
| `docs/yupoo_to_erp_excel_flow.html` | Excel中转架构流程图 | v2.0 ✅ |

---

> v3.0 | 2026-04-15 | 新增架构B(Excel中转)，验证DESCENTE/SAINT模板
> v2.0 | 2026-04-08 | 并发踩坑回退到顺序执行
> v1.0 | 2026-04-03 | 初始版本
