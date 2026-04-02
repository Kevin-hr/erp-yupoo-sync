#!/usr/bin/env python3
"""
MrShopPlus Image Upload Script
Robust, error-resilient upload of 14 images via URL to MrShopPlus product form.

Usage:
    python mrshop_image_upload.py [--dry-run] [--headless] [--resume]

Features:
    - Exponential backoff retry logic for unstable browser connections
    - Selector-based clicks (no pixel coordinates)
    - State validation before each action
    - Resumable from last successful step
    - Dry-run mode for testing
    - Comprehensive logging
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
from typing import List, Optional, Callable

# Configure logging
LOG_DIR = Path("C:/Users/Administrator/Documents/GitHub/ERP/logs")
LOG_DIR.mkdir(parents=True, exist_ok=True)
LOG_FILE = LOG_DIR / f"mrshop_upload_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE, encoding="utf-8"),
        logging.StreamHandler(sys.stdout),
    ],
)
log = logging.getLogger(__name__)


# =============================================================================
# Configuration
# =============================================================================

CREDENTIALS = {
    "email": "litzyjames5976@gmail.com",
    "password": "RX3jesthYF7d",
}

TARGET_URL = "https://www.mrshopplus.com/#/product/form_DTB_proProduct/0?action=4&pkValues=%5B526271466670100%5D"

YUPOO_LINKS = [
    "http://pic.yupoo.com/lol2024/b8d9a9b4/be300f4c.jpeg",
    "http://pic.yupoo.com/lol2024/f5d019e2/8e2aef60.jpeg",
    "http://pic.yupoo.com/lol2024/800a3662/1bed29f7.jpeg",
    "http://pic.yupoo.com/lol2024/911811bc/0fd4db9b.jpeg",
    "http://pic.yupoo.com/lol2024/2b649905/2a5d2a70.jpeg",
    "http://pic.yupoo.com/lol2024/fc1eca1d/166dfb12.jpeg",
    "http://pic.yupoo.com/lol2024/b4866755/0354c12f.jpeg",
    "http://pic.yupoo.com/lol2024/73ed256d/9ff30683.jpeg",
    "http://pic.yupoo.com/lol2024/b1cb2ee3/5f74b00e.jpeg",
    "http://pic.yupoo.com/lol2024/0bdf3514/daa3eb87.jpeg",
    "http://pic.yupoo.com/lol2024/30716bcb/b442add3.jpeg",
    "http://pic.yupoo.com/lol2024/eb9ffaf9/b53a7add.jpeg",
    "http://pic.yupoo.com/lol2024/d092e359/1cc212b7.jpeg",
    "http://pic.yupoo.com/lol2024/7de06d3b/5962e3fa.jpeg",
]

SCREENSHOT_DIR = Path("C:/Users/Administrator/Documents/GitHub/ERP/screenshots")
SCREENSHOT_DIR.mkdir(parents=True, exist_ok=True)

STATE_FILE = Path("C:/Users/Administrator/Documents/GitHub/ERP/logs/mrshop_upload_state.json")

# =============================================================================
# Retry Configuration
# =============================================================================

MAX_RETRIES = 5
INITIAL_BACKOFF = 2.0  # seconds
MAX_BACKOFF = 60.0  # seconds
BACKOFF_MULTIPLIER = 2.0


# =============================================================================
# State Management
# =============================================================================

@dataclass
class UploadState:
    """Tracks progress for resumability."""
    current_step: int = 0
    completed_steps: List[str] = field(default_factory=list)
    existing_images_deleted: bool = False
    upload_modal_open: bool = False
    urls_pasted: bool = False
    images_inserted: bool = False
    saved: bool = False
    last_error: Optional[str] = None
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())

    def save(self):
        """Save state to disk for resume capability."""
        with open(STATE_FILE, "w", encoding="utf-8") as f:
            json.dump(asdict(self), f, indent=2)
        log.debug(f"State saved to {STATE_FILE}")

    @classmethod
    def load(cls) -> "UploadState":
        """Load state from disk if exists."""
        if STATE_FILE.exists():
            try:
                with open(STATE_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                log.info(f"Resuming from previous state: step {data.get('current_step', 0)}")
                return cls(**data)
            except (json.JSONDecodeError, TypeError) as e:
                log.warning(f"Could not load state file: {e}. Starting fresh.")
        return cls()

    def clear(self):
        """Clear saved state."""
        if STATE_FILE.exists():
            STATE_FILE.unlink()
        log.info("State cleared.")


# =============================================================================
# Custom Exceptions
# =============================================================================

class BrowserConnectionError(Exception):
    """Raised when browser connection is lost."""
    pass


class ElementNotFoundError(Exception):
    """Raised when an element cannot be found after retries."""
    pass


class ActionFailedError(Exception):
    """Raised when an action fails after all retries."""
    pass


# =============================================================================
# Retry Decorator
# =============================================================================

def async_retry(
    max_retries: int = MAX_RETRIES,
    initial_backoff: float = INITIAL_BACKOFF,
    max_backoff: float = MAX_BACKOFF,
    multiplier: float = BACKOFF_MULTIPLIER,
    retry_on: tuple = (Exception,),
):
    """
    Decorator for async functions with exponential backoff retry.

    Args:
        max_retries: Maximum number of retry attempts
        initial_backoff: Initial backoff delay in seconds
        max_backoff: Maximum backoff delay in seconds
        multiplier: Backoff multiplier for each retry
        retry_on: Tuple of exception types to retry on
    """
    def decorator(func: Callable):
        async def wrapper(*args, **kwargs):
            backoff = initial_backoff
            last_exception = None

            for attempt in range(max_retries + 1):
                try:
                    return await func(*args, **kwargs)
                except retry_on as e:
                    last_exception = e
                    if attempt < max_retries:
                        log.warning(
                            f"[{func.__name__}] Attempt {attempt + 1}/{max_retries + 1} failed: {e}. "
                            f"Retrying in {backoff:.1f}s..."
                        )
                        await asyncio.sleep(backoff)
                        backoff = min(backoff * multiplier, max_backoff)
                    else:
                        log.error(
                            f"[{func.__name__}] All {max_retries + 1} attempts failed. "
                            f"Last error: {e}"
                        )
            raise last_exception
        return wrapper
    return decorator


# =============================================================================
# Playwright Helpers
# =============================================================================

async def safe_screenshot(page, name: str, state: UploadState):
    """Take screenshot with safe error handling."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = SCREENSHOT_DIR / f"{name}_{timestamp}.png"
    try:
        await page.screenshot(path=str(path), timeout=10000)
        log.info(f"Screenshot saved: {path}")
        return path
    except Exception as e:
        log.warning(f"Failed to take screenshot {name}: {e}")
        return None


