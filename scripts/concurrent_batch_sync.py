#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
极限并发批量同步 - MVP (Extreme Concurrent Batch Sync)
完全不考虑风控，拉满10worker并发，追求吞吐量最大化

用法:
1. 先准备批量商品JSON文件: batch_products.json
   [
     {"album_id": "231019138", "brand_name": "BAPE", "product_name": "Shark Hoodie"},
     {"album_id": "231019139", "brand_name": "Nike", "product_name": "Air Max"},
     ...
   ]

2. 运行极限并发:
python scripts/concurrent_batch_sync.py --batch batch_products.json --workers 10 --use-cdp
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
from typing import List, Optional, Dict, Any

# =============================================================================
# Environment & Config (环境加载)
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

# Path definitions
ROOT_DIR = Path(__file__).parent.parent
LOG_DIR = ROOT_DIR / "logs"
SCREENSHOT_DIR = ROOT_DIR / "screenshots"
LOG_DIR.mkdir(exist_ok=True)
SCREENSHOT_DIR.mkdir(exist_ok=True)

# Configure logging
LOG_FILE = LOG_DIR / f"concurrent_batch_{datetime.now().strftime('%Y%m%d')}.log"
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE, encoding="utf-8"),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger('concurrent_batch')

# 强制依赖检查
try:
    from playwright.async_api import async_playwright, Page, BrowserContext, Browser
except ImportError:
    logger.error("CRITICAL: playwright not installed. Run: pip install playwright ; playwright install chromium")
    sys.exit(1)

# =============================================================================
# Retry & Helper (重试与工具函数)
# =============================================================================

def async_retry(max_retries: int = 3, base_delay: float = 1.0):
    """Exponential backoff retry decorator (指数退避重试装饰器)"""
    def decorator(func):
        async def wrapper(*args, **kwargs):
            last_exception = None
            for attempt in range(max_retries):
                try:
                    return await func(*args, **kwargs)
                except Exception as e:
                    last_exception = e
                    delay = base_delay * (2 ** attempt)
                    logger.warning(f"Attempt {attempt + 1}/{max_retries} failed: {e}, retrying in {delay}s...")
                    await asyncio.sleep(delay)
            logger.error(f"All {max_retries} attempts failed: {last_exception}")
            raise last_exception
        return wrapper
    return decorator

@async_retry(max_retries=3, base_delay=1.0)
async def safe_click(page: Page, selector: str):
    """Safe click with retry (安全点击，带重试)"""
    await page.click(selector, timeout=5000)
    return True

@async_retry(max_retries=3, base_delay=1.0)
async def safe_fill(page: Page, selector: str, value: str):
    """Safe fill with retry (安全填充，带重试)"""
    await page.fill(selector, value, timeout=5000)
    return True

# =============================================================================
# Data Models (数据模型)
# =============================================================================

@dataclass
class ProductTask:
    """Single product sync task (单个商品同步任务)"""
    album_id: str
    brand_name: str
    product_name: str
    product_id: str = "0"
    status: str = "pending"  # pending → running → success → failed
    error: Optional[str] = None
    start_time: Optional[float] = None
    end_time: Optional[float] = None
    image_urls: List[str] = field(default_factory=list)

@dataclass
class BatchResult:
    """Batch sync result (批量同步结果)"""
    total: int = 0
    success: int = 0
    failed: int = 0
    start_time: float = 0.0
    end_time: float = 0.0
    results: List[dict] = field(default_factory=list)

# =============================================================================
# Extractor: Extract image URLs from Yupoo (Yupoo 图片提取)
# =============================================================================

class YupooExtractor:
    """Extract image URLs from Yupoo album (从 Yupoo 相册提取图片URL)"""

    def __init__(self, album_id: str):
        self.album_id = album_id
        self.yupoo_url = f"https://x.yupoo.com/gallery/{album_id}"

    async def extract(self, page: Page) -> List[str]:
        """Extract image URLs (提取图片URL)"""
        logger.info(f"[{self.album_id}] Navigating to {self.yupoo_url}")
        await page.goto(self.yupoo_url, wait_until="networkidle", timeout=30000)
        await asyncio.sleep(2)

        # Click "进入后台"
        await safe_click(page, "a:has-text('进入后台')")
        await asyncio.sleep(2)

        # Click search box and wait
        await safe_click(page, "input[placeholder='搜索']")
        await asyncio.sleep(1)

        # Select ALL images → get URLs from textarea
        urls_text = await page.evaluate("""
            () => {
                // Select all checkboxes
                document.querySelectorAll('.c input[type=\"checkbox\"]').forEach(cb => {
                    if (!cb.checked) cb.click();
                });
                // Click 批量外链
                setTimeout(() => document.querySelector('.btn-group .btn:nth-child(2)').click(), 500);
                // Wait for textarea to appear
                return new Promise(resolve => {
                    setTimeout(() => {
                        const textarea = document.querySelector('textarea');
                        resolve(textarea ? textarea.value : '');
                    }, 1000);
                });
            }
        """)

        if not urls_text or not isinstance(urls_text, str):
            logger.error(f"[{self.album_id}] Failed to get URLs from textarea")
            return []

        urls = [url.strip() for url in urls_text.splitlines() if url.strip()]
        # 极限模式仍然保持14张限制（为了上架能成功，第15留给尺码表）
        urls = urls[:14]
        logger.info(f"[{self.album_id}] Extracted {len(urls)} image URLs (limited to 14)")
        return urls

