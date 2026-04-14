#!/usr/bin/env python3
import json
import re
import pandas as pd
import os
from playwright.sync_api import sync_playwright

# === 配置与常量 ===
# 品牌 Slug 映射
BRAND_SLUGS = {
    'BAPE': 'bape-shoes',
    'ADIDAS': 'adidas-shoes',
    'NIKE': 'nike-shoes',
    'JORDAN': 'jordan-shoes',
    'YEEZY': 'yeezy-shoes',
}
DEFAULT_BRAND_SLUG = 'all-shoes'
ERP_TEMPLATE_CSV = '_template_商品信息.csv'

def get_brand_info(title):
    """根据标题检测品牌并返回 Slug"""
    title_upper = title.upper()
    for brand, slug in BRAND_SLUGS.items():
        if brand in title_upper:
            return brand, slug
    return 'Generic', DEFAULT_BRAND_SLUG

def clean_description(html_content, brand, slug):
    """清理描述：去除 img 标签并注入 SEO 链接"""
    if not html_content:
        html_content = ""
    # 去除所有的 img 标签
    cleaned = re.sub(r'<img[^>]*>', '', html_content)
    # 注入 SEO 链接
    seo_link = f'<p><a href="https://www.stockxshoesvip.com/collections/{slug}" target="_blank">Check more {brand} items</a></p>\n'
    return seo_link + cleaned

def extract_album(album_url):
    """使用 Playwright 拦截 API 并提取数据"""
    data = {"title": "", "images": [], "description": ""}
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context()
        page = context.new_page()
        
        # 拦截照片列表 API
        def handle_response(response):
            if "/api/albums/" in response.url and "/photos" in response.url:
                if response.status == 200:
                    try:
                        res_json = response.json()
                        photos = res_json.get('data', {}).get('list', [])
                        for p_item in photos:
                            path = p_item.get('path')
                            if path:
                                data['images'].append(f"http://pic.yupoo.com{path}")
                    except Exception as e:
                        print(f"Error parsing API response: {e}")

        page.on("response", handle_response)
        
        print(f"Navigating to {album_url}...")
        page.goto(album_url, wait_until="networkidle")
        
        # 获取标题
        try:
            data['title'] = page.inner_text('.showalbum__title')
        except:
            data['title'] = "Unknown Album"
            
        # 获取描述
        try:
            data['description'] = page.inner_html('.showalbum__desc')
        except:
            data['description'] = ""
            
        browser.close()
    
    return data

def generate_erp_csv(album_data, output_file="upload_queue.csv"):
    """将提取的数据转换为 ERP CSV 格式"""
    # 读取模板以获取列结构
    df_template = pd.read_csv(ERP_TEMPLATE_CSV, encoding='utf-8')
    headers = df_template.columns.tolist()
    
    brand, slug = get_brand_info(album_data['title'])
    
    # 转换规则
    main_img = album_data['images'][0] if album_data['images'] else ""
    other_imgs = "\n".join(album_data['images'][1:14]) # 最多保留 14 张主图，这里取 1-13 (13张) + 1张图 = 14张
    
    row = {
        '商品标题*': album_data['title'],
        '商品描述': clean_description(album_data['description'], brand, slug),
        '商品首图*': main_img,
        '商品其他图片': other_imgs,
        '商品上架*': 'N',            # 红线：强制下架
        '物流模板*': '默认模板',
        '计量单位': '双' if 'SHOES' in album_data['title'].upper() else '件/个',
        '商品重量*': 0.5,
        '售价*': 99.00,
        '不记库存*': 'Y'
    }
    
    # 填充默认值
    full_row = {h: row.get(h, "") for h in headers}
    
    # 创建新的 DataFrame
    df_out = pd.DataFrame([full_row])
    df_out.to_csv(output_file, index=False, encoding='utf-8-sig')
    print(f"Generated {output_file} successfully.")

if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("Usage: python extract_to_csv_v3.py <yupoo_album_url>")
        sys.exit(1)
    
    url = sys.argv[1]
    album_info = extract_album(url)
    if album_info['images']:
        generate_erp_csv(album_info)
    else:
        print("No images found in album. Extraction failed.")
