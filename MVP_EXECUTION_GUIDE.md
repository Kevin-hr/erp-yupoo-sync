# ERP极限并发MVP - 执行手册

> 版本：v2.0 | 日期：2026-04-08 | P10 CTO 更新（基于踩坑测试）

---

## ⚠️ 当前状态（必读）

**并发方案踩踏，已回退到顺序执行。**

| 方案 | 状态 | 说明 |
|------|------|------|
| `sync_pipeline.py` 单流程 | ✅ **生产可用** | 顺序执行，完全稳定 |
| `concurrent_batch_final.py` | ❌ 踩踏失败 | 共享CDP session导致ERP表单互相覆盖 |
| `erp_tab_manager.py` | ❌ 失败 | ERP"复制"是SPA路由，非新Tab |
| 独立Browser Context | ❌ 失败 | Cookie注入后Yupoo提取失败 |

---

## 执行方式：顺序执行（稳定）

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
python scripts/sync_pipeline.py --album-id 230251075 --brand-name "BAPE" --product-name "Shark Hoodie" --use-cdp
python scripts/sync_pipeline.py --album-id 228499218 --brand-name "Nike" --product-name "Air Force 1" --use-cdp
python scripts/sync_pipeline.py --album-id 230897512 --brand-name "Adidas" --product-name "Yeezy Boost 350 V2" --use-cdp
```

### 批量任务JSON（用于顺序批处理脚本）

编辑 `batch_example.json`：
```json
[
  {"album_id": "230251075", "brand_name": "BAPE", "product_name": "Shark Hoodie"},
  {"album_id": "228499218", "brand_name": "Nike", "product_name": "Air Force 1"},
  {"album_id": "230897512", "brand_name": "Adidas", "product_name": "Yeezy Boost 350 V2"}
]
```

---

## 吞吐计算（顺序执行）

| 并发数 | 每商品耗时 | 每小时产出 |
|--------|-----------|-----------|
| 1（顺序） | ~2分钟 | **~30款/小时** |

> 实际速度取决于网络+ERP响应，约25-35款/小时。

---

## 并发踩踏问题说明

**根因**：所有worker共享同一个CDP Chrome session，点击ERP"复制"按钮后页面SPA路由跳转互相覆盖。

**修复方向**：每个worker需要独立Chrome实例 + 独立CDP端口（9222/9223/9224...）

---

## 文件清单

| 文件 | 说明 |
|------|------|
| `scripts/sync_pipeline.py` | 生产可用 - 单流程E2E |
| `scripts/concurrent_batch_final.py` | 并发版（踩踏，待修复） |
| `scripts/concurrent_batch_v2.py` | P8产出 - 独立Context（未验证） |
| `scripts/erp_tab_manager.py` | P8产出 - Tab池管理器（未验证） |
| `batch_example.json` | 测试数据 |
| `logs/CONCURRENT_DEBUG_20260408.md` | 并发踩坑完整记录 |
| `logs/sync_20260408.log` | 最近同步日志 |
| `screenshots/` | 截图留证 |

---

## 成功标志

```
Pipeline Execution Success (流水线执行成功)
Evidence saved: screenshots/verify_HHMMSS.png
```

---

> v2.0 | 2026-04-08 | P10 CTO 更新
