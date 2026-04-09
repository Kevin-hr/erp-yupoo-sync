#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
独立浏览器上下文并发批量同步 v2 (Independent Browser Context Concurrent Batch Sync v2)
===========================================================
核心改动：每个 worker 完全独立闭环，不再共享任何 browser / context / page。
- 每个 worker: async with async_playwright() -> browser -> context -> 2 pages
- 每个 worker 用完立即关闭自己的 browser
- asyncio.Semaphore 控制并发数量

用法 (Usage):
python scripts/concurrent_batch_v2.py --batch batch_products.json --workers 3

字段说明 (batch_products.json Fields):
  [
    {"album_id": "231019138", "brand_name": "BAPE", "product_name": "Shark Hoodie"},
    ...
  ]
"""

import argparse
import asyncio
import json
import logging
import os
import sys
import time
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from typing import List, Optional

# =============================================================================
# Environment & Config (环境加载)
# =============================================================================

def load_env_manual(env_path: str = ".env") -> None:
    """手动解析 .env 文件 (manual .env parser)"""
    if not os.path.exists(env_path):
        return
    with open(env_path, "r", encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" in line:
                key, value = line.split("=", 1)
                os.environ[key.strip()] = value.strip()

# 初始化环境
load_env_manual()

# 路径定义
ROOT_DIR = Path(__file__).parent.parent
LOG_DIR = ROOT_DIR / "logs"
SCREENSHOT_DIR = ROOT_DIR / "screenshots"
LOG_DIR.mkdir(exist_ok=True)
SCREENSHOT_DIR.mkdir(exist_ok=True)

# 日志配置 (Logging Configuration)
LOG_FILE = LOG_DIR / f"concurrent_v2_{datetime.now().strftime('%Y%m%d')}.log"
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE, encoding="utf-8"),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger('concurrent_v2')

# Playwright 导入检查
try:
    from playwright.async_api import async_playwright, Page, BrowserContext, Browser
except ImportError:
    logger.error("CRITICAL: playwright not installed. Run: pip install playwright && playwright install chromium")
    sys.exit(1)

# =============================================================================
# Retry & Safe Helpers (重试与安全工具函数)
# =============================================================================

def async_retry(max_retries: int = 3, base_delay: float = 1.0):
    """指数退避重试装饰器 (exponential backoff retry decorator)"""
    def decorator(func):
        async def wrapper(*args, **kwargs):
            last_exception: Optional[Exception] = None
            for attempt in range(max_retries):
                try:
                    return await func(*args, **kwargs)
                except Exception as e:
                    last_exception = e
                    delay = base_delay * (2 ** attempt)
                    logger.warning(f"[{func.__name__}] 尝试 {attempt + 1}/{max_retries} 失败: {e}, {delay:.1f}秒后重试")
                    await asyncio.sleep(delay)
            if last_exception:
                logger.error(f"[{func.__name__}] 所有 {max_retries} 次尝试均失败: {last_exception}")
                raise last_exception
            raise RuntimeError(f"[{func.__name__}] Unknown error after retries")
        return wrapper
    return decorator

@async_retry(max_retries=3, base_delay=1.0)
async def safe_click(page: Page, selector: str, timeout: int = 5000, force: bool = False) -> bool:
    """安全点击，带 dispatch_event 回退 (safe click with dispatch fallback)"""
    try:
        await page.wait_for_selector(selector, state="visible", timeout=timeout)
        await page.click(selector, timeout=timeout, force=force)
        return True
    except Exception as e:
        if "outside" in str(e).lower() or "timeout" in str(e).lower():
            logger.info(f"回退至 dispatch_event 点击: {selector}")
            await page.dispatch_event(selector, 'click')
            return True
        raise e

@async_retry(max_retries=3, base_delay=1.0)
async def safe_fill(page: Page, selector: str, value: str, timeout: int = 5000) -> bool:
    """安全填充 (safe fill)"""
    await page.wait_for_selector(selector, state="visible", timeout=timeout)
    await page.fill(selector, value, timeout=timeout)
    return True

# =============================================================================
# Data Models (数据模型)
# =============================================================================

@dataclass
class ProductTask:
    """单个商品同步任务数据类 (single product sync task)"""
    album_id: str
    brand_name: str
    product_name: str
    product_id: str = "0"
    status: str = "pending"
    error: Optional[str] = None
    start_time: Optional[float] = None
    end_time: Optional[float] = None
    image_urls: List[str] = field(default_factory=list)

@dataclass
class BatchResult:
    """批量同步结果汇总 (batch sync result)"""
    total: int = 0
    success: int = 0
    failed: int = 0
    start_time: float = 0.0
    end_time: float = 0.0
    results: List[dict] = field(default_factory=list)

# =============================================================================
# CDP Cookie Extractor (从已有Chrome提取Cookie)
# =============================================================================

async def extract_cookies_from_cdp(cdp_url: str = "http://localhost:9222") -> List[dict]:
    """从已运行的代理Chrome CDP会话提取Cookie，用于绕过验证码 (extract cookies from running Chrome)"""
    cookies: List[dict] = []
    try:
        async with async_playwright() as p:
            # 这里的连接超时要短，避免挂起
            browser = await p.chromium.connect_over_cdp(cdp_url, timeout=5000)
            for ctx in browser.contexts:
                try:
                    cookies = await ctx.cookies()
                    await browser.disconnect()
                    logger.info(f"[CDP] 从浏览器中提取了 {len(cookies)} 个 Cookie")
                    return cookies
                except Exception:
                    pass
            await browser.disconnect()
    except Exception as e:
        logger.debug(f"[CDP] 无法通过 CDP 提取 Cookie (可能没开浏览器): {e}")
    return cookies

# =============================================================================
# Yupoo Operations (Yupoo 提取组件)
# =============================================================================

async def yupoo_login(context: BrowserContext) -> bool:
    """Yupoo 登录认证，优先从本地文件恢复 (Yupoo login with cookie persistence)"""
    cookies_file = LOG_DIR / "yupoo_cookies.json"
    username = os.getenv("YUPOO_USERNAME")
    password = os.getenv("YUPOO_PASSWORD")
    if not username:
        raise ValueError("YUPOO_USERNAME environment variable is required")
    if not password:
        raise ValueError("YUPOO_PASSWORD environment variable is required")

    if cookies_file.exists():
        try:
            with open(cookies_file, 'r', encoding='utf-8') as f:
                cookies = json.load(f)
            # 过滤过期 cookie
            import time as _time
            valid_cookies = []
            expired_count = 0
            for cookie in cookies:
                if 'expiry' in cookie and cookie['expiry'] < _time.time():
                    expired_count += 1
                    logger.warning(f"Yupoo Cookie {cookie.get('name')} expired at {cookie['expiry']}")
                    continue
                valid_cookies.append(cookie)
            cookies = valid_cookies
            if expired_count > 0:
                logger.warning(f"Yupoo Cookies: {expired_count} 个已过期，已跳过")
            if not cookies:
                logger.warning("Yupoo: 无有效 Cookie，需重新登录")
            else:
                await context.add_cookies(cookies)
                logger.info(f"Yupoo Cookie 已从本地加载（{len(cookies)} 个有效）")
                return True
        except Exception:
            pass

    page = await context.new_page()
    try:
        await page.goto("https://x.yupoo.com/login", timeout=20000)
        await safe_fill(page, "#c_username", username)
        await safe_fill(page, "#c_password", password)
        await page.click(".login__button")
        await page.wait_for_load_state('networkidle', timeout=20000)
        await asyncio.sleep(3)
        cookies = await context.cookies()
        with open(cookies_file, 'w', encoding='utf-8') as f:
            json.dump(cookies, f, indent=2)
        return True
    except Exception as e:
        logger.error(f"Yupoo 登录失败: {e}")
        return False
    finally:
        try:
            await page.close()
        except:
            pass
    return True


async def extract_yupoo_urls(album_id: str, page: Page) -> List[str]:
    """
    CDP拦截模式：通过拦截 Yupoo API 响应获取原始图片 Path (XHR Interception mode)
    遵循教训 R1/R6: 必须包含 hash 字段，拼接格式为 http://pic.yupoo.com{path}
    """
    album_url = f"https://x.yupoo.com/gallery/{album_id}"
    logger.info(f"[{album_id}] 正在访问相册 (XHR 拦截模式): {album_url}")

    api_response_data = None

    async def handle_response(response):
        nonlocal api_response_data
        if "/api/albums/" in response.url and "/photos" in response.url and response.status == 200:
            try:
                api_response_data = await response.json()
                logger.debug(f"[{album_id}] 捕获到 API 响应: {response.url}")
            except Exception as e:
                logger.error(f"[{album_id}] 解析 API 响应失败: {e}")

    page.on("response", handle_response)
    
    try:
        await page.goto(album_url, timeout=20000)
        # 遵循教训：Yupoo 有轮询请求，使用 'load' 状态而非 'networkidle'
        await page.wait_for_load_state('load', timeout=15000)
        
        # 等待数据捕获 (轮询 10 秒)
        for _ in range(50):
            if api_response_data:
                break
            await asyncio.sleep(0.2)

        if not api_response_data:
            # Fallback for DOM recovery if XHR fails
            logger.warning(f"[{album_id}] XHR 拦截未捕获到数据，尝试降级至 DOM 解析")
            return await _extract_yupoo_urls_dom_fallback(album_id, page)

        # 解析 API 数据
        photos = api_response_data.get("data", {}).get("list", [])
        urls = []
        for p in photos:
            path = p.get("path")
            if path:
                # 拼接外链格式：http://pic.yupoo.com/user/hash/id.jpeg
                urls.append(f"http://pic.yupoo.com{path}")
        
        logger.info(f"[{album_id}] 从 API 提取了 {len(urls)} 张完整图片 URLs")
        return urls[:14]

    finally:
        page.remove_listener("response", handle_response)
    
    # 确保总是有返回
    return []


async def _extract_yupoo_urls_dom_fallback(album_id: str, page: Page) -> List[str]:
    """DOM 降级解析 (仅限 XHR 失败时)"""
    photo_ids: List[str] = await page.evaluate("""() => {
        const ids = [];
        const pattern = /photo\\.yupoo\\.com\\/([^\\/]+)\\/([^\\/]+)\\/small\\.(?:jpg|jpeg)/gi;
        let match;
        const html = document.documentElement.outerHTML;
        while ((match = pattern.exec(html)) !== null) { ids.push(match[2]); }
        return [...new Set(ids)];
    }""")
    _username = os.getenv("YUPOO_USERNAME")
    if not _username:
        raise ValueError("YUPOO_USERNAME environment variable is required for DOM fallback")
    user = _username.split("@")[0]
    return [f"http://pic.yupoo.com/{user}/{pid}/" for pid in photo_ids[:14]]

# =============================================================================
# ERP Operations (ERP 上传组件)
# =============================================================================

async def erp_login(context: BrowserContext) -> bool:
    """ERP 登录认证 (ERP login management)"""
    cookies_file = LOG_DIR / "cookies.json"
    email = os.getenv("ERP_USERNAME")
    password = os.getenv("ERP_PASSWORD")
    if not email:
        raise ValueError("ERP_USERNAME environment variable is required")
    if not password:
        raise ValueError("ERP_PASSWORD environment variable is required")

    # 尝试加载持久化 Cookie
    if cookies_file.exists():
        try:
            with open(cookies_file, 'r', encoding='utf-8') as f:
                cookies = json.load(f)
            # 过滤过期 cookie
            import time as _time
            valid_cookies = []
            expired_count = 0
            for cookie in cookies:
                if 'expiry' in cookie and cookie['expiry'] < _time.time():
                    expired_count += 1
                    logger.warning(f"[ERP] Cookie {cookie.get('name')} expired at {cookie['expiry']}")
                    continue
                valid_cookies.append(cookie)
            cookies = valid_cookies
            if expired_count > 0:
                logger.warning(f"[ERP] Cookies: {expired_count} 个已过期，已跳过")
            if not cookies:
                logger.warning("[ERP] 无有效 Cookie，需重新登录")
            else:
                await context.add_cookies(cookies)
                logger.info(f"[ERP] 从文件成功恢复了 {len(cookies)} 个有效 Cookie")
                return True
        except Exception as e:
            logger.warning(f"[ERP] Cookie 恢复失败: {e}")

    page = await context.new_page()
    try:
        await page.goto("https://www.mrshopplus.com/#/login", timeout=30000)
        await safe_fill(page, "#username", email)
        await safe_fill(page, "input[placeholder='请输入密码']", password)
        await page.click("#login-btn")
        await page.wait_for_load_state('networkidle', timeout=30000)
        await asyncio.sleep(5)
        
        if "login" in page.url.lower():
            logger.error("ERP 登录失败：仍停留在登录页面")
            await page.screenshot(path=str(SCREENSHOT_DIR / "erp_login_failed.png"))
            return False
            
        cookies = await context.cookies()
        with open(cookies_file, 'w', encoding='utf-8') as f:
            json.dump(cookies, f, indent=2)
        logger.info("[ERP] 登录成功并已保存会话。")
        return True
    except Exception as e:
        logger.error(f"ERP 登录异常: {e}")
        return False
    finally:
        try:
            await page.close()
        except:
            pass
    return False


async def clear_old_images(page: Page) -> None:
    """清理模板中残留的旧图片 (cleanup legacy template images)"""
    while await page.query_selector(".fa-trash-o"):
        await page.click(".fa-trash-o")
        await asyncio.sleep(0.3)


async def format_description(page: Page, brand_name: str, product_name: str) -> bool:
    # 品牌 Slug 规范 (Brand Slug standard): 
    # 1. 超过两个单词中间必须使用 '-' (hyphen between words)
    # 2. 严禁使用 .lower()，需保留原始品牌名的大小写 (preserves case)
    # 3. 规范: https://www.stockxshoesvip.net/Brand-Name/
    brand_slug = brand_name.strip().replace(" ", "-")
    link_url = f"https://www.stockxshoesvip.net/{brand_slug}/"
    first_line_html = f"Name: <a href='{link_url}' target='_blank'>{brand_name}</a> {product_name}"

    js_code = """
    (firstLineHtml) => {
        let editor = document.querySelector('[contenteditable="true"]');
        if (!editor) {
            const iframes = document.querySelectorAll('iframe');
            for (let iframe of iframes) {
                try {
                    const e = iframe.contentWindow.document.querySelector('[contenteditable="true"], body#tinymce, .mce-content-body');
                    if (e) { editor = e; break; }
                } catch(e) {}
            }
        }
        if (editor) {
            // 工业化红线：严格移除所有 img 标签 (Remove all images in description)
            editor.querySelectorAll('img').forEach(img => img.remove());
            
            // 查找包含 Name: 的第一个块 (Find first block with Name:)
            // 使用正则表达式确保精确匹配起始位置
            const blocks = editor.querySelectorAll('p, div, h1, h2, span');
            let found = false;
            for (let block of blocks) {
                // 使用正则匹配 Name: 块（忽略前导空白）
                if (/^\\s*Name\\s*:/i.test(block.innerText)) {
                    block.innerHTML = firstLineHtml;
                    found = true;
                    break;
                }
            }
            // 如果没找到 Name: 行，则在最前面插入
            if (!found) {
                const newBlock = document.createElement('p');
                newBlock.innerHTML = firstLineHtml;
                editor.prepend(newBlock);
            }
            
            // 触发输入事件确保 Vue/Editor 同步状态
            editor.dispatchEvent(new Event('input', {bubbles: true}));
            editor.dispatchEvent(new Event('change', {bubbles: true}));
            if (typeof tinyMCE !== 'undefined' && tinyMCE.activeEditor) {
                tinyMCE.activeEditor.setDirty(true);
            }
            return true;
        }
        return false;
    }
    """
    success = await page.evaluate(js_code, first_line_html)
    if success:
        logger.info("商品描述格式化成功")
    else:
        logger.warning("未找到 'Name:' 标识行进行格式化")
    return success


async def upload_images_by_url(page: Page, urls: List[str]) -> None:
    """通过 ERP 的 URL 上传功能进行批量插图 (bulk image insertion via URL)"""
    await clear_old_images(page)
    await asyncio.sleep(0.5)
    # 工业级上传按钮定位逻辑 (Align with erp_tab_manager.py)
    upload_selectors = [
        ".img-upload-btn", 
        "button:has-text('上传图片')", 
        ".upload-container.editor-upload-btn",
        "[class*='upload']"
    ]
    working_upload_sel = None
    for sel in upload_selectors:
        try:
            await page.wait_for_selector(sel, timeout=5000)
            working_upload_sel = sel
            break
        except Exception:
            continue
    
    if not working_upload_sel:
        raise RuntimeError("无法在 ERP 编辑页找到图片上传入口")

    await safe_click(page, working_upload_sel)
    await asyncio.sleep(0.5)

    # 切换到 URL 标签 (Switch to URL tab - support both Element Plus and Ant Design)
    tab_selectors = [
        ".el-tabs__item:has-text('URL上传')",
        ".ant-tabs-tab:has-text('URL上传')",
        ".el-tabs__item:has-text('URL')",
        "div[role='tab']:has-text('URL')",
        "div:has-text('URL上传')"
    ]
    tab_found = False
    for t_sel in tab_selectors:
        try:
            await page.wait_for_selector(t_sel, timeout=3000)
            await safe_click(page, t_sel)
            tab_found = True
            break
        except:
            continue
    
    if not tab_found:
        logger.warning("[ERP] 未能找到 URL 上传标签，尝试通过 JS 切换")
        await page.evaluate("""() => {
            const tabs = document.querySelectorAll('.el-tabs__item, .ant-tabs-tab, div[role="tab"], div');
            for (const t of tabs) {
                if (t.innerText.trim() === 'URL上传' || t.innerText.trim() === 'URL') { 
                    t.click(); 
                    return true;
                }
            }
            return false;
        }""")

    await asyncio.sleep(1)

    # 填充 URLs (遵循教训 R3: 使用 JS 绕过 maxlength=153)
    urls_text = "\n".join(urls)
    await page.evaluate(f"""(text) => {{
        const ta = document.querySelector('.el-dialog .el-textarea__inner, textarea');
        if (ta) {{
            ta.value = text;
            ta.dispatchEvent(new Event('input', {{ bubbles: true }}));
            ta.dispatchEvent(new Event('change', {{ bubbles: true }}));
        }}
    }}""", urls_text)
    logger.info(f"[ERP] 已通过 JS 注入 {len(urls)} 条图片 URLs")

    await asyncio.sleep(1)
    
    # 点击确认插入
    insert_selectors = ["button:has-text('插入图片视频')", "button:has-text('确认')", "button:has-text('确定')"]
    for i_sel in insert_selectors:
        try:
            await page.wait_for_selector(i_sel, timeout=3000)
            await safe_click(page, i_sel)
            break
        except:
            continue

    # 等待图片服务器回访下载 (Waiting for server to fetch images)
    await asyncio.sleep(8)
    logger.info(f"{len(urls)} 张图片已插入表单")


async def set_listing_status(page: Page, online: bool = False) -> None:
    """
    最高规则：强制设置商品上架状态 (Highest Rule: Force Product Listing Status)
    
    MrShopPlus ERP 的"商品上架"是一个开关(Switch)。
    - online=True: 保持上架 (Not recommended by Highest Rule)
    - online=False: 设定为下架/灰色 (Mandatory for human audit)
    """
    try:
        # 定位"商品上架"所在的表单项
        listing_item = page.locator(".el-form-item", has_text="商品上架").first
        if await listing_item.count() == 0:
            logger.warning("[ERP] 未能找到 '商品上架' 选项，跳过状态设置")
            return

        # 定位开关组件
        switch = listing_item.locator(".el-switch")
        if await switch.count() == 0:
            logger.warning("[ERP] 未能找到上架开关组件")
            return

        # 增强型：使用 JS 强制探测与切换 (Robust JS Toggling)
        target_state = "true" if online else "false"
        toggle_js = f"""
        async () => {{
            const item = Array.from(document.querySelectorAll('.el-form-item')).find(el => el.innerText.includes('商品上架'));
            if (!item) return 'error_not_found';
            const switchEl = item.querySelector('.el-switch');
            if (!switchEl) return 'error_no_switch';
            
            const isChecked = switchEl.getAttribute('aria-checked') === 'true';
            const target = {{ 'true': true, 'false': false }}['{target_state}'];
            
            if (isChecked !== target) {{
                // 尝试点击核心区域
                const core = switchEl.querySelector('.el-switch__core') || switchEl;
                core.click();
                return 'toggled';
            }}
            return 'already_correct';
        }}
        """
        result = await page.evaluate(toggle_js)
        if result == 'toggled':
            logger.info(f"[ERP] 🚀 成功触发状态切换 -> {'上架' if online else '下架'}")
            await asyncio.sleep(1) # 等待动画完成
        elif result == 'already_correct':
            logger.info(f"[ERP] 商品状态已符合预期 (无需操作)")
        else:
            logger.warning(f"[ERP] 状态切换异常: {result}")

    except Exception as e:
        logger.warning(f"[ERP] 设置上架状态时发生非致命异常: {e}")


async def verify_and_save(page: Page, album_id: str) -> bool:
    """保存商品并验证 action=3 生命周期跳转 (save and lifecycle verification)"""
    ts = datetime.now().strftime("%H%M%S")
    shot_path = SCREENSHOT_DIR / f"v2_verify_{album_id}_{ts}.png"
    await page.screenshot(path=str(shot_path))
    logger.info(f"[{album_id}] 保存前截图已留存: {shot_path}")

    await safe_click(page, "button:has-text('保存')")
    try:
        # action=3 表示保存成功后的跳转状态
        await page.wait_for_url(lambda url: "action=3" in url, timeout=15000)
        logger.info(f"[{album_id}] 商品保存成功 (检测到 action=3 跳转)")
        return True
    except Exception as e:
        logger.error(f"[{album_id}] 保存验证失败或超时: {e}")
        return False

# =============================================================================
# CORE: Single Worker - 完全独立闭环 (fully isolated worker)
# =============================================================================

async def process_single_product(
    task: ProductTask,
    semaphore: asyncio.Semaphore,
) -> ProductTask:
    """
    核心 Worker：实现去共享化。每个任务拥有独立的浏览器实例。
    (Fully isolated worker: each task gets its own playwright/browser/context instance)
    """
    task.status = "running"
    task.start_time = time.time()
    worker_id = id(asyncio.current_task())

    logger.info(f"[{task.album_id}] ▶ Worker {worker_id} 开始处理 - {task.brand_name} {task.product_name}")

    browser: Optional[Browser] = None

    try:
        async with semaphore:
            # ---- Step 1: 启动物理隔离的独立浏览器 ----
            async with async_playwright() as p:
                try:
                    browser = await p.chromium.launch(
                        headless=False, # 冒烟测试开启界面
                        args=['--disable-blink-features=AutomationControlled']
                    )
                except Exception as e:
                    logger.error(f"[{task.album_id}] 浏览器启动失败: {e}")
                    raise RuntimeError(f"浏览器环境异常: {e}")

                context: BrowserContext = await browser.new_context(viewport={'width': 1280, 'height': 900})

                try:
                    # 注入 CDP Cookie 以降低登录成本（影子测试模式）
                    cdp_cookies = await extract_cookies_from_cdp()
                    if cdp_cookies:
                        try:
                            await context.add_cookies(cdp_cookies)
                            logger.info(f"[{task.album_id}] 已注入 CDP 影子 Cookie")
                        except Exception as e:
                            logger.warning(f"[{task.album_id}] CDP Cookie 注入失效: {e}")

                    yupoo_page = await context.new_page()
                    erp_page = await context.new_page()

                    # ---- Step 2: Yupoo 图片资源获取 ----
                    await yupoo_login(context)
                    task.image_urls = await extract_yupoo_urls(task.album_id, yupoo_page)
                    if not task.image_urls:
                        raise RuntimeError("Yupoo 提取结果为空，流程终止。")
                    await yupoo_page.close()

                    # ---- Step 3: ERP 表单自动化 ----
                    login_ok = await erp_login(context)
                    if not login_ok:
                        raise RuntimeError("无法完成 ERP 登录认证")

                    await erp_page.goto(
                        "https://www.mrshopplus.com/#/product/list_DTB_proProduct",
                        wait_until="networkidle", timeout=30000
                    )
                    await asyncio.sleep(3)

                    # 工业级复制按钮定位逻辑
                    copy_selectors = [
                        "i.i-ep-copy-document",
                        ".action-btn:has-text('复制')",
                        "[class*='copy']",
                        "i[class*='copy']"
                    ]
                    working_selector = None
                    for sel in copy_selectors:
                        try:
                            # 缩小等待范围，快速探测
                            await erp_page.wait_for_selector(sel, timeout=5000)
                            logger.info(f"[{task.album_id}] 复制入口定位成功: {sel}")
                            working_selector = sel
                            break
                        except Exception:
                            pass
                    if not working_selector:
                        raise RuntimeError("未能在 ERP 列表中找到复制操作入口")

                    # 工业级：处理复制后的 Vue 状态挂载问题 (Fresh Navigation Fix)
                    # 遵循 sync_pipeline.py 的教训：直接定位到 pkValues 以干净挂载上传组件
                    await safe_click(erp_page, working_selector, force=True)
                    
                    # 等待 URL 变化并提取 pkValues
                    try:
                        await erp_page.wait_for_url(lambda u: "pkValues=" in u, timeout=10000)
                        import re
                        match = re.search(r"pkValues=([^&]+)", erp_page.url)
                        if match:
                            pk_value = match.group(1)
                            fresh_url = f"https://www.mrshopplus.com/#/product/form_DTB_proProduct/0?action=4&pkValues={pk_value}"
                            logger.info(f"[{task.album_id}] 🚀 执行 [Fresh Navigation] 修复 Vue 挂载: {fresh_url}")
                            # 强制刷新页面以确保 Vue 组件完全重新初始化
                            await erp_page.goto(fresh_url, timeout=30000)
                            await erp_page.wait_for_load_state('networkidle', timeout=20000)
                    except Exception as e:
                        logger.warning(f"[{task.album_id}] Fresh Navigation 尝试失败 (非致命): {e}")

                    await asyncio.sleep(2)

                    # 写入新标题
                    title_selector = "input[placeholder='请输入商品名称'], input[placeholder*='商品名称']"
                    await erp_page.wait_for_selector(title_selector, timeout=5000)
                    await erp_page.fill(title_selector, f"{task.brand_name} {task.product_name}")
                    
                    # 格式化描述区域并上传外链图片
                    await format_description(erp_page, task.brand_name, task.product_name)
                    await upload_images_by_url(erp_page, task.image_urls)

                    # 🚀 执行最高规则：确保商品初始为下架状态
                    await set_listing_status(erp_page, online=False)

                    # 保存并验证
                    saved = await verify_and_save(erp_page, task.album_id)
                    if not saved:
                        raise RuntimeError("保存后服务器未返回 action=3 成功标识")

                    task.status = "success"
                    logger.info(
                        f"[{task.album_id}] ✓ 同步成功 (耗时: {time.time() - task.start_time:.1f}s)"
                    )

                finally:
                    try: 
                        await context.close()
                    except: 
                        pass

    except Exception as e:
        task.status = "failed"
        task.error = str(e)
        logger.error(f"[{task.album_id}] ✗ 工作流中断: {e}")
        
        # 失败现场快照 (failure snapshot)
        try:
            ts = datetime.now().strftime("%H%M%S")
            fail_shot = SCREENSHOT_DIR / f"v2_fail_{task.album_id}_{ts}.png"
            # 尝试在 erp_page 还在时截图
            if 'erp_page' in locals() and erp_page:
                await erp_page.screenshot(path=str(fail_shot))
                logger.info(f"[{task.album_id}] 失败现场已保存: {fail_shot}")
        except:
            pass

    finally:
        # 销毁该 Worker 的专用浏览器实例
        if browser:
            try:
                await browser.close()
                logger.debug(f"[{task.album_id}] 独立浏览器进程已销毁")
            except:
                pass

    task.end_time = time.time()
    return task

# =============================================================================
# Batch Orchestrator (批量编排器)
# =============================================================================

async def run_batch_concurrent(
    tasks: List[ProductTask],
    max_workers: int = 3,
) -> BatchResult:
    """并发运行批量同步，完全去共享化 (fully de-shared concurrent batch runner)"""

    result = BatchResult(
        total=len(tasks),
        start_time=time.time(),
        success=0,
        failed=0
    )

    logger.info(f"🚀 启动 v2 批量流水线: {len(tasks)} 个商品, 最大并发: {max_workers}")

    semaphore = asyncio.Semaphore(max_workers)

    # 启动异步任务池
    worker_tasks = [
        process_single_product(task, semaphore)
        for task in tasks
    ]

    # 并发执行并归集结果
    completed = await asyncio.gather(*worker_tasks, return_exceptions=False)

    for task in completed:
        if isinstance(task, ProductTask):
            result.results.append({
                "album_id": task.album_id,
                "brand_name": task.brand_name,
                "product_name": task.product_name,
                "status": task.status,
                "duration": round(task.end_time - task.start_time, 1) if task.end_time and task.start_time else None,
                "error": task.error,
                "image_count": len(task.image_urls)
            })
            if task.status == "success":
                result.success += 1
            else:
                result.failed += 1

    result.end_time = time.time()

    # 结果持久化存档 (Result Archiving)
    result_path = LOG_DIR / f"batch_v2_result_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(result_path, "w", encoding="utf-8") as f:
        json.dump(asdict(result), f, indent=2, ensure_ascii=False)

    total_time = result.end_time - result.start_time
    logger.info("=" * 60)
    logger.info(f"📊 批量同步任务完成: 总数={result.total}, 成功={result.success}, 失败={result.failed}")
    logger.info(f"⏱  总时长: {total_time:.1f}s | 平均单品效能: {(total_time / max(result.total, 1)):.1f}s")
    logger.info(f"💾 归档路径: {result_path}")
    logger.info("=" * 60)

    return result

# =============================================================================
# Batch Loader (批量任务加载器)
# =============================================================================

def load_batch_from_json(json_path: str) -> List[ProductTask]:
    """从 JSON 配置文件加载待同步清单 (load tasks from JSON file)"""
    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    tasks: List[ProductTask] = []
    for item in data:
        task = ProductTask(
            album_id=str(item.get("album_id", "")),
            brand_name=item.get("brand_name", ""),
            product_name=item.get("product_name", ""),
            product_id=str(item.get("product_id", "0"))
        )
        if task.album_id and task.brand_name and task.product_name:
            tasks.append(task)
        else:
            logger.warning(f"跳过无效条目 (缺少必要字段): {item}")

    logger.info(f"成功加载了 {len(tasks)} 条同步任务 (源自: {json_path})")
    return tasks

# =============================================================================
# Entry Point (入口)
# =============================================================================

def main():
    parser = argparse.ArgumentParser(
        description="独立浏览器上下文并发批量同步 v2 (每个worker独立browser)"
    )
    parser.add_argument("--batch", required=True, help="批量商品JSON文件路径")
    parser.add_argument("--workers", type=int, default=3, help="最大并发数 (推荐 ≤ 3)")
    args = parser.parse_args()

    # 1. 加载清单
    tasks = load_batch_from_json(args.batch)
    if not tasks:
        logger.error("清单为空，流程提前结束。")
        sys.exit(1)

    # 2. 异步执行
    asyncio.run(run_batch_concurrent(tasks, args.workers))

if __name__ == "__main__":
    main()
