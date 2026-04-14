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

        # Get all rows and print full details
        rows = await page.query_selector_all(".el-table__row")
        print(f"=== Total rows: {len(rows)} ===")

        for i, row in enumerate(rows[:3]):
            print(f"\\n=== Row {i} ===")
            cells = await row.query_selector_all("td")
            for j, cell in enumerate(cells):
                text = await cell.inner_text()
                print(f"  Cell {j}: {text[:100]}")

            # Try to click on row to open detail
            try:
                # Find the clickable element (usually first cell with product link)
                first_cell = cells[1] if len(cells) > 1 else cells[0]
                await first_cell.click()
                await asyncio.sleep(3)
                print(f"After click URL: {page.url}")
            except Exception as e:
                print(f"Click error: {e}")


asyncio.run(main())
