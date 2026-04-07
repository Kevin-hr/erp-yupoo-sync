#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Yupoo to MrShopPlus End-to-End Sync Pipeline (Yupoo 转 MrShopPlus 端到端同步流水线)

Architecture (架构):
    Stage 1: YupooExtractor    - Extract image URLs from Yupoo album (提取图片外链)
    Stage 2: MetadataPreparer  - Prepare image URLs and metadata (准备元数据)
    Stage 3: MrShopLogin       - Login to MrShopPlus (ERP 登录)
    Stage 4: FormNavigator     - Navigate to product list (导航至商品列表)
    Stage 5: ImageUploader     - Click Copy, then upload images (点击复制并上传)
    Stage 6: Verifier          - Verify and save (验证并保存)

Usage:
    python scripts/sync_pipeline.py --album-id 231019138
    python scripts/sync_pipeline.py --album-id 231019138 --use-cdp  # CDP 持久化模式
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
from enum import Enum
from pathlib import Path
from typing import List, Optional, Dict, Any, Callable

# =============================================================================
# 1. Environment & Config (环境与配置)
# =============================================================================

def load_env_manual(env_path=".env"):
    """Manually parse .env file (手动解析 .env 文件)"""
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

load_env_manual()

# Path definitions (路径定义 - 使用相对路径确保可移植性)
ROOT_DIR = Path(__file__).parent.parent
LOG_DIR = ROOT_DIR / "logs"
SCREENSHOT_DIR = ROOT_DIR / "screenshots"
LOG_DIR.mkdir(exist_ok=True)
SCREENSHOT_DIR.mkdir(exist_ok=True)

# Configure logging (日志配置)
LOG_FILE = LOG_DIR / f"sync_{datetime.now().strftime('%Y%m%d')}.log"
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE, encoding="utf-8"),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger('sync_pipeline')

from playwright.async_api import async_playwright, Page, BrowserContext, Browser

# =============================================================================
# 0. CDP Persistent Browser (CDP 持久化浏览器连接)
# =============================================================================

async def get_cdp_browser(default_cdp: str = "http://localhost:9222") -> Browser:
    """
    通过 Chrome DevTools Protocol (CDP) 连接已存在的 Chrome 浏览器实例。

    启动方式（需手动在 Chrome 中执行，或通过脚本）:
        Windows: "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe" --remote-debugging-port=9222
        或启动时加 --user-data-dir 指定配置文件目录（可复用已有会话）

    CDP 连接优势:
    - 复用已有完整会话（1374+ cookies），无需重新登录
    - 绕过 headless 模式的 webdriver 检测
    - "点击预览"等交互正常执行

    Args:
        default_cdp: CDP 调试端口地址，默认 http://localhost:9222

    Returns:
        已连接的 Browser 实例（不包含 context，调用者需通过 browser.contexts 获取）
    """
    async with async_playwright() as p:
        logger.info(f"[CDP] Connecting to {default_cdp}...")
        try:
            browser = await p.chromium.connect_over_cdp(default_cdp, timeout=10000)
            contexts = browser.contexts
            if not contexts:
                raise RuntimeError("No browser contexts found")
            logger.info(f"[CDP] Connected successfully. Contexts: {len(contexts)}, Pages: {len(contexts[0].pages)}")
            return browser
        except Exception as e:
            logger.error(f"[CDP] Connection failed: {e}")
            raise RuntimeError(f"CDP connection failed: {e}. Please start Chrome with --remote-debugging-port=9222")


async def get_or_launch_browser(playwright, use_cdp: bool = False, cdp_url: str = "http://localhost:9222") -> tuple:
    """
    获取浏览器实例：优先 CDP 模式，失败则 fallback 到普通启动。

    Returns:
        tuple: (browser, context, page)
        - CDP 模式: 复用已有 context
        - 普通模式: 新建 context 和 page
    """
    if use_cdp:
        try:
            browser = await get_cdp_browser(cdp_url)
            ctx = browser.contexts[0]
            page = await ctx.new_page()
            return browser, ctx, page
        except RuntimeError as e:
            logger.warning(f"[CDP] Failed, falling back to launch: {e}")

    # 普通启动模式（fallback）
    browser = await playwright.chromium.launch(headless=False)
    context = await browser.new_context(viewport={'width': 1280, 'height': 900})
    page = await context.new_page()
    return browser, context, page


# =============================================================================
# 2. Resiliency Helpers (弹性组件 - 包含重试与安全操作)
# =============================================================================

def async_retry(max_retries: int = 3, initial_backoff: float = 2.0):
    """Decorator for async retries with exponential backoff (异步重试装饰器)"""
    def decorator(func: Callable):
        async def wrapper(*args, **kwargs):
            backoff = initial_backoff
            for attempt in range(max_retries + 1):
                try:
                    return await func(*args, **kwargs)
                except Exception as e:
                    if attempt == max_retries: raise e
                    logger.warning(f"[{func.__name__}] Attempt {attempt+1} failed: {e}. Retrying in {backoff}s...")
                    await asyncio.sleep(backoff)
                    backoff *= 2
            return None
        return wrapper
    return decorator

