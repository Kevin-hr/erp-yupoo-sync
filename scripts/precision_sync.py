import asyncio
import os
import requests
from playwright.async_api import async_playwright

ALBUM = {"album_id": "232138024", "title": "h150 WE11 DONE 26SS新款液态荧光LOGO弹幕印花短袖T恤"}
TEMP_DIR = r"c:\Users\Administrator\Documents\GitHub\ERP\temp_images"

async def extract_yupoo(page, album_id):
    url = f"https://x.yupoo.com/gallery/{album_id}"
    api_response_data = None
    def handle_response(response):
        nonlocal api_response_data
        if f'/api/albums/{album_id}/photos' in response.url:
            api_response_data = response
    page.on('response', handle_response)
    await page.goto(url)
    await asyncio.sleep(5)
    body = await api_response_data.json()
    photos = body.get('data', {}).get('list', [])
    return [f"http://pic.yupoo.com{p.get('path', '')}" for p in photos[:14]]

async def erp_precision_sync(page, album, images):
    await page.goto("https://www.mrshopplus.com/#/product/list_DTB_proProduct")
    await asyncio.sleep(3)
    
    # Template
    await page.fill('input[placeholder="请输入要搜索的内容"]', "短袖T恤")
    await page.keyboard.press("Enter")
    await asyncio.sleep(5)
    
    # Click Copy
    await page.locator("i.el-icon-document-copy").first.click()
    print("Waiting for Copy Page...")
    await page.wait_for_url(lambda u: "action=2" in u, timeout=20000)
    await asyncio.sleep(5)
    
    # Title & Remark (Native Fill)
    title = album['title'].replace("h150 ", "").strip()
    await page.locator('input[placeholder="请输入商品名称"]').fill(title)
    await page.locator('input[placeholder="请输入商品备注"]').fill(album['album_id'])
    
    # Price
    price_inp = page.locator('input[placeholder="请输入售价"]')
    await price_inp.fill("150")
    
    # Mode Switch
    label = page.locator('label:has-text("多规格")')
    sw = label.locator("xpath=following-sibling::div").locator(".is-checked")
    if await sw.count() > 0:
        await sw.click()
        await asyncio.sleep(2)
        await page.locator(".el-dialog__wrapper:visible .el-dialog__footer button:has-text('确定')").click()
        await asyncio.sleep(2)

    # Status: Unlisted
    await page.locator('input[placeholder="请选择商品状态"]').click()
    await asyncio.sleep(1)
    await page.locator('.el-select-dropdown__item:visible:has-text("下架")').click()
    
    # TinyMCE Hard Overwrite
    content = f'<p><a href="https://www.stockxshoesvip.net/we11done/">STOCKXSHOESVIP</a></p><p>{title}</p>'
    await page.evaluate(f'''(c) => {{
        if (typeof tinymce !== 'undefined' && tinymce.activeEditor) {{
            tinymce.activeEditor.setContent(c);
        }}
    }}''', content)
    
    # Images
    delete_btns = page.locator(".el-upload-list__item-delete")
    for _ in range(await delete_btns.count()):
        await delete_btns.nth(0).click()
        await asyncio.sleep(0.3)
        
    await page.evaluate('''() => {
        let input = document.querySelector('input[type="file"]');
        if (input) {
            input.multiple = true;
            input.id = "steel_upload";
            input.style.display = "block";
        }
    }''')
    await page.locator("#steel_upload").set_input_files(images)
    await asyncio.sleep(10)
    
    # Save
    await page.locator("button.el-button--primary:has-text('保存')").click()
    await page.wait_for_url(lambda u: "list" in u or "action=1" in u, timeout=30000)
    print("SUCCESS")

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.connect_over_cdp("http://localhost:9222")
        context = browser.contexts[0]
        page = await context.new_page()
        urls = await extract_yupoo(page, ALBUM['album_id'])
        local_paths = []
        for i, u in enumerate(urls):
            r = requests.get(u)
            p_ = os.path.join(TEMP_DIR, f"steel_{i}.jpg")
            with open(p_, 'wb') as f: f.write(r.content)
            local_paths.append(p_)
        await erp_precision_sync(page, ALBUM, local_paths)
        await page.close()

if __name__ == "__main__":
    asyncio.run(main())
