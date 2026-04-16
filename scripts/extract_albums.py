#!/usr/bin/env python3
import requests
import re

url = "https://lol2024.x.yupoo.com/categories/5185090"
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}

r = requests.get(url, headers=headers, timeout=30)
print(f"Status: {r.status_code}")
print(f"Content length: {len(r.text)}")

# Look for various patterns
patterns = [
    (r"/albums/(\d+)", "albums"),
    (r"/gallery/(\d+)", "gallery"),
    (r'"id"\s*:\s*"(\d{6,})"', "json id"),
    (r'"album_id"\s*:\s*"(\d+)"', "album_id"),
]

for pattern, name in patterns:
    matches = re.findall(pattern, r.text)
    if matches:
        unique = list(dict.fromkeys(matches))
        print(f"{name}: {len(unique)} matches -> {unique[:10]}")

# Also check for links
links = re.findall(r'href="([^"]*5185090[^"]*)"', r.text)
if links:
    print(f"Internal links to 5185090: {links[:10]}")
