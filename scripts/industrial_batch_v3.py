import asyncio
import os
import requests
from playwright.async_api import async_playwright

ALBUMS = [
  {"album_id": "232138024", "title": "h150 WE11 DONE 26SS新款液态荧光LOGO弹幕印花短袖T恤"},
  {"album_id": "232138020", "title": "h150 WE11 DONE 26SS新款液态荧光LOGO弹幕印花短袖T恤"},
  {"album_id": "232138015", "title": "h140 Well done 25SS春夏新款数据款火焰弹幕LOGO字母印花短袖T恤"},
  {"album_id": "232138011", "title": "h140 Well done 25SS春夏新款数据款火焰弹幕LOGO字母印花短袖T恤"},
  {"album_id": "232138005", "title": "h140 Well done 25SS春夏新款数据款火焰弹幕LOGO字母印花短袖T恤"},
  {"album_id": "232137473", "title": "h140 We11done 杨洋明星同款上身简约字母印花短袖T恤"},
  {"album_id": "232137470", "title": "h140 We11done 杨洋明星同款上身简约字母印花短袖T恤"}
]

TEMP_DIR = r"c:\Users\Administrator\Documents\GitHub\ERP\temp_images"
os.makedirs(TEMP_DIR, exist_ok=True)

async def extract_yupoo(page, album_id):
    url = f"https://x.yupoo.com/gallery/{album_id}"
    print(f"Extracting {album_id}...")
    api_response_data = None
    def handle_response(response):
        nonlocal api_response_data
        if f'/api/albums/{album_id}/photos' in response.url: api_response_data = response
    page.on('response', handle_response)
    for _ in range(2):
        await page.goto(url)
        await asyncio.sleep(4)
        if api_response_data: break
    if not api_response_data: return []
    body = await api_response_data.json()
    photos = body.get('data', {}).get('list', [])
    return [f"http://pic.yupoo.com{p.get('path', '')}" for p in photos[:14]]

async def erp_sync_v3(page, album, images):
    album_id = album['album_id']
    title = album['title'].replace("h150 ", "").replace("h140 ", "").strip()
    price = "150" if "h150" in album['title'] else "140"
    
    print(f"Syncing {album_id} - {title}...")
    await page.goto("https://www.mrshopplus.com/#/product/list_DTB_proProduct")
    await asyncio.sleep(3)
    
    # Template Copy
    await page.fill('input[placeholder="请输入要搜索的内容"]', "短袖T恤")
    await page.keyboard.press("Enter")
    await asyncio.sleep(4)
    await page.locator("i.el-icon-document-copy").first.click()
    await page.wait_for_url(lambda u: "action=2" in u, timeout=15000)
    await asyncio.sleep(6) # Stabilization
    
    # 1. Title & Remark
    await page.locator('input[placeholder="请输入商品名称"]').fill(title)
    await page.locator('input[placeholder="请输入商品备注"]').fill(album_id)
    
    # 2. Sequential Status & Spec Toggle
    # Status: Unlisted
    await page.locator('input[placeholder="请选择商品状态"]').click()
    await asyncio.sleep(1)
    await page.locator('.el-select-dropdown__item:visible:has-text("下架")').click()
    await asyncio.sleep(1)
    
    # Toggle Specs OFF
    label = page.locator('label:has-text("多规格")')
    sw = label.locator("xpath=following-sibling::div").locator(".el-switch.is-checked")
    if await sw.count() > 0:
        await sw.click()
        await asyncio.sleep(3)
        confirm = page.locator(".el-dialog__wrapper:visible button:has-text('确定')")
        if await confirm.count() > 0: await confirm.click()
        await asyncio.sleep(5) # Critical UI Recover Wait
        
    # 3. Price Injection (Recovery)
    # Target the first empty price input in the form
    price_inp = page.locator('input[placeholder="请输入售价"]').first
    await price_inp.fill(price)
    await price_inp.dispatch_event('change')
    
    # 4. Description Purge & Brand Prepend
    brand_link = f'<p><a href="https://www.stockxshoesvip.net/we11done/">STOCKXSHOESVIP</a></p><p>{title}</p>'
    await page.evaluate(f'''(c) => {{
        if (typeof tinymce !== 'undefined' && tinymce.activeEditor) {{
            tinymce.activeEditor.setContent(c);
        }}
    }}''', brand_link)
    
    # 5. SEO & Extra Description Purge
    await page.evaluate('''() => {
        // Clear all textareas and inputs that contain "Nike" or "Kobe" if they aren't the title
        document.querySelectorAll('input, textarea').forEach(el => {
            if (el.value.includes('Nike') || el.value.includes('Kobe')) {
                el.value = '';
                el.dispatchEvent(new Event('input', { bubbles: true }));
            }
        });
    }''')
    
    # 6. Images
    delete_btns = page.locator(".el-upload-list__item-delete")
    for _ in range(await delete_btns.count()):
        await delete_btns.nth(0).click()
        await asyncio.sleep(0.3)
    
    # Force Multiple Ingestion
    await page.evaluate('''() => {
        let input = document.querySelector('input[type="file"]');
        if (input) {
            input.multiple = true;
            input.id = "steel_v3_upload";
            input.style.display = "block";
        }
    }''')
    await page.locator("#steel_v3_upload").set_input_files(images)
    await asyncio.sleep(15) 
    
    # 7. Save
    print("Saving...")
    await page.locator("button.el-button--primary:has-text('保存')").click()
    try:
        await page.wait_for_url(lambda u: "list" in u or "action=1" in u or "action=3" in u, timeout=40000)
        print(f"SUCCESS: {album_id}")
        return True
    except:
        print(f"VERIFICATION TIMEOUT: {album_id}")
        return False

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.connect_over_cdp("http://localhost:9222")
        context = browser.contexts[0]
        page = await context.new_page()
        for i, album in enumerate(ALBUMS):
            print(f"--- Batch {i+1}/7 ---")
            img_urls = await extract_yupoo(page, album['album_id'])
            if not img_urls: continue
            local_paths = []
            for j, u in enumerate(img_urls):
                try:
                    r = requests.get(u, timeout=10)
                    p_ = os.path.join(TEMP_DIR, f"v3_{album['album_id']}_{j}.jpg")
                    with open(p_, 'wb') as f: f.write(r.content)
                    local_paths.append(p_)
                except: pass
            await erp_sync_v3(page, album, local_paths)
            await asyncio.sleep(2)
        await page.close()

if __name__ == "__main__":
    asyncio.run(main())
