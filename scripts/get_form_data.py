import asyncio
import json
from playwright.async_api import async_playwright


async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context()

        with open("logs/cookies.json", "r") as f:
            cookies = json.load(f)
        await context.add_cookies(cookies)

        page = await context.new_page()

        # Navigate to product edit page
        await page.goto(
            "https://www.mrshopplus.com/#/product/form_DTB_proProduct/0?action=3&pkValues=%5B526982433392410%5D"
        )
        await page.wait_for_load_state("networkidle", timeout=30000)
        await asyncio.sleep(8)

        # Extract using JavaScript
        form_data = await page.evaluate("""() => {
            const data = {};
            
            // Get inputs
            const inputs = document.querySelectorAll('input');
            inputs.forEach((inp, i) => {
                const name = inp.name || inp.id || `input_${i}`;
                const type = inp.type;
                if (type === 'text' || type === 'number') {
                    data[name] = inp.value;
                }
            });
            
            // Get textareas
            const textareas = document.querySelectorAll('textarea');
            textareas.forEach((ta, i) => {
                const name = ta.name || ta.id || `textarea_${i}`;
                data[name] = ta.value || ta.innerText;
            });
            
            // Get TinyMCE content (product description)
            const mce_iframes = document.querySelectorAll('iframe[id^="vue-tinymce"]');
            mce_iframes.forEach((iframe, i) => {
                try {
                    const doc = iframe.contentDocument || iframe.contentWindow.document;
                    data[`mce_content_${i}`] = doc.body.innerText;
                } catch(e) {
                    data[`mce_content_${i}`] = 'CORS error';
                }
            });
            
            return data;
        }""")

        print("=== Form Data ===")
        for key, val in form_data.items():
            if val:
                print(f"{key}: {str(val)[:80]}")

        # Also get the displayed labels
        labels = await page.evaluate("""() => {
            const labels = document.querySelectorAll('.el-form-item__label');
            const result = [];
            labels.forEach(lab => {
                result.push(lab.innerText);
            });
            return result;
        }""")
        print(f"\\n=== Labels ({len(labels)}) ===")
        for lab in labels[:20]:
            print(f"  {lab}")


asyncio.run(main())
