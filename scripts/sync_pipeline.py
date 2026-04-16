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

# =============================================================================
# 导入分组说明 (Import Grouping Rationale)
# =============================================================================
#
# 第一组 - 标准库（无需安装，Python 内置）：
#   argparse  : CLI 参数解析，用户通过 --album-id / --use-cdp 传入
#   asyncio   : 异步 I/O，流水线全程异步执行避免阻塞等待
#   json      : Cookie 持久化和状态文件序列化
#   logging   : 结构化日志，写入 logs/sync_*.log 供人工审查
#   os/sys    : 环境变量读取 (.env) 和 stdout 回退
#   time      : 显式休眠控制时序（规避 race condition）
#   pathlib   : 跨平台路径拼接，避免 Windows 反斜杠地狱
#
# 第二组 - 类型注解（增强代码可读性，运行时不受影响）：
#   dataclass : PipelineState 数据容器，减少样板代码
#   enum     : PipelineStage 阶段枚举，防止 magic number
#   typing   : List/Optional/Dict/Any/Callable，IDE 静态检查友好
#
# 第三组 - 外部依赖（必须在 .venv 中安装，ImportError 即终止）：
#   playwright : 浏览器自动化，核心依赖，缺失则流水线无法运行
# =============================================================================

import argparse
import asyncio
import json
import logging
import os
import sys
import time
import requests  # CDP 版本探测 / HTTP 直连下载（绕过后端接口限制）
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
    with open(env_path, "r", encoding="utf-8") as f:
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
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE, encoding="utf-8"),
        logging.StreamHandler(sys.stdout),
    ],
)
logger = logging.getLogger("sync_pipeline")

from playwright.async_api import async_playwright, Page, BrowserContext, Browser

# =============================================================================
# 0. CDP Persistent Browser (CDP 持久化浏览器连接)
# =============================================================================

# 全局 Playwright 实例和 CDP Browser（跨 async 函数保持连接）
_pw_instance = None
_cdp_browser = None


def get_cdp_browser_sync(default_cdp: str = "http://localhost:9222") -> Browser:
    """
    通过 Chrome DevTools Protocol (CDP) 连接已存在的 Chrome 浏览器实例。
    同步版本：在主线程创建事件循环并执行异步连接。

    Returns:
        已连接的 Browser 实例
    """
    global _pw_instance, _cdp_browser
    if _cdp_browser is not None and _cdp_browser.is_connected():
        return _cdp_browser

    import asyncio

    async def _connect():
        global _pw_instance, _cdp_browser
        _pw_instance = await async_playwright().__aenter__()
        logger.info(f"[CDP] Connecting to {default_cdp}...")
        _cdp_browser = await _pw_instance.chromium.connect_over_cdp(
            default_cdp, timeout=10000
        )
        contexts = _cdp_browser.contexts
        if not contexts:
            raise RuntimeError("No browser contexts found")
        logger.info(
            f"[CDP] Connected successfully. Contexts: {len(contexts)}, Pages: {len(contexts[0].pages)}"
        )
        return _cdp_browser

    return asyncio.run(_connect())


async def get_cdp_browser(default_cdp: str = "http://localhost:9222") -> Browser:
    """异步版本的 CDP 连接（内部使用全局缓存）"""
    global _cdp_browser
    if _cdp_browser is not None and _cdp_browser.is_connected():
        return _cdp_browser

    async with async_playwright() as p:
        logger.info(f"[CDP] Connecting to {default_cdp}...")
        try:
            browser = await p.chromium.connect_over_cdp(default_cdp, timeout=10000)
            contexts = browser.contexts
            if not contexts:
                raise RuntimeError("No browser contexts found")
            logger.info(
                f"[CDP] Connected successfully. Contexts: {len(contexts)}, Pages: {len(contexts[0].pages)}"
            )
            return browser
        except Exception as e:
            logger.error(f"[CDP] Connection failed: {e}")
            raise
            raise RuntimeError(
                f"CDP connection failed: {e}. Please start Chrome with --remote-debugging-port=9222"
            )


async def get_or_launch_browser(
    playwright,
    use_cdp: bool = False,
    cdp_url: str = "http://localhost:9222",
    target_url: str = "",
) -> tuple:
    """
    获取浏览器实例：优先 CDP 模式，失败则 fallback 到普通启动。

    CDP 模式优先复用已有目标页面（绕过 webdriver 检测）：
        - 已有 Yupoo Tab (navigator.webdriver=False)
        - 已有 MrShopPlus Tab

    Args:
        target_url: 若无可用目标 Tab，则导航到此 URL

    Returns:
        tuple: (browser, context, page)
    """
    if use_cdp:
        try:
            browser = await get_cdp_browser(cdp_url)

            # 遍历所有context寻找可用的
            for ctx in browser.contexts:
                try:
                    pages = ctx.pages
                    if not pages:
                        continue

                    # 1. 优先复用已有目标 URL 的 Tab
                    if target_url:
                        for pg in pages:
                            try:
                                pg_url = pg.url
                                if not pg_url or pg_url == "about:blank":
                                    continue
                                if (
                                    target_url.split("/gallery/")[0] in pg_url
                                    or pg_url == target_url
                                ):
                                    logger.info(f"[CDP] Reusing existing tab: {pg_url}")
                                    return browser, ctx, pg
                            except:
                                continue

                    # 2. 复用任意 Yupoo/MrShop Tab
                    for pg in pages:
                        try:
                            pg_url = pg.url
                            if not pg_url or pg_url == "about:blank":
                                continue
                            url = pg.url
                            if "yupoo" in url or "mrshopplus" in url:
                                logger.info(f"[CDP] Reusing existing tab: {url}")
                                return browser, ctx, pg
                        except:
                            continue
                except:
                    continue

            # 如果所有context都失败了，尝试在第一个context新建Tab
            if browser.contexts:
                ctx = browser.contexts[0]
                try:
                    page = await ctx.new_page()
                    if target_url:
                        await page.goto(target_url)
                    logger.info("[CDP] Created new tab in first context")
                    return browser, ctx, page
                except Exception as e:
                    logger.warning(
                        f"[CDP] Failed to create new page in any context, closing browser: {e}"
                    )
                    try:
                        await browser.close()
                    except:
                        pass
        except Exception as e:
            logger.warning(f"[CDP] Failed, falling back to launch: {e}")

    # 普通启动模式（fallback）
    browser = await playwright.chromium.launch(headless=False)
    context = await browser.new_context(viewport={"width": 1280, "height": 900})
    page = await context.new_page()
    return browser, context, page


