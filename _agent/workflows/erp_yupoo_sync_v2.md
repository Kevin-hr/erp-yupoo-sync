---
description: Industrialized Yupoo to MrShopPlus ERP Synchronization Workflow (v2.1)
---

# Yupoo to ERP Sync Workflow (工业级同步工作流)

// turbo-all

## 1. Environment Setup (环境准备)
1. Ensure `.env` contains valid `YUPOO_USERNAME` and `ERP_USERNAME`.
2. Verify `yupoo_cookies.json` and `cookies.json` exist to bypass login UI.
3. Check network stability for `pic.yupoo.com` access.

## 2. Phase 1: Robust Extraction (稳健提取)
1. **Direct Navigation**: Go to `https://x.yupoo.com/gallery/<album_id>`.
2. **Item Selection**: Use `dispatch_event('click')` on `label.Checkbox__main` to select all items.
3. **Modal Trigger**: Force-click `批量外链` button.
4. **URL Capture**: Extract text from `textarea` and filter to exactly 14 URLs (ERP limit).

## 3. Phase 2: Metadata Injection (元数据注入)
1. Clean album title (remove internal codes like H110).
2. Format data for the ERP payload.

## 4. Phase 3: ERP 'Copy' Listing (ERP 复制上架)
1. **Form Entry**: Navigate to the product list `https://www.mrshopplus.com/#/product/list_DTB_proProduct`.
2. **Copy Template**: Identify a template product and click the `复制` (Copy) button (icon with two overlapping squares).
3. **Data Replacement**:
    - [NEW] Replace Title with official English name (Brand + Model).
    - [NEW] Replace images (clear old, paste new ≤ 14).
4. **Save Verification**: Click `保存` and wait for URL to transition to `action=3`.


## 5. Phase 4: Verification & Audit (验证与审计)
1. Capture screenshot of the final product form.
2. Log success/failure status to `logs/sync_results.json`.
3. Perform random 1-in-50 manual audit.
