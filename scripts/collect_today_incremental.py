# -*- coding: utf-8 -*-
"""
Incremental collection for 28 products - saves progress after each album
"""

import json
import subprocess
import re
import time
from pathlib import Path


def run_cli(cmd):
    """Run playwright-cli command"""
    result = subprocess.run(
        cmd, shell=True, capture_output=True, encoding="utf-8", errors="ignore"
    )
    return (
        result.stdout if result.stdout else "",
        result.stderr if result.stderr else "",
    )


def convert_to_pic_url(photo_url):
    """Convert photo.yupoo.com URL to pic.yupoo.com URL"""
    match = re.match(r"https://photo\.yupoo\.com/([^/]+)/([^/]+)/.*", photo_url)
    if match:
        user_id = match.group(1)
        img_id = match.group(2)
        return f"http://pic.yupoo.com/{user_id}/{img_id}/image.jpeg"
    return photo_url


def main():
    # Read album list
    albums = []
    with open("inputs/today_albums_list.txt", "r", encoding="utf-8") as f:
        for line in f:
            parts = line.strip().split("|")
            if len(parts) == 2:
                albums.append({"album_id": parts[0], "title": parts[1]})

    # Check progress
    progress_file = Path("inputs/today_progress.json")
    if progress_file.exists():
        with open(progress_file, "r", encoding="utf-8") as f:
            progress = json.load(f)
        results = progress.get("results", [])
        start_idx = progress.get("last_idx", 0)
    else:
        results = []
        start_idx = 0

    print(f"=== Resuming from album {start_idx + 1}/{len(albums)} ===\n")

    # Open browser if needed
    if start_idx == 0:
        print("Opening browser...")
        run_cli('playwright-cli open --headed "https://lol2024.x.yupoo.com/"')
        time.sleep(3)

    for i in range(start_idx, len(albums)):
        album = albums[i]
        album_id = album["album_id"]
        title = album["title"]

        print(f"[{i + 1}/{len(albums)}] Collecting: {title}")

        # Navigate to album
        url = f"https://lol2024.x.yupoo.com/albums/{album_id}?uid=1"
        run_cli(f'playwright-cli goto "{url}"')
        time.sleep(2)

        # Extract image URLs
        stdout, _ = run_cli(
            "playwright-cli eval \"Array.from(document.querySelectorAll('main img')).map(img => img.src).join('\\n')\""
        )

        # Parse URLs
        images = []
        for line in stdout.split("\n"):
            match = re.search(r'https://photo\.yupoo\.com/[^\s"]+', line)
            if match:
                images.append(convert_to_pic_url(match.group()))

        # Skip first image (size chart)
        if len(images) > 1:
            first_image = images[1]
            other_images = (
                images[2:14] if len(images) > 2 else []
            )  # Max 13 other images
        elif len(images) == 1:
            first_image = images[0]
            other_images = []
        else:
            first_image = ""
            other_images = []

        # Save result
        result = {
            "album_id": album_id,
            "title": title,
            "first_image": first_image,
            "other_images": other_images,
        }
        results.append(result)

        print(
            f"  First image: {first_image[:50]}..."
            if first_image
            else "  First image: None"
        )
        print(f"  Other images: {len(other_images)}")

        # Save progress
        with open(progress_file, "w", encoding="utf-8") as f:
            json.dump(
                {"last_idx": i + 1, "results": results}, f, ensure_ascii=False, indent=2
            )

        # Go back to home
        run_cli('playwright-cli goto "https://lol2024.x.yupoo.com/"')
        time.sleep(1)

    # Close browser
    print("\nClosing browser...")
    run_cli("playwright-cli close")

    # Save final output
    output_path = Path("inputs/today_28_products.json")
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    # Clean up progress file
    if progress_file.exists():
        progress_file.unlink()

    print(f"\n=== Collection Complete ===")
    print(f"Output: {output_path}")
    print(f"Total: {len(results)} products")


if __name__ == "__main__":
    main()