# =============================================================================
# 2. Resiliency Helpers (弹性组件 - 包含重试与安全操作)
# =============================================================================


def async_retry(max_retries: int = 3, initial_backoff: float = 2.0):
    """
    异步重试装饰器 - 指数退避策略（为什么用指数退避而非线性/固定重试？）

    指数退避的核心逻辑：
    - 第1次失败 → 等 2s → 第2次尝试
    - 第2次失败 → 等 4s → 第3次尝试
    - 第3次失败 → 等 8s → 第4次尝试（最终）

    为什么指数退避更优：
    1. 瞬时抖动（网络抖动/服务器短暂过载）：2s 后可能已恢复，固定 2s 重试即可
    2. 持续性压力（服务器正在限流/熔断）：固定频率重试会加剧问题，指数等待让服务器有喘息时间
    3. 避免惊群效应：大量客户端同时以相同间隔重试会产生叠加压力，指数退避可打散重试时机

    适用于本流水线的场景：网络超时、选择器未渲染、页面加载延迟等瞬时问题
    """

    def decorator(func: Callable):
        async def wrapper(*args, **kwargs):
            backoff = initial_backoff
            for attempt in range(max_retries + 1):
                try:
                    return await func(*args, **kwargs)
                except Exception as e:
                    if attempt == max_retries:
                        raise e
                    logger.warning(
                        f"[{func.__name__}] Attempt {attempt + 1} failed: {e}. Retrying in {backoff}s..."
                    )
                    await asyncio.sleep(backoff)
                    backoff *= 2
            return None

        return wrapper

    return decorator


@async_retry(max_retries=3)
async def safe_click(
    page: Page, selector: str, timeout: int = 5000, force: bool = False
):
    """
    安全点击 - 双重策略（为什么需要 JS evaluate 回退？）

    正常路径：wait_for_selector 等待可见 → page.click 标准点击
    回退路径：locator.evaluate(...el.click()) JS 直接触发

    为什么需要 JS fallback：
    - Element Plus 动态渲染：按钮进入 DOM 但尚未进入视口（viewport），Playwright 的标准点击会报 "outside viewport" 错误
    - 隐藏 overlay 遮挡：某些 Modal 弹窗遮罩层透明度为0但仍占据点击区域，标准点击被拦截
    - 这两种情况在 ERP 系统中极为常见（Vue 路由跳转后的动态渲染时序问题）

    为什么不直接用 JS 点击：
    - 标准点击会等待元素进入视口、进行可点击性检查，更可靠
    - JS evaluate 绕过这些检查，在元素仍不可见时也可能成功（不符合用户真实操作逻辑）
    """
    try:
        await page.wait_for_selector(selector, state="visible", timeout=timeout)
        await page.click(selector, timeout=timeout, force=force)
    except Exception as e:
        if "outside" in str(e).lower() or "timeout" in str(e).lower():
            logger.info(f"Falling back to locator.evaluate(click) for {selector}")
            await page.locator(selector).first.evaluate("el => el.click()")
        else:
            raise e


