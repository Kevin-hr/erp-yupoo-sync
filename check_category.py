import requests
import re
import sys

url = "https://lol2024.x.yupoo.com/categories/5185090"
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept": "text/html,application/xhtml+xml",
    "Accept-Language": "zh-CN,zh;q=0.9",
}
r = requests.get(url, headers=headers, timeout=15)
html = r.text

print(f"Status: {r.status_code}, Length: {len(html)}")

# 查找相册ID模式
patterns = [
    r"/gallery/(\d+)",
    r"/albums/(\d+)",
    r'"id":\s*(\d{6,})',
    r'"albumId":\s*(\d+)',
]

for pat in patterns:
    matches = re.findall(pat, html)
    if matches:
        unique = list(dict.fromkeys(matches))
        print(f"Pattern {pat!r}: {len(unique)} matches -> {unique[:10]}")

# 尝试找JSON数据块
json_blocks = re.findall(r"window\.__INITIAL_STATE__\s*=\s*(\{.*?\});", html, re.DOTALL)
if json_blocks:
    print(f"Found {len(json_blocks)} JSON blocks")
    for i, block in enumerate(json_blocks[:1]):
        print(f"Block {i} length: {len(block)}")
        print(block[:500])
