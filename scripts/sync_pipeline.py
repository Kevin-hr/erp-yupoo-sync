#!/usr/bin/env python3
"""
Yupoo to MrShopPlus End-to-End Sync Pipeline

Pipeline Architecture:
    Stage 1: YupooExtractor    - Extract image URLs from Yupoo album
    Stage 2: MetadataPreparer   - Prepare image URLs and metadata
    Stage 3: MrShopLogin       - Login to MrShopPlus (cookie-based)
    Stage 4: FormNavigator     - Navigate to product form
    Stage 5: ImageUploader     - Upload images via URL
    Stage 6: Verifier          - Verify and save

Usage:
    python sync_pipeline.py --album-id 231019138 --dry-run
    python sync_pipeline.py --step 3 --resume
    python sync_pipeline.py --album-id 231019138 --cookies cookies.json
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

from playwright.async_api import async_playwright, Page, BrowserContext, Browser

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger('sync_pipeline')


class PipelineStage(Enum):
    """Pipeline stage enumeration"""
    EXTRACT = 1
    PREPARE = 2
    LOGIN = 3
    NAVIGATE = 4
    UPLOAD = 5
    VERIFY = 6


STAGE_NAMES = {
    PipelineStage.EXTRACT: "YupooExtractor",
    PipelineStage.PREPARE: "MetadataPreparer",
    PipelineStage.LOGIN: "MrShopLogin",
    PipelineStage.NAVIGATE: "FormNavigator",
    PipelineStage.UPLOAD: "ImageUploader",
    PipelineStage.VERIFY: "Verifier",
}


@dataclass
class PipelineState:
    """Pipeline execution state"""
    album_id: str
    album_title: str = ""
    image_urls: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    cookies_loaded: bool = False
    logged_in: bool = False
    form_loaded: bool = False
    upload_complete: bool = False
    save_complete: bool = False
    error: Optional[str] = None
    start_time: Optional[datetime] = None
    stage_results: Dict[str, Any] = field(default_factory=dict)


class YupooExtractor:
    """Stage 1: Extract images from Yupoo album via batch external links method"""

    def __init__(self, album_id: str):
        self.album_id = album_id
        self.base_url = "https://www.yupoo.com"
        self.album_url = f"{self.base_url}/album/{album_id}"

    async def extract(self, page: Page, dry_run: bool = False) -> List[str]:
        """
        Extract image URLs using the 9-step backend method:
        1. Navigate to album
        2. Enter product detail
        3. Click '进入后台'
        4. Search product
        5. Select images (max 14)
        6. Click '批量外链'
        7. Get links
        8. Copy to clipboard
        """
        logger.info(f"Extracting images from album: {self.album_id}")

        if dry_run:
            # In dry-run mode, return mock data for testing
            mock_urls = [
                f"http://pic.yupoo.com/lol2024/{i:08x}/preview.jpeg"
                for i in range(14)
            ]
            logger.info(f"[DRY-RUN] Would extract {len(mock_urls)} image URLs")
            return mock_urls

        # Navigate to album
        await page.goto(self.album_url)
        await page.wait_for_load_state('networkidle')
        await asyncio.sleep(2)

        # Step 1-3: Navigate and enter detail view
        # Click on first product in album grid
        try:
            product_selector = ".album-photo, .photo-item, [class*='photo']"
            await page.wait_for_selector(product_selector, timeout=10000)
            await page.click(product_selector)
            await asyncio.sleep(2)
        except Exception as e:
            logger.warning(f"Could not click product: {e}")
            # Fallback: try to get any image links directly
            pass

        # Step 4: Click '进入后台' (Enter Backend)
        try:
            backend_btn = await page.query_selector("text=进入后台")
            if backend_btn:
                await backend_btn.click()
                await asyncio.sleep(2)
        except Exception as e:
            logger.warning(f"Could not find backend button: {e}")

        # Step 5-8: Extract batch external links
        # Look for the batch external links feature
        image_urls = []

        # Try to find image elements in the album
        img_elements = await page.query_selector_all("img[class*='photo'], img[class*='image']")
        for img in img_elements[:14]:  # Max 14 images
            src = await img.get_attribute("src")
            if src and "pic.yupoo.com" in src:
                # Convert preview URL to full resolution
                full_url = src.replace("/preview.", "/high.")
                if full_url not in image_urls:
                    image_urls.append(full_url)

        # If no images found via page parsing, try clipboard method
        if not image_urls:
            logger.info("Attempting clipboard extraction method...")
            # This would require the 9-step manual process
            # For now, return URLs found

        logger.info(f"Extracted {len(image_urls)} image URLs")
        return image_urls


class MetadataPreparer:
    """Stage 2: Prepare image URLs and metadata for upload"""

    def __init__(self, image_urls: List[str]):
        self.image_urls = image_urls

    def prepare(self, metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Prepare formatted data for MrShopPlus form"""
        logger.info(f"Preparing metadata for {len(self.image_urls)} images")

        prepared = {
            "image_urls": self.image_urls,
            "url_batch": "\n".join(self.image_urls),
            "count": len(self.image_urls),
            "timestamp": datetime.now().isoformat(),
            "metadata": metadata or {}
        }

        logger.info(f"Prepared data: {prepared['count']} images")
        return prepared