# =============================================================================
# Uploader: Upload to MrShopPlus (上传到 ERP)
# =============================================================================

class MrShopPlusUploader:
    """Upload images and product to MrShopPlus ERP (上传图片到 MrShopPlus ERP)"""

    def __init__(self, product: ProductTask):
        self.product = product
        self.erp_url = "https://www.mrshopplus.com/#/product/list_DTB_proProduct"

    async def clear_old_images(self, page: Page):
        """Clear all existing images (清理所有旧图片)"""
        while await page.query_selector(".fa-trash-o"):
            await page.click(".fa-trash-o")
            await asyncio.sleep(0.3)

    async def format_description(self, page: Page):
        """Format description: remove images, format first line (格式化描述：移除图片，格式化首行)"""
        brand_name = self.product.brand_name
        product_name = self.product.product_name

        if not brand_name or not product_name:
            logger.error(f"[{self.product.album_id}] Brand and Product name required")
            raise ValueError("Brand and Product name required")

        brand_slug = brand_name.replace(" ", "-")
        link_url = f"https://www.stockxshoesvip.net/{brand_slug}/"
        first_line_html = f"Name: <a href='{link_url}' target='_blank'>{brand_name}</a> {product_name}"

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
                // ENFORCE NO IMAGES IN DESCRIPTION
                let imgs = editor.querySelectorAll('img');
                imgs.forEach(img => img.remove());

                // Replace first line with Name:
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
            logger.info(f"[{self.product.album_id}] Description formatted")
        else:
            logger.warning(f"[{self.product.album_id}] Could not format description")
        return success

    async def upload_images(self, page: Page, image_urls: List[str]):
        """Upload images by URL (通过URL上传图片)"""
        await self.clear_old_images(page)
        await asyncio.sleep(0.5)

        await safe_click(page, ".img-upload-btn")
        await asyncio.sleep(0.5)
        await safe_click(page, ".ant-tabs-tab:has-text('URL上传')")
        await asyncio.sleep(0.5)
        await safe_fill(page, "textarea", "\n".join(image_urls))
        await asyncio.sleep(0.5)
        await safe_click(page, "button:has-text('插入图片视频')")
        await asyncio.sleep(5)
        logger.info(f"[{self.product.album_id}] {len(image_urls)} images inserted")

    async def verify_and_save(self, page: Page):
        """Verify and save (验证并保存)"""
        ts = datetime.now().strftime("%H%M%S")
        shot_path = SCREENSHOT_DIR / f"concurrent_verify_{self.product.album_id}_{ts}.png"
        await page.screenshot(path=str(shot_path))
        logger.info(f"[{self.product.album_id}] Screenshot saved: {shot_path}")

        await safe_click(page, "button:has-text('保存')")
        # Wait for redirect to action=3
        await page.wait_for_url(lambda url: "action=3" in url, timeout=15000)
        logger.info(f"[{self.product.album_id}] ✓ Product saved successfully!")
        return True

# =============================================================================
# Single Worker (单个Worker执行任务)
# =============================================================================

