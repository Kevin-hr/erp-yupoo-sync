#!/usr/bin/env python3
"""Extract album links from Yupoo category page using Playwright CDP"""

import asyncio
import json
from playwright.async_api import async_playwright


async def main():
    async with async_playwright() as p:
        browser = await p.chromium.connect_over_cdp("http://localhost:9222")
        context = await browser.new_context(viewport={"width": 1280, "height": 900})
        page = await context.new_page()

        try:
            print("Navigating to category page...")
            await page.goto(
                "https://lol2024.x.yupoo.com/categories/5185090",
                timeout=30000,
                wait_until="domcontentloaded",
            )

            # Short wait for initial render
            await asyncio.sleep(3)

            # Try scrolling to trigger lazy loading
            await page.evaluate("window.scrollBy(0, 500)")
            await asyncio.sleep(1)
            await page.evaluate("window.scrollBy(0, 500)")
            await asyncio.sleep(1)

            print("Extracting album links...")
            album_links = await page.evaluate("""
                () => {
                    const links = [];
                    document.querySelectorAll('a[href*="/gallery/"]').forEach(a => {
                        const match = a.href.match(/\\/gallery\\/(\\d+)/);
                        if (match && match[1].length > 5) {
                            links.push({
                                album_id: match[1],
                                href: a.href
                            });
                        }
                    });
                    return links;
                }
            """)

            # Deduplicate
            seen = set()
            unique_albums = []
            for album in album_links:
                if album["album_id"] not in seen:
                    seen.add(album["album_id"])
                    unique_albums.append(album)

            print(f"Found {len(unique_albums)} unique albums:")
            for album in unique_albums:
                print(f"  {album['album_id']}")

            if unique_albums:
                with open("category_5185090_albums.json", "w", encoding="utf-8") as f:
                    json.dump(unique_albums, f, indent=2, ensure_ascii=False)
                print(f"Saved to category_5185090_albums.json")

        except Exception as e:
            print(f"Error: {e}")
            import traceback

            traceback.print_exc()
        finally:
            await page.close()
            await context.close()


if __name__ == "__main__":
    asyncio.run(main())
