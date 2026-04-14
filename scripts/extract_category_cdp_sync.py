"""同步版本 - 直接连接到已有Chrome CDP, 无asyncio"""

import re
from playwright.sync_api import sync_playwright

CDP_URL = "http://localhost:9222"


def main():
    url = "https://lol2024.x.yupoo.com/categories/5185090"

    with sync_playwright() as p:
        print("Connecting to Chrome CDP...")
        browser = p.chromium.connect_over_cdp(CDP_URL)
        print(f"Connected! Browser: {browser}")

        context = browser.contexts[0] if browser.contexts else browser.new_context()
        page = context.new_page()

        print(f"Navigating to {url} ...")
        page.goto(url, wait_until="domcontentloaded", timeout=15000)
        print(f"Loaded! URL: {page.url}")

        # 等待一点让JS渲染
        page.wait_for_timeout(3000)

        # 截图看看
        page.screenshot(path="tmp_category.png")
        print("截图保存到 tmp_category.png")

        # 提取相册链接
        album_links = page.query_selector_all("a[href*='/gallery/']")
        print(f"\n找到 {len(album_links)} 个相册链接")

        album_ids = []
        for link in album_links:
            href = link.get_attribute("href")
            if href:
                m = re.search(r"/gallery/(\d+)", href)
                if m:
                    album_ids.append(m.group(1))

        unique = list(dict.fromkeys(album_ids))
        print(f"\n去重后 {len(unique)} 个相册ID:")
        for aid in unique:
            print(f"  https://x.yupoo.com/gallery/{aid}")

        # 也尝试从innerHTML提取
        html = page.content()
        gallery_ids = re.findall(r"/gallery/(\d{8,})", html)
        unique_gallery = list(dict.fromkeys(gallery_ids))
        print(f"\n从HTML提取到 {len(unique_gallery)} 个gallery ID:")
        for gid in unique_gallery[:20]:
            print(f"  {gid}")

        browser.close()
        print("\n完成!")


if __name__ == "__main__":
    main()
