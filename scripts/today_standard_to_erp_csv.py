#!/usr/bin/env python3
import argparse
import csv
import re
import sys
from pathlib import Path
from typing import Iterable


ERP_HEADERS = [
    "商品ID",
    "商品标题*",
    "副标题",
    "商品描述",
    "商品首图*",
    "商品其他图片",
    "关键信息",
    "属性",
    "商品上架*",
    "物流模板*",
    "类别名称",
    "标签",
    "计量单位",
    "商品备注",
    "不记库存*",
    "商品重量*",
    "包装长度",
    "包装宽度",
    "包装高度",
    "SEO标题",
    "SEO描述",
    "SEO关键词",
    "SEO URL Handle",
    "规格1",
    "规格2",
    "规格3",
    "规格4",
    "SKU值",
    "SKU图片",
    "售价*",
    "原价",
    "库存",
    "SKU",
]


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
        w = csv.DictWriter(f, fieldnames=headers, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)


def _contains_chinese(s: str) -> bool:
    return bool(re.search(r"[\u4e00-\u9fff]", s or ""))


def _dedup_keep_order(items: Iterable[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for x in items:
        x2 = (x or "").strip()
        if not x2:
            continue
        if x2 in seen:
            continue
        seen.add(x2)
        out.append(x2)
    return out


def _clean_images(main: str, other_multiline: str) -> tuple[str, str, list[str]]:
    main0 = (main or "").strip()
    others0 = (other_multiline or "").replace("\r\n", "\n").replace("\r", "\n")
    others = [x.strip() for x in others0.split("\n") if x.strip()]

    all_imgs = [main0] + others
    all_imgs = [u.replace("https://", "http://") for u in all_imgs]
    all_imgs = [u.replace("photo.yupoo.com", "pic.yupoo.com") for u in all_imgs]
    all_imgs = _dedup_keep_order(all_imgs)
    if not all_imgs:
        return "", "", []
    main_img = all_imgs[0]
    other_imgs = all_imgs[1:14]
    return main_img, "\n".join(other_imgs), [main_img] + other_imgs


def _brand_from_title(title: str) -> str:
    t = (title or "").strip()
    low = t.lower()
    if low.startswith("louis vuitton "):
        return "LOUIS VUITTON"
    if low.startswith("louisvuitton "):
        return "LOUIS VUITTON"
    if low.startswith("saint laurent "):
        return "SAINT LAURENT"
    if low.startswith("miu miu "):
        return "MIU MIU"
    if low.startswith("thom browne "):
        return "THOM BROWNE"
    if low.startswith("alexander wang "):
        return "ALEXANDER WANG"
    if low.startswith("ami paris "):
        return "AMI PARIS"
    first = t.split(" ", 1)[0].strip()
    if not first:
        return ""
    return first.upper()


def _brand_display(brand_key: str) -> str:
    m = {
        "LOUIS VUITTON": "Louis Vuitton",
        "BALENCIAGA": "Balenciaga",
        "CLOT": "CLOT",
        "SAINT LAURENT": "Saint Laurent",
        "CELINE": "Celine",
        "PRADA": "Prada",
        "FENDI": "Fendi",
        "DIOR": "Dior",
    }
    return m.get(brand_key, brand_key)


def _desc_html(title: str, brand_display: str) -> str:
    t = (title or "").strip()
    b = (brand_display or "").strip()
    brand_line = f"<p><span style=\"font-family: Tahoma;\">Brand: {b}</span></p>\n" if b else ""
    return (
        f"<p><span style=\"font-family: Tahoma;\">Name: {t}</span></p>\n"
        f"{brand_line}"
        "<p><span style=\"font-family: Tahoma;\">Category: Clothing</span></p>"
    )


def _normalize_spaces(s: str) -> str:
    x = (s or "").strip()
    x = re.sub(r"\s+", " ", x).strip()
    return x


def _make_unique_title(title: str, seen: dict[str, int]) -> str:
    base = _normalize_spaces(title)
    if not base:
        base = "Untitled"
    base2 = base
    if len(base2) > 255:
        base2 = base2[:255].rstrip()
    n = seen.get(base2, 0) + 1
    seen[base2] = n
    if n == 1:
        return base2
    suffix = f" {n}"
    if len(base2) + len(suffix) <= 255:
        return base2 + suffix
    cut = 255 - len(suffix)
    return base2[:cut].rstrip() + suffix


def _blank_row() -> dict[str, str]:
    return {h: "" for h in ERP_HEADERS}


def _require(cond: bool, msg: str, errors: list[str]) -> None:
    if not cond:
        errors.append(msg)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", required=True, help="标准CSV（列名通常为 A,B,D,E）")
    ap.add_argument("--output", required=True, help="ERP可导入CSV输出路径")
    ap.add_argument("--price", default="59.00")
    ap.add_argument("--compare-at", default="99.00")
    ap.add_argument("--stock", default="999")
    ap.add_argument("--weight", default="0.300")
    ap.add_argument("--sizes", default="S,M,L,XL")
    args = ap.parse_args()

    in_path = Path(args.input)
    out_path = Path(args.output)

    rows_in = _read_csv_any_encoding(in_path)
    seen_titles: dict[str, int] = {}
    out_rows: list[dict] = []
    errors: list[str] = []

    sizes = [s.strip() for s in (args.sizes or "").split(",") if s.strip()]
    if not sizes:
        sizes = ["S", "M", "L", "XL"]

    for idx, r in enumerate(rows_in, start=1):
        title_raw = r.get("B") or r.get("产品英文名") or r.get("english_product_name") or ""
        main_raw = r.get("D") or r.get("商品首图") or r.get("main") or ""
        other_raw = r.get("E") or r.get("商品其他图片") or r.get("others") or ""

        title = _make_unique_title(title_raw, seen_titles)
        brand_key = _brand_from_title(title)
        brand_display = _brand_display(brand_key)
        desc = _desc_html(title, brand_display)
        main_img, other_imgs, all_imgs = _clean_images(main_raw, other_raw)

        _require(bool(title.strip()), f"row#{idx}: empty title", errors)
        _require(bool(main_img.strip()), f"row#{idx}: empty main image", errors)
        _require(len(all_imgs) <= 14, f"row#{idx}: images > 14 ({len(all_imgs)})", errors)
        _require(all("pic.yupoo.com" in u for u in all_imgs), f"row#{idx}: non-pic.yupoo.com image found", errors)
        _require(all("photo.yupoo.com" not in u for u in all_imgs), f"row#{idx}: photo.yupoo.com image found", errors)
        _require(not _contains_chinese(desc), f"row#{idx}: description contains Chinese", errors)
        _require(f"Name: {title}" in desc, f"row#{idx}: Name line mismatch", errors)

        spec_block = "Size\n" + "\n".join(sizes)

        r_main = _blank_row()
        r_main["商品ID"] = ""
        r_main["商品标题*"] = title
        r_main["副标题"] = ""
        r_main["商品描述"] = desc
        r_main["商品首图*"] = main_img
        r_main["商品其他图片"] = other_imgs
        r_main["关键信息"] = ""
        r_main["属性"] = ""
        r_main["商品上架*"] = "N"
        r_main["物流模板*"] = "Clothing"
        r_main["类别名称"] = brand_display
        r_main["标签"] = title
        r_main["计量单位"] = "件/个"
        r_main["商品备注"] = ""
        r_main["不记库存*"] = "Y"
        r_main["商品重量*"] = str(args.weight)
        r_main["包装长度"] = ""
        r_main["包装宽度"] = ""
        r_main["包装高度"] = ""
        r_main["SEO标题"] = title
        r_main["SEO描述"] = title
        r_main["SEO关键词"] = f"{brand_display}, {title}".strip(", ").strip()
        r_main["SEO URL Handle"] = ""
        r_main["规格1"] = ""
        r_main["规格2"] = spec_block
        r_main["规格3"] = ""
        r_main["规格4"] = ""
        r_main["SKU值"] = f"Size:{sizes[0]}"
        r_main["SKU图片"] = ""
        r_main["售价*"] = str(args.price)
        r_main["原价"] = str(args.compare_at)
        r_main["库存"] = str(args.stock)
        r_main["SKU"] = ""

        out_rows.append(r_main)

        for sz in sizes[1:]:
            r_sku = _blank_row()
            r_sku["SKU值"] = f"Size:{sz}"
            r_sku["售价*"] = str(args.price)
            r_sku["原价"] = str(args.compare_at)
            r_sku["库存"] = str(args.stock)
            out_rows.append(r_sku)

    _write_csv_utf8sig(out_path, out_rows, ERP_HEADERS)

    if errors:
        sys.stderr.write("VALIDATION_FAILED\n")
        for e in errors[:200]:
            sys.stderr.write(e + "\n")
        if len(errors) > 200:
            sys.stderr.write(f"... {len(errors)-200} more\n")
        return 2

    sys.stdout.write(
        f"OK rows_in={len(rows_in)} rows_out={len(out_rows)} output={out_path.as_posix()}\n"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

