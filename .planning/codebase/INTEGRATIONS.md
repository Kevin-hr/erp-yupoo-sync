# External Integrations

**Analysis Date:** 2026-04-07

## APIs & External Services

### Yupoo Platform (采集端)

**Service:** Yupoo Photo Album Service
- **Base URL:** `https://lol2024.x.yupoo.com/albums`
- **Login URL:** `https://x.yupoo.com/login`
- **Gallery URL Pattern:** `https://x.yupoo.com/gallery/{album_id}`

**Authentication:**
- Method: Username/Password form submission
- Selectors: `#c_username`, `#c_password`, `.login__button`
- Cookie persistence: `logs/yupoo_cookies.json`
- Session: 独立浏览器上下文，禁止与 MrShopPlus 共享

**Album Extraction (scripts/sync_pipeline.py lines 181-242):**
```
1. 直接访问相册: https://x.yupoo.com/gallery/{album_id}
2. 全选图片复选框: label.Checkbox__main:visible, .Checkbox__main:visible
3. 点击批量外链按钮: button:has-text('批量外链'), .toolbar__button:has-text('批量外链')
4. 预览/生成: span:has-text('预览'), button:has-text('生成外链')
5. 提取 textarea 内容: textarea.Input__input
6. 过滤 pic.yupoo.com 链接
7. 限制 14 张 (第 15 位留给尺码表)
```

### MrShopPlus ERP (上架端)

**Service:** MrShopPlus E-commerce ERP
- **Base URL:** `https://www.mrshopplus.com`
- **Login URL:** `https://www.mrshopplus.com/#/login`
- **Product List URL:** `https://www.mrshopplus.com/#/product/list_DTB_proProduct`

**Authentication:**
- Method: Username/Password form submission
- Selectors: `#username`, `input[placeholder='请输入密码']`, `#login-btn`
- Cookie persistence: `logs/cookies.json`

**Product Navigation & Upload (scripts/sync_pipeline.py lines 413-430):**
```
1. 访问商品列表: https://www.mrshopplus.com/#/product/list_DTB_proProduct
2. 点击复制按钮: i.i-ep-copy-document, .action-btn:has-text('复制')
3. 替换商品名称: input[placeholder='请输入商品名称'], input[placeholder*='商品名称']
4. 打开上传弹窗: .img-upload-btn
5. 切换到 URL 上传: .ant-tabs-tab:has-text('URL上传')
6. 粘贴图片链接: textarea (换行分隔)
7. 插入图片: button:has-text('插入图片视频')
8. 保存: button:has-text('保存')
9. 验证 URL 包含 action=3
```

## Data Storage

**Cookies (Browser Session Persistence):**
| File | Platform | Format | 用途 |
|------|----------|--------|------|
| `logs/cookies.json` | MrShopPlus | JSON (Playwright cookies) | ERP 会话复用 |
| `logs/yupoo_cookies.json` | Yupoo | JSON (Playwright cookies) | Yupoo 会话复用 |

**Logs:**
| File | Format | 用途 |
|------|--------|------|
| `logs/sync_YYYYMMDD.log` | Text | 每日执行日志 |
| `logs/album_{id}_urls.txt` | Text | 提取的图片 URL 列表 |

**Screenshots:**
| File | Format | 用途 |
|------|--------|------|
| `screenshots/verify_HHMMSS.png` | PNG | 验证截图 |
| `screenshots/check_album.png` | PNG | 相册检查 |
| `screenshots/yupoo_login.png` | PNG | Yupoo 登录验证 |
| `screenshots/erp_product_saved.png` | PNG | ERP 保存验证 |

**State Persistence:**
| File | Format | 用途 |
|------|--------|------|
| `logs/pipeline_state.json` | JSON | Pipeline 断点续传状态 |

## Authentication & Identity

**Yupoo Auth (scripts/sync_pipeline.py lines 145-178):**
```python
class YupooLogin:
    def login(self, context: BrowserContext) -> bool:
        # 1. 尝试加载已有 cookies
        if self.cookies_file.exists():
            await context.add_cookies(json.load(f))
            return True
        # 2. 无 cookie -> 表单登录
        await page.goto("https://x.yupoo.com/login")
        await safe_fill(page, "#c_username", self.username)
        await safe_fill(page, "#c_password", self.password)
        await page.click(".login__button")
        await page.wait_for_load_state('networkidle')
        # 3. 保存新 cookie
        cookies = await context.cookies()
        with open(self.cookies_file, 'w') as f:
            json.dump(cookies, f)
```

**MrShopPlus Auth (scripts/sync_pipeline.py lines 246-277):**
```python
class MrShopLogin:
    def login(self, context: BrowserContext) -> bool:
        # 同上模式，URL: https://www.mrshopplus.com/#/login
        # Selectors: #username, input[placeholder='请输入密码'], #login-btn
```

## Monitoring & Observability

**Error Tracking:**
- 内置 try/except 异常捕获
- 指数退避重试: `@async_retry(max_retries=3)` decorator

**Logs:**
- File: `logs/sync_YYYYMMDD.log`
- Console: stdout via `logging.StreamHandler(sys.stdout)`
- Format: `%(asctime)s [%(levelname)s] %(name)s: %(message)s`

**Screenshots:**
- 保存路径: `screenshots/`
- 命名规则: `{prefix}_{timestamp}.png`
- 用途: 操作证据、错误追溯

## Environment Configuration

**Required env vars (.env):**
| Variable | Default | 说明 |
|----------|---------|------|
| `YUPOO_USERNAME` | lol2024 | Yupoo 账号 |
| `YUPOO_PASSWORD` | 9longt#3 | Yupoo 密码 |
| `YUPOO_BASE_URL` | https://lol2024.x.yupoo.com/albums | Yupoo 基础 URL |
| `ERP_USERNAME` | zhiqiang | MrShopPlus 账号 |
| `ERP_PASSWORD` | 123qazwsx | MrShopPlus 密码 |
| `ERP_BASE_URL` | https://www.mrshopplus.com | ERP 基础 URL |
| `MAX_CONCURRENT_WORKERS` | 3 | 最大并发数 |
| `SAVE_SCREENSHOTS` | True | 是否保存截图 |
| `DRY_RUN` | False | 模拟运行模式 |

**Secrets Location:**
- Primary: `.env` file (NOT committed to git)
- Fallback: Environment variables
- Hardcoded defaults: 仅用于开发参考

## Cross-Cutting Concerns

**Browser Context Isolation:**
- Yupoo 和 MrShopPlus 必须使用独立 BrowserContext
- 禁止共享 Cookie 或会话状态
- 代码: `scripts/sync_pipeline.py` lines 403-405

**Anti-Fingerprinting:**
- Viewport 设置: `{'width': 1280, 'height': 800}`
- Headless 模式: `headless=False` (可见浏览器)
- 独立上下文隔离

**Retry Mechanism:**
```python
@async_retry(max_retries=3, initial_backoff=2.0)
async def safe_click(page, selector, timeout=5000, force=False):
    # 失败时指数退避: 2s -> 4s -> 8s
    # 触发条件: timeout, "outside" in error message
```

---

*Integration audit: 2026-04-07*