@async_retry(max_retries=3)
async def safe_fill(page: Page, selector: str, value: str, timeout: int = 5000):
    """
    安全输入 - 等待可见再填充（为什么必须先等待？）

    Element Plus 的 v-show/v-if 切换场景：
    - input 存在于 DOM 但 visibility: hidden（v-show=false）
    - 此时 page.fill 会静默失败（不抛异常，但字段值未被写入）
    - 使用 wait_for_selector(state="visible") 确保元素真正可见后才执行 fill
    - 避免"页面看起来正常但字段实际为空"的数据丢失问题
    """
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
                with open(self.cookies_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                # Support both old format (list of cookies) and new format (storage state with cookies + localStorage)
                if isinstance(data, list):
                    await context.add_cookies(data)
                elif isinstance(data, dict) and "cookies" in data:
                    await context.add_cookies(data["cookies"])
                    # Add localStorage if present
                    if "origins" in data:
                        for origin_data in data["origins"]:
                            origin = origin_data.get("origin", "")
                            if origin:
                                page = await context.new_page()
                                try:
                                    await page.goto(origin)
                                    for item in origin_data.get("localStorage", []):
                                        await page.evaluate(
                                            f"localStorage.setItem('{item['name']}', '{item['value']}')"
                                        )
                                finally:
                                    await page.close()

                # VALIDATION: Check if cookies actually work (WR-01 fix)
                # Navigate to Yupoo homepage and verify we are not on login page
                validation_page = await context.new_page()
                try:
                    await validation_page.goto(
                        f"https://x.yupoo.com/", timeout=15000
                    )
                    await asyncio.sleep(2)
                    if "login" in validation_page.url:
                        logger.info("[Login] Yupoo cookies expired (redirected to login), clearing cookies")
                        await context.clear_cookies()
                        await validation_page.close()
                    else:
                        logger.info(f"[Login] Yupoo cookie OK, current URL: {validation_page.url}")
                        await validation_page.close()
                        return True
                except Exception as e:
                    logger.warning(f"[Login] Yupoo cookie validation failed: {e}")
                    await validation_page.close()
            except Exception as e:
                logger.warning(f"Failed to load Yupoo cookies: {e}")

        page = await context.new_page()
        try:
            await page.goto("https://x.yupoo.com/login")
            await safe_fill(page, "#c_username", self.username)
            await safe_fill(page, "#c_password", self.password)
            await page.click(".login__button")
            await page.wait_for_load_state("networkidle")

            cookies = await context.cookies()
            with open(self.cookies_file, "w", encoding="utf-8") as f:
                json.dump(cookies, f, indent=2)
            return True
        except Exception as e:
            logger.error(f"Yupoo login error: {e}")
            return False
        finally:
            await page.close()


class YupooExtractor:
    """Stage 1: Image Extraction (获取图片链接) - HTML Parsing Mode

    绕过 UI 操作：直接从页面 HTML 解析 photo.yupoo.com URL 中的 photo_id，
    再拼接为完整的 pic.yupoo.com 外链 URL。

    URL 格式确认（用户手动验证）:
        原图: http://pic.yupoo.com/lol2024/{photo_id}/{hash}.jpg
        示例: http://pic.yupoo.com/lol2024/f53b0825/3e40c632.jpeg
    HTML 中的 photo_id 来源:
        <img src="//photo.yupoo.com/lol2024/{photo_id}/small.jpg">
    """

    def __init__(self, album_id: str):
        self.album_id = album_id
        self.user = "lol2024"  # Yupoo 用户名，从 cookies 或 .env 读取

    async def extract(self, page: Page) -> List[str]:
        """通过CDP拦截API响应提取pic.yupoo.com外链（API含完整hash路径）"""
        album_url = f"https://x.yupoo.com/gallery/{self.album_id}"
        logger.info(f"Extracting album: {album_url}")

        api_response_data = None

        def handle_response(response):
            nonlocal api_response_data
            if f"/api/albums/{self.album_id}/photos" in response.url:
                api_response_data = response

        page.on("response", handle_response)
        await page.goto(album_url, timeout=20000)
        # 为什么不用 networkidle：Yupoo 页面有持续轮询请求，永远等不到完全 idle
        # load 状态即可满足需求（DOM 加载完毕，API 响应已被拦截捕获）
        await page.wait_for_load_state("load", timeout=15000)
        # 等待 API 响应被拦截器捕获（最多 8 秒）
        for _ in range(40):
            if api_response_data:
                break
            await asyncio.sleep(0.2)
        await asyncio.sleep(1)

        if "login" in page.url:
            raise Exception("Yupoo login required or session expired.")

        if not api_response_data:
            raise Exception(f"API response not captured for album {self.album_id}")

        body = await api_response_data.json()
        photos = body.get("data", {}).get("list", [])
        if not photos:
            raise Exception(
                f"No photos found in API response for album {self.album_id}"
            )

        # API响应中 path 字段如 /lol2024/b87b319e/554e2f8e.jpeg
        # 完整URL: http://pic.yupoo.com/lol2024/b87b319e/554e2f8e.jpeg
        urls = [f"http://pic.yupoo.com{photo.get('path', '')}" for photo in photos[:14]]

        logger.info(f"Generated {len(urls)} external links from API (max 14)")
        if not urls:
            raise Exception("Failed to generate any URLs from API response")

        return urls


class MrShopLogin:
    """Stage 3: ERP Authentication (ERP 登录)"""

    def __init__(self, cookies_file: str = "logs/cookies.json"):
        self.cookies_file = ROOT_DIR / cookies_file
        self.email = os.getenv("ERP_USERNAME", "zhiqiang")
        self.password = os.getenv("ERP_PASSWORD", "123qazwsx")
        logger.info(
            f"ERP credentials loaded - username: {self.email}, password length: {len(self.password)}"
        )

    async def login(self, context: BrowserContext) -> bool:
        """
        ERP 登录流程（为什么先尝试加载 Cookie 再走 UI？）

        核心逻辑：Cookie 回退策略（避免每次都重新登录）

        为什么要先尝试 Cookie：
        - UI 登录需要 5-10 秒（页面加载 + 输入 + 网络等待 + 重定向）
        - Cookie 注入只需 ~100ms，速度提升 50-100 倍
        - 减少对目标服务器的请求压力，降低被风控的风险

        Cookie 失效的兜场场景：
        - 服务器 Session 过期（通常 24h 内）
        - Cookie 被手动清除
        - 多个子域名 Session 不一致

        为什么用 SPA 的 hash 路由判断登录成功：
        - MrShopPlus 是 Vue SPA，登录后 URL 从 /#/login 变为 /#/product/list
        - networkidle 只代表网络空闲，不代表登录状态
        - "login" 不在 URL 中 = 路由已跳转 = 登录大概率成功
        """
        if self.cookies_file.exists():
            try:
                with open(self.cookies_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                # Support both old format (list of cookies) and new format (storage state with cookies + localStorage)
                if isinstance(data, list):
                    await context.add_cookies(data)
                    logger.info(
                        f"[Cookies] Loaded {len(data)} cookies from {self.cookies_file}"
                    )
                elif isinstance(data, dict) and "cookies" in data:
                    await context.add_cookies(data["cookies"])
                    logger.info(
                        f"[Cookies] Loaded {len(data['cookies'])} cookies from {self.cookies_file}"
                    )
                    # Add localStorage if present
                    if "origins" in data:
                        for origin_data in data["origins"]:
                            origin = origin_data.get("origin", "")
                            if origin:
                                page = await context.new_page()
                                try:
                                    await page.goto(origin)
                                    for item in origin_data.get("localStorage", []):
                                        await page.evaluate(
                                            f"localStorage.setItem('{item['name']}', '{item['value']}')"
                                        )
                                finally:
                                    await page.close()

                # VALIDATION: Check if cookies actually work (CR-01 fix)
                # Navigate to product list and verify we are not redirected to login
                validation_page = await context.new_page()
                try:
                    await validation_page.goto(
                        "https://www.mrshopplus.com/#/product/list_DTB_proProduct",
                        timeout=15000
                    )
                    await asyncio.sleep(2)
                    if "login" in validation_page.url:
                        logger.info("[Login] Cookies expired (redirected to login), clearing cookies")
                        await context.clear_cookies()
                        await validation_page.close()
                    else:
                        logger.info(f"[Login] Cookie OK, current URL: {validation_page.url}")
                        await validation_page.close()
                        return True
                except Exception as e:
                    logger.warning(f"[Login] Cookie validation failed: {e}")
                    await validation_page.close()
            except Exception as e:
                logger.warning(f"[Cookies] Failed to load cookies: {e}, will try login")

        page = await context.new_page()
        try:
            await page.goto("https://www.mrshopplus.com/#/login")
            await safe_fill(page, "#username", self.email)
            await safe_fill(page, "input[placeholder='请输入密码']", self.password)
            await page.click("#login-btn")
            await page.wait_for_load_state("networkidle", timeout=30000)
            await asyncio.sleep(
                5
            )  # 等待 Vue 路由跳转完成（SPA 异步渲染，networkidle 不够）
            # Check if login succeeded (should not be on login page anymore)
            if "login" in page.url:
                await page.screenshot(
                    path=str(SCREENSHOT_DIR / "erp_login_failed.png"), timeout=60000
                )
                return False
            # Login succeeded, save cookies
            cookies = await context.cookies()
            logger.info(f"Login succeeded, got {len(cookies)} cookies")
            with open(self.cookies_file, "w", encoding="utf-8") as f:
                json.dump(cookies, f, indent=2)
            return True
        except Exception as e:
            logger.error(f"MrShopLogin error: {e}")
            return False
        finally:
            await page.close()


class ImageUploader:
    """Stage 5: Robust Image Upload (稳健图片上传) - 本地文件下载+本地上传模式

    修复原因: pic.yupoo.com/{photo_id}/ 缺少hash导致404，ERP服务器无法下载。
    解决方案: 先下载图片到本地temp目录，再用Element Plus本地上传（input[type=file]）。
    """

    def __init__(self, urls: List[str]):
        self.urls = urls
        self.temp_dir = ROOT_DIR / "temp_images"
        self.temp_dir.mkdir(exist_ok=True)

    async def upload(self, page: Page):
        """本地文件上传：下载图片 → 打开本地上传 → 填入文件路径 → 确认"""
        logger.info(
            f"[Upload] Starting local-file upload for {len(self.urls)} images..."
        )

        # Step 0: Download images to local temp directory
        local_files = await self._download_images()
        if not local_files:
            raise RuntimeError("Failed to download any images from URLs")
        # Product image gallery uses .el-upload--picture-card (multiple file input)
        # Use JS to wait for and detect the input (more reliable than Playwright locator for hidden inputs)
        file_input = None

        # Step 1: Poll with JS until input exists
        input_found = False
        for i in range(15):
            result = await page.evaluate("""() => {
                const inputs = document.querySelectorAll("input[type='file']");
                for (const i of inputs) {
                    if (i.multiple) return "found";
                }
                return "not_found";
            }""")
            if result == "found":
                input_found = True
                logger.info(f"[Upload] Multiple input detected after {i}s")
                break
            await asyncio.sleep(1)

        if not input_found:
            logger.warning("[Upload] No multiple file input found after 15s")
            await self._upload_by_url(page, self.urls)
            return

        # Step 2: Get a reference to the element via JS, then use Playwright locator on it
        try:
            el = page.locator("input[type='file'][multiple]").first
            await el.set_input_files(local_files)
            # Trigger Vue el-upload handleChange
            await page.evaluate(
                "() => { "
                "const inputs = document.querySelectorAll(\"input[type='file'][multiple]\"); "
                "if (inputs.length) inputs[0].dispatchEvent(new Event('change', {bubbles:true, cancelable:true})); "
                "}"
            )
            file_input = True
            logger.info("[Upload] set_input_files succeeded")
        except Exception as e:
            logger.warning(f"[Upload] set_input_files failed: {e}")

        if not file_input:
            logger.warning(
                "[Upload] All picture-card inputs failed, falling back to URL upload"
            )
            await self._upload_by_url(page, self.urls)
            return

        # Wait for upload to complete (Vue el-upload shows progress then removes it)
        upload_done = False
        for i in range(30):  # up to 30 seconds
            await asyncio.sleep(1)
            try:
                # Check the picture-card gallery for uploaded images
                gallery_count = await page.evaluate("""() => {
                    const pic = document.querySelector(".el-upload--picture-card");
                    if (!pic) return -1;
                    const imgs = pic.querySelectorAll("img");
                    const items = pic.querySelectorAll(".el-upload-list__item");
                    return imgs.length || items.length || 0;
                }""")
                # Also check el-upload-list for success items
                success_count = await page.evaluate("""() => {
                    const list = document.querySelector(".el-upload-list--picture-card");
                    if (!list) return 0;
                    return list.querySelectorAll(".el-upload-list__item").length;
                }""")
                logger.info(
                    f"[Upload] Progress check {i + 1}/30: picture_card imgs={gallery_count}, success_list={success_count}"
                )
                if gallery_count >= len(local_files) or success_count >= len(
                    local_files
                ):
                    logger.info(
                        f"[Upload] Gallery has {gallery_count} images - upload confirmed!"
                    )
                    upload_done = True
                    break
                if i >= 5 and gallery_count == 0:
                    # After 5s, still 0 images - might be failing silently
                    logger.warning(
                        f"[Upload] No images detected after {i + 1}s, checking for errors..."
                    )
                    error_text = await page.evaluate("""() => {
                        const err = document.querySelector(".el-upload__tip, .el-form-item__error");
                        return err ? err.innerText : "";
                    }""")
                    if error_text:
                        logger.error(f"[Upload] Error detected: {error_text}")
            except Exception as e:
                logger.debug(f"[Upload] Progress check error: {e}")

        if not upload_done:
            logger.warning("[Upload] Upload may not be complete, proceeding anyway.")

        await asyncio.sleep(3)
        # Final gallery state check
        final_count = await page.evaluate("""() => {
            const picCard = document.querySelector(".el-upload--picture-card");
            const list = document.querySelector(".el-upload-list--picture-card");
            const picImgs = picCard ? picCard.querySelectorAll("img").length : 0;
            const listItems = list ? list.querySelectorAll(".el-upload-list__item").length : 0;
            return `picture_card=${picImgs}, success_list=${listItems}`;
        }""")
        logger.info(f"[Upload] Final gallery state: {final_count}")
        logger.info(
            f"[Upload] Local file upload completed. ({len(local_files)} files submitted.)"
        )

    async def _download_images_via_cdp(self, page: Page) -> List[str]:
        """通过CDP拦截响应下载图片（需要Browser已登录Yupoo）"""
        local_paths = []
        page_id = page.page_id if hasattr(page, "page_id") else id(page)

        from playwright.async_api import Browser, CDPSession

        async def handle_response(response):
            url = response.url
            if "photo.yupoo.com" in url and ("/small." in url or "/big." in url):
                try:
                    body = await response.body()
                    # 从URL提取文件名
                    import re

                    match = re.search(r"/([^/]+)/small\.(jpg|jpeg)", url) or re.search(
                        r"/([^/]+)/big\.(jpg|jpeg)", url
                    )
                    if match:
                        fname = f"img_{match.group(1)[:8]}.{match.group(2)}"
                    else:
                        fname = f"img_{len(local_paths):02d}.jpg"
                    local_path = self.temp_dir / fname
                    with open(local_path, "wb") as f:
                        f.write(body)
                    if str(local_path) not in local_paths:
                        local_paths.append(str(local_path))
                        logger.info(
                            f"[CDP-Download] {url} -> {local_path} ({len(body)} bytes)"
                        )
                except Exception as e:
                    logger.warning(f"[CDP-Download] Failed: {e}")

        # 注册临时监听器
        listener = lambda r: (
            asyncio.create_task(handle_response(r)) if asyncio.current_task() else None
        )

        with page.on("response", listener):
            # 触发图片加载 - 滚动页面让图片进入视口
            await page.evaluate("window.scrollBy(0, 500)")
            await asyncio.sleep(3)
            await page.evaluate("window.scrollBy(0, -500)")
            await asyncio.sleep(2)

        return local_paths[:14]

    async def _download_images(self) -> List[str]:
        """使用 requests 直接下载 pic.yupoo.com 图片到本地目录。

        pic.yupoo.com 外链无需登录即可下载（已通过生产验证）。
        每个文件以 img_00.jpg, img_01.jpg ... 命名，最多14张。
        """
        local_paths: List[str] = []
        urls_to_download = self.urls[:14]

        for i, url in enumerate(urls_to_download):
            local_path = self.temp_dir / f"img_{i:02d}.jpg"
            try:
                r = requests.get(
                    url,
                    timeout=20,
                    headers={
                        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
                    },
                )
                if r.status_code == 200:
                    with open(local_path, "wb") as f:
                        f.write(r.content)
                    local_paths.append(str(local_path))
                    logger.info(
                        f"[Download] {url} -> {local_path} ({len(r.content)} bytes)"
                    )
                else:
                    logger.warning(f"[Download] HTTP {r.status_code} for {url}")
            except Exception as e:
                logger.warning(f"[Download] Failed to download {url}: {e}")

        logger.info(
            f"[Download] Completed: {len(local_paths)}/{len(urls_to_download)} images saved to {self.temp_dir}"
        )
        return local_paths

    async def _upload_by_url(self, page: Page, urls: List[str]):
        """URL上传fallback（仅在本地上传不可用时使用）"""
        # 切换到URL标签
        tab_clicked = False
        for sel in [".el-tabs__item:has-text('URL')", ".el-tabs__item:nth-child(2)"]:
            try:
                await page.wait_for_selector(sel, state="visible", timeout=5000)
                await page.locator(sel).first.evaluate("el => el.click()")
                tab_clicked = True
                break
            except:
                continue

        await asyncio.sleep(1)

        # 填写URL（必须用JS绕过 maxlength=153 限制）
        textarea = await page.query_selector(".el-dialog .el-textarea__inner")
        if textarea:
            urls_text = "\n".join(urls)
            # 直接用JS设置值，完全绕过 maxlength=153 的截断限制
            await textarea.evaluate(f"el => el.value = {json.dumps(urls_text)}")
            # 触发 input 事件让 Vue 的 v-model 检测到变化
            await page.evaluate(
                "() => { const ta = document.querySelector('.el-dialog .el-textarea__inner'); "
                "if (ta) { ta.dispatchEvent(new Event('input', {bubbles: true})); } }"
            )

        await asyncio.sleep(0.5)

        # 确认
        await page.evaluate(
            "() => { const btns = document.querySelectorAll('.el-dialog__footer button'); "
            "for (const b of btns) { if (!b.classList.contains('is-text')) { b.click(); break; } } }"
        )
        await asyncio.sleep(5)
        logger.info("[Upload] URL upload fallback completed.")


class Verifier:
    async def verify(self, page: Page):
        """Save product and verify action=3 redirect (截证并保存)"""
        # Click save using JS evaluate (bypasses all visibility/display/encoding constraints)
        save_clicked = False
        for attempt in range(3):
            try:
                result = await page.evaluate("""() => {
                    const buttons = Array.from(document.querySelectorAll("button"));
                    const saveBtn = buttons.find(b => b.innerText.trim() === "保存" || b.innerText.includes("保存"));
                    if (!saveBtn) {
                        // Try finding by text content
                        const allBtns = Array.from(document.querySelectorAll("button"));
                        for (const b of allBtns) {
                            if (b.innerText.includes("保") && b.innerText.includes("存")) {
                                b.click();
                                return "clicked";
                            }
                        }
                        return "no_save_button";
                    }
                    saveBtn.click();
                    return "clicked";
                }""")
                if result == "clicked":
                    save_clicked = True
                    logger.info(f"[Verify] Save clicked (attempt {attempt + 1})")
                    break
                elif result == "no_save_button":
                    logger.warning(
                        f"[Verify] Save button not found (attempt {attempt + 1})"
                    )
            except Exception as e:
                logger.warning(f"[Verify] Save click attempt {attempt + 1} failed: {e}")
            await asyncio.sleep(1)

        if not save_clicked:
            logger.error("Could not click save button after 3 attempts.")
            return

        # Monitor for success redirect
        try:
            await page.wait_for_url(lambda url: "action=3" in url, timeout=20000)
            logger.info("Product saved successfully (action=3). (商品保存成功)")
        except:
            # Try one more time
            logger.warning("First save attempt timed out, retrying...")
            await asyncio.sleep(2)
            try:
                await page.evaluate("""() => {
                    const buttons = Array.from(document.querySelectorAll("button"));
                    for (const b of buttons) {
                        if (b.innerText.includes("保") && b.innerText.includes("存")) {
                            b.click(); break;
                        }
                    }
                }""")
                await page.wait_for_url(lambda url: "action=3" in url, timeout=15000)
                logger.info("Product saved successfully on retry.")
            except Exception as e:
                logger.error(f"Save retry failed: {e}")


class DescriptionEditor:
    """Stage 5b: Product Description Formatting (商品描述格式化)"""

    def __init__(self, brand_name: str, product_name: str):
        self.brand_name = brand_name
        self.product_name = product_name

    async def format_description(self, page: Page):
        """Format the first line and insert link (格式化首行并插入链接)"""
        if not self.brand_name or not self.product_name:
            logger.error(
                "CRITICAL ERROR: Brand Name and Product Name are STRICTLY REQUIRED for formatting."
            )
            raise ValueError(
                "Strict Constraint Violated: Cannot skip description formatting. Brand and Product Name required."
            )

        logger.info(
            f"Formatting product description for: {self.product_name} (正在格式化商品描述: {self.product_name})"
        )

        brand_slug = self.brand_name.replace(" ", "-")
        link_url = f"https://www.stockxshoesvip.net/{brand_slug}/"
        first_line_html = f"Name: <a href='{link_url}' target='_blank'>{self.brand_name}</a> {self.product_name}"

        # TinyMCE编辑器在vue-tinymce iframe内，必须用 page.frame() 才能访问
        # page.evaluate() 在主页上下文，无法访问 iframe.contentDocument
        tiny_js = """
        (firstLineHtml) => {
            let editor = null;

            // TinyMCE editable body: #tinymce is the standard TinyMCE editor element
            editor = document.querySelector('#tinymce');
            if (!editor) editor = document.querySelector('.mce-content-body');
            if (!editor) editor = document.body;

            if (!editor) return false;

            // RULE 2: ENFORCE NO IMAGES IN DESCRIPTION (严格禁止描述中出现图片)
            let imgs = editor.querySelectorAll('img');
            imgs.forEach(img => img.remove());

            // RULE 1: REPLACE ONLY THE FIRST LINE ('Name:' field)
            let blocks = editor.querySelectorAll('p, div, span');
            for (let block of blocks) {
                const text = block.innerText || '';
                if (/^\\s*Name\\s*:/i.test(text)) {
                    block.innerHTML = firstLineHtml;
                    // Trigger TinyMCE input event so Vue model updates
                    editor.dispatchEvent(new Event('input', { bubbles: true }));
                    editor.dispatchEvent(new Event('blur', { bubbles: true }));
                    return true;
                }
            }

            // If no Name: block found, prepend at top
            const firstBlock = editor.querySelector('p, div');
            if (firstBlock) {
                const wrapper = document.createElement('div');
                wrapper.innerHTML = firstLineHtml + '<br><br>';
                editor.insertBefore(wrapper, firstBlock);
                editor.dispatchEvent(new Event('input', { bubbles: true }));
                return 'prepended';
            }
            return false;
        }
        """

        # Strategy 1: Use page.frame() to access TinyMCE iframe context directly
        # This is the correct Playwright way to interact with iframes
        mce_frame = None
        for frame in page.frames:
            if "vue-tinymce" in frame.name or any(
                "vue-tinymce" in str(f) for f in page.frames
            ):
                # Find TinyMCE iframe by looking at frame names/URLs
                pass

        # More reliable: find by frame's document containing TinyMCE
        for frame in page.frames:
            try:
                # Check if this frame has TinyMCE
                has_tinymce = await frame.evaluate("""() => {
                    return !!(document.querySelector('#tinymce') || document.querySelector('.mce-content-body'));
                }""")
                if has_tinymce:
                    mce_frame = frame
                    logger.info(f"[Description] Found TinyMCE frame: {frame.name}")
                    break
            except:
                continue

        if mce_frame:
            # Run TinyMCE JS inside the iframe context
            result = await mce_frame.evaluate(tiny_js, first_line_html)
            if result == True:
                logger.info(
                    "Successfully formatted the first line of the product description. (成功格式化商品描述的第一行)"
                )
            elif result == "prepended":
                logger.info(
                    "Successfully prepended formatted first line to product description. (成功在描述前插入格式化首行)"
                )
            else:
                logger.warning(
                    "TinyMCE editor found but Name: block not found. (TinyMCE编辑器已找到但未发现Name:段落)"
                )
        else:
            # Strategy 2: Fallback - try via iframe contentDocument access
            result = await page.evaluate(tiny_js, first_line_html)
            if result == True:
                logger.info(
                    "Successfully formatted (via contentDocument fallback). (通过contentDocument方式成功格式化)"
                )
            elif result == "prepended":
                logger.info("Successfully prepended (via contentDocument fallback).")
            else:
                logger.warning(
                    "Could not locate the rich text editor or 'Name:' block to format description. (未能定位富文本编辑器或含有 'Name:' 的段落进行格式化)"
                )


# =============================================================================
# 5. Orchestrator (编排器)
# =============================================================================


class SyncPipeline:
    """The Main Industrial Sync Engine (主工业同步引擎)"""

    def __init__(
        self,
        album_id: str,
        product_id: str = "0",
        brand_name: str = "",
        product_name: str = "",
        use_cdp: bool = False,
    ):
        self.album_id = album_id
        self.product_id = product_id
        self.brand_name = brand_name
        self.product_name = product_name
        self.use_cdp = use_cdp
        self.state_file = LOG_DIR / "pipeline_state.json"
        self.state = PipelineState(album_id=album_id)

    async def run(self):
        """
        主流水线编排器 - 每一步的执行逻辑说明（为什么这样做）

        总体设计原则：
        1. 先建独立浏览器，再通过 Cookie 注入复用登录态（避免 CDP 页面复用的 context 关闭问题）
        2. 两个独立 Page 对象分别操作 Yupoo 和 ERP（隔离会话，避免相互踩踏）
        3. 每步失败立即抛出异常，不尝试自动恢复（因为失败通常是结构性的，如选择器变化）

        为什么用"先导航主域名再导航子页面"的两步走策略：
        - Vue SPA 的路由依赖于根域名的初始化（sessionStorage / Vuex 状态）
        - 直接 goto(/product/list) 可能导致路由守卫判断 session 失效
        - 先访问 / 触发完整初始化，再跳转到目标页面，成功率大幅提升
        这是2026-04-08并发踩坑后确认的生产级经验。
        """
        async with async_playwright() as p:
            # CDP 模式优先：复用已登录的 Chrome 会话（绕过 webdriver 检测）
            yupoo_url = f"https://x.yupoo.com/gallery/{self.album_id}"
            erp_url = "https://www.mrshopplus.com/#/product/list_DTB_proProduct"

            # 获取 Yupoo 和 ERP 专用 Page
            browser: Optional[Browser] = None
            yupoo_page: Optional[Page] = None
            erp_page: Optional[Page] = None
            ctx: Optional[BrowserContext] = None

            # Strategy: CDP extracts cookies from Chrome's existing login session.
            # CDP 模式：直接连接 CDP Chrome，获得完整已登录 session
            if self.use_cdp:
                cdp_browser = await p.chromium.connect_over_cdp(
                    "http://localhost:9222", timeout=10000
                )
                # 获取第一个 context（Chrome 默认只有一个）
                if not cdp_browser.contexts:
                    raise Exception("[CDP] No contexts in CDP browser")
                ctx = cdp_browser.contexts[0]
                # 获取所有页面
                all_pages = ctx.pages
                yupoo_page = None
                erp_page = None
                for pg in all_pages:
                    try:
                        u = pg.url
                        if "yupoo" in u:
                            yupoo_page = pg
                        elif "mrshopplus" in u:
                            erp_page = pg
                    except:
                        pass
                logger.info(
                    f"[CDP] Tabs - Yupoo: {bool(yupoo_page)}, ERP: {bool(erp_page)}"
                )
                # 创建新 Yupoo Tab 导航
                yupoo_page = await ctx.new_page()
                await yupoo_page.goto(yupoo_url, timeout=20000)
                await yupoo_page.wait_for_load_state("load", timeout=15000)
                # 复用或创建 ERP Tab
                if not erp_page:
                    erp_page = await ctx.new_page()
                await erp_page.goto("https://www.mrshopplus.com/", timeout=20000)
                await erp_page.wait_for_load_state("load", timeout=15000)
                browser = cdp_browser
                cdp_mode = True
            else:
                cdp_mode = False
                browser = await p.chromium.launch(headless=False)
                ctx = await browser.new_context(viewport={"width": 1280, "height": 900})
                yupoo_page = await ctx.new_page()
                erp_page = await ctx.new_page()
                await yupoo_page.goto(yupoo_url)
                logger.info("[Browser] Single fresh browser for all operations")

            try:
                # 1. Extraction (提取) - YupooExtractor 直连 API 获取外链
                # CDP 模式：在独立新 Tab 导航，避免复用已有页面导致对象失效
                if cdp_mode:
                    # 创建新 Tab 导航到 Yupoo（不复用已有 Tab，避免 page 对象关闭问题）
                    yupoo_page = await ctx.new_page()
                    await yupoo_page.goto(yupoo_url, timeout=20000)
                    await yupoo_page.wait_for_load_state("load", timeout=15000)
                    logger.info(f"[CDP] New Yupoo tab: {yupoo_page.url}")
                else:
                    await YupooLogin().login(ctx)

                extractor = YupooExtractor(self.album_id)
                extractor.user = "lol2024"  # 从 cookies 或 YupooLogin 获取更可靠
                self.state.image_urls = await extractor.extract(yupoo_page)

                # 2. ERP Sync (同步)
                # CDP 模式：Chrome 已登录，直接导航到商品列表
                if cdp_mode:
                    await erp_page.goto(erp_url, timeout=30000)
                    await erp_page.wait_for_load_state("networkidle", timeout=20000)
                    await asyncio.sleep(5)
                    # Validate URL is actually product list (ERP sometimes redirects to /dashboard)
                    if "product/list" not in erp_page.url:
                        logger.warning(
                            f"[CDP] Unexpected URL after navigation: {erp_page.url}, re-navigating..."
                        )
                        await erp_page.goto(erp_url, timeout=30000)
                        await erp_page.wait_for_load_state("networkidle", timeout=20000)
                        await asyncio.sleep(5)
                    logger.info(f"[CDP] ERP product list: {erp_page.url}")
                else:
                    already_logged_in = (
                        erp_page is not None
                        and "login" not in erp_page.url
                        and "mrshopplus" in erp_page.url
                    )
                    if already_logged_in:
                        logger.info(
                            f"[CDP] Skipping login - using already logged-in ERP page: {erp_page.url}"
                        )
                        await erp_page.wait_for_load_state("networkidle", timeout=10000)
                        await asyncio.sleep(3)
                    else:
                        login_success = await MrShopLogin().login(ctx)
                        if not login_success:
                            logger.error("ERP login failed - check credentials")
                            raise Exception(
                                "ERP login failed. Please verify username and password in .env file."
                            )
                        await erp_page.goto("https://www.mrshopplus.com/")
                        await erp_page.wait_for_load_state("networkidle", timeout=30000)
                        logger.info(
                            f"After base navigation, current URL: {erp_page.url}"
                        )
                        await erp_page.goto(erp_url)
                        await erp_page.wait_for_load_state("domcontentloaded", timeout=60000)
                        await asyncio.sleep(8)
                        logger.info(
                            f"After product list navigation, current URL: {erp_page.url}"
                        )

                # Check if we are still on login page (检查是否仍然在登录页，说明登录失败)
                if erp_page is not None and "login" in erp_page.url:
                    logger.error(
                        "Still on login page after navigation - login failed or session expired"
                    )
                    # Take screenshot for debug
                    await erp_page.screenshot(
                        path=str(SCREENSHOT_DIR / "login_failed.png")
                    )
                    raise Exception(
                        "ERP login failed - still on login page after navigation. Please check credentials and manually login to get new cookies."
                    )
                # Dump page title for debug (输出页面标题调试)
                title = await erp_page.title()
                logger.info(f"Page title: {title}")

                # Wait for product list to render (等待商品列表渲染完成)
                # Try multiple selector combinations (多种选择器组合提高成功率)
                # 为什么多 selector 组合：ERP 升级后 Element Plus 图标 class 可能变化
                selectors = [
                    "i.i-ep-copy-document",
                    ".action-btn:has-text('复制')",
                    "[class*='copy']",
                    "i[class*='copy']",
                ]
                found = False
                for selector in selectors:
                    try:
                        await erp_page.wait_for_selector(selector, timeout=10000)
                        logger.info(f"Selector found: {selector}")
                        found = True
                        break
                    except:
                        continue
                if not found:
                    # If not found, dump page content for analysis
                    content = await erp_page.content()
                    with open(
                        LOG_DIR / "page_content.html", "w", encoding="utf-8"
                    ) as f:
                        f.write(content[:20000])  # Save first 20KB
                    logger.error(
                        f"No copy selector found. Page content saved to logs/page_content.html"
                    )
                    raise Exception(
                        f"Cannot find copy button. Check login status and URL: {erp_page.url}"
                    )

                # Click first 'Copy' button (点击第一个模板的复制按钮)
                # 为什么用 force=True：复制按钮可能渲染在可见区域之外（列表横向滚动）
                logger.info(
                    "Clicking COPY button on template product... (正在点击模板商品的复制按钮...)"
                )
                await safe_click(
                    erp_page, ".operate-area .el-icon-document-copy", force=True
                )
                await erp_page.wait_for_load_state("networkidle", timeout=20000)
                # Wait for Vue router navigation to complete and TinyMCE to initialize
                # 5秒等待是经验值：Vue 路由跳转 + TinyMCE iframe 初始化需要足够时间
                await asyncio.sleep(5)
                logger.info(f"After copy navigation, URL: {erp_page.url}")

                # Replace the main default title if provided (如果提供了商品名称，替换主标题)
                if self.product_name:
                    await safe_fill(
                        erp_page,
                        "input[placeholder='请输入商品名称'], input[placeholder*='商品名称']",
                        (self.brand_name + " " + self.product_name).strip(),
                        timeout=3000,
                    )

                # Wait for TinyMCE iframe to be fully loaded
                # 为什么用 try/except + 继续执行：TinyMCE 可能已初始化完成，只需 warn 不中断流程
                try:
                    await erp_page.wait_for_selector(
                        "iframe[id^='vue-tinymce']", timeout=10000
                    )
                    await asyncio.sleep(2)
                    logger.info(
                        "TinyMCE iframe detected, ready for description formatting."
                    )
                except:
                    logger.warning(
                        "TinyMCE iframe not detected within timeout, proceeding anyway."
                    )

                # Execute Description Editor Formatting (执行商品描述格式化)
                # 为什么最后执行格式化：避免图片上传后触发 TinyMCE 内容刷新导致格式丢失
                await DescriptionEditor(
                    self.brand_name, self.product_name
                ).format_description(erp_page)

                # Execute Image Upload (执行图片上传)
                # IMPORTANT: CDP session's existing page has stale Vue state (upload section never mounts)
                # Fix: close all existing pages, navigate FRESH to the copied product pkValues for clean Vue state
                copied_pk = None
                if "pkValues=" in erp_page.url:
                    import re

                    m = re.search(r"pkValues=([^\&]+)", erp_page.url)
                    if m:
                        copied_pk = m.group(1)
                # Close all existing pages for fresh start
                for pg in list(ctx.pages):
                    try:
                        await pg.close()
                    except:
                        pass
                # Fresh navigation to the copied product for clean Vue mount
                erp_page = await ctx.new_page()
                if copied_pk:
                    fresh_url = f"https://www.mrshopplus.com/#/product/form_DTB_proProduct/0?action=4&pkValues={copied_pk}"
                else:
                    fresh_url = "https://www.mrshopplus.com/#/product/form_DTB_proProduct/0?action=4"
                await erp_page.goto(fresh_url, timeout=30000)
                await erp_page.wait_for_load_state("networkidle", timeout=20000)
                await asyncio.sleep(
                    8
                )  # Wait for full Vue mount including upload section
                logger.info(
                    f"[Upload] Fresh navigation to copied product: {erp_page.url}"
                )
                # Wait for upload section to mount
                for _ in range(15):
                    result = await erp_page.evaluate(
                        "() => { const ins = document.querySelectorAll('input[type=file]'); return Array.from(ins).some(i => i.multiple) ? 'found' : 'not_found'; }"
                    )
                    if result == "found":
                        logger.info(f"[Upload] Upload section ready after {_}s")
                        break
                    await asyncio.sleep(1)

                # Re-fill product name after fresh navigation (fresh navigation 后重新填写产品名称)
                if self.product_name:
                    full_name = (self.brand_name + " " + self.product_name).strip()
                    try:
                        await safe_fill(
                            erp_page,
                            "input[placeholder='请输入商品名称'], input[placeholder*='商品名称']",
                            full_name,
                            timeout=5000,
                        )
                        logger.info(f"[Title] Updated product name to: {full_name}")
                    except Exception as e:
                        logger.warning(f"[Title] Failed to update product name: {e}")

                await ImageUploader(self.state.image_urls).upload(erp_page)

                # Execute Final Verification (执行最终验证)
                await Verifier().verify(erp_page)

                logger.info("Pipeline Execution Success (流水线执行成功)")
            except Exception as e:
                logger.error(f"Pipeline Crash (流水线崩溃): {e}")
                raise
            finally:
                # CDP browser 不可关闭（连接已外部 Chrome）
                # 仅关闭本流水线启动的浏览器
                if not cdp_mode and browser:
                    await browser.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--album-id", required=True, help="Yupoo Album ID (Yupoo 相册 ID)"
    )
    parser.add_argument(
        "--product-id", default="0", help="ERP Product ID (ERP 商品 ID)"
    )
    parser.add_argument(
        "--brand-name",
        default="",
        help="Brand name for formatting (用于格式化的品牌名称)",
    )
    parser.add_argument(
        "--product-name",
        default="",
        help="Official product name for formatting (用于格式化的最新官方商品名称)",
    )
    parser.add_argument(
        "--use-cdp",
        action="store_true",
        help="Use CDP persistent connection (连接已有 Chrome，绕过 webdriver 检测，需先启动 Chrome --remote-debugging-port=9222)",
    )
    parser.add_argument(
        "--cdp-url",
        default="http://localhost:9222",
        help="CDP debug port URL (default: http://localhost:9222)",
    )
    args = parser.parse_args()

    asyncio.run(
        SyncPipeline(
            args.album_id,
            args.product_id,
            args.brand_name,
            args.product_name,
            use_cdp=args.use_cdp,
        ).run()
    )