@async_retry(max_retries=3, retry_on=(BrowserConnectionError,))
async def safe_click(page, selector: str, timeout: float = 5000, state: Optional[UploadState] = None):
    """
    Click element safely with retry logic.

    Handles:
    - Target closed errors (browser disconnection)
    - Element not found
    - Element not visible (zero width/height)
    """
    try:
        element = await page.wait_for_selector(selector, timeout=timeout, state="visible")
        if element is None:
            raise ElementNotFoundError(f"Element not found: {selector}")

        # Check if element has valid dimensions
        box = await element.bounding_box()
        if box is None or box["width"] == 0 or box["height"] == 0:
            raise ElementNotFoundError(f"Element has zero dimensions: {selector}")

        await element.click(timeout=timeout)
        log.debug(f"Clicked: {selector}")
        return element

    except ElementNotFoundError:
        raise
    except Exception as e:
        error_msg = str(e)
        if "target closed" in error_msg.lower() or "could not read protocol" in error_msg.lower():
            raise BrowserConnectionError(f"Browser connection lost: {e}") from e
        raise


@async_retry(max_retries=3, retry_on=(BrowserConnectionError,))
async def safe_fill(page, selector: str, value: str, timeout: float = 5000):
    """Fill input safely with retry logic."""
    try:
        element = await page.wait_for_selector(selector, timeout=timeout, state="visible")
        if element is None:
            raise ElementNotFoundError(f"Element not found: {selector}")
        await element.fill(value, timeout=timeout)
        log.debug(f"Filled: {selector}")
        return element
    except ElementNotFoundError:
        raise
    except Exception as e:
        if "target closed" in str(e).lower() or "could not read protocol" in str(e).lower():
            raise BrowserConnectionError(f"Browser connection lost: {e}") from e
        raise


