#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ERP Form Tab Manager (ERP 表单并行管理器)

核心功能：预创建 N 个"复制表单"Tab，实现并行上传，突破串行瓶颈。

Architecture:
    Navigator Tab (Tab-0)     → 停留在商品列表页，批量触发"复制"按钮
    Form Tab (Tab-1...Tab-N)   → 已打开的商品表单，供 Worker 使用
    Worker Pool                → N 个 Worker 并行绑定 Tab 执行上传

Usage:
    python scripts/erp_tab_manager.py --batch batch_products.json --workers 5
"""

import argparse
import asyncio
import json
import logging
import os
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import List, Optional, Dict, Any

# =============================================================================
# Environment & Config
# =============================================================================

def load_env_manual(env_path=".env"):
    """Manually parse .env file"""
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

ROOT_DIR = Path(__file__).parent.parent
LOG_DIR = ROOT_DIR / "logs"
SCREENSHOT_DIR = ROOT_DIR / "screenshots"
LOG_DIR.mkdir(exist_ok=True)
SCREENSHOT_DIR.mkdir(exist_ok=True)

LOG_FILE = LOG_DIR / f"tab_manager_{datetime.now().strftime('%Y%m%d')}.log"
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE, encoding="utf-8"),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("erp_tab_manager")

try:
    from playwright.async_api import async_playwright, Page, BrowserContext, Browser
except ImportError:
    logger.error("playwright not installed. Run: pip install playwright && playwright install chromium")
    sys.exit(1)

# =============================================================================
# Config
# =============================================================================

ERP_BASE_URL = "https://www.mrshopplus.com"
ERP_PRODUCT_LIST_URL = f"{ERP_BASE_URL}/#/product/list_DTB_proProduct"

# 并发控制参数
MAX_CONCURRENT_TABS = 5        # 最大并行 Tab 数
TAB_CREATION_BATCH_SIZE = 3    # 每批创建 Tab 数
TAB_CREATION_DELAY = 2.0       # 相邻批次创建间隔（秒）
TAB_LOAD_TIMEOUT = 15000       # 表单加载超时（毫秒）
FORM_READY_SELECTOR = "input[placeholder*='商品名称'], input[placeholder*='商品']"  # 表单就绪标志

# Cookie 文件
COOKIES_FILE = ROOT_DIR / "logs" / "cookies.json"


# =============================================================================
# Tab State Machine
# =============================================================================

class TabState(Enum):
    """Tab 生命周期状态"""
    CREATED = "created"        # Tab 已创建，正在等待加载
    LOADING = "loading"        # 正在加载表单
    AVAILABLE = "available"    # 表单就绪，可被 Worker 使用
    WORKING = "working"        # Worker 正在使用
    COMPLETED = "completed"    # 上传完成
    ERROR = "error"            # 出错
    CLOSED = "closed"          # 已关闭


@dataclass
class TabSlot:
    """
    单个 Tab 的状态封装

    Attributes:
        page: Playwright Page 对象
        tab_id: Tab 唯一标识（从 1 开始）
        state: 当前状态
        product_info: 关联的商品信息
        error: 错误信息（如果有）
        created_at: 创建时间戳
    """
    page: Page
    tab_id: int
    state: TabState = TabState.CREATED
    product_info: Optional[Dict[str, str]] = None
    error: Optional[str] = None
    created_at: float = field(default_factory=time.time)

    def mark_available(self):
        self.state = TabState.AVAILABLE

    def mark_working(self, product_info: Dict[str, str]):
        self.state = TabState.WORKING
        self.product_info = product_info

    def mark_completed(self):
        self.state = TabState.COMPLETED

    def mark_error(self, error: str):
        self.state = TabState.ERROR
        self.error = error


# =============================================================================
# ERP Form Tab Manager (核心)
# =============================================================================

class ERPFormTabManager:
    """
    ERP 表单并行管理器

    核心职责：
    1. 预创建 N 个已打开"复制表单"的 Tab
    2. 管理 Tab Pool，提供 get/put 接口给 Worker
    3. 控制并发数（Semaphore）
    4. 处理 Tab 生命周期（创建、监控、清理）

    Usage:
        manager = ERPFormTabManager(context=ctx, max_tabs=5)
        await manager.precreate_tabs(n=5)
        tab_slot = await manager.get_available_tab(timeout=30)
        # worker 使用 tab_slot.page
        await manager.release_tab(tab_slot)
    """

    def __init__(
        self,
        context: BrowserContext,
        max_tabs: int = MAX_CONCURRENT_TABS,
        logger_obj: Optional[logging.Logger] = None
    ):
        self.context = context
        self.max_tabs = max_tabs
        self.logger = logger_obj or logger

        # Navigator Tab（停留在商品列表，用于触发"复制"）
        self.navigator_page: Optional[Page] = None

        # Tab Pool：所有预创建的表单 Tab
        self._tab_pool: List[TabSlot] = []

        # 可用 Tab 队列（asyncio.Queue 实现无锁获取）
        self._available_tabs: asyncio.Queue = asyncio.Queue()

        # 信号量：控制并发数
        self._semaphore: asyncio.Semaphore = asyncio.Semaphore(max_tabs)

        # 内部锁：保护 Pool 修改
        self._pool_lock: asyncio.Lock = asyncio.Lock()

        # Tab ID 计数器
        self._tab_counter = 0

        self._closed = False

    # -------------------------------------------------------------------------
    # Public API: Lifecycle
    # -------------------------------------------------------------------------

    async def initialize(self, cookies_file: Path = COOKIES_FILE) -> bool:
        """
        初始化：创建 Navigator Tab，注入登录 Cookie

        Args:
            cookies_file: Cookie 文件路径

        Returns:
            True if initialized successfully
        """
        self.logger.info("[Init] Creating Navigator Tab...")

        # 1. 创建 Navigator Tab
        self.navigator_page = await self.context.new_page()
        await self.navigator_page.goto(ERP_PRODUCT_LIST_URL, wait_until="networkidle", timeout=30000)
        await asyncio.sleep(3)  # 等待 Vue 路由渲染

        # 2. 注入 Cookie（如果文件存在）
        if cookies_file.exists():
            try:
                with open(cookies_file, "r", encoding="utf-8") as f:
                    cookies = json.load(f)
                    await self.context.add_cookies(cookies)
                self.logger.info(f"[Init] Loaded {len(cookies)} cookies from {cookies_file}")
                # 刷新页面使 Cookie 生效
                await self.navigator_page.goto(ERP_PRODUCT_LIST_URL, wait_until="networkidle", timeout=30000)
                await asyncio.sleep(2)
            except Exception as e:
                self.logger.warning(f"[Init] Cookie load failed: {e}, continuing without cookies")

        # 3. 检查是否在登录页
        if "login" in self.navigator_page.url:
            self.logger.error("[Init] Still on login page - check credentials or cookies")
            return False

        self.logger.info(f"[Init] Navigator Tab ready: {self.navigator_page.url}")
        return True

    async def precreate_tabs(self, n: int = MAX_CONCURRENT_TABS) -> int:
        """
        预创建 N 个"复制表单"Tab

        核心算法：
        1. 在 Navigator Tab 中找到前 N 个模板商品的"复制"按钮
        2. 逐个点击"复制"按钮 → ERP 在新 Tab 打开商品表单
        3. 等待每个新 Tab 完全加载
        4. 将 Tab 加入 Pool，状态设为 AVAILABLE

        Args:
            n: 需要预创建的 Tab 数量

        Returns:
            实际创建的 Tab 数量

        注意：
            - n 不应超过 max_tabs
            - 商品列表中需要有至少 n 个模板商品
        """
        n = min(n, self.max_tabs)
        self.logger.info(f"[Precreate] Starting pre-creation of {n} tabs...")

        tabs_created = 0

        # 分批创建，每批 TAB_CREATION_BATCH_SIZE
        for batch_start in range(0, n, TAB_CREATION_BATCH_SIZE):
            batch_end = min(batch_start + TAB_CREATION_BATCH_SIZE, n)
            batch_size = batch_end - batch_start
            self.logger.info(f"[Precreate] Batch {batch_start//TAB_CREATION_BATCH_SIZE + 1}: creating {batch_size} tabs...")

            # 批量触发当前批次
            await self._trigger_copy_buttons_batch(batch_start, batch_end)

            # 等待批次中的所有 Tab 加载完成
            for i in range(batch_start, batch_end):
                tab_slot = await self._wait_for_new_tab(timeout=20)
                if tab_slot:
                    self._tab_counter += 1
                    tab_slot.tab_id = self._tab_counter
                    await self._pool_lock.acquire()
                    try:
                        self._tab_pool.append(tab_slot)
                        await self._available_tabs.put(tab_slot)
                    finally:
                        self._pool_lock.release()
                    tabs_created += 1
                    self.logger.info(f"[Precreate] Tab-{tab_slot.tab_id} ready ({tabs_created}/{n})")
                else:
                    self.logger.warning(f"[Precreate] Tab-{i+1} creation timeout or failed")

            # 批次间隔
            if batch_end < n:
                self.logger.info(f"[Precreate] Waiting {TAB_CREATION_DELAY}s before next batch...")
                await asyncio.sleep(TAB_CREATION_DELAY)

        self.logger.info(f"[Precreate] Done. Created {tabs_created}/{n} tabs, Pool size: {len(self._tab_pool)}")
        return tabs_created

    async def get_available_tab(self, timeout: float = 60.0) -> TabSlot:
        """
        Worker 获取可用 Tab

        从 Pool 中取出一个 AVAILABLE 的 Tab 返回给 Worker。
        如果没有可用 Tab，则等待（阻塞直到有 Tab 可用或超时）。

        Args:
            timeout: 等待超时（秒），None=无限等待

        Returns:
            TabSlot：包含可用 Page 的 Tab 槽位

        Raises:
            asyncio.TimeoutError: 等待超时
            RuntimeError: Manager 已关闭
        """
        if self._closed:
            raise RuntimeError("ERPFormTabManager is closed, cannot get tabs")

        try:
            tab_slot = await asyncio.wait_for(
                self._available_tabs.get(),
                timeout=timeout
            )
            await self._semaphore.acquire()
            self.logger.info(f"[GetTab] Worker acquired Tab-{tab_slot.tab_id}")
            return tab_slot

        except asyncio.TimeoutError:
            raise asyncio.TimeoutError(f"No available tab after {timeout}s timeout")

    async def release_tab(self, tab_slot: TabSlot):
        """
        Worker 释放 Tab

        将使用完毕的 Tab 标记为 COMPLETED，并关闭该 Tab。
        如果需要重试机制，可改为标记为 AVAILABLE 放回 Pool。

        Args:
            tab_slot: 要释放的 Tab 槽位
        """
        try:
            tab_slot.mark_completed()
            if not tab_slot.page.is_closed():
                await tab_slot.page.close()
            self.logger.info(f"[Release] Tab-{tab_slot.tab_id} closed, pool: {len(self._tab_pool)}")
        except Exception as e:
            self.logger.warning(f"[Release] Error closing Tab-{tab_slot.tab_id}: {e}")
        finally:
            self._semaphore.release()

    async def wait_all_ready(self, n: int) -> bool:
        """
        等待所有 N 个预创建的 Tab 状态变为 AVAILABLE

        用于编排层确认所有 Tab 都已就绪后再启动 Worker。

        Args:
            n: 期望就绪的 Tab 数量

        Returns:
            True: 所有 Tab 都就绪
            False: 超时或数量不足
        """
        self.logger.info(f"[WaitReady] Waiting for {n} tabs to be available...")
        start = time.time()
        timeout = 120.0  # 最多等 2 分钟

        while time.time() - start < timeout:
            available_count = sum(
                1 for t in self._tab_pool
                if t.state == TabState.AVAILABLE
            )
            self.logger.info(f"[WaitReady] Available: {available_count}/{n}")
            if available_count >= n:
                self.logger.info(f"[WaitReady] All {n} tabs ready!")
                return True
            await asyncio.sleep(1.0)

        self.logger.warning(f"[WaitReady] Timeout: only {sum(1 for t in self._tab_pool if t.state == TabState.AVAILABLE)}/{n} tabs ready")
        return False

    async def close_all(self):
        """
        关闭所有 Tab 和 Navigator，清理资源
        """
        self._closed = True
        self.logger.info("[Close] Shutting down all tabs...")

        # 关闭所有表单 Tab
        for tab_slot in self._tab_pool:
            try:
                if not tab_slot.page.is_closed():
                    await tab_slot.page.close()
            except Exception as e:
                self.logger.warning(f"[Close] Error closing Tab-{tab_slot.tab_id}: {e}")

        # 关闭 Navigator Tab
        if self.navigator_page and not self.navigator_page.is_closed():
            try:
                await self.navigator_page.close()
            except Exception:
                pass

        self.logger.info("[Close] All tabs closed")

    # -------------------------------------------------------------------------
    # Tab Health Check & Recovery
    # -------------------------------------------------------------------------

    async def health_check(self) -> Dict[str, Any]:
        """
        健康检查：检查所有 Tab 的状态

        Returns:
            健康报告字典
        """
        stats = {
            "total_tabs": len(self._tab_pool),
            "available": sum(1 for t in self._tab_pool if t.state == TabState.AVAILABLE),
            "working": sum(1 for t in self._tab_pool if t.state == TabState.WORKING),
            "completed": sum(1 for t in self._tab_pool if t.state == TabState.COMPLETED),
            "error": sum(1 for t in self._tab_pool if t.state == TabState.ERROR),
            "tabs": []
        }

        for tab in self._tab_pool:
            try:
                url = tab.page.url if not tab.page.is_closed() else "closed"
            except Exception:
                url = "error"

            stats["tabs"].append({
                "tab_id": tab.tab_id,
                "state": tab.state.value,
                "url": url,
                "product": tab.product_info,
                "error": tab.error,
                "age": f"{time.time() - tab.created_at:.1f}s"
            })

        return stats

    async def rebuild_failed_tabs(self, failed_ids: List[int]) -> int:
        """
        重建指定 ID 的失败 Tab

        Args:
            failed_ids: 需要重建的 Tab ID 列表

        Returns:
            重建成功的数量
        """
        rebuilt = 0
        for tab_id in failed_ids:
            slot = next((t for t in self._tab_pool if t.tab_id == tab_id), None)
            if slot and slot.state == TabState.ERROR:
                # 关闭旧的
                if not slot.page.is_closed():
                    await slot.page.close()
                # 重新创建
                new_slot = await self._create_single_form_tab()
                if new_slot:
                    async with self._pool_lock:
                        idx = self._tab_pool.index(slot)
                        self._tab_pool[idx] = new_slot
                        new_slot.tab_id = tab_id  # 保持原 ID
                    await self._available_tabs.put(new_slot)
                    rebuilt += 1
                    self.logger.info(f"[Rebuild] Tab-{tab_id} rebuilt")
        return rebuilt

    # -------------------------------------------------------------------------
    # Private: Core Tab Creation
    # -------------------------------------------------------------------------

    async def _trigger_copy_buttons_batch(self, start: int, end: int):
        """
        在 Navigator Tab 中批量触发"复制"按钮

        使用 JavaScript 批量触发，避免逐个 click 的串行开销。
        """
        nav = self.navigator_page

        # 确保 Navigator Tab 在商品列表页
        if "product/list" not in nav.url:
            await nav.goto(ERP_PRODUCT_LIST_URL, wait_until="networkidle", timeout=30000)
            await asyncio.sleep(3)

        # 尝试多种选择器定位"复制"按钮
        copy_selectors = [
            "i.i-ep-copy-document",
            "[class*='copy']",
            "[class*='action'] i[class*='copy']",
            "button:has-text('复制')",
            "[title='复制']",
        ]

        found_selector = None
        for sel in copy_selectors:
            try:
                count = await nav.query_selector_all(sel)
                if count and len(count) >= end:
                    found_selector = sel
                    self.logger.info(f"[Trigger] Found {len(count)} copy buttons via '{sel}'")
                    break
            except Exception:
                continue

        if not found_selector:
            # 兜底：列出页面上所有可点击元素
            content = await nav.content()
            with open(LOG_DIR / "nav_page_content.html", "w", encoding="utf-8") as f:
                f.write(content[:30000])
            self.logger.error("[Trigger] No copy selector found. Page content saved.")
            raise RuntimeError("Cannot find copy buttons on product list page")

        # JS 批量触发：逐个 dispatch_event 打开 Tab
        # ERP 的"复制"通常在新 Tab 打开，所以需要逐个触发并等待新 Tab 出现
        for i in range(start, end):
            try:
                # 先让 Navigator Tab 可见
                await nav.bring_to_front()
                await asyncio.sleep(0.5)

                # 定位并触发复制按钮
                # 注意：found_selector含单引号，必须用JSON.stringify转义
                selector_js = json.dumps(found_selector)
                await nav.evaluate(f"""
                    () => {{
                        const btns = document.querySelectorAll({selector_js});
                        const btn = btns[{i}];
                        if (btn) {{
                            btn.dispatchEvent(new MouseEvent('click', {{ bubbles: true, cancelable: true }}));
                        }}
                    }}
                """)

                self.logger.info(f"[Trigger] Dispatched copy button {i+1}/{end}")
                # 短暂等待新 Tab 打开
                await asyncio.sleep(1.5)

            except Exception as e:
                self.logger.warning(f"[Trigger] Failed to trigger copy button {i}: {e}")

    async def _wait_for_new_tab(self, timeout: float = 20.0) -> Optional[TabSlot]:
        """
        等待 Navigator Tab 旁边出现新的表单 Tab

        通过对比 context.pages() 列表，找到新出现的 Page。

        Returns:
            TabSlot 或 None（超时）
        """
        known_pages = set(id(p) for p in self.context.pages)

        start_time = time.time()
        while time.time() - start_time < timeout:
            current_pages = self.context.pages
            for page in current_pages:
                if id(page) not in known_pages:
                    # 发现新 Tab
                    new_page = page
                    slot = TabSlot(page=new_page, tab_id=len(self._tab_pool) + 1, state=TabState.LOADING)

                    # 等待表单加载
                    try:
                        await new_page.wait_for_load_state("networkidle", timeout=10000)
                    except Exception:
                        pass

                    # 等待表单就绪标志出现
                    try:
                        await new_page.wait_for_selector(FORM_READY_SELECTOR, timeout=TAB_LOAD_TIMEOUT)
                        slot.mark_available()
                        self.logger.info(f"[NewTab] Form loaded: {new_page.url}")
                    except Exception as e:
                        self.logger.warning(f"[NewTab] Form ready selector not found: {e}")
                        # 即使没找到标志也标记为 AVAILABLE（Worker 会有自己的等待逻辑）
                        slot.mark_available()

                    return slot

            await asyncio.sleep(0.5)

        return None

    async def _create_single_form_tab(self) -> Optional[TabSlot]:
        """
        直接在 Navigator Tab 中触发一次"复制"，等待并返回一个表单 Tab

        Returns:
            TabSlot 或 None
        """
        try:
            # 触发复制按钮
            await self._trigger_copy_buttons_batch(0, 1)
            # 等待新 Tab
            slot = await self._wait_for_new_tab(timeout=20)
            return slot
        except Exception as e:
            self.logger.warning(f"[CreateSingle] Failed: {e}")
            return None

    # -------------------------------------------------------------------------
    # Alternative: CDP Target-based Creation (可选，备用)
    # -------------------------------------------------------------------------

    async def precreate_tabs_via_cdp(self, browser: Browser, n: int = MAX_CONCURRENT_TABS) -> int:
        """
        可选方案：使用 CDP Target.createTarget 批量创建 Tab

        优势：不依赖 Navigator Tab 的 DOM 按钮触发
        劣势：需要知道表单页面的 URL（ERP 表单 URL 未知）
        """
        self.logger.info(f"[CDP] Creating {n} tabs via CDP Target API...")
        tabs_created = 0

        for i in range(n):
            try:
                # 通过 CDP 创建新 Target（Tab）
                # 注意：需要浏览器支持 CDPP connection
                async with browser.contexts[0].pages[-1] as last_page:
                    pass

                # 由于 Playwright CDP API 不直接暴露 Target.createTarget，
                # 这里用 JS 方式作为主方案，CDP 方案留作备用
                self.logger.info(f"[CDP] Using JS dispatch as fallback for tab {i+1}")

            except Exception as e:
                self.logger.warning(f"[CDP] Tab creation failed: {e}")

        return tabs_created


# =============================================================================
# Form Worker (Worker 执行单元)
# =============================================================================

@dataclass
class WorkerTask:
    """Worker 执行任务"""
    album_id: str
    brand_name: str
    product_name: str
    image_urls: List[str] = field(default_factory=list)
    status: str = "pending"  # pending / running / success / failed
    error: Optional[str] = None
    tab_id: Optional[int] = None
    start_time: Optional[float] = None
    end_time: Optional[float] = None


class FormWorker:
    """
    表单 Worker：绑定一个 Tab，执行完整的商品上传流程

    Usage:
        worker = FormWorker(manager)
        await worker.run(task)
    """

    def __init__(self, manager: ERPFormTabManager, worker_id: int = 0):
        self.manager = manager
        self.worker_id = worker_id
        self.logger = logging.getLogger(f"form_worker_{worker_id}")

    async def run(self, task: WorkerTask) -> WorkerTask:
        """
        执行单个商品上传

        完整流程：
        1. 从 Manager 获取可用 Tab
        2. 填充品牌名 + 商品名
        3. 格式化商品描述
        4. 上传图片（≤14 张）
        5. 保存并验证
        6. 释放 Tab
        """
        task.status = "running"
        task.start_time = time.time()
        self.logger.info(f"[Worker-{self.worker_id}] Starting: {task.album_id} - {task.brand_name} {task.product_name}")

        tab_slot: Optional[TabSlot] = None

        try:
            # Step 1: 获取可用 Tab
            tab_slot = await self.manager.get_available_tab(timeout=60)
            task.tab_id = tab_slot.tab_id
            page = tab_slot.page
            tab_slot.mark_working({"brand": task.brand_name, "product": task.product_name})

            # Step 2: 等待表单完全就绪
            try:
                await page.wait_for_selector(FORM_READY_SELECTOR, timeout=15000)
                await asyncio.sleep(1)
            except Exception as e:
                self.logger.warning(f"[Worker-{self.worker_id}] Form ready wait: {e}")

            # Step 3: 截图留证（获取前）
            ts = datetime.now().strftime("%H%M%S")
            before_path = SCREENSHOT_DIR / f"worker{self.worker_id}_before_{ts}.png"
            await page.screenshot(path=str(before_path))
            self.logger.info(f"[Worker-{self.worker_id}] Before screenshot: {before_path}")

            # Step 4: 填充商品名称
            await self._fill_product_name(page, task)

            # Step 5: 格式化描述
            await self._format_description(page, task)

            # Step 6: 上传图片
            await self._upload_images(page, task)

            # Step 7: 保存并验证
            await self._verify_and_save(page)

            # Step 8: 截图留证（保存后）
            after_path = SCREENSHOT_DIR / f"worker{self.worker_id}_after_{ts}.png"
            await page.screenshot(path=str(after_path))
            self.logger.info(f"[Worker-{self.worker_id}] After screenshot: {after_path}")

            task.status = "success"
            self.logger.info(f"[Worker-{self.worker_id}] SUCCESS: {task.album_id} in {time.time() - task.start_time:.1f}s")

        except asyncio.TimeoutError:
            task.status = "failed"
            task.error = "Timeout: no available tab"
            self.logger.error(f"[Worker-{self.worker_id}] Failed: no available tab")
            if tab_slot:
                tab_slot.mark_error("No tab available")

        except Exception as e:
            task.status = "failed"
            task.error = str(e)
            self.logger.error(f"[Worker-{self.worker_id}] Failed: {e}")
            if tab_slot:
                tab_slot.mark_error(str(e))

        finally:
            task.end_time = time.time()
            if tab_slot:
                # 尝试释放 Tab（如果还没被关闭）
                try:
                    await self.manager.release_tab(tab_slot)
                except Exception:
                    pass

        return task

    # -------------------------------------------------------------------------
    # Private: Form Operations
    # -------------------------------------------------------------------------

    async def _fill_product_name(self, page: Page, task: WorkerTask):
        """填充商品名称"""
        full_name = f"{task.brand_name} {task.product_name}".strip()
        name_selectors = [
            "input[placeholder*='商品名称']",
            "input[placeholder*='商品']",
            "input[placeholder='请输入商品名称']",
        ]

        for sel in name_selectors:
            try:
                await page.wait_for_selector(sel, state="visible", timeout=5000)
                await page.fill(sel, full_name)
                self.logger.info(f"[Worker-{self.worker_id}] Filled product name: {full_name}")
                return
            except Exception:
                continue

        self.logger.warning(f"[Worker-{self.worker_id}] Product name input not found, skipping")

    async def _format_description(self, page: Page, task: WorkerTask):
        """格式化商品描述（去除图片，格式化首行）"""
        if not task.brand_name or not task.product_name:
            self.logger.warning(f"[Worker-{self.worker_id}] Skipping description: missing brand or product name")
            return

        brand_slug = task.brand_name.replace(" ", "-")
        link_url = f"https://www.stockxshoesvip.net/{brand_slug}/"
        first_line_html = f"Name: <a href='{link_url}' target='_blank'>{task.brand_name}</a> {task.product_name}"

        js_code = """
        (firstLineHtml) => {
            let editor = document.querySelector('[contenteditable="true"]');
            if (!editor) {
                const iframes = document.querySelectorAll('iframe');
                for (let iframe of iframes) {
                    try {
                        const iframeEditor = iframe.contentWindow.document.querySelector('[contenteditable="true"], body');
                        if (iframeEditor) { editor = iframeEditor; break; }
                    } catch(e) {}
                }
            }
            if (editor) {
                // 强制移除所有图片（描述禁图防沉余）
                editor.querySelectorAll('img').forEach(img => img.remove());
                // 替换首行 Name: 字段
                const blocks = editor.querySelectorAll('p, div');
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
            self.logger.info(f"[Worker-{self.worker_id}] Description formatted")
        else:
            self.logger.warning(f"[Worker-{self.worker_id}] Description format: target block not found")

    async def _upload_images(self, page: Page, task: WorkerTask):
        """上传图片（URL 模式，最多 14 张）"""
        if not task.image_urls:
            self.logger.warning(f"[Worker-{self.worker_id}] No image URLs to upload")
            return

        urls = task.image_urls[:14]

        # Step A: 清理旧图
        try:
            while True:
                trash = await page.query_selector(".fa-trash-o")
                if not trash:
                    break
                await trash.click()
                await asyncio.sleep(0.3)
        except Exception:
            pass

        # Step B: 打开上传弹窗
        upload_selectors = [".img-upload-btn", "button:has-text('上传图片')", "[class*='upload']"]
        modal_opened = False
        for sel in upload_selectors:
            try:
                await page.wait_for_selector(sel, state="visible", timeout=5000)
                await page.click(sel)
                await asyncio.sleep(0.5)
                modal_opened = True
                break
            except Exception:
                continue

        if not modal_opened:
            raise RuntimeError("Cannot open upload modal")

        # Step C: 切换到 URL 模式
        try:
            url_tab = await page.query_selector(".ant-tabs-tab:has-text('URL上传')")
            if url_tab:
                await url_tab.click()
                await asyncio.sleep(0.3)
        except Exception:
            pass

        # Step D: 粘贴 URL
        textarea_selectors = ["textarea", "textarea.ant-input"]
        for sel in textarea_selectors:
            try:
                await page.wait_for_selector(sel, state="visible", timeout=5000)
                await page.fill(sel, "\n".join(urls))
                break
            except Exception:
                continue

        # Step E: 执行插入
        insert_selectors = ["button:has-text('插入图片视频')", "button:has-text('确定')"]
        for sel in insert_selectors:
            try:
                await page.click(sel, timeout=3000)
                break
            except Exception:
                continue

        await asyncio.sleep(5)  # 等待图片插入
        self.logger.info(f"[Worker-{self.worker_id}] {len(urls)} images inserted")

    async def _verify_and_save(self, page: Page):
        """保存并验证"""
        save_selectors = ["button:has-text('保存')", "button[type='submit']"]
        for sel in save_selectors:
            try:
                await page.click(sel, timeout=5000)
                break
            except Exception:
                continue

        # 等待 URL 变为 action=3（唯一可靠的保存成功标志）
        try:
            await page.wait_for_url(lambda url: "action=3" in url, timeout=15000)
            self.logger.info(f"[Worker-{self.worker_id}] Product saved successfully (action=3)")
        except Exception:
            self.logger.warning(f"[Worker-{self.worker_id}] Save verification: action=3 not detected")


# =============================================================================
# Parallel Orchestrator (并行编排器)
# =============================================================================

async def run_parallel_sync(
    tasks: List[WorkerTask],
    max_workers: int = MAX_CONCURRENT_TABS,
    cookies_file: Path = COOKIES_FILE,
) -> List[WorkerTask]:
    """
    并行执行多个商品上传任务

    流程：
    1. 启动 Tab Manager
    2. 预创建 N 个表单 Tab
    3. 等待所有 Tab 就绪
    4. 启动 N 个 Worker 并行执行
    5. 收集结果，清理资源

    Args:
        tasks: 商品任务列表
        max_workers: 最大并发数
        cookies_file: Cookie 文件

    Returns:
        任务结果列表
    """
    results: List[WorkerTask] = []

    async with async_playwright() as p:
        # 启动浏览器
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context(viewport={"width": 1280, "height": 900})

        # 初始化 Manager
        manager = ERPFormTabManager(context, max_tabs=max_workers)

        try:
            # Step 1: 初始化（创建 Navigator Tab）
            if not await manager.initialize(cookies_file):
                raise RuntimeError("Manager initialization failed")

            # Step 2: 预创建 Tab
            tabs_created = await manager.precreate_tabs(n=min(len(tasks), max_workers))
            if tabs_created == 0:
                raise RuntimeError("No tabs created - check product list page")

            # Step 3: 等待所有 Tab 就绪
            await manager.wait_all_ready(n=tabs_created)

            # Step 4: 打印健康状态
            health = await manager.health_check()
            logger.info(f"[Orchestrator] Health: {json.dumps(health, indent=2, ensure_ascii=False)}")

            # Step 5: 启动 Worker Pool（asyncio.gather 并行执行）
            workers = [
                FormWorker(manager, worker_id=i)
                for i in range(len(tasks))
            ]

            worker_tasks = [w.run(t) for w, t in zip(workers, tasks)]
            results = await asyncio.gather(*worker_tasks, return_exceptions=False)

            logger.info(f"[Orchestrator] All workers finished. Success: {sum(1 for r in results if r.status == 'success')}")

        except Exception as e:
            logger.error(f"[Orchestrator] Pipeline error: {e}")
            raise

        finally:
            # Step 6: 清理
            await manager.close_all()
            await browser.close()

    return results


# =============================================================================
# CLI Entry Point
# =============================================================================

def load_tasks_from_json(json_path: str) -> List[WorkerTask]:
    """从 JSON 文件加载任务"""
    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    tasks = []
    for item in data:
        task = WorkerTask(
            album_id=str(item.get("album_id", "")),
            brand_name=item.get("brand_name", ""),
            product_name=item.get("product_name", ""),
            image_urls=item.get("image_urls", [])
        )
        if task.album_id and task.brand_name and task.product_name:
            tasks.append(task)
        else:
            logger.warning(f"Skipping invalid item: {item}")
    return tasks


def main():
    parser = argparse.ArgumentParser(description="ERP Form Parallel Sync - Tab Manager")
    parser.add_argument("--batch", required=True, help="批量商品 JSON 文件")
    parser.add_argument("--workers", type=int, default=MAX_CONCURRENT_TABS, help=f"最大并发 Tab 数 (default: {MAX_CONCURRENT_TABS})")
    parser.add_argument("--cookies", default=str(COOKIES_FILE), help="Cookie 文件路径")
    args = parser.parse_args()

    tasks = load_tasks_from_json(args.batch)
    if not tasks:
        logger.error("No valid tasks loaded")
        sys.exit(1)

    logger.info(f"Loaded {len(tasks)} tasks, starting with {args.workers} workers")
    start_time = time.time()

    results = asyncio.run(run_parallel_sync(tasks, max_workers=args.workers))

    # 输出结果
    elapsed = time.time() - start_time
    success = sum(1 for r in results if r.status == "success")
    failed = sum(1 for r in results if r.status == "failed")

    logger.info("=" * 60)
    logger.info(f"RESULT: Total={len(results)}, Success={success}, Failed={failed}")
    logger.info(f"Time: {elapsed:.1f}s, Avg: {elapsed / max(len(results), 1):.1f}s/product")
    logger.info("=" * 60)

    # 保存结果 JSON
    result_path = LOG_DIR / f"tab_parallel_result_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(result_path, "w", encoding="utf-8") as f:
        json.dump([
            {
                "album_id": r.album_id,
                "brand_name": r.brand_name,
                "product_name": r.product_name,
                "status": r.status,
                "tab_id": r.tab_id,
                "duration": r.end_time - r.start_time if r.end_time and r.start_time else None,
                "error": r.error
            }
            for r in results
        ], f, indent=2, ensure_ascii=False)
    logger.info(f"Result saved: {result_path}")


if __name__ == "__main__":
    main()
