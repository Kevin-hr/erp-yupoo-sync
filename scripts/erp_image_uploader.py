import asyncio
from playwright.async_api import async_playwright
import os

async def upload_erp_images():
    # MrShopPlus credentials (corrected by user)
    username = "zhiqiang"
    password = "123qazwsx"
    
    # Yupoo credentials (corrected by user)
    yupoo_user = "lol2024"
    yupoo_pass = "9longt#3"
    yupoo_url = "https://lol2024.x.yupoo.com/albums"
    target_url = "https://www.mrshopplus.com/#/product/form_DTB_proProduct/0?action=4&pkValues=%5B526271466670100%5D"
    
    yupoo_links = [
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
        "http://pic.yupoo.com/lol2024/7de06d3b/5962e3fa.jpeg"
    ]

    async with async_playwright() as p:
        # Launch browser in non-headless mode for visibility if possible, 
        # but here we use default (headless or as configured)
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context(viewport={'width': 1920, 'height': 1080})
        page = await context.new_page()

        print(f"Logging into MrShopPlus with {username}...")
        await page.goto("https://www.mrshopplus.com/#/login?redirect=%2Fmain")
        await page.fill("#username", username)
        await page.fill("input[placeholder='请输入密码']", password)
        await page.click("#login-btn")
        await page.wait_for_timeout(3000) # Wait for login
        
        print(f"Navigating to product form: {target_url}")
        await page.goto(target_url)
        await page.wait_for_selector(".imglist-img", timeout=10000)
        
        # 1. Delete existing images
        print("Clearing existing images...")
        while True:
            trash_icons = await page.query_selector_all(".fa-trash-o")
            if not trash_icons:
                break
            await trash_icons[0].click()
            await page.wait_for_timeout(500)
            
        # 2. Click Upload button (+)
        print("Opening upload modal...")
        await page.click(".img-upload-btn .fa-plus")
        await page.wait_for_selector(".ant-modal-content", timeout=5000)
        
        # 3. Choose URL Upload tab
        # Based on screenshots, find the text "URL上传"
        tabs = await page.query_selector_all(".ant-tabs-tab")
        for tab in tabs:
            if "URL上传" in await tab.inner_text():
                await tab.click()
                break
        
        # 4. Paste links
        print("Pasting Yupoo links...")
        await page.fill("textarea", "\n".join(yupoo_links))
        
        # 5. Insert
        # Find button with text "插入图片视频"
        buttons = await page.query_selector_all("button")
        for btn in buttons:
            if "插入图片视频" in await btn.inner_text():
                await btn.click()
                break
        
        await page.wait_for_timeout(3000) # Wait for processing
        
        # 6. Save
        print("Saving product...")
        save_btn = await page.query_selector("button:has-text('保存')")
        if save_btn:
            await save_btn.click()
            print("Successfully clicked Save.")
        else:
            print("Save button not found.")
            
        # Capture final state
        screenshot_path = "C:/Users/Administrator/Documents/GitHub/ERP/final_erp_upload.png"
        await page.screenshot(path=screenshot_path)
        print(f"Workflow complete. Screenshot saved to {screenshot_path}")
        
        await browser.close()

if __name__ == "__main__":
    asyncio.run(upload_erp_images())