async def wait_for_network_idle(page, timeout: float = 10000):
    """Wait for network to be idle."""
    try:
        await page.wait_for_load_state("networkidle", timeout=timeout)
    except Exception as e:
        log.warning(f"Network idle wait failed: {e}")


async def count_elements(page, selector: str) -> int:
    """Count elements matching selector."""
    try:
        elements = await page.query_selector_all(selector)
        return len(elements)
    except Exception:
        return 0


# =============================================================================
# Core Upload Steps
# =============================================================================

STEP_LOGIN = "login"
STEP_NAVIGATE = "navigate"
STEP_DELETE_EXISTING = "delete_existing"
STEP_OPEN_UPLOAD_MODAL = "open_upload_modal"
STEP_SELECT_URL_TAB = "select_url_tab"
STEP_PASTE_URLS = "paste_urls"
STEP_INSERT_IMAGES = "insert_images"
STEP_SAVE = "save"


class MrShopUploader:
    """MrShopPlus image uploader with robust error handling."""

    def __init__(self, dry_run: bool = False, headless: bool = False, resume: bool = False):
        self.dry_run = dry_run
        self.headless = headless
        self.resume = resume
        self.state = UploadState.load() if resume else UploadState()
        self.browser = None
        self.context = None
        self.page = None

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.cleanup()
        return False

    async def cleanup(self):
        """Clean up browser resources."""
        if self.page:
            try:
                await self.page.close()
            except Exception:
                pass
            self.page = None
        if self.context:
            try:
                await self.context.close()
            except Exception:
                pass
            self.context = None
        if self.browser:
            try:
                await self.browser.close()
            except Exception:
                pass
            self.browser = None
        log.info("Browser resources cleaned up.")

    async def initialize_browser(self):
        """Initialize Playwright browser with robust error handling."""
        log.info("Initializing browser...")

        try:
            from playwright.async_api import async_playwright

            p = await async_playwright().start()
            self.browser = await p.chromium.launch(
                headless=self.headless,
                args=["--disable-blink-features=AutomationControlled"],
            )
            self.context = await self.browser.new_context(
                viewport={"width": 1920, "height": 1080},
                user_agent=(
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/120.0.0.0 Safari/537.36"
                ),
            )
            self.page = await self.context.new_page()
            log.info("Browser initialized successfully.")
            return True

        except Exception as e:
            log.error(f"Failed to initialize browser: {e}")
            raise

    async def step_login(self) -> bool:
        """Step 1: Login to MrShopPlus."""
        if STEP_LOGIN in self.state.completed_steps:
            log.info("Step 'login' already completed, skipping.")
            return True

        log.info(f"[STEP {self.state.current_step + 1}] Logging in...")

        try:
            await self.page.goto("https://www.mrshopplus.com/#/login", timeout=30000)
            await wait_for_network_idle(self.page)

            # Wait for login form elements
            await self.page.wait_for_selector("#username", timeout=10000)

            await safe_fill(self.page, "#username", CREDENTIALS["email"])
            await safe_fill(self.page, "input[placeholder='请输入密码']", CREDENTIALS["password"])

            await safe_click(self.page, "#login-btn")

            # Wait for redirect after login
            await asyncio.sleep(3)
            await wait_for_network_idle(self.page)

            current_url = self.page.url
            if "login" in current_url.lower():
                log.warning("May still be on login page. Proceeding anyway...")

            await safe_screenshot(self.page, "after_login", self.state)

            self.state.completed_steps.append(STEP_LOGIN)
            self.state.current_step += 1
            self.state.save()
            log.info("Login step completed.")
            return True

        except Exception as e:
            self.state.last_error = str(e)
            self.state.save()
            log.error(f"Login step failed: {e}")
            return False

    async def step_navigate_to_product(self) -> bool:
        """Step 2: Navigate to product form."""
        if STEP_NAVIGATE in self.state.completed_steps:
            log.info("Step 'navigate' already completed, skipping.")
            return True

        log.info(f"[STEP {self.state.current_step + 1}] Navigating to product form...")

        try:
            await self.page.goto(TARGET_URL, timeout=30000)
            await wait_for_network_idle(self.page)
            await asyncio.sleep(2)

            # Wait for product form content
            await self.page.wait_for_selector(".imglist-img, .img-upload-btn, [class*='product']", timeout=10000)

            await safe_screenshot(self.page, "product_form", self.state)

            self.state.completed_steps.append(STEP_NAVIGATE)
            self.state.current_step += 1
            self.state.save()
            log.info("Navigate step completed.")
            return True

        except Exception as e:
            self.state.last_error = str(e)
            self.state.save()
            log.error(f"Navigate step failed: {e}")
            return False

    async def step_delete_existing_images(self) -> bool:
        """Step 3: Delete all existing images in the product images section."""
        if STEP_DELETE_EXISTING in self.state.completed_steps:
            log.info("Step 'delete_existing' already completed, skipping.")
            return True

        log.info(f"[STEP {self.state.current_step + 1}] Deleting existing images...")

        try:
            max_deletions = 50  # Safety limit
            deletions = 0

            while deletions < max_deletions:
                # Try multiple selectors for trash icons
                trash_selectors = [
                    ".fa-trash-o",
                    "[class*='delete']",
                    "[class*='trash']",
                    "button[aria-label*='删除']",
                    ".anticon-delete",
                ]

                trash_icon = None
                for selector in trash_selectors:
                    trash_icon = await self.page.query_selector(selector)
                    if trash_icon:
                        log.debug(f"Found trash icon with selector: {selector}")
                        break

                if not trash_icon:
                    # Check if there are any images left
                    img_count = await count_elements(self.page, ".imglist-img, [class*='img-list'] img")
                    if img_count == 0:
                        log.info("No more images to delete.")
                        break
                    log.warning(f"No trash icon found but {img_count} images still present. Retrying...")
                    await asyncio.sleep(1)
                    continue

                # Scroll element into view before clicking
                await trash_icon.scroll_into_view_if_needed()
                await asyncio.sleep(0.3)

                await safe_click(self.page, ".fa-trash-o, [class*='delete'], [class*='trash'], button[aria-label*='删除'], .anticon-delete", timeout=3000)

                deletions += 1
                log.info(f"Deleted image {deletions}")
                await asyncio.sleep(0.5)  # Wait for animation

            await safe_screenshot(self.page, "after_delete", self.state)

            self.state.existing_images_deleted = True
            self.state.completed_steps.append(STEP_DELETE_EXISTING)
            self.state.current_step += 1
            self.state.save()
            log.info(f"Delete step completed. Total deleted: {deletions}")
            return True

        except Exception as e:
            self.state.last_error = str(e)
            self.state.save()
            log.error(f"Delete step failed: {e}")
            return False

    async def step_open_upload_modal(self) -> bool:
        """Step 4: Click the + button to open upload modal."""
        if STEP_OPEN_UPLOAD_MODAL in self.state.completed_steps:
            log.info("Step 'open_upload_modal' already completed, skipping.")
            return True

        log.info(f"[STEP {self.state.current_step + 1}] Opening upload modal...")

        try:
            # Find the + upload button with multiple selector strategies
            plus_selectors = [
                ".img-upload-btn .fa-plus",
                ".img-upload-btn",
                "[class*='upload-btn']",
                "[class*='upload'] .fa-plus",
                "button:has-text('+')",
                "[aria-label*='上传']",
            ]

            plus_btn = None
            for selector in plus_selectors:
                plus_btn = await self.page.query_selector(selector)
                if plus_btn:
                    log.debug(f"Found plus button with selector: {selector}")
                    break

            if not plus_btn:
                raise ElementNotFoundError("Plus/upload button not found")

            # Scroll into view
            await plus_btn.scroll_into_view_if_if_needed()
            await asyncio.sleep(0.5)

            # Click with force if needed
            await plus_btn.click(timeout=5000, force=True)

            # Wait for modal to appear
            await asyncio.sleep(1)

            # Verify modal opened
            modal_selectors = [".ant-modal-content", "[class*='modal']", "[class*='upload-modal']"]
            modal_opened = False
            for selector in modal_selectors:
                modal = await self.page.query_selector(selector)
                if modal:
                    modal_opened = True
                    log.debug(f"Modal found with selector: {selector}")
                    break

            if not modal_opened:
                # Try clicking by text
                tabs = await self.page.query_selector_all(".ant-tabs-tab")
                for tab in tabs:
                    text = await tab.inner_text()
                    if "URL" in text or "上传" in text:
                        await tab.click()
                        modal_opened = True
                        break

            await safe_screenshot(self.page, "upload_modal", self.state)

            self.state.upload_modal_open = True
            self.state.completed_steps.append(STEP_OPEN_UPLOAD_MODAL)
            self.state.current_step += 1
            self.state.save()
            log.info("Upload modal step completed.")
            return True

        except Exception as e:
            self.state.last_error = str(e)
            self.state.save()
            log.error(f"Open upload modal step failed: {e}")
            return False

    async def step_select_url_tab(self) -> bool:
        """Step 5: Select the URL upload tab."""
        if STEP_SELECT_URL_TAB in self.state.completed_steps:
            log.info("Step 'select_url_tab' already completed, skipping.")
            return True

        log.info(f"[STEP {self.state.current_step + 1}] Selecting URL upload tab...")

        try:
            # Wait for modal content
            await self.page.wait_for_selector(".ant-modal-content", timeout=5000)

            # Find and click URL upload tab
            tab_selectors = [
                ".ant-tabs-tab:has-text('URL上传')",
                ".ant-tabs-tab:has-text('链接上传')",
                "[class*='tab']:has-text('URL')",
                "div:has-text('URL上传')",
            ]

            tab_clicked = False
            for selector in tab_selectors:
                tabs = await self.page.query_selector_all(selector)
                for tab in tabs:
                    text = await tab.inner_text()
                    if "URL" in text or "链接" in text:
                        await tab.click()
                        tab_clicked = True
                        log.debug(f"Clicked URL tab with selector: {selector}")
                        break
                if tab_clicked:
                    break

            if not tab_clicked:
                # Try by clicking on any tab and then looking for URL option
                all_tabs = await self.page.query_selector_all(".ant-tabs-tab")
                for tab in all_tabs:
                    text = await tab.inner_text()
                    log.debug(f"Found tab: {text}")

            await asyncio.sleep(0.5)
            await safe_screenshot(self.page, "url_tab_selected", self.state)

            self.state.completed_steps.append(STEP_SELECT_URL_TAB)
            self.state.current_step += 1
            self.state.save()
            log.info("URL tab selection step completed.")
            return True

        except Exception as e:
            self.state.last_error = str(e)
            self.state.save()
            log.error(f"Select URL tab step failed: {e}")
            return False

    async def step_paste_urls(self) -> bool:
        """Step 6: Paste Yupoo URLs into textarea."""
        if STEP_PASTE_URLS in self.state.completed_steps:
            log.info("Step 'paste_urls' already completed, skipping.")
            return True

        log.info(f"[STEP {self.state.current_step + 1}] Pasting {len(YUPOO_LINKS)} URLs...")

        if self.dry_run:
            log.info("[DRY RUN] Would paste URLs:")
            for url in YUPOO_LINKS:
                log.info(f"  - {url}")
            self.state.completed_steps.append(STEP_PASTE_URLS)
            self.state.current_step += 1
            self.state.save()
            return True

        try:
            # Wait for textarea to be visible
            textarea_selectors = ["textarea", "textarea[placeholder*='URL']", "textarea[placeholder*='链接']"]
            textarea = None

            for selector in textarea_selectors:
                textarea = await self.page.wait_for_selector(selector, timeout=5000, state="visible")
                if textarea:
                    log.debug(f"Found textarea with selector: {selector}")
                    break

            if not textarea:
                raise ElementNotFoundError("Textarea for URLs not found")

            # Clear and fill with URLs
            await textarea.fill("")
            urls_text = "\n".join(YUPOO_LINKS)
            await textarea.fill(urls_text)

            log.info(f"Pasted {len(YUPOO_LINKS)} URLs into textarea.")
            await safe_screenshot(self.page, "urls_pasted", self.state)

            self.state.urls_pasted = True
            self.state.completed_steps.append(STEP_PASTE_URLS)
            self.state.current_step += 1
            self.state.save()
            log.info("Paste URLs step completed.")
            return True

        except Exception as e:
            self.state.last_error = str(e)
            self.state.save()
            log.error(f"Paste URLs step failed: {e}")
            return False

    async def step_insert_images(self) -> bool:
        """Step 7: Click '插入图片视频' button."""
        if STEP_INSERT_IMAGES in self.state.completed_steps:
            log.info("Step 'insert_images' already completed, skipping.")
            return True

        log.info(f"[STEP {self.state.current_step + 1}] Inserting images...")

        if self.dry_run:
            log.info("[DRY RUN] Would click '插入图片视频' button.")
            self.state.completed_steps.append(STEP_INSERT_IMAGES)
            self.state.current_step += 1
            self.state.save()
            return True

        try:
            # Find insert button
            button_selectors = [
                "button:has-text('插入图片视频')",
                "button:has-text('插入图片')",
                "[class*='insert']",
                "button[type='primary']",
            ]

            insert_btn = None
            for selector in button_selectors:
                buttons = await self.page.query_selector_all(selector)
                for btn in buttons:
                    text = await btn.inner_text()
                    if "插入" in text:
                        insert_btn = btn
                        log.debug(f"Found insert button with selector: {selector}")
                        break
                if insert_btn:
                    break

            if not insert_btn:
                raise ElementNotFoundError("Insert images button not found")

            await insert_btn.scroll_into_view_if_needed()
            await asyncio.sleep(0.3)
            await insert_btn.click(timeout=5000, force=True)

            log.info("Clicked '插入图片视频' button. Waiting for processing...")
            await asyncio.sleep(5)  # Wait for image processing

            await safe_screenshot(self.page, "images_inserted", self.state)

            self.state.images_inserted = True
            self.state.completed_steps.append(STEP_INSERT_IMAGES)
            self.state.current_step += 1
            self.state.save()
            log.info("Insert images step completed.")
            return True

        except Exception as e:
            self.state.last_error = str(e)
            self.state.save()
            log.error(f"Insert images step failed: {e}")
            return False

    async def step_save(self) -> bool:
        """Step 8: Click save button and capture result."""
        if STEP_SAVE in self.state.completed_steps:
            log.info("Step 'save' already completed, skipping.")
            return True

        log.info(f"[STEP {self.state.current_step + 1}] Saving product...")

        if self.dry_run:
            log.info("[DRY RUN] Would click '保存' button.")
            self.state.completed_steps.append(STEP_SAVE)
            self.state.current_step += 1
            self.state.save()
            return True

        try:
            # Scroll to bottom of page first
            await self.page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            await asyncio.sleep(1)

            # Find save button
            save_selectors = [
                "button:has-text('保存')",
                "button[type='primary']:has-text('保存')",
                "[class*='footer'] button:has-text('保存')",
                "[class*='action'] button:has-text('保存')",
            ]

            save_btn = None
            for selector in save_selectors:
                save_btn = await self.page.query_selector(selector)
                if save_btn:
                    log.debug(f"Found save button with selector: {selector}")
                    break

            if not save_btn:
                raise ElementNotFoundError("Save button not found")

            await save_btn.scroll_into_view_if_needed()
            await asyncio.sleep(0.3)
            await save_btn.click(timeout=5000, force=True)

            log.info("Clicked '保存' button. Waiting for save to complete...")
            await asyncio.sleep(3)

            await safe_screenshot(self.page, "final_result", self.state)

            self.state.saved = True
            self.state.completed_steps.append(STEP_SAVE)
            self.state.current_step += 1
            self.state.save()
            log.info("Save step completed.")
            return True

        except Exception as e:
            self.state.last_error = str(e)
            self.state.save()
            log.error(f"Save step failed: {e}")
            return False

    async def run(self):
        """Run the complete upload workflow."""
        log.info("=" * 60)
        log.info("MrShopPlus Image Upload Script Starting")
        log.info(f"Dry run mode: {self.dry_run}")
        log.info(f"Resume mode: {self.resume}")
        log.info(f"Headless mode: {self.headless}")
        log.info("=" * 60)

        try:
            await self.initialize_browser()

            # Run all steps in sequence
            steps = [
                self.step_login,
                self.step_navigate_to_product,
                self.step_delete_existing_images,
                self.step_open_upload_modal,
                self.step_select_url_tab,
                self.step_paste_urls,
                self.step_insert_images,
                self.step_save,
            ]

            for step in steps:
                log.info(f"Executing: {step.__name__}")
                success = await step()
                if not success:
                    log.error(f"Step {step.__name__} failed. Check logs for details.")
                    log.info(f"Last error: {self.state.last_error}")
                    log.info("Run again with --resume to continue from last successful step.")
                    return False

                # Small delay between steps
                await asyncio.sleep(1)

            log.info("=" * 60)
            log.info("ALL STEPS COMPLETED SUCCESSFULLY!")
            log.info("=" * 60)

            # Clear state on full success
            self.state.clear()

            return True

        except KeyboardInterrupt:
            log.warning("Interrupted by user. Progress saved. Run with --resume to continue.")
            self.state.save()
            return False

        except Exception as e:
            log.error(f"Unexpected error: {e}")
            self.state.last_error = str(e)
            self.state.save()
            log.info("Run with --resume to continue from last successful step.")
            return False

        finally:
            await self.cleanup()


# =============================================================================
# Main Entry Point
# =============================================================================

def parse_args():
    parser = argparse.ArgumentParser(
        description="MrShopPlus Image Upload Script - Robust URL-based image uploader"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Test run without actually performing actions",
    )
    parser.add_argument(
        "--headless",
        action="store_true",
        help="Run browser in headless mode",
    )
    parser.add_argument(
        "--resume",
        action="store_true",
        help="Resume from last interrupted run",
    )
    parser.add_argument(
        "--clear-state",
        action="store_true",
        help="Clear saved state and start fresh",
    )
    return parser.parse_args()


async def main():
    args = parse_args()

    if args.clear_state:
        state = UploadState()
        state.clear()
        log.info("State cleared. Starting fresh.")
        return

    async with MrShopUploader(
        dry_run=args.dry_run,
        headless=args.headless,
        resume=args.resume,
    ) as uploader:
        success = await uploader.run()
        sys.exit(0 if success else 1)


if __name__ == "__main__":
    asyncio.run(main())