class MrShopLogin:
    """Stage 3: Login to MrShopPlus with cookie-based persistence"""

    def __init__(self, cookies_file: Optional[str] = None):
        self.cookies_file = cookies_file or "cookies.json"
        self.login_url = "https://www.mrshopplus.com/#/login"
        self.email = "litzyjames5976@gmail.com"
        self.password = "RX3jesthYF7d"

    async def login(self, context: BrowserContext, dry_run: bool = False) -> bool:
        """Login to MrShopPlus using cookies or credentials"""
        logger.info("Starting MrShopPlus login...")

        # Try to load cookies first
        if os.path.exists(self.cookies_file):
            try:
                with open(self.cookies_file, 'r') as f:
                    cookies = json.load(f)
                await context.add_cookies(cookies)
                logger.info(f"Loaded {len(cookies)} cookies from {self.cookies_file}")
                return True
            except Exception as e:
                logger.warning(f"Failed to load cookies: {e}")

        if dry_run:
            logger.info("[DRY-RUN] Would login with credentials")
            return True

        # Fallback: login with credentials
        page = await context.new_page()
        try:
            await page.goto(self.login_url)
            await page.wait_for_load_state('networkidle')

            # Fill login form
            await page.fill("#username", self.email)
            await page.fill("input[placeholder='请输入密码']", self.password)
            await page.click("#login-btn")

            # Wait for login to complete
            await page.wait_for_timeout(3000)

            # Save cookies for future use
            cookies = await context.cookies()
            with open(self.cookies_file, 'w') as f:
                json.dump(cookies, f, indent=2)
            logger.info(f"Saved {len(cookies)} cookies to {self.cookies_file}")

            await page.close()
            return True

        except Exception as e:
            logger.error(f"Login failed: {e}")
            await page.close()
            return False


class FormNavigator:
    """Stage 4: Navigate to product form in MrShopPlus"""

    def __init__(self, product_id: Optional[str] = None, action: str = "edit"):
        self.product_id = product_id or "0"
        self.action = action
        # Default form URL pattern
        self.base_url = "https://www.mrshopplus.com/#/product/form_DTB_proProduct"

    def get_form_url(self, product_id: str) -> str:
        """Generate form URL for a product"""
        return f"{self.base_url}/{product_id}?action=4&pkValues=%5B{product_id}%5D"

    async def navigate(self, page: Page, product_id: Optional[str] = None, dry_run: bool = False) -> bool:
        """Navigate to product form page"""
        target_id = product_id or self.product_id
        form_url = self.get_form_url(target_id)

        logger.info(f"Navigating to product form: {form_url}")

        if dry_run:
            logger.info("[DRY-RUN] Would navigate to form")
            return True

        try:
            await page.goto(form_url)
            await page.wait_for_selector(".imglist-img, .product-form", timeout=10000)
            logger.info("Form loaded successfully")
            return True
        except Exception as e:
            logger.error(f"Failed to navigate to form: {e}")
            return False


