import argparse
import asyncio
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path

from playwright.async_api import async_playwright, Page

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.build_yesterday_products_erp_excel import (  # noqa: E402
    _apply_title_rules,
    _split_products_by_dup_title,
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


async def _collect_albums_in_date_group(page: Page, date_key: str) -> list[AlbumItem]:
    await _ensure_not_login(page)
    date_key = (date_key or "").strip()
    if not date_key:
        return []

    items = await page.evaluate(
        """(dateKey) => {
  const out = [];
  const re = /\\/albums\\/(\\d+)/;
  const h2s = Array.from(document.querySelectorAll('main h2, main h3, main h4'));
  const match = h2s.find(h => (h.textContent || '').replace(/\\s+/g,' ').includes(dateKey));
  const section = match ? match.parentElement : null;
  if (!section) return [];
  const links = Array.from(section.querySelectorAll('a[href*=\"/albums/\"]'));
  for (const a of links) {
    const href = a.href || a.getAttribute('href') || '';
    const m = href.match(re);
    if (!m) continue;
    const album_id = m[1];
    let title = (a.getAttribute('title') || a.getAttribute('aria-label') || '').trim();
    if (!title) title = ((a.querySelector('img') && a.querySelector('img').getAttribute('alt')) || '').trim();
    if (!title) title = (a.textContent || '').trim();
    title = title.replace(/\\s+/g,' ').trim();
    out.push({album_id, href, title});
  }
  return out;
}"""
        ,
        date_key,
    )

    seen: dict[str, AlbumItem] = {}
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
    return list(seen.values())


async def _extract_album_product(page: Page, album: AlbumItem, *, base_url: str) -> dict:
    album_id = album.album_id
    url = f"{base_url}/albums/{album_id}"
    await page.goto(url, wait_until="domcontentloaded")
    await _ensure_not_login(page)

    resp = await page.wait_for_response(
        lambda r: f"/api/albums/{album_id}/photos" in (r.url or ""),
        timeout=25000,
    )
    data = await resp.json()

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
  const og = document.querySelector('meta[property=\"og:title\"]');
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
    date_key = args.date_key

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
        work_page = await ctx.new_page()
        created_pages = [list_page, work_page]

        await list_page.goto(f"{base_url}/albums", wait_until="domcontentloaded")
        await list_page.wait_for_timeout(2000)
        await _ensure_not_login(list_page)

        albums = await _collect_albums_in_date_group(list_page, date_key)
        albums.sort(key=lambda x: int(x.album_id))
        if args.limit > 0:
            albums = albums[: args.limit]

        products: list[dict] = []
        for idx, album in enumerate(albums, 1):
            p1 = await _extract_album_product(work_page, album, base_url=base_url)
            products.append(p1)
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
    ap.add_argument("--date-key", required=True, type=str, help="Example: 04-23 or 昨天")
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

