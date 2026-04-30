#!/usr/bin/env python3
"""
Batch process product images to extract official English names.
Then update ERP Excel file with English names in column C.
"""

import json
import requests
import time
from pathlib import Path
from datetime import datetime
import openpyxl


def download_image(url: str, save_path: Path) -> bool:
    """Download image from URL."""
    try:
        resp = requests.get(url, timeout=15)
        if resp.status_code == 200:
            save_path.write_bytes(resp.content)
            return True
    except Exception as e:
        print(f"    Download error: {e}")
    return False


def main():
    # Load products
    products_file = Path("inputs/yesterday_products_final.json")
    with open(products_file, "r", encoding="utf-8") as f:
        products = json.load(f)

    print(f"Processing {len(products)} products...")

    # Create temp directory
    temp_dir = Path(".dumate/temp_images")
    temp_dir.mkdir(parents=True, exist_ok=True)

    # Process each product
    english_names = {}

    for i, product in enumerate(products):
        name = product.get("name", "")
        images = product.get("images", [])
        album_id = product.get("album_id", "")

        print(f"\n[{i + 1}/{len(products)}] {name[:40]}...")

        if not images:
            print("    No images")
            continue

        # Download first image
        img_url = images[0]
        img_path = temp_dir / f"{album_id}.jpg"

        if download_image(img_url, img_path):
            print(f"    Downloaded: {img_path.name}")
            # Store for later processing
            english_names[album_id] = {
                "chinese_name": name,
                "image_path": str(img_path),
                "needs_review": True,
            }
        else:
            print("    Download failed")

        # Rate limiting
        time.sleep(0.5)

    # Save mapping
    mapping_file = Path("inputs/english_names_mapping.json")
    with open(mapping_file, "w", encoding="utf-8") as f:
        json.dump(english_names, f, ensure_ascii=False, indent=2)

    print(f"\n\nDownloaded images for {len(english_names)} products")
    print(f"Mapping saved to: {mapping_file}")
    print("\nImages are ready for visual recognition in .dumate/temp_images/")


if __name__ == "__main__":
    main()