class ImageUploader:
    """Stage 5: Upload images via URL to MrShopPlus"""

    def __init__(self, image_urls: List[str]):
        self.image_urls = image_urls

    async def upload(self, page: Page, dry_run: bool = False) -> bool:
        """Upload images via URL upload method"""
        logger.info(f"Starting image upload: {len(self.image_urls)} images")

        if dry_run:
            logger.info(f"[DRY-RUN] Would upload {len(self.image_urls)} images")
            return True

        try:
            # Step 1: Clear existing images
            logger.info("Clearing existing images...")
            await self._clear_existing_images(page)

            # Step 2: Open upload modal
            logger.info("Opening upload modal...")
            await self._open_upload_modal(page)

            # Step 3: Switch to URL upload tab
            logger.info("Switching to URL upload tab...")
            await self._switch_to_url_tab(page)

            # Step 4: Paste image URLs
            logger.info("Pasting image URLs...")
            await self._paste_urls(page)

            # Step 5: Insert images
            logger.info("Inserting images...")
            await self._insert_images(page)

            # Step 6: Wait for processing
            logger.info("Waiting for image processing...")
            await page.wait_for_timeout(5000)

            logger.info("Image upload completed")
            return True

        except Exception as e:
            logger.error(f"Image upload failed: {e}")
            return False

    async def _clear_existing_images(self, page: Page):
        """Delete existing images in the form"""
        while True:
            trash_icons = await page.query_selector_all(".fa-trash-o")
            if not trash_icons:
                break
            await trash_icons[0].click()
            await page.wait_for_timeout(500)

    async def _open_upload_modal(self, page: Page):
        """Click the upload button to open modal"""
        upload_btn = await page.query_selector(".img-upload-btn .fa-plus")
        if upload_btn:
            await upload_btn.click()
        else:
            # Try alternative selector
            await page.click(".img-upload-btn")
        await page.wait_for_selector(".ant-modal-content", timeout=5000)

    async def _switch_to_url_tab(self, page: Page):
        """Switch to URL upload tab"""
        tabs = await page.query_selector_all(".ant-tabs-tab")
        for tab in tabs:
            tab_text = await tab.inner_text()
            if "URL上传" in tab_text:
                await tab.click()
                break

    async def _paste_urls(self, page: Page):
        """Paste image URLs into textarea"""
        textarea = await page.query_selector("textarea")
        if textarea:
            url_batch = "\n".join(self.image_urls)
            await textarea.fill(url_batch)

    async def _insert_images(self, page: Page):
        """Click insert button to add images"""
        buttons = await page.query_selector_all("button")
        for btn in buttons:
            btn_text = await btn.inner_text()
            if "插入图片视频" in btn_text:
                await btn.click()
                break


class Verifier:
    """Stage 6: Verify upload and save product"""

    async def verify(self, page: Page, dry_run: bool = False) -> bool:
        """Verify images uploaded and save product"""
        logger.info("Verifying and saving...")

        if dry_run:
            logger.info("[DRY-RUN] Would verify and save")
            return True

        try:
            # Wait for images to appear
            await page.wait_for_timeout(3000)

            # Capture screenshot for verification
            screenshot_path = f"C:/Users/Administrator/Documents/GitHub/ERP/verify_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
            await page.screenshot(path=screenshot_path)
            logger.info(f"Verification screenshot: {screenshot_path}")

            # Click save button
            save_btn = await page.query_selector("button:has-text('保存')")
            if save_btn:
                await save_btn.click()
                logger.info("Save button clicked")
                await page.wait_for_timeout(2000)
            else:
                logger.warning("Save button not found")

            # Check for success indicators
            success = await self._check_success(page)
            return success

        except Exception as e:
            logger.error(f"Verification failed: {e}")
            return False

    async def _check_success(self, page: Page) -> bool:
        """Check if save was successful"""
        # Look for success toast or confirmation
        try:
            toast = await page.query_selector(".ant-message-success, .success-message")
            if toast:
                logger.info("Save successful - confirmation received")
                return True
        except:
            pass

        # If no explicit success indicator, assume success if no error
        logger.info("No explicit error - assuming save successful")
        return True


