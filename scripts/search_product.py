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

        # Navigate to product list
        await page.goto("https://www.mrshopplus.com/#/product/list_DTB_proProduct")
        await page.wait_for_load_state("networkidle", timeout=30000)
        await asyncio.sleep(8)

        # Try search with JS
        search_input = await page.query_selector('input[placeholder*="请输入"]')
        if search_input:
            await search_input.click()
            await asyncio.sleep(1)

        # Use JS to trigger search
        await page.evaluate("""() => {
            const inputs = document.querySelectorAll('input');
            for (const inp of inputs) {
                if (inp.placeholder && inp.placeholder.includes('请输入')) {
                    inp.value = 'Descente';
                    inp.dispatchEvent(new Event('input', {bubbles: true}));
                    inp.dispatchEvent(new KeyboardEvent('keydown', {key: 'Enter', bubbles: true}));
                    break;
                }
            }
        }""")
        await asyncio.sleep(5)

        # Get all product data
        rows = await page.query_selector_all(".el-table__row")
        print(f"Found {len(rows)} rows")

        for i, row in enumerate(rows):
            # Get all cell text
            cells = await row.query_selector_all("td")
            cell_texts = []
            for cell in cells:
                text = await cell.inner_text()
                cell_texts.append(text.strip()[:50])
            print(f"Row {i}: {cell_texts}")


asyncio.run(main())
