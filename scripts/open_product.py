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

        # Look for first product row and double-click to edit
        rows = await page.query_selector_all(".el-table__row")
        if rows:
            # Get row data before click
            first_row = rows[0]
            cells = await first_row.query_selector_all("td")
            product_id = await cells[-1].inner_text() if len(cells) > 0 else "N/A"
            print(f"First product ID from row: {product_id}")

            # Try to get product ID from the checkbox value or row attribute
            row_html = await first_row.inner_html()
            print(f"Row HTML snippet: {row_html[:500]}")

            # Try clicking on product name (usually in cell index 1 or 2)
            for attempt in range(5):
                try:
                    # Find link/span in the row that might be clickable
                    clickables = await first_row.query_selector_all(
                        'a, .cell a, span[class*="name"], div[class*="product"]'
                    )
                    if clickables:
                        for cl in clickables:
                            txt = await cl.inner_text()
                            if txt and len(txt.strip()) > 3:
                                print(f"Clickable: {txt[:50]}")
                                await cl.click()
                                await asyncio.sleep(5)
                                print(f"URL after click: {page.url}")
                                break
                    break
                except Exception as e:
                    print(f"Click attempt {attempt + 1} failed: {e}")
                    await asyncio.sleep(1)


asyncio.run(main())
