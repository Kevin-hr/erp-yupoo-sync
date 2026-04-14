# ERP 相册同步流水线 (Yupoo to MrShopPlus ERP Sync Pipeline)

## What This Is

将 Yupoo 相册产品图片自动同步至 MrShopPlus ERP 完成上架的浏览器自动化流水线。核心流程：Yupoo 提取外链 → Excel 中转填充 → ERP 批量导入 → 截图留证。

## Core Value

用最小的操作步骤、最低的维护成本，将相册产品可靠地批量上架到 ERP。绕过 TinyMCE/表单操作等脆弱环节，用 Excel 批量导入取而代之。

## Requirements

### Validated

- [x] **v1.0** Yupoo 相册提取 + ERP 单条表单上传（基础可用）
- [x] **v2.0** CDP 工业级提取器 + 熔断机制 + 并发安全重构
- [x] **v2.3.0** 强制下架审核 + 审计状态 + Cookie 过期检测
- [x] **v3.0.0** 工业级同步流水线 v3：CDP 提取器 + Docker 容器化 + SOP.md

### Active

- [ ] **v3.1.0** Excel 中转站模式：Excel 模板填充 + ERP 批量导入（进行中）

### Out of Scope

- ERP API 直接对接（无公开 API，需逆向）
- 多语言 ERP 系统支持
- 独立部署的 Web UI

## Context

### 项目背景

多品牌跨境电商运营需要将 Yupoo 相册中的产品图片同步至 MrShopPlus ERP 完成上架。品牌包括：WE11DONE、DESCENTE、SAINT LAURENT 等，需要高效批量处理。

### 现有资源

- **Excel 导入模板**：`商品导入模板 (1).xlsx`（33列，商品信息 + 计量单位 2个Sheet）
- **ERP 导入结果**：`商品导入结果_527345264973337.xlsx`（实际导入验证）
- **ERP 账号**：`zhiqiang / 123qazwsx`，Base URL: `https://www.mrshopplus.com`
- **Yupoo 账号**：`lol2024 / 9longt#3`
- **已验证提取器**：CDP XHR 拦截提取 `/api/albums/{id}/photos`

### 技术环境

- Python + Playwright（CDP 连接现有 Chrome）
- Docker 容器化部署（已验证）
- lark-cli 飞书集成能力
- ERP 商品导入字段映射（来自实际导入结果文件）

### ERP 导入字段映射（已验证）

| Excel 列 | 字段名 | 数据来源 | 处理说明 |
|----------|--------|----------|----------|
| 商品标题 | `商品标题*` | 相册标题 | 去除内部编号（如H110）|
| 商品描述 | `商品描述` | 相册描述 | 提取尺码行，移除图片 |
| 商品首图 | `商品首图*` | Yupoo 外链第1张 | URL |
| 商品其他图片 | `商品其他图片` | Yupoo 外链第2-14张 | 换行分隔，≤14张 |
| 规格1 | `规格1` | 相册描述颜色行 | 如 Color:Yellow |
| 规格2 | `规格2` | 相册描述尺码行 | 如 Size:41 |
| SKU值 | `SKU值` | 颜色+尺码组合 | `Color:Yellow\nSize:41` |
| 售价/原价 | `售价*/原价` | ERP 商品价格 | 参考模板默认值 |
| 商品上架 | `商品上架*` | — | 强制 `N`（下架待审）|
| 物流模板 | `物流模板*` | — | ERP 系统配置 |
| 类别名称 | `类别名称` | 相册分类名 | 品牌→类别映射 |
| 计量单位 | `计量单位` | — | 参考计量单位Sheet |

### 核心痛点（v3.1 待解决）

| 痛点 | 当前方案 | 问题 |
|------|----------|------|
| TinyMCE 编辑器操作 | JS 注入绕过 iframe | 脆弱，维护成本高 |
| textarea maxlength=153 | JS 注入控制 value | 绕过行为不可靠 |
| 图片上传需要新鲜导航 | Fresh Navigation 逻辑 | 逻辑复杂易出错 |
| 单条复制操作慢 | sync_pipeline.py 单worker | 效率低 |

**解决思路**：放弃表单操作，改用 Excel 批量导入，绕过所有前端限制。

## Evolution

This document evolves at phase transitions and milestone boundaries.

**After each phase transition** (via `/gsd-transition`):
1. Requirements invalidated? → Move to Out of Scope with reason
2. Requirements validated? → Move to Validated with phase reference
3. New requirements emerged? → Add to Active
4. Decisions to log? → Add to Key Decisions
5. "What This Is" still accurate? → Update if drifted

**After each milestone** (via `/gsd-complete-milestone`):
1. Full review of all sections
2. Core Value check — still the right priority?
3. Audit Out of Scope — reasons still valid?
4. Update Context with current state

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Excel 中转站架构 | 绕过 TinyMCE/表单操作脆弱环节，用 ERP 原生批量导入 | v3.1.0 进行中 |
| 强制下架审核 | 所有同步商品必须设为下架状态，禁止自动发布 | v2.3.0 已验证 |
| CDP XHR 拦截提取 | 正则拼图图片外链 404，改用拦截 `/api/albums/{id}/photos` | v3.0.0 已验证 |
| 单worker + CDP共享Chrome | 所有并发方案因 SPA 路由踩踏失败 | v2.3.0 已验证 |

---

*Last updated: 2026-04-15 — v3.1.0 Excel中转站模式 started*
