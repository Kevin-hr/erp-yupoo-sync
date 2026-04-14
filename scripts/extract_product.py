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

        # Check pagination info
        pagination = await page.query_selector(".el-pagination")
        if pagination:
            pagination_text = await pagination.inner_text()
            print(f"Pagination: {pagination_text[:200]}")

        # Look for total count
        total = await page.query_selector(".el-pagination__total")
        if total:
            print(f"Total: {await total.inner_text()}")

        # Get first product names
        rows = await page.query_selector_all(".el-table__row")
        print(f"Total rows: {len(rows)}")

        for i, row in enumerate(rows[:20]):
            cells = await row.query_selector_all("td")
            if len(cells) > 1:
                product_name = await cells[1].inner_text()
                print(f"{i + 1}. {product_name[:80]}")


asyncio.run(main())
