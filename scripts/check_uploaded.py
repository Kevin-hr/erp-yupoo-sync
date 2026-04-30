# -*- coding: utf-8 -*-
"""
Check if albums have been uploaded before processing.
Reads from logs/uploaded_albums.json to prevent duplicate uploads.

Usage:
    from scripts.check_uploaded import is_uploaded, filter_new_albums

    # Check single album
    if is_uploaded('234120090'):
        print('Already uploaded, skipping...')

    # Filter new albums from a list
    new_albums = filter_new_albums(album_list)
"""

import json
from pathlib import Path
from typing import List, Dict, Optional


UPLOADED_RECORD_PATH = Path("logs/uploaded_albums.json")


def load_uploaded_record() -> Dict:
    """Load uploaded albums record from JSON file."""
    if not UPLOADED_RECORD_PATH.exists():
        return {"albums": {}, "total_count": 0}

    with open(UPLOADED_RECORD_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def is_uploaded(album_id: str) -> bool:
    """
    Check if an album has been uploaded.

    Args:
        album_id: The album ID to check

    Returns:
        True if album has been uploaded, False otherwise
    """
    record = load_uploaded_record()
    return str(album_id) in record.get("albums", {})


def get_uploaded_info(album_id: str) -> Optional[Dict]:
    """
    Get upload info for an album.

    Args:
        album_id: The album ID to check

    Returns:
        Dict with upload info if found, None otherwise
    """
    record = load_uploaded_record()
    return record.get("albums", {}).get(str(album_id))


def filter_new_albums(album_ids: List[str]) -> List[str]:
    """
    Filter out albums that have already been uploaded.

    Args:
        album_ids: List of album IDs to filter

    Returns:
        List of album IDs that have NOT been uploaded
    """
    record = load_uploaded_record()
    uploaded = set(record.get("albums", {}).keys())
    return [str(aid) for aid in album_ids if str(aid) not in uploaded]


def mark_as_uploaded(album_id: str, title: str, status: str = "uploaded") -> None:
    """
    Mark an album as uploaded in the record.

    Args:
        album_id: The album ID to mark
        title: The product title
        status: Upload status (default: 'uploaded')
    """
    from datetime import datetime

    record = load_uploaded_record()

    record["albums"][str(album_id)] = {
        "title": title,
        "uploaded_date": datetime.now().strftime("%Y-%m-%d"),
        "status": status,
    }
    record["total_count"] = len(record["albums"])
    record["last_updated"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    with open(UPLOADED_RECORD_PATH, "w", encoding="utf-8") as f:
        json.dump(record, f, ensure_ascii=False, indent=2)


def get_uploaded_count() -> int:
    """Get total count of uploaded albums."""
    record = load_uploaded_record()
    return record.get("total_count", 0)


def list_uploaded_albums(limit: int = 10) -> List[Dict]:
    """
    List uploaded albums.

    Args:
        limit: Maximum number of albums to return

    Returns:
        List of dicts with album_id and info
    """
    record = load_uploaded_record()
    albums = record.get("albums", {})

    result = []
    for i, (album_id, info) in enumerate(albums.items()):
        if i >= limit:
            break
        result.append({"album_id": album_id, **info})
    return result


if __name__ == "__main__":
    import sys

    sys.stdout.reconfigure(encoding="utf-8")

    print("=== Uploaded Albums Check ===")
    print(f"Total uploaded: {get_uploaded_count()}")
    print()

    # Show sample
    print("Recent uploads:")
    for item in list_uploaded_albums(10):
        print(f"  {item['album_id']}: {item['title'][:50]}...")

    print()

    # Test filter
    test_albums = ["234120090", "234116658", "999999999"]
    new_albums = filter_new_albums(test_albums)
    print(f"Test filter: {test_albums}")
    print(f"New albums (not uploaded): {new_albums}")
