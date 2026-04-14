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

        # Navigate directly to product edit page
        # Using the URL we discovered: action=3 means edit mode
        await page.goto(
            "https://www.mrshopplus.com/#/product/form_DTB_proProduct/0?action=3&pkValues=%5B526982433392410%5D"
        )
        await page.wait_for_load_state("networkidle", timeout=30000)
        await asyncio.sleep(8)

        print(f"URL: {page.url}")
        print(f"Title: {await page.title()}")

        # Take screenshot
        await page.screenshot(path="logs/product_form.png", full_page=True)
        print("Screenshot saved to logs/product_form.png")

        # Extract form data
        product_data = {}

        # Get all input fields
        inputs = await page.query_selector_all("input")
        print(f"\\n=== Found {len(inputs)} inputs ===")
        for inp in inputs:
            inp_type = await inp.get_attribute("type")
            inp_name = await inp.get_attribute("name")
            inp_id = await inp.get_attribute("id")
            inp_placeholder = await inp.get_attribute("placeholder")
            inp_value = await inp.get_attribute("value")
            if inp_type not in ["checkbox", "radio", "hidden", "file"]:
                print(
                    f"  {inp_id or inp_name}: {inp_placeholder or inp_type}: {str(inp_value)[:50] if inp_value else ''}"
                )

        # Get all textareas
        textareas = await page.query_selector_all("textarea")
        print(f"\\n=== Found {len(textareas)} textareas ===")
        for ta in textareas:
            ta_id = await ta.get_attribute("id")
            ta_name = await ta.get_attribute("name")
            ta_placeholder = await ta.get_attribute("placeholder")
            ta_content = await ta.inner_text()
            print(f"  {ta_id or ta_name}: {ta_placeholder}: {str(ta_content)[:100]}")

        # Get all select dropdowns
        selects = await page.query_selector_all("select")
        print(f"\\n=== Found {len(selects)} selects ===")
        for sel in selects:
            sel_id = await sel.get_attribute("id")
            sel_name = await sel.get_attribute("name")
            sel_value = await sel.get_attribute("value")
            print(f"  {sel_id or sel_name}: value={sel_value}")


asyncio.run(main())
