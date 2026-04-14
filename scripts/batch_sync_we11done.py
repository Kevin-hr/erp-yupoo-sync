import asyncio
import os
import json
import logging
import requests
from playwright.async_api import async_playwright

# FINAL DATA LIST
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
    print(f"Extracting {url}...")
    api_response_data = None
    def handle_response(response):
        nonlocal api_response_data
        if f'/api/albums/{album_id}/photos' in response.url:
            api_response_data = response
    for _ in range(3):
        page.on('response', handle_response)
        await page.goto(url, timeout=40000)
        await asyncio.sleep(5)
        if not api_response_data:
            await page.evaluate("window.scrollTo(0, document.body.scrollHeight/2)")
            await asyncio.sleep(3)
            await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            await asyncio.sleep(2)
        if api_response_data: break
        print(f"Retrying extraction for {album_id}...")
    if not api_response_data: raise Exception(f"Failed to capture API response for {album_id}")
    try: body = await api_response_data.json()
    except: return []
    photos = body.get('data', {}).get('list', [])
    image_urls = [f"http://pic.yupoo.com{p.get('path', '')}" for p in photos[:14]]
    return image_urls

async def download_images(urls):
    if not urls: return []
    for f in os.listdir(TEMP_DIR):
        try: os.remove(os.path.join(TEMP_DIR, f))
        except: pass
    local_paths = []
    for i, url in enumerate(urls):
        try:
            r = requests.get(url, timeout=12)
            if r.status_code == 200:
                path = os.path.join(TEMP_DIR, f"img_{i}.jpg")
                with open(path, 'wb') as f: f.write(r.content)
                local_paths.append(path)
        except: pass
    return local_paths

async def erp_sync(page, album_data, local_images):
    title = album_data['title']
    album_id = album_data['album_id']
    price = "150" if "h150" in title else "140"
    clean_title = title.replace("h150 ", "").replace("h140 ", "").strip()
    
    print(f"Listing {clean_title} (ID: {album_id}) on ERP...")
    await page.goto("https://www.mrshopplus.com/#/product/list_DTB_proProduct")
    await asyncio.sleep(3)
    
    # Template Selection
    search_input = page.locator('input[placeholder="请输入要搜索的内容"]').first
    await search_input.clear()
    await search_input.fill("短袖T恤")
    await page.keyboard.press("Enter")
    await asyncio.sleep(4)
    
    copy_btn = page.locator("i.el-icon-document-copy").first
    await copy_btn.click()
    await asyncio.sleep(8)
    
    # Title & Remark Injection (FIXED MULTI-ARG)
    await page.evaluate(f'''([t, rid]) => {{
        let titleInp = [...document.querySelectorAll('input')].find(i => i.placeholder === '请输入商品名称');
        if (titleInp) {{
            titleInp.value = t;
            titleInp.dispatchEvent(new Event('input', {{ bubbles: true }}));
        }}
        let remarkInp = [...document.querySelectorAll('input')].find(i => i.placeholder === '请输入商品备注');
        if (remarkInp) {{
            remarkInp.value = rid;
            remarkInp.dispatchEvent(new Event('input', {{ bubbles: true }}));
        }}
    }}''', [clean_title, album_id])
    
    # Single-Spec Mode Switch
    print("Switching Mode...")
    await page.evaluate('''() => {
        let label = [...document.querySelectorAll('label')].find(l => l.innerText.includes('多规格'));
        if (label) {
            let sw = label.nextElementSibling.querySelector('.el-switch');
            if (sw && sw.classList.contains('is-checked')) sw.click();
        }
    }''')
    await asyncio.sleep(3)
    confirm_btn = page.locator(".el-dialog__wrapper:visible .el-dialog__footer button:has-text('确定')").first
    if await confirm_btn.count() > 0:
        await confirm_btn.click()
        await asyncio.sleep(2)

    # Price Injection
    await page.evaluate(f'''(p) => {{
        let inp = [...document.querySelectorAll('input')].find(i => i.placeholder === '请输入售价');
        if (inp) {{
            inp.value = p;
            inp.dispatchEvent(new Event('input', {{ bubbles: true }}));
            inp.dispatchEvent(new Event('change', {{ bubbles: true }}));
        }}
    }}''', price)
    
    # Status: Unlisted
    await page.evaluate('''() => {
        let inp = [...document.querySelectorAll('input')].find(i => i.placeholder === '请选择商品状态');
        if (inp) inp.click();
    }''')
    await asyncio.sleep(2)
    await page.evaluate('''() => {
        let items = [...document.querySelectorAll('.el-select-dropdown__item')];
        let target = items.find(el => el.innerText.includes('下架') && el.offsetParent !== null);
        if (target) target.click();
    }''')
    
    # TinyMCE: TOTAL OVERWRITE
    brand_link = f'<a href="https://www.stockxshoesvip.net/we11done/">STOCKXSHOESVIP</a>'
    print("Formatting description...")
    await page.evaluate(f"""
        (function() {{
            var editor = tinymce.activeEditor;
            if (editor) {{
                editor.setContent('<p>{brand_link}</p><p>{clean_title}</p>');
            }}
        }})()
    """)
    
    # Image Management
    print("Uploading gallery images...")
    try:
        delete_btns = page.locator(".el-upload-list__item-delete")
        for _ in range(await delete_btns.count()):
            await delete_btns.nth(0).click()
            await asyncio.sleep(0.3)
            
        await page.evaluate('''() => {
            let section = [...document.querySelectorAll('.el-form-item__label')].find(l => l.innerText.includes('商品图片'));
            if (section) {
                let input = section.parentElement.querySelector('input[type="file"]');
                if (input) {
                    input.multiple = true;
                    input.style.display = 'block';
                    input.style.opacity = '1';
                    input.id = 'recon_upload';
                }
            }
        }''')
        
        file_input = page.locator("#recon_upload").first
        if await file_input.count() > 0:
            await file_input.set_input_files(local_images)
            print(f"Uploaded {len(local_images)} images.")
        else:
            await page.locator(".el-upload__input").first.set_input_files(local_images)
            
        await asyncio.sleep(12) 
    except Exception as e: print(f"Upload error: {e}")
    
    # Save & Verify
    print("Saving...")
    await page.locator("button.el-button--primary:has-text('保存')").first.click()
    try:
        await page.wait_for_url(lambda u: "action=3" in u or "list" in u, timeout=40000)
        print(f"SUCCESS: {album_id}")
        return True
    except:
        print(f"VERIFICATION TIMEOUT: {album_id}")
        return False

async def main():
    async with async_playwright() as p:
        try: browser = await p.chromium.connect_over_cdp("http://localhost:9222")
        except: return
        context = browser.contexts[0]
        page = await context.new_page()
        for i, album in enumerate(ALBUMS):
            print(f"--- Processing {i+1}/7: {album['album_id']} ---")
            try:
                img_urls = await extract_yupoo(page, album['album_id'])
                local_images = await download_images(img_urls)
                if local_images:
                    await erp_sync(page, album, local_images)
                else: print(f"Skip {album['album_id']} (no images)")
                await asyncio.sleep(2)
            except Exception as e: print(f"Error {album['album_id']}: {e}")
        await page.close()

if __name__ == "__main__":
    asyncio.run(main())
