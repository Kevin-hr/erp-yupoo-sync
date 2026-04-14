"""使用Playwright启动独立Chrome访问Yupoo分类页"""

import re
from playwright.sync_api import sync_playwright


def main():
    url = "https://lol2024.x.yupoo.com/categories/5185090"

    with sync_playwright() as p:
        print("Launching Chrome...")
        # 启动独立Chrome (不用CDP)
        browser = p.chromium.launch(
            headless=True,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--no-sandbox",
                "--disable-dev-shm-usage",
                "--disable-gpu",
            ],
        )

        context = browser.new_context(
            viewport={"width": 1280, "height": 900},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            extra_http_headers={
                "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            },
        )

        page = context.new_page()

        print(f"Navigating to {url} ...")
        page.goto(url, wait_until="domcontentloaded", timeout=20000)

        # 等待React渲染
        page.wait_for_timeout(5000)

        # 截图
        page.screenshot(path="tmp_cat.png", full_page=True)
        print("截图: tmp_cat.png")

        # 提取gallery链接
        links = page.query_selector_all("a[href*='/gallery/']")
        print(f"\n找到 {len(links)} 个gallery链接")

        album_ids = []
        for link in links:
            href = link.get_attribute("href")
            if href:
                m = re.search(r"/gallery/(\d+)", href)
                if m:
                    album_id = m.group(1)
                    text = link.inner_text().strip()[:40]
                    album_ids.append((album_id, text))

        # 去重
        seen = set()
        unique = []
        for aid, text in album_ids:
            if aid not in seen:
                seen.add(aid)
                unique.append((aid, text))

        print(f"\n去重后 {len(unique)} 个相册:")
        for aid, text in unique:
            print(f"  {aid}: {text}")

        # 也从innerHTML找
        html = page.content()
        html_ids = re.findall(r"/gallery/(\d{8,})", html)
        html_unique = list(dict.fromkeys(html_ids))
        if html_unique:
            print(f"\n从HTML源码提取到 {len(html_unique)} 个ID:")
            for gid in html_unique[:20]:
                print(f"  {gid}")

        browser.close()
        print("\n完成!")


if __name__ == "__main__":
    main()
