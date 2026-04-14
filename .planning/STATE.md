# State

## Project
ERP Sync Pipeline — Milestone v3.1: Excel中转站模式

## Last Updated
2026-04-15

## Current Position

Phase: Not started (defining requirements)
Plan: —
Status: Defining requirements
Last activity: 2026-04-15 — Milestone v3.1.0 started (Excel中转站模式)

## Accumulated Context

### v3.0.0 交付物（已验证）
- CDP XHR 拦截提取：`/api/albums/{id}/photos` 含 hash 完整 path
- Docker 容器化部署：`Dockerfile` + `docker-compose.yml`
- Cookie 过期检测：MrShopLogin + YupooLogin 已添加 expiry 检查
- 强制下架审核：所有同步商品 `上架=N`
- ERP 导入字段映射：33列模板，2 Sheet（商品信息 + 计量单位）

### 核心痛点（v3.1 解决）
- TinyMCE 编辑器 JS 注入脆弱 → 改用 Excel 批量导入
- textarea maxlength=153 绕过不可靠 → 改用 Excel URL 列
- 单条复制效率低 → 改用 Excel 批量导入

### 待办

| Date | Title | Area |
|------|-------|------|
| 2026-04-15 | Excel 中转站模式 v3.1.0 | tooling |
