#!/usr/bin/env python3
import argparse
import csv
import json
import re
from pathlib import Path
from urllib.parse import parse_qs, unquote


def _load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def _extract_impress_token(cookies: list[dict]) -> dict:
    for cookie in cookies:
        if cookie.get("name") != "impress":
            continue
        raw = cookie.get("value") or ""
        try:
            return json.loads(unquote(raw))
        except Exception:
            return {}
    return {}


def _find_local_storage_value(origins: list[dict], key_prefix: str) -> str:
    for origin in origins:
        for item in origin.get("localStorage") or []:
            name = item.get("name") or ""
            if name.startswith(key_prefix):
                return item.get("value") or ""
    return ""


def _load_session_state(session_file: Path) -> dict:
    raw = _load_json(session_file)
    cookies = raw.get("cookies") or []
    origins = raw.get("origins") or []
    impress = _extract_impress_token(cookies)
    gallery_raw = _find_local_storage_value(origins, "gallery@")
    category_raw = _find_local_storage_value(origins, "category@")
    gallery = json.loads(gallery_raw) if gallery_raw else {}
    category = json.loads(category_raw) if category_raw else {}
    return {
        "username": impress.get("username") or "",
        "bucket": impress.get("bucket") or "",
        "gallery": gallery,
        "category": category,
    }


def _load_cache_products(cache_files: list[Path]) -> dict[str, dict]:
    out: dict[str, dict] = {}
    for path in cache_files:
        if not path.exists():
            continue
        try:
            data = _load_json(path)
        except Exception:
            continue
        if not isinstance(data, list):
            continue
        for item in data:
            album_id = str(item.get("album_id") or "").strip()
            if not album_id:
                url = str(item.get("url") or "")
                m = re.search(r"/albums/(\d+)", url)
                album_id = m.group(1) if m else ""
            if album_id and album_id not in out:
                out[album_id] = item
    return out


def _album_ids_from_session(session_state: dict, category_id: str | None) -> list[str]:
    gallery = session_state.get("gallery") or {}
    category = session_state.get("category") or {}
    if category_id:
        category_data = (category.get("categoryData") or {}).get(f"{category_id}_1") or []
        return [str(x) for x in category_data]

    page1 = (gallery.get("galleryListData") or {}).get("1") or []
    if page1:
        return [str(x) for x in page1]

    sort_ids = gallery.get("sort") or []
    return [str(x) for x in sort_ids]


def _normalize_images(images: list[str]) -> list[str]:
    out = []
    for url in images:
        u = str(url or "").strip()
        if not u:
            continue
        u = u.replace("https://", "http://").replace("photo.yupoo.com", "pic.yupoo.com")
        if u not in out:
            out.append(u)
    return out[:14]


def _english_name(item: dict) -> str:
    return (
        str(item.get("english_name") or "").strip()
        or str(item.get("title") or "").strip()
        or str(item.get("name") or "").strip()
    )


def _product_name(item: dict, album_id: str) -> str:
    return str(item.get("title") or "").strip() or str(item.get("name") or "").strip() or f"album_{album_id}"


def _product_url(username: str, album_id: str, item: dict) -> str:
    url = str(item.get("url") or "").strip()
    if url:
        return url
    if username:
        return f"https://{username}.x.yupoo.com/albums/{album_id}?uid=1"
    return f"https://x.yupoo.com/albums/{album_id}"


def _build_rows(session_state: dict, album_ids: list[str], cache_map: dict[str, dict]) -> list[dict]:
    username = session_state.get("username") or "lol2024"
    rows: list[dict] = []
    for idx, album_id in enumerate(album_ids, start=1):
        item = cache_map.get(album_id) or {}
        images = _normalize_images(item.get("images") or [])
        row = {
            "no": idx,
            "album_id": album_id,
            "product_name": _product_name(item, album_id),
            "english_product_name": _english_name(item),
            "url": _product_url(username, album_id, item),
            "image_count": len(images),
        }
        for i in range(14):
            row[f"pic_{i + 1:02d}"] = images[i] if i < len(images) else ""
        rows.append(row)
    return rows


def _filter_rows(rows: list[dict], keyword: str, require_images: bool) -> list[dict]:
    out = rows
    if keyword:
        kw = keyword.strip().lower()
        out = [
            row
            for row in out
            if kw in row["product_name"].lower()
            or kw in row["english_product_name"].lower()
            or kw in row["url"].lower()
        ]
    if require_images:
        out = [row for row in out if int(row["image_count"]) > 0]
    for idx, row in enumerate(out, start=1):
        row["no"] = idx
    return out


def _write_csv(rows: list[dict], output_csv: Path) -> None:
    output_csv.parent.mkdir(parents=True, exist_ok=True)
    headers = ["no", "album_id", "product_name", "english_product_name", "url", "image_count"]
    headers.extend([f"pic_{i:02d}" for i in range(1, 15)])
    with output_csv.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=headers)
        writer.writeheader()
        writer.writerows(rows)


def main() -> int:
    ap = argparse.ArgumentParser(description="Search Yupoo cache/session and export CSV with pic_* columns.")
    ap.add_argument("--session-file", default="yupoo_session.json", type=str)
    ap.add_argument("--category-id", default="", type=str)
    ap.add_argument("--keyword", default="", type=str)
    ap.add_argument("--cache-json", action="append", default=[], help="Existing product JSON cache file; can be repeated.")
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--require-images", action="store_true")
    ap.add_argument("--output", required=True, type=str)
    args = ap.parse_args()

    session_file = Path(args.session_file)
    if not session_file.exists():
        raise SystemExit(f"session file not found: {session_file}")

    cache_files = [Path(p) for p in args.cache_json]
    session_state = _load_session_state(session_file)
    album_ids = _album_ids_from_session(session_state, args.category_id.strip() or None)
    if args.limit and args.limit > 0:
        album_ids = album_ids[: args.limit]
    if not album_ids:
        raise SystemExit("no album ids found in session cache")

    cache_map = _load_cache_products(cache_files)
    rows = _build_rows(session_state, album_ids, cache_map)
    rows = _filter_rows(rows, args.keyword, args.require_images)
    if args.limit and args.limit > 0:
        rows = rows[: args.limit]
    if not rows:
        raise SystemExit("no rows matched search conditions")
    _write_csv(rows, Path(args.output))

    cached_hits = sum(1 for row in rows if row["image_count"] > 0)
    print(f"output={args.output}")
    print(f"rows={len(rows)}")
    print(f"cached_rows_with_images={cached_hits}")
    print(f"category_id={args.category_id or 'ALL'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