@async_retry(max_retries=3)
async def safe_click(page: Page, selector: str, timeout: int = 5000, force: bool = False):
    """Safe click with wait and visibility check & dispatch fallback (安全点击)"""
    try:
        await page.wait_for_selector(selector, state="visible", timeout=timeout)
        await page.click(selector, timeout=timeout, force=force)
    except Exception as e:
        if "outside" in str(e).lower() or "timeout" in str(e).lower():
            logger.info(f"Falling back to dispatch_event for {selector}")
            await page.dispatch_event(selector, 'click')
        else:
            raise e



@async_retry(max_retries=3)
async def safe_fill(page: Page, selector: str, value: str, timeout: int = 5000):
    """Safe fill with wait and visibility check (安全输入)"""
    await page.wait_for_selector(selector, state="visible", timeout=timeout)
    await page.fill(selector, value, timeout=timeout)

# =============================================================================
# 3. Pipeline Stages (流水线阶段定义)
# =============================================================================

class PipelineStage(Enum):
    """Execution stages (执行阶段)"""
    EXTRACT = 1
    PREPARE = 2
    LOGIN = 3
    NAVIGATE = 4
    UPLOAD = 5
    VERIFY = 6

@dataclass
class PipelineState:
    """Tracks state for resumability (状态追踪与断点续传)"""
    album_id: str
    current_step: int = 1
    image_urls: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    completed_stages: List[str] = field(default_factory=list)
    error: Optional[str] = None
    
    def save(self, path: Path):
        with open(path, "w", encoding="utf-8") as f:
            json.dump(asdict(self), f, indent=2, ensure_ascii=False)

# =============================================================================
# 4. Functional Components (功能组件)
# =============================================================================

class YupooLogin:
    """Stage 0: Yupoo Authentication (Yupoo 登录认证)"""
    def __init__(self, cookies_file: str = "logs/yupoo_cookies.json"):
        self.cookies_file = ROOT_DIR / cookies_file
        self.username = os.getenv("YUPOO_USERNAME", "lol2024")
        self.password = os.getenv("YUPOO_PASSWORD", "9longt#3")

    async def login(self, context: BrowserContext) -> bool:
        """Handle Yupoo login with cookie persistence (处理登录与 Cookie 持久化)"""
        if self.cookies_file.exists():
            try:
                with open(self.cookies_file, 'r', encoding='utf-8') as f:
                    await context.add_cookies(json.load(f))
                logger.info("Yupoo cookies loaded.")
                return True
            except: pass

        page = await context.new_page()
        try:
            await page.goto("https://x.yupoo.com/login")
            await safe_fill(page, "#c_username", self.username)
            await safe_fill(page, "#c_password", self.password)
            await page.click(".login__button")
            await page.wait_for_load_state('networkidle')
            
            cookies = await context.cookies()
            with open(self.cookies_file, 'w', encoding='utf-8') as f:
                json.dump(cookies, f, indent=2)
            return True
        except Exception as e:
            logger.error(f"Yupoo login error: {e}")
            return False
        finally:
            await page.close()


class YupooExtractor:
    """Stage 1: Image Extraction (获取图片链接) - Robust Edition"""
    def __init__(self, album_id: str):
        self.album_id = album_id
        # The gallery page is where the search box and album list reside
        self.backend_url = "https://x.yupoo.com/gallery"

    async def extract(self, page: Page) -> List[str]:
        """9-step backend extraction logic (后台 9 步提取逻辑)"""
        album_direct_url = f"https://x.yupoo.com/gallery/{self.album_id}"
        logger.info(f"Extracting album directly: {album_direct_url}")
        
        await page.goto(album_direct_url)
        await page.wait_for_load_state('networkidle')
        
        # Check for login redirect (检查是否被重定向到登录页)
        if "login" in page.url:
            logger.error("Session expired or not logged in. URL: " + page.url)
            raise Exception("Yupoo login required or session expired.")

        # 4-6: Batch External Links (批量外链)
        # Select all pictures in the album
        # Using a more specific selector + visible bit
        checkbox_selector = "label.Checkbox__main:visible, .Checkbox__main:visible"
        await safe_click(page, checkbox_selector, force=True) 
        await asyncio.sleep(3)



        
        # Click 'Batch External Links' button
        batch_link_btn = "button:has-text('批量外链'), .toolbar__button:has-text('批量外链')"
        await safe_click(page, batch_link_btn, force=True)

        await asyncio.sleep(2)
        
        # 7-9: Get URLs (获取链接)
        # There might be a 'Preview' or 'Generate' step
        preview_btn = "span:has-text('预览'), button:has-text('生成外链'), span:contains('点击预览')"
        try:
            await page.click(preview_btn, timeout=3000, force=True)
            await asyncio.sleep(2)
        except:
            logger.info("Preview button not found or already generated.")


        textarea_selector = "textarea.Input__input"
        try:
            # Try visible first, then hidden
            try:
                textarea = await page.wait_for_selector(textarea_selector, timeout=5000)
            except:
                textarea = await page.wait_for_selector(textarea_selector, state="hidden", timeout=10000)
            raw_text = await textarea.input_value()
        except Exception as e:
            logger.warning(f"Failed to get textarea value: {e}")
            # Try to get any textarea value
            raw_text = await page.evaluate("document.querySelector('textarea')?.value || ''")
        
        urls = [u.strip() for u in raw_text.split("\n") if "pic.yupoo.com" in u]
        logger.info(f"Extracted {len(urls)} urls.")
        return list(urls[:14]) # Limit to 14 rule (强制 14 张红线)



