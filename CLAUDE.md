# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Working Directory

**Path**: `C:\Users\Administrator\Documents\GitHub\ERP`

```bash
cd C:\Users\Administrator\Documents\GitHub\ERP
```

---

## Project Overview

**ERP E-commerce Sync Automation** — Automates the flow of product images from Yupoo photo albums to MrShopPlus ERP for listing. Uses Playwright for browser-based automation with a pipeline/orchestrator architecture.

### Core Problem
Manual copying of image URLs from Yupoo and pasting into MrShopPlus is repetitive and error-prone. This system automates the 9-step Yupoo extraction + 6-step ERP upload process.

---

## Architecture

```
CLI / Timer Trigger
        ↓
SyncPipeline (6-stage orchestrator)
├── YupooExtractor     → Album navigation, batch external link extraction
├── MetadataPreparer   → URL formatting, batch preparation
├── MrShopLogin        → Cookie-based session persistence
├── FormNavigator      → Product form navigation
├── ImageUploader      → URL-based image insertion
└── Verifier           → Screenshot validation, save confirmation
```

**Key Constraint**: Each platform (Yupoo/MrShopPlus) maintains **independent browser contexts** — never share cookies or browser state between them.

---

## Scripts

| Script | Purpose | Key Features |
|--------|---------|--------------|
| `scripts/sync_pipeline.py` | Main E2E orchestrator | 6-stage pipeline, step-by-step resume, dry-run mode |
| `scripts/mrshop_image_upload.py` | Robust MrShopPlus uploader | Exponential backoff retry, state persistence, multi-selector fallback |
| `scripts/erp_image_uploader.py` | Standalone ERP uploader | Simplified upload workflow |

### Common Commands

```bash
# Full pipeline with album
python scripts/sync_pipeline.py --album-id 231019138

# Dry run (no actual changes)
python scripts/sync_pipeline.py --album-id 231019138 --dry-run

# Resume from specific step
python scripts/sync_pipeline.py --album-id 231019138 --step 3 --resume

# Standalone MrShopPlus uploader
python scripts/mrshop_image_upload.py --dry-run --headless --resume

# Clear saved state and restart
python scripts/mrshop_image_upload.py --clear-state
```

---

## Platform Credentials

| Platform | Username | Password | URL |
|----------|----------|----------|-----|
| Yupoo | `lol2024` | `9longt#3` | `https://lol2024.x.yupoo.com/albums` |
| MrShopPlus | `litzyjames5976@gmail.com` | `RX3jesthYF7d` | `https://www.mrshopplus.com` |

> Credentials appear in scripts for automation purposes. Treat as read-only reference.

---

## Key Implementation Details

### Pipeline Stages (sync_pipeline.py)
1. **EXTRACT** — Navigate Yupoo album, enter backend mode, extract ≤14 image URLs via batch external link feature
2. **PREPARE** — Format URLs as newline-separated batch
3. **LOGIN** — MrShopPlus cookie-based auth (loads from `cookies.json` if exists)
4. **NAVIGATE** — Navigate to product form URL pattern: `/#/product/form_DTB_proProduct/{id}`
5. **UPLOAD** — Open modal → URL upload tab → paste URLs → insert images
6. **VERIFY** — Screenshot capture + save button click

### Image Upload Flow (mrshop_image_upload.py)
```
Login → Navigate to product → Delete existing images → Open modal →
URL tab → Paste textarea → Insert images → Save
```
State is saved after each step for `--resume` capability.

### State Management
- `logs/mrshop_upload_state.json` — Tracks completed steps for resumability
- `logs/` — Contains timestamped execution logs
- `screenshots/` — Contains verification screenshots

---

## Data Flow

| Yupoo Source | MrShopPlus Field | Notes |
|--------------|------------------|-------|
| Album title | `商品名称` | Strip internal IDs (e.g., H110) |
| Album description | `商品描述` | Extract size info (M/XL/2XL) |
| Image URLs (≤14) | `商品图片` | 15th slot reserved for size chart |
| Category | `类别` | Map to ERP categories (e.g., BAPE → T-Shirt) |

---

## Constraints

- **Image limit**: ≤14 images per product (15th slot for size chart)
- **Cookie refresh**: Session cookies require manual refresh periodically
- **Concurrency**: ERP upload supports ≤3 concurrent workers to avoid rate limits