async def process_single_product(
    task: ProductTask,
    semaphore: asyncio.Semaphore,
    use_cdp: bool = False,
    cdp_browser: Optional[Browser] = None
) -> ProductTask:
    """Process a single product task (处理单个商品任务)"""

    task.status = "running"
    task.start_time = time.time()
    logger.info(f"▶ Starting: {task.album_id} - {task.brand_name} {task.product_name}")

    try:
        async with semaphore:
            async with async_playwright() as p:
                # Get browser context - each worker creates its OWN context
                if use_cdp and cdp_browser:
                    # CDP模式：每个worker创建独立的浏览器上下文，避免SPA路由踩踏
                    context = await cdp_browser.new_context()
                    yupoo_page = await context.new_page()
                    erp_page = await context.new_page()
                else:
                    # 独立上下文
                    browser = await p.chromium.launch(headless=False)
                    context = await browser.new_context()
                    yupoo_page = await context.new_page()
                    erp_page = await context.new_page()

                # Step 1: Extract from Yupoo
                extractor = YupooExtractor(task.album_id)
                urls = await extractor.extract(yupoo_page)
                if not urls:
                    raise RuntimeError("Failed to extract image URLs from Yupoo")
                task.image_urls = urls

                # Step 2: Navigate to ERP product list
                logger.info(f"[{task.album_id}] Navigating to ERP product list")
                await erp_page.goto("https://www.mrshopplus.com/#/product/list_DTB_proProduct", wait_until="networkidle", timeout=30000)
                await asyncio.sleep(2)

                # TODO: 这里需要找到目标模板商品并点击"复制"
                # 极限MVP假设：已经在正确页面，手动定位后点击复制进入表单
                # 用户需要确保：已经打开复制表单后再运行
                # 这里简化处理，等待用户已经打开商品编辑页面
                await asyncio.sleep(1)

                # Step 3: Upload images
                uploader = MrShopPlusUploader(task)
                await uploader.upload_images(erp_page, urls)

                # Step 4: Format description
                await uploader.format_description(erp_page)

                # Step 5: Verify and save
                await uploader.verify_and_save(erp_page)

                # Cleanup if not CDP
                if not use_cdp and not browser_context:
                    await browser.close()

        task.status = "success"
        logger.info(f"✓ Completed: {task.album_id} in {time.time() - task.start_time:.1f}s")

    except Exception as e:
        task.status = "failed"
        task.error = str(e)
        logger.error(f"✗ Failed: {task.album_id} - {e}")

    task.end_time = time.time()
    return task

# =============================================================================
# Main Batch Orchestrator (主批量编排)
# =============================================================================

async def run_batch_concurrent(
    tasks: List[ProductTask],
    max_workers: int = 10,
    use_cdp: bool = False
) -> BatchResult:
    """Run batch sync with concurrent workers (并发运行批量同步)"""

    result = BatchResult(
        total=len(tasks),
        start_time=time.time(),
        success=0,
        failed=0
    )

    logger.info(f"🚀 Starting concurrent batch: {len(tasks)} products, {max_workers} workers")

    semaphore = asyncio.Semaphore(max_workers)

    # If CDP, connect once and pass browser (not context) so each worker creates its own context
    cdp_browser: Optional[Browser] = None
    if use_cdp:
        async with async_playwright() as p:
            cdp_browser = await p.chromium.connect_over_cdp("http://localhost:9222")
            logger.info(f"Connected to CDP browser")

    # Create all worker tasks
    worker_tasks = [
        process_single_product(task, semaphore, use_cdp, cdp_browser)
        for task in tasks
    ]

    # Run all workers
    completed_tasks = await asyncio.gather(*worker_tasks, return_exceptions=False)

    # Count results
    for task in completed_tasks:
        if isinstance(task, ProductTask):
            result.results.append({
                "album_id": task.album_id,
                "brand_name": task.brand_name,
                "product_name": task.product_name,
                "status": task.status,
                "duration": task.end_time - task.start_time if task.end_time and task.start_time else None,
                "error": task.error,
                "image_count": len(task.image_urls)
            })
            if task.status == "success":
                result.success += 1
            else:
                result.failed += 1

    result.end_time = time.time()

    # Save result to JSON
    result_path = LOG_DIR / f"batch_result_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(result_path, "w", encoding="utf-8") as f:
        json.dump(asdict(result), f, indent=2, ensure_ascii=False)

    # Print summary
    total_time = result.end_time - result.start_time
    logger.info("=" * 60)
    logger.info(f"📊 BATCH COMPLETE: Total={result.total}, Success={result.success}, Failed={result.failed}")
    logger.info(f"⏱️  Total time: {total_time:.1f}s, Average: {(total_time / max(result.total, 1)):.1f}s/product")
    logger.info(f"💾 Result saved: {result_path}")
    logger.info("=" * 60)

    return result

def load_batch_from_json(json_path: str) -> List[ProductTask]:
    """Load batch tasks from JSON file (从JSON加载批量任务)"""
    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    tasks = []
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
            logger.warning(f"Skipping invalid item: missing required fields -> {item}")

    logger.info(f"Loaded {len(tasks)} valid product tasks from {json_path}")
    return tasks

def main():
    parser = argparse.ArgumentParser(description="极限并发批量同步 - 不考虑风控，拉满吞吐量")
    parser.add_argument("--batch", required=True, help="批量商品JSON文件路径")
    parser.add_argument("--workers", type=int, default=10, help="最大并发worker数 (default: 10)")
    parser.add_argument("--use-cdp", action="store_true", help="使用CDP连接已有Chrome (推荐，更稳定)")
    args = parser.parse_args()

    # Load tasks
    tasks = load_batch_from_json(args.batch)
    if not tasks:
        logger.error("No valid tasks loaded, exiting")
        sys.exit(1)

    # Run concurrent batch
    asyncio.run(run_batch_concurrent(tasks, args.workers, args.use_cdp))

if __name__ == "__main__":
    main()
