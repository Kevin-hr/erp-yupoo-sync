"""极简Yupoo分类页相册ID提取 - 使用已有Chrome CDP"""

import asyncio
import re
from playwright.async_api import async_playwright


async def main():
    url = "https://lol2024.x.yupoo.com/categories/5185090"

    async with async_playwright() as p:
        # 连接到已有Chrome CDP
        browser = await p.chromium.connect_over_cdp("http://localhost:9222")
        context = await browser.new_context(
            viewport={"width": 1280, "height": 900},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        )
        page = await context.new_page()

        print(f"Navigating to {url}...")
        await page.goto(url, wait_until="domcontentloaded", timeout=30000)

        # 等待JS渲染
        await asyncio.sleep(5)

        # 提取所有相册链接
        # Yupoo相册链接格式: https://x.yupoo.com/gallery/{id} 或 https://lol2024.x.yupoo.com/gallery/{id}
        album_links = await page.query_selector_all("a[href*='/gallery/']")
        album_ids = []
        for link in album_links:
            href = await link.get_attribute("href")
            if href:
                match = re.search(r"/gallery/(\d+)", href)
                if match:
                    album_ids.append(match.group(1))

        # 去重
        unique_albums = list(dict.fromkeys(album_ids))
        print(f"\n找到 {len(unique_albums)} 个相册:")
        for aid in unique_albums:
            print(f"  - {aid}")

        # 也尝试从页面文本提取
        text = await page.inner_text("body")
        all_ids = re.findall(r"(\d{8,})", text)
        numeric_ids = [i for i in all_ids if len(i) >= 8]
        unique_numeric = list(dict.fromkeys(numeric_ids))
        print(f"\n从页面文本提取到 {len(unique_numeric)} 个数字ID (>=8位):")
        for nid in unique_numeric[:20]:
            print(f"  - {nid}")

        await browser.close()


if __name__ == "__main__":
    asyncio.run(main())