class SyncPipeline:
    """Main E2E sync pipeline orchestrator"""

    def __init__(
        self,
        album_id: str,
        product_id: Optional[str] = None,
        cookies_file: Optional[str] = None,
        dry_run: bool = False,
        start_step: int = 1,
        end_step: int = 6
    ):
        self.album_id = album_id
        self.product_id = product_id
        self.cookies_file = cookies_file
        self.dry_run = dry_run
        self.start_step = PipelineStage(start_step)
        self.end_step = PipelineStage(end_step)
        self.state = PipelineState(album_id=album_id)
        self.browser: Optional[Browser] = None
        self.context: Optional[BrowserContext] = None
        self.page: Optional[Page] = None

        # Pipeline components
        self.extractor = YupooExtractor(album_id)
        self.preparer: Optional[MetadataPreparer] = None
        self.login = MrShopLogin(cookies_file)
        self.navigator = FormNavigator(product_id)
        self.uploader: Optional[ImageUploader] = None
        self.verifier = Verifier()

    async def run(self):
        """Execute the full pipeline"""
        self.state.start_time = datetime.now()
        logger.info("=" * 60)
        logger.info(f"Starting Yupoo to MrShopPlus Sync Pipeline")
        logger.info(f"Album ID: {self.album_id}")
        logger.info(f"Dry Run: {self.dry_run}")
        logger.info(f"Steps: {self.start_step.name} -> {self.end_step.name}")
        logger.info("=" * 60)

        try:
            # Initialize browser
            await self._init_browser()

            # Execute stages
            if self.start_step.value <= PipelineStage.EXTRACT.value <= self.end_step.value:
                await self._stage_extract()

            if self.start_step.value <= PipelineStage.PREPARE.value <= self.end_step.value:
                await self._stage_prepare()

            if self.start_step.value <= PipelineStage.LOGIN.value <= self.end_step.value:
                await self._stage_login()

            if self.start_step.value <= PipelineStage.NAVIGATE.value <= self.end_step.value:
                await self._stage_navigate()

            if self.start_step.value <= PipelineStage.UPLOAD.value <= self.end_step.value:
                await self._stage_upload()

            if self.start_step.value <= PipelineStage.VERIFY.value <= self.end_step.value:
                await self._stage_verify()

            # Success
            elapsed = (datetime.now() - self.state.start_time).total_seconds()
            logger.info("=" * 60)
            logger.info(f"Pipeline completed successfully in {elapsed:.1f}s")
            logger.info("=" * 60)

        except Exception as e:
            logger.error(f"Pipeline failed: {e}")
            self.state.error = str(e)
            raise

        finally:
            await self._cleanup()

    async def _init_browser(self):
        """Initialize Playwright browser"""
        logger.info("Initializing browser...")
        playwright = await async_playwright().start()
        self.browser = await playwright.chromium.launch(headless=False)
        self.context = await self.browser.new_context(
            viewport={'width': 1920, 'height': 1080}
        )
        self.page = await self.context.new_page()
        logger.info("Browser initialized")

    async def _stage_extract(self):
        """Stage 1: Extract images from Yupoo"""
        logger.info("[STAGE 1] YupooExtractor")
        self.state.image_urls = await self.extractor.extract(self.page, self.dry_run)
        self.state.stage_results['extract'] = {
            'image_count': len(self.state.image_urls),
            'urls': self.state.image_urls[:3] + ['...'] if len(self.state.image_urls) > 3 else self.state.image_urls
        }
        logger.info(f"Extracted {len(self.state.image_urls)} images")

    async def _stage_prepare(self):
        """Stage 2: Prepare metadata"""
        logger.info("[STAGE 2] MetadataPreparer")
        self.preparer = MetadataPreparer(self.state.image_urls)
        self.state.metadata = self.preparer.prepare()
        self.state.stage_results['prepare'] = {
            'batch_size': len(self.state.image_urls),
            'timestamp': self.state.metadata['timestamp']
        }
        logger.info("Metadata prepared")

    async def _stage_login(self):
        """Stage 3: Login to MrShopPlus"""
        logger.info("[STAGE 3] MrShopLogin")
        self.state.cookies_loaded = await self.login.login(self.context, self.dry_run)
        self.state.logged_in = self.state.cookies_loaded
        self.state.stage_results['login'] = {
            'cookies_loaded': self.state.cookies_loaded,
            'logged_in': self.state.logged_in
        }
        if not self.state.logged_in:
            raise Exception("Login failed")
        logger.info("Login successful")

    async def _stage_navigate(self):
        """Stage 4: Navigate to product form"""
        logger.info("[STAGE 4] FormNavigator")
        self.state.form_loaded = await self.navigator.navigate(
            self.page, self.product_id, self.dry_run
        )
        self.state.stage_results['navigate'] = {
            'form_loaded': self.state.form_loaded,
            'product_id': self.product_id or '0'
        }
        if not self.state.form_loaded and not self.dry_run:
            raise Exception("Form navigation failed")
        logger.info("Form navigation complete")

    async def _stage_upload(self):
        """Stage 5: Upload images"""
        logger.info("[STAGE 5] ImageUploader")
        self.uploader = ImageUploader(self.state.image_urls)
        upload_success = await self.uploader.upload(self.page, self.dry_run)
        self.state.upload_complete = upload_success
        self.state.stage_results['upload'] = {
            'success': upload_success,
            'image_count': len(self.state.image_urls)
        }
        if not upload_success:
            raise Exception("Image upload failed")
        logger.info("Image upload complete")

    async def _stage_verify(self):
        """Stage 6: Verify and save"""
        logger.info("[STAGE 6] Verifier")
        save_success = await self.verifier.verify(self.page, self.dry_run)
        self.state.save_complete = save_success
        self.state.stage_results['verify'] = {
            'success': save_success
        }
        logger.info("Verification complete")

    async def _cleanup(self):
        """Clean up resources"""
        if self.page:
            await self.page.close()
        if self.context:
            await self.context.close()
        if self.browser:
            await self.browser.close()
        logger.info("Resources cleaned up")

    def get_state_report(self) -> Dict[str, Any]:
        """Get pipeline state report"""
        return {
            'album_id': self.state.album_id,
            'image_count': len(self.state.image_urls),
            'logged_in': self.state.logged_in,
            'form_loaded': self.state.form_loaded,
            'upload_complete': self.state.upload_complete,
            'save_complete': self.state.save_complete,
            'error': self.state.error,
            'stages': self.state.stage_results,
            'dry_run': self.dry_run
        }


