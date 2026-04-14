import asyncio
from playwright.async_api import async_playwright
import os

async def run():
    async with async_playwright() as p:
        # Connect to existing Chrome instance
        try:
            browser = await p.chromium.connect_over_cdp("http://localhost:9222")
        except Exception as e:
            print(f"Failed to connect to CDP: {e}")
            return
            
        context = browser.contexts[0]
        page = await context.new_page()
        
        print("Connected to CDP. Navigating to ERP...")
        await page.goto("https://www.mrshopplus.com/#/product/list_DTB_proProduct")
        await asyncio.sleep(3)
        
        # Search for DESCENTE
        print("Searching for product...")
        await page.fill("input[placeholder='商品名稱']", "DESCENTE")
        await page.keyboard.press("Enter")
        await asyncio.sleep(2)
        
        # Click Copy (复制) - looking for the icon class or button
        # Usually it is a button with an icon representing two papers
        # Trying multiple selectors for robustness
        copy_selectors = [
            ".el-button--text:has(i.el-icon-document-copy)",
            "button:has(i.el-icon-copy-document)",
            "button:has-text('复制')",
            "i.el-icon-document-copy"
        ]
        
        copy_btn = None
        for sel in copy_selectors:
            btn = page.locator(sel).first
            if await btn.is_visible():
                copy_btn = btn
                break
        
        if not copy_btn:
             print("Copy button not found. Using position-based click or checking DOM...")
             # Just click the first action button in the row if possible
             copy_btn = page.locator("td.el-table__cell .el-button--text").first
             
        print("Clicking Copy button...")
        await copy_btn.click()
        await asyncio.sleep(5)
        
        # Update Title
        print("Updating title...")
        title_input = page.locator("input[placeholder='请输入商品名称']").first
        if await title_input.is_visible():
            await title_input.fill("DESCENTE/迪桑特 硅胶小标运动 短袖Polo衫")
        
        # Update Price
        print("Updating price...")
        price_input = page.locator("input[placeholder='请输入銷售价']").first
        if await price_input.is_visible():
            await price_input.fill("150")
        
        # Delete existing images
        print("Deleting existing images...")
        delete_btns = page.locator(".el-upload-list__item-delete")
        count = await delete_btns.count()
        for i in range(count):
            try:
                await delete_btns.nth(0).click(timeout=1000)
                await asyncio.sleep(0.3)
            except:
                break
            
        # Upload new images
        print("Uploading new images...")
        temp_images_dir = r"c:\Users\Administrator\Documents\GitHub\ERP\temp_images"
        images = [os.path.join(temp_images_dir, f"img_{i}.jpg") for i in range(14)]
        images = [f for f in images if os.path.exists(f)]
        
        file_input = page.locator("input[type='file'][multiple]").first
        if await file_input.is_enabled():
            await file_input.set_input_files(images)
            print(f"Uploaded {len(images)} images.")
            await asyncio.sleep(8) # Wait for upload
        
        # Set Status to Unlisted (下架)
        print("Setting status to Unlisted...")
        # Status dropdown
        status_input = page.locator("input[placeholder='请选择商品状态']").first
        if await status_input.is_visible():
            await status_input.click()
            await asyncio.sleep(1)
            await page.click("li.el-select-dropdown__item:has-text('下架')")
        
        # Description - Inject into TinyMCE
        print("Injecting description...")
        brand_link = "Name: <a href='https://www.stockxshoesvip.net/descente/' target='_blank'>DESCENTE</a> 迪桑特 硅胶小标运动 短袖Polo衫"
        
        # Simple injection if window.tinyMCE exists
        await page.evaluate(f'''(text) => {{
            if (window.tinyMCE && window.tinyMCE.activeEditor) {{
                window.tinyMCE.activeEditor.setContent(text);
            }} else {{
                // Try finding iframe
                const frames = document.querySelectorAll('iframe');
                for (let f of frames) {{
                    if (f.id && f.id.includes('tinymce')) {{
                        f.contentDocument.body.innerHTML = text;
                    }}
                }}
            }}
        }}''', brand_link)

        # Save
        print("Saving...")
        save_btn = page.locator("button:has-text('保存')").first
        if await save_btn.is_visible():
            await save_btn.click()
        
        # Verify redirect
        try:
            await page.wait_for_url(lambda u: "action=3" in u, timeout=20000)
            print("Success! Product listed and action=3 reached.")
            if not os.path.exists("screenshots"): os.makedirs("screenshots")
            await page.screenshot(path="screenshots/listing_success.png")
        except:
            print("Timed out waiting for save redirect. Check screenshot.")
            if not os.path.exists("screenshots"): os.makedirs("screenshots")
            await page.screenshot(path="screenshots/listing_timeout.png")

        await asyncio.sleep(2)
        await page.close()

asyncio.run(run())
