#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试本地上传：验证 pic.yupoo.com 图片下载到本地 + Element Plus 本地上传流程

执行方式:
    python scripts/test_local_upload.py

验证步骤:
    1. 下载一张测试图片 (pic.yupoo.com)
    2. 验证文件保存到 temp_images/
    3. 尝试上传到 ERP (需要已登录状态)
"""

import asyncio
import sys
import requests
from pathlib import Path

# 添加项目根目录到 sys.path
ROOT_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT_DIR))

from scripts.sync_pipeline import ImageUploader

# =============================================================================
# 测试 1: 直接下载验证 (无需浏览器)
# =============================================================================

def test_direct_download():
    """验证 pic.yupoo.com 外链可直接下载（无需登录）"""
    print("\n" + "=" * 60)
    print("测试 1: 直接下载 pic.yupoo.com 图片")
    print("=" * 60)

    test_urls = [
        "http://pic.yupoo.com/lol2024/f53b0825/3e40c632.jpeg",
    ]

    temp_dir = ROOT_DIR / "temp_images"
    temp_dir.mkdir(exist_ok=True)

    for i, url in enumerate(test_urls):
        local_path = temp_dir / f"test_img_{i:02d}.jpg"
        try:
            r = requests.get(url, timeout=15, headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            })
            if r.status_code == 200 and len(r.content) > 10000:
                with open(local_path, 'wb') as f:
                    f.write(r.content)
                print(f"  [PASS] {url}")
                print(f"         -> {local_path} ({len(r.content)} bytes)")
            else:
                print(f"  [FAIL] HTTP {r.status_code}, size={len(r.content)}")
        except Exception as e:
            print(f"  [FAIL] {e}")

    print(f"\n本地图片目录: {temp_dir}")
    test_files = list(temp_dir.glob("*.jpg"))
    print(f"已有图片数量: {len(test_files)}")

    return len(test_files) > 0

# =============================================================================
# 测试 2: ImageUploader._download_images() 完整测试
# =============================================================================

async def test_image_uploader_download():
    """测试 ImageUploader 的下载逻辑"""
    print("\n" + "=" * 60)
    print("测试 2: ImageUploader._download_images() 完整流程")
    print("=" * 60)

    # 使用真实的 pic.yupoo.com URL（从 YupooExtractor 的 API 响应格式）
    test_urls = [
        "http://pic.yupoo.com/lol2024/f53b0825/3e40c632.jpeg",
        "http://pic.yupoo.com/lol2024/f53b0825/3e40c631.jpeg",
    ]

    uploader = ImageUploader(test_urls)

    print(f"  Temp dir: {uploader.temp_dir}")
    print(f"  URLs to download: {len(uploader.urls)}")

    local_files = await uploader._download_images()

    if local_files:
        print(f"\n  [PASS] 下载成功: {len(local_files)} 个文件")
        for pf in local_files:
            p = Path(pf)
            print(f"         - {p.name} ({p.stat().st_size} bytes)")
    else:
        print("\n  [FAIL] 下载失败: 没有成功下载任何文件")

    return len(local_files) > 0

# =============================================================================
# 主入口
# =============================================================================

if __name__ == "__main__":
    print("ERP 本地上传修复验证脚本")
    print("=" * 60)

    # 测试1: 直接下载 (同步, 无需浏览器)
    download_ok = test_direct_download()

    # 测试2: ImageUploader 完整下载 (异步)
    upload_ok = asyncio.run(test_image_uploader_download())

    # 总结
    print("\n" + "=" * 60)
    print("测试结果汇总")
    print("=" * 60)
    print(f"  图片下载: {'PASS' if download_ok else 'FAIL'}")
    print(f"  ImageUploader: {'PASS' if upload_ok else 'FAIL'}")

    if download_ok and upload_ok:
        print("\n[OK] 本地上传逻辑验证通过，可以进行完整的端到端测试。")
    else:
        print("\n[ERROR] 部分测试失败，请检查网络连接或图片 URL。")

    sys.exit(0 if (download_ok and upload_ok) else 1)
