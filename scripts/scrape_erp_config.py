#!/usr/bin/env python3
import time
import json
import os
from playwright.sync_api import sync_playwright

def scrape_config():
    base_url = "https://www.mrshopplus.com"
    cookies_path = "logs/cookies.json"
    
    with sync_playwright() as p:
        print("Launching browser...")
        browser = p.chromium.launch(headless=True)
        # 尝试加载现有 Cookie 以绕过登录
        if os.path.exists(cookies_path):
            with open(cookies_path, "r", encoding="utf-8") as f:
                cookies = json.load(f)
            context = browser.new_context(viewport={'width': 1920, 'height': 1080})
            context.add_cookies(cookies)
            print("Loaded cookies from logs/cookies.json")
        else:
            context = browser.new_context(viewport={'width': 1920, 'height': 1080})

        page = context.new_page()
        
        # 验证是否已登录，直接去商品列表
        target_url = f"{base_url}/#/product/list_DTB_proProduct"
        print(f"Navigating to: {target_url}")
        page.goto(target_url, wait_until="networkidle")
        page.wait_for_timeout(5000)
        page.screenshot(path="screenshots/erp_check_login.png")
        
        # 如果还在登录页，则手动登录（兜底）
        if "login" in page.url:
            print("Cookies expired or invalid. Attempting manual login...")
            # 注意：之前的 404 是因为去了 /admin/login。这次直接去 base_url 找登录框
            page.goto(base_url, wait_until="networkidle")
            # ... 登录逻辑同上，但使用更宽松的选择器
            try:
                page.fill('input[type="text"]', "zhiqiang")
                page.fill('input[type="password"]', "123qazwsx")
                page.click('button:has-text("登录")')
                page.wait_for_timeout(5000)
            except:
                pass

        # 获取类目 - 尝试真实路径
        categories = []
        try:
            cat_url = f"{base_url}/#/product/category"
            print(f"Navigating to Category: {cat_url}")
            page.goto(cat_url, wait_until="networkidle")
            page.wait_for_timeout(5000)
            page.screenshot(path="screenshots/erp_categories_v2.png")
            
            # 提取类目名称
            cat_els = page.query_selector_all('.category-name, .el-table__row .cell')
            categories = list(set([el.inner_text().strip() for el in cat_els if el.inner_text().strip()]))
            # 过滤掉表头
            headers = ["操作", "排序", "类目名称", "图标", "是否显示", "新增时间"]
            categories = [c for c in categories if c not in headers]
        except Exception as e:
            print(f"Category extraction failed: {e}")

        # 获取物流
        logistics = []
        try:
            log_url = f"{base_url}/#/setting/logistics"
            print(f"Navigating to Logistics: {log_url}")
            page.goto(log_url, wait_until="networkidle")
            page.wait_for_timeout(5000)
            page.screenshot(path="screenshots/erp_logistics_v2.png")
            
            log_els = page.query_selector_all('.template-name, .el-table__row .cell')
            logistics = list(set([el.inner_text().strip() for el in log_els if el.inner_text().strip()]))
            log_headers = ["操作", "模板名称", "计费方式", "状态", "最后修改时间"]
            logistics = [l for l in logistics if l not in log_headers]
        except Exception as e:
            print(f"Logistics extraction failed: {e}")
            
        # 最终数据
        result = {
            "categories": categories,
            "logistics": logistics,
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
        }
        
        with open("erp_config_actual.json", "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        
        print(f"Scrapped {len(categories)} categories and {len(logistics)} logistics templates.")
        browser.close()

if __name__ == "__main__":
    if not os.path.exists("screenshots"):
        os.makedirs("screenshots")
    scrape_config()