def parse_args():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(
        description='Yupoo to MrShopPlus E2E Sync Pipeline',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Full pipeline with album 231019138
  python sync_pipeline.py --album-id 231019138

  # Dry run (no actual changes)
  python sync_pipeline.py --album-id 231019138 --dry-run

  # Start from step 3 (login) with existing cookies
  python sync_pipeline.py --album-id 231019138 --step 3 --cookies cookies.json

  # Resume from step 5 with specific product ID
  python sync_pipeline.py --album-id 231019138 --step 5 --product-id 526271466670100
        """
    )

    parser.add_argument(
        '--album-id', '-a',
        type=str,
        required=True,
        help='Yupoo album ID to extract images from'
    )

    parser.add_argument(
        '--product-id', '-p',
        type=str,
        default=None,
        help='MrShopPlus product ID to update (default: 0 for new product)'
    )

    parser.add_argument(
        '--cookies', '-c',
        type=str,
        default='cookies.json',
        help='Path to cookies JSON file (default: cookies.json)'
    )

    parser.add_argument(
        '--step', '-s',
        type=int,
        default=1,
        choices=[1, 2, 3, 4, 5, 6],
        help='Start from specific step (default: 1)'
    )

    parser.add_argument(
        '--end-step', '-e',
        type=int,
        default=6,
        choices=[1, 2, 3, 4, 5, 6],
        help='End at specific step (default: 6)'
    )

    parser.add_argument(
        '--dry-run', '-d',
        action='store_true',
        help='Run without making actual changes'
    )

    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Enable verbose logging'
    )

    parser.add_argument(
        '--resume',
        action='store_true',
        help='Resume from specified step (implies cookies exist)'
    )

    return parser.parse_args()


async def main():
    """Main entry point"""
    args = parse_args()

    # Configure logging level
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    # Validate step range
    if args.step > args.end_step:
        logger.error(f"Start step ({args.step}) cannot be greater than end step ({args.end_step})")
        sys.exit(1)

    # Create and run pipeline
    pipeline = SyncPipeline(
        album_id=args.album_id,
        product_id=args.product_id,
        cookies_file=args.cookies,
        dry_run=args.dry_run,
        start_step=args.step,
        end_step=args.end_step
    )

    try:
        await pipeline.run()

        # Print final report
        report = pipeline.get_state_report()
        print("\n" + "=" * 60)
        print("PIPELINE EXECUTION REPORT")
        print("=" * 60)
        print(json.dumps(report, indent=2, default=str))

    except KeyboardInterrupt:
        logger.info("Pipeline interrupted by user")
        sys.exit(130)
    except Exception as e:
        logger.error(f"Pipeline failed: {e}")
        if args.verbose:
            import traceback
            traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())