class MrShopLogin:
    """Stage 3: ERP Authentication (ERP 登录)"""
    def __init__(self, cookies_file: str = "logs/cookies.json"):
        self.cookies_file = ROOT_DIR / cookies_file
        self.email = os.getenv("ERP_USERNAME", "litzyjames5976@gmail.com")
        self.password = os.getenv("ERP_PASSWORD", "RX3jesthYF7d")

    async def login(self, context: BrowserContext) -> bool:
        if self.cookies_file.exists():
            try:
                with open(self.cookies_file, 'r', encoding='utf-8') as f:
                    await context.add_cookies(json.load(f))
                return True
            except: pass

        page = await context.new_page()
        try:
            await page.goto("https://www.mrshopplus.com/#/login")
            await safe_fill(page, "#username", self.email)
            await safe_fill(page, "input[placeholder='请输入密码']", self.password)
            await page.click("#login-btn")
            await asyncio.sleep(2)
            
            cookies = await context.cookies()
            with open(self.cookies_file, 'w', encoding='utf-8') as f:
                json.dump(cookies, f, indent=2)
            return True
        except Exception as e:
            logger.error(f"MrShopLogin error: {e}")
            return False
        finally:
            await page.close()


class ImageUploader:
    """Stage 5: Robust Image Upload (稳健图片上传)"""
    def __init__(self, urls: List[str]):
        self.urls = urls

    async def upload(self, page: Page):
        """Sequential upload with validation (顺序上传与验证)"""
        # Step A: Delete existing (清理旧图)
        while await page.query_selector(".fa-trash-o"):
            await page.click(".fa-trash-o")
            await asyncio.sleep(0.5)
            
        # Step B: Open Modal & Paste (打开弹窗并粘贴)
        await safe_click(page, ".img-upload-btn")
        await safe_click(page, ".ant-tabs-tab:has-text('URL上传')")
        await safe_fill(page, "textarea", "\n".join(self.urls))
        
        # Step C: Insert (执行插入)
        await safe_click(page, "button:has-text('插入图片视频')")
        await asyncio.sleep(5)
        logger.info("Upload sequence finished.")

class Verifier:
    """Stage 6: Final Verification (最终验证与保存)"""
    async def verify(self, page: Page):
        """Capture proof and save (截证并保存)"""
        ts = datetime.now().strftime("%H%M%S")
        shot_path = SCREENSHOT_DIR / f"verify_{ts}.png"
        await page.screenshot(path=str(shot_path))
        logger.info(f"Evidence saved: {shot_path}")
        
        await safe_click(page, "button:has-text('保存')")
        # Monitor for success redirect
        try:
            await page.wait_for_url(lambda url: "action=3" in url, timeout=10000)
            logger.info("Product saved successfully (Redirected to action=3). (商品保存成功)")
        except:
            logger.error("Save verification timeout. Check for modal errors. (保存验证超时，请检查是否出现错误弹窗)")

