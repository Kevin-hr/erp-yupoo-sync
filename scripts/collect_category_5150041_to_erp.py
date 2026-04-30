import argparse
import asyncio
import re
import json
import sys
from dataclasses import dataclass
from pathlib import Path

from playwright.async_api import async_playwright, Page

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.build_yesterday_products_erp_excel import (
    _split_products_by_dup_title,
    _apply_title_rules,
    _write_output,
)


ALBUM_RE = re.compile(r"/albums/(\d+)")


@dataclass
class AlbumItem:
    album_id: str
    href: str
    title_hint: str


def _norm_space(s: str) -> str:
    return re.sub(r"\s+", " ", (s or "").strip())


def _strip_dash_sep(s: str) -> str:
    return re.sub(r"\s+-\s+", " ", (s or "")).strip()


async def _ensure_not_login(page: Page) -> None:
    t = (await page.title()) or ""
    u = page.url or ""
    if "login" in u.lower() or "登录" in t:
        raise RuntimeError(f"Yupoo requires login (url={u})")


async def _scroll_collect_albums(page: Page, *, max_rounds: int = 40) -> list[AlbumItem]:
    seen: dict[str, AlbumItem] = {}
    stable = 0
    last = 0

    for _ in range(max_rounds):
        await _ensure_not_login(page)
        items = await page.evaluate(
            """() => {
  const out = [];
  const re = /\\/albums\\/(\\d+)/;
  const anchors = Array.from(document.querySelectorAll('a[href*="/albums/"]'));
  for (const a of anchors) {
    const href = a.href || a.getAttribute('href') || '';
    const m = href.match(re);
    if (!m) continue;
    const album_id = m[1];
    let title = (a.getAttribute('title') || '').trim();
    if (!title) title = ((a.querySelector('img') && a.querySelector('img').getAttribute('alt')) || '').trim();
    if (!title) title = (a.textContent || '').trim();
    title = title.replace(/\\s+/g, ' ').trim();
    out.push({album_id, href, title});
  }
  return out;
}"""
        )
        for it in items:
            aid = str(it.get("album_id") or "")
            if not aid:
                continue
            if aid not in seen:
                seen[aid] = AlbumItem(
                    album_id=aid,
                    href=str(it.get("href") or ""),
                    title_hint=str(it.get("title") or ""),
                )
        cur = len(seen)
        if cur == last:
            stable += 1
        else:
            stable = 0
            last = cur
        if stable >= 3:
            break
        await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
        await page.wait_for_timeout(1200)
    return list(seen.values())


async def _extract_album_products(
    page: Page,
    album: AlbumItem,
    *,
    base_url: str,
) -> dict:
    album_id = album.album_id
    url = f"{base_url}/albums/{album_id}"
    await page.goto(url, wait_until="domcontentloaded")
    await _ensure_not_login(page)

    try:
        resp = await page.wait_for_response(
            lambda r: f"/api/albums/{album_id}/photos" in (r.url or ""),
            timeout=25000,
        )
    except Exception:
        raise RuntimeError(f"album {album_id} photos api not captured")

    try:
        data = await resp.json()
    except Exception:
        raise RuntimeError(f"album {album_id} photos api json parse failed")

    paths = []
    for item in (data.get("data") or {}).get("list") or []:
        p = item.get("path") or ""
        if p:
            paths.append(p)
    urls = []
    for p in paths:
        if p.startswith("http://") or p.startswith("https://"):
            urls.append(p)
        else:
            if not p.startswith("/"):
                p = "/" + p
            urls.append("http://pic.yupoo.com" + p)

    title = ""
    try:
        title = await page.evaluate(
            """() => {
  const h1 = document.querySelector('h1');
  if (h1 && h1.textContent) return h1.textContent.trim();
  const og = document.querySelector('meta[property="og:title"]');
  if (og && og.getAttribute('content')) return og.getAttribute('content').trim();
  return (document.title || '').trim();
}"""
        )
    except Exception:
        title = ""
    title = _norm_space(title) or _norm_space(album.title_hint)
    title = _strip_dash_sep(title)

    main = urls[0] if urls else ""
    others = urls[1:14] if len(urls) > 1 else []
    return {"title": title, "main": main, "others": others, "album_id": album_id}


async def run(args: argparse.Namespace) -> int:
    base_url = args.base_url.rstrip("/")
    cdp_url = args.cdp_url
    pages = [int(x) for x in args.pages.split(",") if x.strip()]

    out_json = Path(args.out_json)
    out_unique = Path(args.out_unique)
    out_dups = Path(args.out_dups)
    out_json.parent.mkdir(parents=True, exist_ok=True)
    out_unique.parent.mkdir(parents=True, exist_ok=True)
    out_dups.parent.mkdir(parents=True, exist_ok=True)

    async with async_playwright() as p:
        browser = await p.chromium.connect_over_cdp(cdp_url, timeout=10000)
        if not browser.contexts:
            raise RuntimeError("No browser context found via CDP (need logged-in persistent profile)")
        ctx = browser.contexts[0]

        list_page = await ctx.new_page()
        created_pages = [list_page]
        albums_all: dict[str, AlbumItem] = {}

        for pn in pages:
            url = f"{base_url}/categories/{args.category_id}?page={pn}"
            await list_page.goto(url, wait_until="domcontentloaded")
            await list_page.wait_for_timeout(1500)
            await _ensure_not_login(list_page)
            albums = await _scroll_collect_albums(list_page)
            for a in albums:
                albums_all.setdefault(a.album_id, a)

        album_items = list(albums_all.values())
        album_items.sort(key=lambda x: int(x.album_id))
        if args.limit > 0:
            album_items = album_items[: args.limit]

        work_page = await ctx.new_page()
        created_pages.append(work_page)

        products: list[dict] = []
        for idx, album in enumerate(album_items, 1):
            try:
                p = await _extract_album_products(work_page, album, base_url=base_url)
            except Exception as e:
                raise RuntimeError(f"[{idx}/{len(album_items)}] {e}")
            products.append(p)
            if idx % 10 == 0:
                out_json.write_text(json.dumps(products, ensure_ascii=False, indent=2), encoding="utf-8")

        out_json.write_text(json.dumps(products, ensure_ascii=False, indent=2), encoding="utf-8")

        uniq, dups = _split_products_by_dup_title(products)
        uniq = _apply_title_rules(uniq, use_image_color_for_dups=False)
        dups = _apply_title_rules(dups, use_image_color_for_dups=True)

        _write_output(Path(args.template), uniq, out_unique)
        _write_output(Path(args.template), dups, out_dups)

        for pg in created_pages:
            try:
                await pg.close()
            except Exception:
                pass
        return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--category-id", required=True, type=str)
    ap.add_argument("--pages", required=True, type=str, help="Comma-separated pages, e.g. 1,2")
    ap.add_argument("--base-url", default="https://lol2024.x.yupoo.com", type=str)
    ap.add_argument("--cdp-url", default="http://127.0.0.1:9222", type=str)
    ap.add_argument("--template", required=True, type=str)
    ap.add_argument("--out-json", required=True, type=str)
    ap.add_argument("--out-unique", required=True, type=str)
    ap.add_argument("--out-dups", required=True, type=str)
    ap.add_argument("--limit", default=0, type=int)
    args = ap.parse_args()

    try:
        return asyncio.run(run(args))
    except Exception as e:
        print(str(e))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())

