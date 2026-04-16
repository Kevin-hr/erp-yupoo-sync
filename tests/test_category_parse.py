# -*- coding: utf-8 -*-
import requests
import re

# 尝试找 API
urls = [
    'https://x.yupoo.com/categories/5147772',
    'https://lol2024.x.yupoo.com/categories/5147772',
    'https://yupoo.com/categories/5147772',
]

for url in urls:
    r = requests.get(url, timeout=10, headers={
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
        'X-Requested-With': 'XMLHttpRequest',
    })
    html = r.text
    # 查找 API URL
    api_urls = re.findall(r'["\']([^"\']*(?:albums?|categories?)[^"\']*api[^"\']*)["\']', html)
    if api_urls:
        print(f'\nURL: {url}')
        print(f'API URLs: {api_urls[:5]}')

    # 查找所有 JS 文件引用
    js_files = re.findall(r'src=["\']([^"\']*\.js[^"\']*)["\']', html)
    if js_files:
        print(f'JS files: {js_files[:5]}')

    # 查找内联脚本中的 API 配置
    inline_scripts = re.findall(r'<script[^>]*>(.*?)</script>', html, re.DOTALL)
    for script in inline_scripts:
        if 'api' in script.lower() or 'album' in script.lower():
            print(f'\nInline script from {url}:')
            print(script[:500])
