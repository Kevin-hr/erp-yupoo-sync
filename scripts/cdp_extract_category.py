"""直接连接到已有Yupoo分类页CDP page, 无需跳转"""

import requests
import json

CDP_BASE = "http://localhost:9222"
PAGE_ID = "6789C20AB90AD80E80AF7ADE544AFD3E"  # 分类页5185090


def cdp_cmd(method, params=None):
    """发送CDP命令"""
    resp = requests.post(
        f"{CDP_BASE}/json/send/{PAGE_ID}",
        json={"id": 1, "method": method, "params": params or {}},
        headers={"Content-Type": "application/json"},
        timeout=10,
    )
    return resp.json()


def main():
    print("=== CDP连接到Yupoo分类页 ===")
    print(f"Page ID: {PAGE_ID}")
    print(f"URL: https://lol2024.x.yupoo.com/categories/5185090")

    # 1. 先获取页面当前信息
    print("\n[1] 获取页面信息...")
    result = cdp_cmd(
        "Runtime.evaluate",
        {
            "expression": """
        ({
            url: window.location.href,
            title: document.title,
            bodyText: document.body.innerText.slice(0, 500),
            galleryLinks: Array.from(document.querySelectorAll('a[href*="/gallery/"]')).map(a => ({
                href: a.href,
                text: a.innerText.trim()
            })).slice(0, 20)
        })
        """,
            "returnByValue": True,
        },
    )

    print(f"Result: {json.dumps(result, indent=2, ensure_ascii=False)[:2000]}")

    # 2. 尝试找React组件中的数据
    print("\n[2] 查找React状态数据...")
    result2 = cdp_cmd(
        "Runtime.evaluate",
        {
            "expression": """
        (() => {
            // 查找__INITIAL_STATE__或类似全局变量
            if (window.__INITIAL_STATE__) return {source: '__INITIAL_STATE__', keys: Object.keys(window.__INITIAL_STATE__)};
            if (window.__PRELOADED_STATE__) return {source: '__PRELOADED_STATE__', keys: Object.keys(window.__PRELOADED_STATE__)};
            // 查找script标签中的JSON数据
            const scripts = Array.from(document.querySelectorAll('script[type="application/json"]'));
            return {scriptCount: scripts.length, found: scripts.map(s => s.textContent.slice(0, 200))};
        })()
        """,
            "returnByValue": True,
        },
    )
    print(f"React state: {json.dumps(result2, indent=2, ensure_ascii=False)[:2000]}")

    # 3. 获取完整DOM
    print("\n[3] 提取gallery链接...")
    result3 = cdp_cmd(
        "Runtime.evaluate",
        {
            "expression": """
        Array.from(document.querySelectorAll('a[href*="/gallery/"]'))
            .map(a => {
                const href = a.href;
                const text = a.innerText.trim();
                const parts = href.split('/gallery/');
                const id = parts.length > 1 ? parts[1].split('?')[0] : null;
                return {id, href, text};
            })
            .filter(x => x.id && x.id.length >= 8)
            .slice(0, 20)
        """,
            "returnByValue": True,
        },
    )
    print(f"Gallery links: {json.dumps(result3, indent=2, ensure_ascii=False)[:3000]}")


if __name__ == "__main__":
    main()