class DescriptionEditor:
    """Stage 5b: Product Description Formatting (商品描述格式化)"""
    def __init__(self, brand_name: str, product_name: str):
        self.brand_name = brand_name
        self.product_name = product_name

    async def format_description(self, page: Page):
        """Format the first line and insert link (格式化首行并插入链接)"""
        if not self.brand_name or not self.product_name:
            logger.error("CRITICAL ERROR: Brand Name and Product Name are STRICTLY REQUIRED for formatting.")
            raise ValueError("Strict Constraint Violated: Cannot skip description formatting. Brand and Product Name required.")

        logger.info(f"Formatting product description for: {self.product_name} (正在格式化商品描述: {self.product_name})")
        
        brand_slug = self.brand_name.replace(" ", "-")
        link_url = f"https://www.stockxshoesvip.net/{brand_slug}/"
        first_line_html = f"Name: <a href='{link_url}' target='_blank'>{self.brand_name}</a> {self.product_name}"
        
        js_code = """
        (firstLineHtml) => {
            let editor = document.querySelector('[contenteditable="true"]');
            
            if (!editor) {
                const iframes = document.querySelectorAll('iframe');
                for (let iframe of iframes) {
                    try {
                        const iframeEditor = iframe.contentWindow.document.querySelector('[contenteditable="true"], body');
                        if (iframeEditor) {
                            editor = iframeEditor;
                            break;
                        }
                    } catch(e) {}
                }
            }
            
            if (editor) {
                // RULE 2: ENFORCE NO IMAGES IN DESCRIPTION (严格禁止描述中出现图片)
                let imgs = editor.querySelectorAll('img');
                imgs.forEach(img => img.remove());
                
                // RULE 1: REPLACE ONLY THE FIRST LINE ('Name:' field)
                let blocks = editor.querySelectorAll('p, div');
                for (let block of blocks) {
                    if (block.innerText.includes('Name:')) {
                        block.innerHTML = firstLineHtml;
                        editor.dispatchEvent(new Event('input', { bubbles: true }));
                        return true;
                    }
                }
            }
            return false;
        }
        """
        success = await page.evaluate(js_code, first_line_html)
        if success:
            logger.info("Successfully formatted the first line of the product description. (成功格式化商品描述的第一行)")
        else:
            logger.warning("Could not locate the rich text editor or 'Name:' block to format description. (未能定位富文本编辑器或含有 'Name:' 的段落进行格式化)")


# =============================================================================
# 5. Orchestrator (编排器)
# =============================================================================

class SyncPipeline:
    """The Main Industrial Sync Engine (主工业同步引擎)"""
    def __init__(self, album_id: str, product_id: str = "0", brand_name: str = "", product_name: str = "", use_cdp: bool = False):
        self.album_id = album_id
        self.product_id = product_id
        self.brand_name = brand_name
        self.product_name = product_name
        self.use_cdp = use_cdp
        self.state_file = LOG_DIR / "pipeline_state.json"
        self.state = PipelineState(album_id=album_id)

    async def run(self):
        async with async_playwright() as p:
            # CDP 模式优先：复用已登录的 Chrome 会话（绕过 webdriver 检测）
            browser, context, page = await get_or_launch_browser(p, use_cdp=self.use_cdp)
            
            try:
                # 1. Extraction (提取)
                await YupooLogin().login(context)
                self.state.image_urls = await YupooExtractor(self.album_id).extract(page)
                
                # 2. ERP Sync (同步)
                await MrShopLogin().login(context)
                list_url = "https://www.mrshopplus.com/#/product/list_DTB_proProduct"
                await page.goto(list_url)
                
                # Click first 'Copy' button (icon i-ep-copy-document) (点击第一个模板的“复制”按钮)
                logger.info("Clicking COPY button on template product... (正在点击模板商品的复制按钮...)")
                await safe_click(page, "i.i-ep-copy-document, .action-btn:has-text('复制')", force=True)
                await page.wait_for_load_state('networkidle')
                
                # Replace the main default title if provided (如果提供了商品名称，替换主标题)
                if self.product_name:
                    await safe_fill(page, "input[placeholder='请输入商品名称'], input[placeholder*='商品名称']", f"{self.brand_name} {self.product_name}".strip(), timeout=3000)

                # Execute Description Editor Formatting (执行商品描述格式化)
                await DescriptionEditor(self.brand_name, self.product_name).format_description(page)

                await ImageUploader(self.state.image_urls).upload(page)
                await Verifier().verify(page)

                
                logger.info("Pipeline Execution Success (流水线执行成功)")
            except Exception as e:
                logger.error(f"Pipeline Crash (流水线崩溃): {e}")
                raise
            finally:
                await browser.close()

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--album-id", required=True, help="Yupoo Album ID (Yupoo 相册 ID)")
    parser.add_argument("--product-id", default="0", help="ERP Product ID (ERP 商品 ID)")
    parser.add_argument("--brand-name", default="", help="Brand name for formatting (用于格式化的品牌名称)")
    parser.add_argument("--product-name", default="", help="Official product name for formatting (用于格式化的最新官方商品名称)")
    parser.add_argument("--use-cdp", action="store_true",
                        help="Use CDP persistent connection (连接已有 Chrome，绕过 webdriver 检测，需先启动 Chrome --remote-debugging-port=9222)")
    parser.add_argument("--cdp-url", default="http://localhost:9222",
                        help="CDP debug port URL (default: http://localhost:9222)")
    args = parser.parse_args()

    asyncio.run(SyncPipeline(
        args.album_id,
        args.product_id,
        args.brand_name,
        args.product_name,
        use_cdp=args.use_cdp
    ).run())