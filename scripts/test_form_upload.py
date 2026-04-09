#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
表单复制+图片上传测试 (Form Copy + Image Upload E2E Test)
Task #4: 完整E2E测试

使用CDP连接现有Chrome，注入cookies，执行:
1. 访问商品列表
2. 点击复制按钮
3. 等待TinyMCE初始化
4. 格式化描述（brand + product name）
5. 上传图片（URL方式）
6. 截图留证
7. 保存并等待action=3
"""

import asyncio
import json
import sys
import time
from pathlib import Path
from datetime import datetime

# 设置UTF-8输出
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

ROOT_DIR = Path(__file__).parent.parent
LOG_DIR = ROOT_DIR / "logs"
SCREENSHOT_DIR = ROOT_DIR / "screenshots"
LOG_DIR.mkdir(exist_ok=True)
SCREENSHOT_DIR.mkdir(exist_ok=True)

# 导入Playwright
try:
    from playwright.async_api import async_playwright, Page, BrowserContext
except ImportError:
    print("[ERROR] Playwright未安装，请先运行: pip install playwright && python -m playwright install chromium")
    sys.exit(1)

# ============ 辅助函数 ============

async def safe_click(page: Page, selector: str, timeout: int = 5000, force: bool = False):
    """安全点击"""
    try:
        await page.wait_for_selector(selector, state="visible", timeout=timeout)
        await page.click(selector, timeout=timeout, force=force)
    except Exception as e:
        if "outside" in str(e).lower() or "timeout" in str(e).lower():
            print(f"[WARN] Fallback click for {selector}")
            await page.locator(selector).first.evaluate("el => el.click()")
        else:
            raise e


async def safe_fill(page: Page, selector: str, value: str, timeout: int = 5000):
    """安全填充"""
    await page.wait_for_selector(selector, state="visible", timeout=timeout)
    await page.fill(selector, value, timeout=timeout)


def load_cookies(cookies_file: Path):
    """加载cookies"""
    with open(cookies_file, 'r', encoding='utf-8') as f:
        return json.load(f)


def load_yupoo_extract_result(result_file: Path) -> dict:
    """加载Yupoo提取结果"""
    if result_file.exists():
        with open(result_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {"status": "pending", "urls": []}


# ============ 主测试流程 ============

async def run_form_upload_test():
    """执行表单复制+图片上传E2E测试"""
    print("[TEST] 开始表单复制+图片上传E2E测试...")
    print(f"[TEST] 时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    # 加载cookies
    cookies_file = LOG_DIR / "cookies.json"
    extract_result_file = LOG_DIR / "yupoo_extract_result.json"

    if not cookies_file.exists():
        print(f"[ERROR] cookies文件不存在: {cookies_file}")
        return {"status": "error", "error": f"cookies文件不存在: {cookies_file}"}

    cookies = load_cookies(cookies_file)
    print(f"[COOKIES] 加载了 {len(cookies)} 个cookies")

    # 加载提取结果
    extract_result = load_yupoo_extract_result(extract_result_file)
    print(f"[EXTRACT] 提取结果状态: {extract_result.get('status')}, URL数量: {len(extract_result.get('urls', []))}")

    # 如果没有URLs，使用测试URLs
    if not extract_result.get('urls'):
        print("[WARN] yupoo_extract_result.json为空，使用测试URLs")
        # 使用一些已知存在的测试图片URL（来自之前的成功案例）
        test_urls = [
            "http://pic.yupoo.com/lol2024/f53b0825/3e40c632.jpeg",
            "http://pic.yupoo.com/lol2024/f53b0825/3e40c633.jpeg",
            "http://pic.yupoo.com/lol2024/f53b0825/3e40c634.jpeg",
        ]
        # 只用3个测试URL，避免浪费
        image_urls = test_urls[:3]
    else:
        image_urls = extract_result.get('urls', [])[:14]

    print(f"[URLS] 使用 {len(image_urls)} 个图片URLs进行上传测试")

    # 测试参数
    brand_name = "Generic Brand"
    product_name = "Test Product 230897512"

    result = {
        "status": "unknown",
        "url_final": "",
        "screenshot": "",
        "error": ""
    }

    async with async_playwright() as p:
        # CDP连接
        cdp_url = "http://localhost:9222"
        print(f"[CDP] 连接到 {cdp_url}...")

        try:
            browser = await p.chromium.connect_over_cdp(cdp_url, timeout=15000)
            print(f"[CDP] 连接成功! Browser: {browser}")
        except Exception as e:
            print(f"[ERROR] CDP连接失败: {e}")
            result["status"] = "error"
            result["error"] = f"CDP连接失败: {e}"
            return result

        # 创建新context并注入cookies
        try:
            ctx = await browser.new_context(viewport={'width': 1280, 'height': 900})
            await ctx.add_cookies(cookies)
            print(f"[CONTEXT] 新浏览器上下文创建成功，已注入 {len(cookies)} 个cookies")
        except Exception as e:
            print(f"[ERROR] 创建浏览器上下文失败: {e}")
            result["status"] = "error"
            result["error"] = f"创建浏览器上下文失败: {e}"
            return result

        # 创建新page
        page = await ctx.new_page()
        erp_url = "https://www.mrshopplus.com/#/product/list_DTB_proProduct"

        try:
            # Step 1: 访问商品列表
            print(f"[STEP1] 访问商品列表: {erp_url}")
            await page.goto(erp_url, timeout=30000)
            await page.wait_for_load_state('networkidle', timeout=20000)
            await asyncio.sleep(3)
            print(f"[STEP1] 当前URL: {page.url}")

            # 截图: 商品列表
            list_shot = SCREENSHOT_DIR / "form_upload_test_list.png"
            await page.screenshot(path=str(list_shot))
            print(f"[STEP1] 截图已保存: {list_shot}")

            # Step 2: 等待并点击复制按钮
            print("[STEP2] 等待复制按钮...")
            copy_selectors = [
                ".operate-area .el-icon-document-copy",
                "i[class*='copy']",
                "[class*='copy']"
            ]

            copy_btn_found = False
            for sel in copy_selectors:
                try:
                    await page.wait_for_selector(sel, state="visible", timeout=8000)
                    print(f"[STEP2] 找到复制按钮: {sel}")
                    copy_btn_found = True
                    break
                except:
                    continue

            if not copy_btn_found:
                # 保存页面内容用于调试
                content = await page.content()
                with open(LOG_DIR / "page_content_form_test.html", "w", encoding="utf-8") as f:
                    f.write(content[:30000])
                print(f"[ERROR] 复制按钮未找到，页面内容已保存")
                result["status"] = "error"
                result["error"] = "复制按钮未找到"
                result["screenshot"] = str(list_shot)
                return result

            # 点击复制按钮
            print("[STEP2] 点击复制按钮...")
            await safe_click(page, ".operate-area .el-icon-document-copy", force=True)
            await page.wait_for_load_state('networkidle', timeout=20000)

            # 等待Vue路由+ TinyMCE初始化
            print("[STEP2] 等待TinyMCE初始化 (5秒)...")
            await asyncio.sleep(5)
            print(f"[STEP2] 点击后URL: {page.url}")

            # 截图: 复制后的表单页
            form_shot_before = SCREENSHOT_DIR / "form_upload_test_before_upload.png"
            await page.screenshot(path=str(form_shot_before))
            print(f"[STEP2] 表单页截图: {form_shot_before}")

            # Step 3: 等待TinyMCE iframe
            print("[STEP3] 等待TinyMCE iframe...")
            try:
                await page.wait_for_selector("iframe[id^='vue-tinymce']", timeout=10000)
                await asyncio.sleep(2)
                print("[STEP3] TinyMCE iframe已就绪")
            except Exception as e:
                print(f"[WARN] TinyMCE iframe未找到: {e}")

            # Step 4: 格式化描述（设置brand + product name首行）
            print(f"[STEP4] 格式化描述: brand={brand_name}, product={product_name}")

            # 填充商品名称
            name_selectors = [
                "input[placeholder='请输入商品名称']",
                "input[placeholder*='商品名称']",
            ]
            for sel in name_selectors:
                try:
                    await page.wait_for_selector(sel, state="visible", timeout=3000)
                    await safe_fill(page, sel, f"{brand_name} {product_name}")
                    print(f"[STEP4] 商品名称已填充: {sel}")
                    break
                except:
                    continue

            # TinyMCE格式化描述
            brand_slug = brand_name.replace(" ", "-")
            link_url = f"https://www.stockxshoesvip.net/{brand_slug}/"
            first_line_html = f"Name: <a href='{link_url}' target='_blank'>{brand_name}</a> {product_name}"

            tiny_js = """
            (firstLineHtml) => {
                let editor = null;
                editor = document.querySelector('#tinymce');
                if (!editor) editor = document.querySelector('.mce-content-body');
                if (!editor) editor = document.body;

                if (!editor) return false;

                // 移除所有图片
                let imgs = editor.querySelectorAll('img');
                imgs.forEach(img => img.remove());

                // 查找Name:段落并替换
                let blocks = editor.querySelectorAll('p, div, span');
                for (let block of blocks) {
                    const text = block.innerText || '';
                    if (/^\\s*Name\\s*:/i.test(text)) {
                        block.innerHTML = firstLineHtml;
                        editor.dispatchEvent(new Event('input', { bubbles: true }));
                        editor.dispatchEvent(new Event('blur', { bubbles: true }));
                        return true;
                    }
                }

                // 如果没找到，插入到开头
                const firstBlock = editor.querySelector('p, div');
                if (firstBlock) {
                    const wrapper = document.createElement('div');
                    wrapper.innerHTML = firstLineHtml + '<br><br>';
                    editor.insertBefore(wrapper, firstBlock);
                    editor.dispatchEvent(new Event('input', { bubbles: true }));
                    return 'prepended';
                }
                return false;
            }
            """

            # 尝试通过iframe执行
            mce_frame = None
            for frame in page.frames:
                try:
                    has_tinymce = await frame.evaluate("""() => {
                        return !!(document.querySelector('#tinymce') || document.querySelector('.mce-content-body'));
                    }""")
                    if has_tinymce:
                        mce_frame = frame
                        print(f"[STEP4] 找到TinyMCE frame: {frame.name}")
                        break
                except:
                    continue

            if mce_frame:
                result_js = await mce_frame.evaluate(tiny_js, first_line_html)
                print(f"[STEP4] TinyMCE格式化结果: {result_js}")
            else:
                result_js = await page.evaluate(tiny_js, first_line_html)
                print(f"[STEP4] TinyMCE格式化结果(page context): {result_js}")

            # Step 5: 上传图片
            print(f"[STEP5] 开始上传图片 ({len(image_urls)} 张)...")

            # 5a: 打开上传弹窗
            print("[STEP5a] 打开上传弹窗...")
            upload_btn_selectors = [
                ".upload-container.editor-upload-btn",
                ".avatar-upload-wrap",
                "[class*='upload']"
            ]

            upload_btn_found = False
            for sel in upload_btn_selectors:
                try:
                    await page.wait_for_selector(sel, state="visible", timeout=5000)
                    await page.locator(sel).first.evaluate("el => el.click()")
                    upload_btn_found = True
                    print(f"[STEP5a] 上传按钮已点击: {sel}")
                    break
                except Exception as e:
                    print(f"[STEP5a] 上传按钮 {sel} 失败: {e}")
                    continue

            if not upload_btn_found:
                # JS fallback
                await page.evaluate("""() => {
                    const btns = document.querySelectorAll('[class*="upload"]');
                    for (const b of btns) {
                        if (b.offsetParent !== null) { b.click(); break; }
                    }
                }""")
                upload_btn_found = True

            await asyncio.sleep(2)

            # 截图: 上传弹窗
            dialog_shot = SCREENSHOT_DIR / "form_upload_test_dialog.png"
            await page.screenshot(path=str(dialog_shot))
            print(f"[STEP5a] 上传弹窗截图: {dialog_shot}")

            # 5b: 切换到URL标签
            print("[STEP5b] 切换到URL标签...")
            tab_selectors = [
                ".el-tabs__item:has-text('URL')",
                ".el-tabs__item:nth-child(2)",
            ]

            tab_switched = False
            for sel in tab_selectors:
                try:
                    await page.wait_for_selector(sel, state="visible", timeout=5000)
                    await page.locator(sel).first.evaluate("el => el.click()")
                    tab_switched = True
                    print(f"[STEP5b] URL标签已切换: {sel}")
                    break
                except:
                    continue

            if not tab_switched:
                await page.evaluate("""() => {
                    const tabs = document.querySelectorAll('.el-tabs__item');
                    for (const t of tabs) { if (t.innerText.includes('URL')) { t.click(); break; } }
                }""")
                tab_switched = True

            await asyncio.sleep(1)

            # 5c: 填写URLs
            print("[STEP5c] 填写图片URLs...")
            textarea_selectors = [
                ".el-dialog .el-textarea__inner",
                ".el-textarea__inner",
            ]

            url_text = "\n".join(image_urls)
            textarea_filled = False

            for sel in textarea_selectors:
                try:
                    el = await page.query_selector(sel)
                    if el and await el.is_visible():
                        await el.fill(url_text)
                        textarea_filled = True
                        print(f"[STEP5c] textarea已填充: {sel}, {len(image_urls)} URLs")
                        break
                except Exception as e:
                    print(f"[STEP5c] textarea {sel} 失败: {e}")
                    continue

            if not textarea_filled:
                # JS fallback
                await page.evaluate(f"""
                    (urls) => {{
                        const textareas = document.querySelectorAll('.el-textarea__inner');
                        for (const ta of textareas) {{
                            if (ta.offsetParent !== null) {{
                                ta.value = urls.join('\\n');
                                ta.dispatchEvent(new Event('input', {{ bubbles: true }}));
                                ta.dispatchEvent(new Event('change', {{ bubbles: true }}));
                                break;
                            }}
                        }}
                    }}
                """, image_urls)
                textarea_filled = True

            await asyncio.sleep(0.5)

            # 5d: 点击确认按钮
            print("[STEP5d] 点击确认按钮...")
            btn_selectors = [
                ".el-dialog__footer button.el-button--primary",
                "button:has-text('确认')",
                "button:has-text('确定')",
            ]

            btn_clicked = False
            for sel in btn_selectors:
                try:
                    btns = await page.query_selector_all(sel)
                    for btn in btns:
                        if await btn.is_visible():
                            await btn.click(timeout=3000)
                            btn_clicked = True
                            print(f"[STEP5d] 确认按钮已点击: {sel}")
                            break
                    if btn_clicked:
                        break
                except:
                    continue

            if not btn_clicked:
                await page.evaluate("""() => {
                    const btns = document.querySelectorAll('.el-dialog__footer button');
                    for (const b of btns) {
                        if (!b.classList.contains('is-text') && !b.classList.contains('is-plain')) {
                            b.click(); break;
                        }
                    }
                }""")
                btn_clicked = True

            await asyncio.sleep(5)
            print("[STEP5] 图片上传序列完成")

            # Step 6: 截图留证
            print("[STEP6] 截图留证...")
            shot_path = SCREENSHOT_DIR / "form_upload_test.png"
            await page.screenshot(path=str(shot_path))
            result["screenshot"] = str(shot_path)
            print(f"[STEP6] 截图已保存: {shot_path}")

            # Step 7: 保存并等待action=3
            print("[STEP7] 点击保存按钮...")
            save_selectors = [
                "button:has-text('保存')",
                "button:has-text('保存商品')",
            ]

            for sel in save_selectors:
                try:
                    await page.wait_for_selector(sel, state="visible", timeout=5000)
                    await page.locator(sel).first.evaluate("el => el.click()")
                    print(f"[STEP7] 保存按钮已点击: {sel}")
                    break
                except:
                    continue

            # 等待action=3
            print("[STEP7] 等待action=3...")
            try:
                await page.wait_for_url(lambda url: "action=3" in url, timeout=15000)
                print(f"[STEP7] 保存成功! URL: {page.url}")
                result["status"] = "success"
                result["url_final"] = page.url
            except Exception as e:
                print(f"[STEP7] 保存验证超时: {e}")
                result["status"] = "action3_timeout"
                result["url_final"] = page.url
                result["error"] = f"action=3超时: {e}"

            # 最终截图
            final_shot = SCREENSHOT_DIR / "form_upload_test_final.png"
            await page.screenshot(path=str(final_shot))
            print(f"[FINAL] 最终截图: {final_shot}")

        except Exception as e:
            print(f"[ERROR] 测试过程出错: {e}")
            import traceback
            traceback.print_exc()
            result["status"] = "error"
            result["error"] = str(e)

            # 失败时也截图
            try:
                err_shot = SCREENSHOT_DIR / "form_upload_test_error.png"
                await page.screenshot(path=str(err_shot))
                result["screenshot"] = str(err_shot)
            except:
                pass

        finally:
            await page.close()
            await ctx.close()
            try:
                await browser.close()
            except:
                pass  # CDP browser may not have close()
            print("[TEST] 浏览器已关闭")

    # 保存结果
    result_file = LOG_DIR / "form_upload_result.json"
    with open(result_file, 'w', encoding='utf-8') as f:
        json.dump(result, f, indent=2, ensure_ascii=False)
    print(f"[RESULT] 结果已保存: {result_file}")
    print(f"[RESULT] 状态: {result['status']}")
    print(f"[RESULT] URL: {result.get('url_final', 'N/A')}")

    return result


if __name__ == "__main__":
    result = asyncio.run(run_form_upload_test())
    sys.exit(0 if result["status"] == "success" else 1)
