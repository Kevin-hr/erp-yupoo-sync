#!/usr/bin/env python3
import argparse
import csv
import io
import re
from dataclasses import dataclass
from pathlib import Path

import requests
from PIL import Image


def _read_csv_any_encoding(path: Path) -> list[dict]:
    for enc in ["utf-8-sig", "gb18030", "utf-8", "cp1252", "latin-1"]:
        try:
            with path.open("r", encoding=enc, newline="") as f:
                return list(csv.DictReader(f))
        except UnicodeDecodeError:
            continue
    raise RuntimeError(f"cannot decode csv: {path}")


def _write_csv_utf8sig(path: Path, rows: list[dict], headers: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=headers)
        w.writeheader()
        w.writerows(rows)


def _clean_cn_name(s: str) -> str:
    x = (s or "").strip()
    x = re.sub(r"^\s*[hH]\d+\s+", "", x)
    x = re.sub(r"\s+", " ", x).strip()
    return x


def _extract_leading_english(s: str) -> str:
    x = (s or "").strip()
    x = re.sub(r"^\s*[hH]\d+\s+", "", x)
    m = re.match(r"^[A-Za-z0-9][A-Za-z0-9 &/.\-']{2,}", x)
    if not m:
        return ""
    eng = m.group(0).strip()
    eng = re.sub(r"[/.]$", "", eng).strip()
    return eng


@dataclass(frozen=True)
class ColorInfo:
    name: str


def _rgb_to_color_name(r: int, g: int, b: int) -> str:
    mx = max(r, g, b)
    mn = min(r, g, b)
    if mx < 45:
        return "Black"
    if mn > 210 and mx > 230:
        return "White"
    if mx - mn < 25:
        if mx < 140:
            return "Gray"
        return "White"
    if r > 180 and g < 120 and b < 120:
        return "Red"
    if b > 160 and r < 140 and g < 170:
        return "Blue"
    if g > 160 and r < 150 and b < 150:
        return "Green"
    if r > 160 and g > 130 and b < 110:
        return "Yellow"
    if r > 120 and g > 70 and b < 90:
        return "Brown"
    return "Multicolor"


def _dominant_color_from_url(url: str, sess: requests.Session) -> ColorInfo:
    u = (url or "").strip()
    if not u:
        return ColorInfo(name="")
    r = sess.get(u, timeout=30)
    r.raise_for_status()
    img = Image.open(io.BytesIO(r.content)).convert("RGB")
    img = img.resize((96, 96))
    pixels = list(img.get_flattened_data())
    filtered = []
    for pr, pg, pb in pixels:
        if pr > 245 and pg > 245 and pb > 245:
            continue
        filtered.append((pr, pg, pb))
    if not filtered:
        pr, pg, pb = pixels[len(pixels) // 2]
        return ColorInfo(name=_rgb_to_color_name(pr, pg, pb))
    sr = sum(p[0] for p in filtered) // len(filtered)
    sg = sum(p[1] for p in filtered) // len(filtered)
    sb = sum(p[2] for p in filtered) // len(filtered)
    return ColorInfo(name=_rgb_to_color_name(sr, sg, sb))


def _guess_product_type(cn: str) -> str:
    m = [
        ("短袖", "T-Shirt"),
        ("T恤", "T-Shirt"),
        ("长袖", "Long Sleeve"),
        ("衬衫", "Shirt"),
        ("外套", "Jacket"),
        ("卫衣", "Hoodie"),
        ("夹克", "Jacket"),
        ("裤", "Pants"),
        ("牛仔", "Jeans"),
        ("帽", "Cap"),
        ("包", "Bag"),
        ("鞋", "Shoes"),
    ]
    for k, v in m:
        if k in cn:
            return v
    return ""


def _guess_features(cn: str) -> list[str]:
    feats = []
    m = [
        ("刺绣", "Embroidered"),
        ("印花", "Print"),
        ("字母", "Letter"),
        ("logo", "Logo"),
        ("Logo", "Logo"),
        ("联名", "Collaboration"),
        ("拼色", "Color Block"),
    ]
    for k, v in m:
        if k in cn and v not in feats:
            feats.append(v)
    return feats


def _normalize_english_name(cn_name: str, img_url: str, sess: requests.Session) -> str:
    cn = _clean_cn_name(cn_name)
    base = _extract_leading_english(cn)
    color = _dominant_color_from_url(img_url, sess).name
    typ = _guess_product_type(cn)
    feats = _guess_features(cn)

    parts = []
    if base:
        parts.append(base.replace("  ", " ").strip())
    if typ and (not base or typ.lower() not in base.lower()):
        parts.append(typ)
    for f in feats:
        if base and f.lower() in base.lower():
            continue
        parts.append(f)
    if color and (not base or color.lower() not in base.lower()):
        parts.append(color)

    out = " ".join([p for p in parts if p]).strip()
    out = re.sub(r"\s+", " ", out).strip()
    out = out.replace(" - ", " ").strip()
    out = re.sub(r"\s+", " ", out).strip()
    return out


def _extract_from_pic_columns(row: dict) -> tuple[str, str]:
    main = (row.get("pic_01") or "").strip()
    others = []
    for k in [f"pic_{x:02d}" for x in range(2, 15)]:
        v = (row.get(k) or "").strip()
        if v:
            others.append(v)
    return main, "\n".join(others)


def _extract_from_letter_columns(row: dict) -> tuple[str, str]:
    main = (row.get("D") or "").strip()
    others = []
    for k in sorted(row.keys()):
        if k in {"A", "B", "C", "D"}:
            continue
        v = (row.get(k) or "").strip()
        if not v:
            continue
        others.append(v)
    return main, "\n".join(others)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", required=True, type=str)
    ap.add_argument("--output", required=True, type=str)
    args = ap.parse_args()

    src = Path(args.input)
    rows = _read_csv_any_encoding(src)
    sess = requests.Session()

    out_rows: list[dict] = []
    seen: dict[str, int] = {}
    for i, row in enumerate(rows, start=1):
        cn_name = row.get("C") or row.get("product_name") or ""
        if any(k.startswith("pic_") for k in row.keys()):
            main_img, other_imgs = _extract_from_pic_columns(row)
        else:
            main_img, other_imgs = _extract_from_letter_columns(row)

        eng_name = (row.get("B") or row.get("product_name_en") or "").strip()
        if not eng_name:
            eng_name = _normalize_english_name(cn_name, main_img, sess)
        base = re.sub(r"\s+", " ", eng_name).strip()
        if base:
            n = seen.get(base, 0) + 1
            seen[base] = n
            if n > 1:
                eng_name = f"{base} {n}"

        out_rows.append(
            {
                "A": str(i),
                "B": eng_name,
                "C": _clean_cn_name(cn_name),
                "D": main_img.strip(),
                "E": other_imgs,
            }
        )

    headers = ["A", "B", "C", "D", "E"]
    _write_csv_utf8sig(Path(args.output), out_rows, headers)
    print(f"output={args.output}")
    print(f"rows={len(out_rows)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
