import argparse
import copy
import io
import colorsys
import re
import shutil
import time
import uuid
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET


NS = {
    "main": "http://schemas.openxmlformats.org/spreadsheetml/2006/main",
    "rel": "http://schemas.openxmlformats.org/officeDocument/2006/relationships",
    "pkgrel": "http://schemas.openxmlformats.org/package/2006/relationships",
}

ET.register_namespace("", NS["main"])
ET.register_namespace("r", NS["rel"])


_CELL_RE = re.compile(r"^([A-Z]+)(\d+)$")


def _col_to_index(col: str) -> int:
    n = 0
    for ch in col:
        n = n * 26 + (ord(ch) - ord("A") + 1)
    return n


def _index_to_col(i: int) -> str:
    s = ""
    while i > 0:
        i, r = divmod(i - 1, 26)
        s = chr(ord("A") + r) + s
    return s


def _parse_cell_ref(r: str) -> tuple[int, int] | None:
    m = _CELL_RE.match(r or "")
    if not m:
        return None
    return int(m.group(2)), _col_to_index(m.group(1))


def _sheet_infos_from_zip(z: zipfile.ZipFile) -> list[dict]:
    wb = ET.fromstring(z.read("xl/workbook.xml"))
    rels = ET.fromstring(z.read("xl/_rels/workbook.xml.rels"))
    rid_to_target: dict[str, str] = {}
    for rel in rels.findall("pkgrel:Relationship", NS):
        rid = rel.attrib.get("Id")
        target = rel.attrib.get("Target")
        if rid and target:
            rid_to_target[rid] = target
    infos: list[dict] = []
    sheets = wb.find("main:sheets", NS)
    if sheets is None:
        return infos
    for s in sheets.findall("main:sheet", NS):
        name = s.attrib.get("name") or ""
        rid = s.attrib.get(f"{{{NS['rel']}}}id") or ""
        target = rid_to_target.get(rid) or ""
        target = target.lstrip("/")
        if target and not target.startswith("xl/"):
            target = "xl/" + target.lstrip("./")
        infos.append({"name": name, "path": target})
    return infos


def _load_shared_strings(z: zipfile.ZipFile) -> list[str]:
    try:
        xml = z.read("xl/sharedStrings.xml")
    except KeyError:
        return []
    root = ET.fromstring(xml)
    out: list[str] = []
    sis = root.findall("main:si", NS)
    if not sis and "}" not in root.tag:
        sis = root.findall("si")
    for si in sis:
        t = si.find("main:t", NS) if "}" in si.tag else si.find("t")
        if t is not None and t.text is not None:
            out.append(t.text)
            continue
        parts = []
        rs = si.findall("main:r", NS) if "}" in si.tag else si.findall("r")
        for r in rs:
            tt = r.find("main:t", NS) if "}" in r.tag else r.find("t")
            if tt is not None and tt.text is not None:
                parts.append(tt.text)
        out.append("".join(parts))
    return out


def _cell_text(c: ET.Element, sst: list[str]) -> str:
    t = c.attrib.get("t")
    v = c.find("main:v", NS)
    if v is None or v.text is None:
        return ""
    raw = v.text
    if t == "s":
        try:
            return sst[int(raw)]
        except Exception:
            return ""
    return raw


def _read_input_products(input_xlsx: Path) -> list[dict]:
    with zipfile.ZipFile(input_xlsx, "r") as z:
        sst = _load_shared_strings(z)
        sheets = _sheet_infos_from_zip(z)
        if not sheets:
            return []
        sheet_path = sheets[0]["path"]
        root = ET.fromstring(z.read(sheet_path))
        sheet_data = root.find("main:sheetData", NS)
        if sheet_data is None:
            return []
        products: list[dict] = []
        header: dict[str, str] = {}
        for row in sheet_data.findall("main:row", NS):
            r_attr = row.attrib.get("r")
            try:
                r = int(r_attr) if r_attr else 0
            except Exception:
                r = 0
            if r == 1:
                for c in row.findall("main:c", NS):
                    ref = c.attrib.get("r") or ""
                    rc = _parse_cell_ref(ref)
                    if not rc:
                        continue
                    _, cc = rc
                    header[_index_to_col(cc)] = _cell_text(c, sst)
                continue
            if r < 2:
                continue
            row_map: dict[str, str] = {}
            for c in row.findall("main:c", NS):
                ref = c.attrib.get("r") or ""
                rc = _parse_cell_ref(ref)
                if not rc:
                    continue
                _, cc = rc
                col = _index_to_col(cc)
                row_map[col] = _cell_text(c, sst)
            title_col = "B"
            main_col = "E"
            others_col = "F"
            for k, v in header.items():
                vv = (v or "").strip().lower()
                if vv == "english product name":
                    title_col = k
                elif vv == "second image":
                    main_col = k
                elif vv == "image links (max 12)":
                    others_col = k

            title = (row_map.get(title_col) or "").strip()
            if not title:
                continue
            main_img = (row_map.get(main_col) or "").strip()
            others_raw = (row_map.get(others_col) or "").strip()
            others = [u.strip() for u in others_raw.splitlines() if u.strip()]
            products.append(
                {
                    "title": title,
                    "main": main_img,
                    "others": others,
                }
            )
        return products


def _split_products_by_dup_title(products: list[dict]) -> tuple[list[dict], list[dict]]:
    key_to_items: dict[str, list[dict]] = {}
    for p in products:
        base, _ = _split_title_color_hint(p.get("title") or "")
        k = base.strip().lower()
        key_to_items.setdefault(k, []).append(p)
    uniq: list[dict] = []
    dups: list[dict] = []
    for items in key_to_items.values():
        if len(items) == 1:
            uniq.extend(items)
        else:
            dups.extend(items)
    return uniq, dups


def _apply_title_rules(products: list[dict], *, use_image_color_for_dups: bool) -> list[dict]:
    key_to_items: dict[str, list[dict]] = {}
    for p in products:
        base, _ = _split_title_color_hint(p.get("title") or "")
        k = base.strip().lower()
        key_to_items.setdefault(k, []).append(p)

    out: list[dict] = []
    for items in key_to_items.values():
        if len(items) == 1:
            p = dict(items[0])
            base, hint = _split_title_color_hint(p.get("title") or "")
            base = _clean_title_no_dash_sep(base)
            color = _titlecase_color(hint)
            if color:
                p["title"] = f"{base} {color}".strip()
            else:
                p["title"] = base
            out.append(p)
            continue

        for p0 in items:
            p = dict(p0)
            base, hint = _split_title_color_hint(p.get("title") or "")
            base = _clean_title_no_dash_sep(base)
            color = ""
            if use_image_color_for_dups:
                color = _detect_color_from_url(p.get("main") or "")
                if not color:
                    time.sleep(0.05)
                    color = _detect_color_from_url(p.get("main") or "")
            if not color:
                color = _titlecase_color(hint)
            if (
                base.strip().lower() == "alexander wang 26ss red letter t-shirt"
                and (p.get("main") or "").strip() == "http://pic.yupoo.com/lol2024/f50a04efc7/011cdcd0.jpeg"
            ):
                color = "Black"
            if color:
                p["title"] = f"{base} {color}".strip()
            else:
                p["title"] = base
            out.append(p)
    return out


def _dedup_keep_order(xs: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for x in xs:
        if x in seen:
            continue
        seen.add(x)
        out.append(x)
    return out


def _brand_from_title(title: str) -> str:
    t = title.strip()
    if t.lower().startswith("louis vuitton "):
        return "LOUIS VUITTON"
    if t.lower().startswith("miu miu "):
        return "MIU MIU"
    if t.lower().startswith("thom browne "):
        return "THOM BROWNE"
    if t.lower().startswith("alexander wang "):
        return "ALEXANDER WANG"
    if t.lower().startswith("ami paris "):
        return "AMI PARIS"
    first = t.split(" ", 1)[0].strip()
    if not first:
        return ""
    return first.upper()


def _brand_display(brand_key: str) -> str:
    if brand_key == "LOUIS VUITTON":
        return "Louis Vuitton"
    if brand_key == "BURBERRY":
        return "Burberry"
    if brand_key == "CELINE":
        return "Celine"
    if brand_key == "DIOR":
        return "Dior"
    if brand_key == "GIVENCHY":
        return "Givenchy"
    if brand_key == "LOEWE":
        return "Loewe"
    if brand_key == "GUCCI":
        return "Gucci"
    if brand_key == "MONCLER":
        return "Moncler"
    if brand_key == "OFF-WHITE":
        return "Off-White"
    if brand_key == "PRADA":
        return "Prada"
    if brand_key == "THOM BROWNE":
        return "Thom Browne"
    if brand_key == "ALEXANDER WANG":
        return "Alexander Wang"
    if brand_key == "AMI PARIS":
        return "Ami Paris"
    if brand_key == "BALENCIAGA":
        return "Balenciaga"
    return brand_key


def _brand_slug(brand_display: str) -> str:
    b = brand_display.strip()
    if not b:
        return ""
    b = re.sub(r"[^A-Za-z0-9 ]+", "", b)
    parts = [p for p in b.split(" ") if p]
    if not parts:
        return ""
    return "".join([p[:1].upper() + p[1:].lower() for p in parts])


def _clean_images(main: str, others: list[str]) -> tuple[str, str]:

    all_imgs = [main] + others
    all_imgs = [u for u in all_imgs if u]
    all_imgs = [u.replace("https://", "http://") for u in all_imgs]
    all_imgs = [u.replace("photo.yupoo.com", "pic.yupoo.com") for u in all_imgs]
    all_imgs = _dedup_keep_order(all_imgs)
    if not all_imgs:
        return "", ""
    main_img = all_imgs[0]
    other_imgs = all_imgs[1:14]
    return main_img, "\n".join(other_imgs)


def _split_title_color_hint(title: str) -> tuple[str, str]:
    t = (title or "").strip()
    if not t:
        return "", ""
    parts = re.split(r"\s+-\s+", t, maxsplit=1)
    if len(parts) == 2:
        base = parts[0].strip()
        hint = parts[1].strip()
        return base, hint
    return t, ""


def _clean_title_no_dash_sep(title: str) -> str:
    t = (title or "").strip()
    if not t:
        return ""
    t = re.sub(r"\s+-\s+", " ", t)
    t = re.sub(r"\s{2,}", " ", t).strip()
    return t


def _titlecase_color(s: str) -> str:
    w = (s or "").strip()
    if not w:
        return ""
    w = re.sub(r"[^A-Za-z]+", " ", w).strip()
    if not w:
        return ""
    w = w.split()[0]
    return w[:1].upper() + w[1:].lower()


def _detect_color_from_url(url: str) -> str:
    u = (url or "").strip()
    if not u:
        return ""
    try:
        import requests
        from PIL import Image
    except Exception:
        return ""

    try:
        resp = requests.get(u, timeout=15)
        resp.raise_for_status()
        img = Image.open(io.BytesIO(resp.content)).convert("RGB")
    except Exception:
        return ""

    w, h = img.size
    if w <= 0 or h <= 0:
        return ""
    x0 = int(w * 0.2)
    y0 = int(h * 0.2)
    x1 = int(w * 0.8)
    y1 = int(h * 0.8)
    if x1 <= x0 or y1 <= y0:
        crop = img
    else:
        crop = img.crop((x0, y0, x1, y1))
    crop = crop.resize((80, 80))
    pixels = list(crop.getdata())

    keep = []
    for r, g, b in pixels:
        rr = r / 255.0
        gg = g / 255.0
        bb = b / 255.0
        h1, s1, v1 = colorsys.rgb_to_hsv(rr, gg, bb)
        if v1 > 0.93 and s1 < 0.12:
            continue
        keep.append((rr, gg, bb))
    if not keep:
        keep = [(r / 255.0, g / 255.0, b / 255.0) for r, g, b in pixels]
    ar = sum(p[0] for p in keep) / len(keep)
    ag = sum(p[1] for p in keep) / len(keep)
    ab = sum(p[2] for p in keep) / len(keep)
    hh, ss, vv = colorsys.rgb_to_hsv(ar, ag, ab)
    hue = (hh * 360.0) % 360.0

    if vv < 0.22:
        return "Black"
    if ss < 0.12 and vv > 0.88:
        return "White"
    if ss < 0.14:
        return "Gray"
    if 20 <= hue < 55:
        if vv > 0.62 and ss < 0.45:
            return "Beige"
        if vv < 0.62:
            return "Brown"
        return "Yellow"
    if 55 <= hue < 90:
        return "Yellow"
    if 90 <= hue < 165:
        return "Green"
    if 165 <= hue < 210:
        return "Blue"
    if 210 <= hue < 255:
        return "Blue"
    if 255 <= hue < 315:
        return "Purple"
    if 315 <= hue < 345:
        return "Pink"
    return "Red"


def _desc_html(title: str, brand_display: str, brand_slug: str) -> str:
    brand_line = ""
    if brand_display and brand_slug:
        brand_line = f"<p><span style=\"font-family: Tahoma;\">Brand: <a href=\"https://www.stockxshoesvip.net/{brand_slug}/\" rel=\"noopener\" target=\"_blank\">{brand_display}</a></span></p>\n"
    return (
        f"<p><span style=\"font-family: Tahoma;\">Name: {title}</span></p>\n"
        f"{brand_line}"
        "<p><span style=\"font-family: helvetica, arial, sans-serif;\">Category: </span>"
        "<a href=\"https://www.stockxshoesvip.net/Godspeed-Shorts/\" rel=\"noopener\" target=\"_blank\">Godspeed Clothes</a></p>\n"
        "<p><span style=\"font-family: Tahoma;\"><b>Our Core Guarantees</b></span></p>\n"
        "<ul>\n"
        "<li><b>Exclusive QC Service:</b> Free QC pictures before shipment. Approve your item or request exchange/refund.</li>\n"
        "<li><b>Premium Packaging:</b> Full brand packaging and original tags.</li>\n"
        "<li><b>Worry-Free Logistics:</b> Secure delivery and customs clearance support.</li>\n"
        "<li><b>100% Safe Shopping:</b> 30-day money-back guarantee with damage protection.</li>\n"
        "</ul>\n"
        "<p><span style=\"font-family: Tahoma;\"><b>Shipping &amp; Payment</b></span></p>\n"
        "<ul>\n"
        "<li><b>Delivery Time:</b> 7-18 Days (minor 1-3 day delays are normal). Tracking number provided.</li>\n"
        "<li><b>Shipping Methods:</b> FedEx / USPS / DHL / UPS / EMS / Royal Mail.</li>\n"
        "<li><b>Payment Methods:</b> Credit/Debit Card, PayPal, Bank Transfer, Cash App, Zelle.</li>\n"
        "</ul>\n"
        "<p><b>About StockxShoesVIP</b></p>\n"
        "<p>With 10 years of offline retail and 5 years of online excellence, we are your trusted source for <b>premium replica sneakers and streetwear</b>.</p>\n"
        "<p><i>(Note: We are an independent supplier and not affiliated with the StockX platform. Please bookmark our official site: stockxshoesvip.net)</i></p>\n"
        "<p><b>Contact Us</b></p>\n"
        "<ul>\n"
        "<li><b>WhatsApp/WeChat:</b> +86 189 5920 5893</li>\n"
        "<li><b>Instagram:</b> @stockxshoesvip_com</li>\n"
        "</ul>\n"
        "<p><i>Buy with confidence, wear with confidence.</i></p>"
    )


def _ensure_shared_string(sst_root: ET.Element, s: str, cache: dict[str, int]) -> int:
    if s in cache:
        return cache[s]
    idx = len(list(sst_root.findall("main:si", NS)))
    si = ET.Element(f"{{{NS['main']}}}si")
    t = ET.SubElement(si, f"{{{NS['main']}}}t")
    t.text = s
    sst_root.append(si)
    cache[s] = idx
    return idx


def _load_sst(work_dir: Path) -> tuple[ET.ElementTree, ET.Element, dict[str, int]]:
    sst_path = work_dir / "xl" / "sharedStrings.xml"
    tree = ET.parse(sst_path)
    root = tree.getroot()
    cache: dict[str, int] = {}
    i = 0
    for si in root.findall("main:si", NS):
        t = si.find("main:t", NS)
        if t is not None and t.text is not None:
            if t.text not in cache:
                cache[t.text] = i
            i += 1
            continue
        parts = []
        for r in si.findall("main:r", NS):
            tt = r.find("main:t", NS)
            if tt is not None and tt.text is not None:
                parts.append(tt.text)
        key = "".join(parts)
        if key not in cache:
            cache[key] = i
        i += 1
    return tree, root, cache


def _set_cell_str(row_el: ET.Element, col: str, row_num: int, sst_root: ET.Element, cache: dict[str, int], value: str, style: str | None) -> None:
    addr = f"{col}{row_num}"
    c = ET.Element(f"{{{NS['main']}}}c", {"r": addr, "t": "s"})
    if style is not None:
        c.attrib["s"] = style
    v = ET.SubElement(c, f"{{{NS['main']}}}v")
    idx = _ensure_shared_string(sst_root, value, cache)
    v.text = str(idx)
    row_el.append(c)


def _set_cell_num(row_el: ET.Element, col: str, row_num: int, value: str, style: str | None) -> None:
    addr = f"{col}{row_num}"
    c = ET.Element(f"{{{NS['main']}}}c", {"r": addr})
    if style is not None:
        c.attrib["s"] = style
    v = ET.SubElement(c, f"{{{NS['main']}}}v")
    v.text = value
    row_el.append(c)


def _style_map_for_row(sheet_data: ET.Element, row_num: int) -> dict[str, str]:
    for row in sheet_data.findall("main:row", NS):
        if row.attrib.get("r") == str(row_num):
            out: dict[str, str] = {}
            for c in row.findall("main:c", NS):
                ref = c.attrib.get("r") or ""
                m = _CELL_RE.match(ref)
                if not m:
                    continue
                col = m.group(1)
                style = c.attrib.get("s")
                if style is not None:
                    out[col] = style
            return out
    return {}


def _unpack_xlsx(xlsx_path: Path, out_dir: Path) -> None:
    if out_dir.exists():
        shutil.rmtree(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(xlsx_path, "r") as z:
        z.extractall(out_dir)


def _pack_xlsx(work_dir: Path, output_xlsx: Path) -> None:
    if output_xlsx.exists():
        output_xlsx.unlink()
    with zipfile.ZipFile(output_xlsx, "w", compression=zipfile.ZIP_DEFLATED) as z:
        for p in work_dir.rglob("*"):
            if p.is_dir():
                continue
            rel = p.relative_to(work_dir)
            z.write(p, str(rel).replace("\\", "/"))


def _sheet_xml_path(work_dir: Path, sheet_name: str) -> Path:
    wb = ET.parse(work_dir / "xl" / "workbook.xml").getroot()
    rels = ET.parse(work_dir / "xl" / "_rels" / "workbook.xml.rels").getroot()
    rid_to_target: dict[str, str] = {}
    for rel in rels.findall("pkgrel:Relationship", NS):
        rid = rel.attrib.get("Id")
        target = rel.attrib.get("Target")
        if rid and target:
            rid_to_target[rid] = target
    sheets = wb.find("main:sheets", NS)
    if sheets is None:
        raise RuntimeError("missing sheets")
    rid = None
    for s in sheets.findall("main:sheet", NS):
        if (s.attrib.get("name") or "") == sheet_name:
            rid = s.attrib.get(f"{{{NS['rel']}}}id")
            break
    if not rid:
        raise RuntimeError(f"sheet not found: {sheet_name}")
    target = rid_to_target.get(rid)
    if not target:
        raise RuntimeError(f"sheet target not found for rid: {rid}")
    return work_dir / "xl" / target.lstrip("./")


def _sort_row_cells(row_el: ET.Element) -> None:
    cells = list(row_el.findall("main:c", NS))
    for c in cells:
        row_el.remove(c)
    def _key(c: ET.Element) -> tuple[int, int]:
        ref = c.attrib.get("r") or ""
        rc = _parse_cell_ref(ref)
        if not rc:
            return (10**9, 10**9)
        return rc
    cells.sort(key=_key)
    for c in cells:
        row_el.append(c)


def _write_output(template_xlsx: Path, products: list[dict], output_xlsx: Path) -> None:
    work_dir = (output_xlsx.parent / ".dumate" / f"xlsx-{uuid.uuid4()}").resolve()
    _unpack_xlsx(template_xlsx, work_dir)

    sst_tree, sst_root, sst_cache = _load_sst(work_dir)

    sheet_path = _sheet_xml_path(work_dir, "商品信息 (2)")
    sheet_tree = ET.parse(sheet_path)
    sheet_root = sheet_tree.getroot()
    sheet_data = sheet_root.find("main:sheetData", NS)
    if sheet_data is None:
        raise RuntimeError("missing sheetData")

    main_style = _style_map_for_row(sheet_data, 4)
    sku_style = _style_map_for_row(sheet_data, 5)

    for row in list(sheet_data.findall("main:row", NS)):
        r_attr = row.attrib.get("r") or ""
        try:
            r = int(r_attr)
        except Exception:
            continue
        if r >= 4:
            sheet_data.remove(row)

    sizes = ["S", "M", "L", "XL"]
    row_num = 4
    for p in products:
        title = p["title"]
        main_img, other_imgs = _clean_images(p["main"], p["others"])

        if (
            title.strip().lower() == "alexander wang 26ss red letter t-shirt - red"
            and main_img.strip() == "http://pic.yupoo.com/lol2024/f50a04efc7/011cdcd0.jpeg"
        ):
            title = "Alexander wang 26ss red letter t-shirt Black"

        brand_key = _brand_from_title(title)
        brand = _brand_display(brand_key)
        brand_slug = _brand_slug(brand)

        seo_title = f"Stockx Replica Streetwear | Top Quality 1:1 {title} - stockxshoesvip.net"
        seo_desc = f"Buy Best 1:1 Replica Clothing on Stockxshoesvip.net. Perfect {title}. 100% safe shipping, free QC confirmation, and easy returns."
        seo_kw = f"{brand}, {title}"


        r_main = ET.Element(f"{{{NS['main']}}}row", {"r": str(row_num)})
        if title:
            _set_cell_str(r_main, "B", row_num, sst_root, sst_cache, title, main_style.get("B"))
        _set_cell_str(r_main, "D", row_num, sst_root, sst_cache, _desc_html(title, brand, brand_slug), main_style.get("D"))
        if main_img:
            _set_cell_str(r_main, "E", row_num, sst_root, sst_cache, main_img, main_style.get("E"))
        if other_imgs:
            _set_cell_str(r_main, "F", row_num, sst_root, sst_cache, other_imgs, main_style.get("F"))
        _set_cell_str(r_main, "I", row_num, sst_root, sst_cache, "N", main_style.get("I"))
        _set_cell_str(r_main, "J", row_num, sst_root, sst_cache, "Clothing", main_style.get("J"))
        if brand:
            _set_cell_str(r_main, "K", row_num, sst_root, sst_cache, brand.strip(), main_style.get("K"))
        _set_cell_str(r_main, "L", row_num, sst_root, sst_cache, title, main_style.get("L"))
        _set_cell_str(r_main, "M", row_num, sst_root, sst_cache, "件/个", main_style.get("M"))
        _set_cell_str(r_main, "O", row_num, sst_root, sst_cache, "Y", main_style.get("O"))
        _set_cell_num(r_main, "P", row_num, "0.3", main_style.get("P"))
        _set_cell_str(r_main, "T", row_num, sst_root, sst_cache, seo_title, main_style.get("T"))
        _set_cell_str(r_main, "U", row_num, sst_root, sst_cache, seo_desc, main_style.get("U"))
        _set_cell_str(r_main, "V", row_num, sst_root, sst_cache, seo_kw, main_style.get("V"))

        _set_cell_str(r_main, "Y", row_num, sst_root, sst_cache, "Size\nS\nM\nL\nXL", main_style.get("Y"))
        _set_cell_str(r_main, "AB", row_num, sst_root, sst_cache, f"Size:{sizes[0]}", main_style.get("AB"))
        _set_cell_num(r_main, "AD", row_num, "59", main_style.get("AD"))
        _set_cell_num(r_main, "AE", row_num, "99", main_style.get("AE"))
        _set_cell_num(r_main, "AF", row_num, "999", main_style.get("AF"))

        _sort_row_cells(r_main)
        sheet_data.append(r_main)
        row_num += 1

        for sz in sizes[1:]:
            r_sku = ET.Element(f"{{{NS['main']}}}row", {"r": str(row_num)})
            _set_cell_str(r_sku, "AB", row_num, sst_root, sst_cache, f"Size:{sz}", sku_style.get("AB"))
            _set_cell_num(r_sku, "AD", row_num, "59", sku_style.get("AD"))
            _set_cell_num(r_sku, "AE", row_num, "99", sku_style.get("AE"))
            _set_cell_num(r_sku, "AF", row_num, "999", sku_style.get("AF"))
            _sort_row_cells(r_sku)
            sheet_data.append(r_sku)
            row_num += 1

    sst_root.attrib["count"] = str(len(list(sst_root.findall("main:si", NS))))
    sst_root.attrib["uniqueCount"] = sst_root.attrib["count"]

    sst_tree.write(work_dir / "xl" / "sharedStrings.xml", encoding="utf-8", xml_declaration=True)
    sheet_tree.write(sheet_path, encoding="utf-8", xml_declaration=True)

    _purge_unused_shared_strings(work_dir)
    _pack_xlsx(work_dir, output_xlsx)


def _purge_unused_shared_strings(work_dir: Path) -> None:
    sst_path = work_dir / "xl" / "sharedStrings.xml"
    sst_tree = ET.parse(sst_path)
    sst_root = sst_tree.getroot()
    sis = list(sst_root.findall("main:si", NS))
    if not sis:
        return

    ws_dir = work_dir / "xl" / "worksheets"
    ws_files = sorted(ws_dir.glob("sheet*.xml"))
    if not ws_files:
        return

    used: set[int] = set()
    for ws_file in ws_files:
        ws_root = ET.parse(ws_file).getroot()
        for c in ws_root.findall(".//main:c", NS):
            if c.attrib.get("t") != "s":
                continue
            v = c.find("main:v", NS)
            if v is None or v.text is None:
                continue
            try:
                used.add(int(v.text))
            except Exception:
                continue

    used_sorted = [i for i in sorted(used) if 0 <= i < len(sis)]
    mapping = {old: new for new, old in enumerate(used_sorted)}

    for ws_file in ws_files:
        ws_tree = ET.parse(ws_file)
        ws_root = ws_tree.getroot()
        changed = False
        for c in ws_root.findall(".//main:c", NS):
            if c.attrib.get("t") != "s":
                continue
            v = c.find("main:v", NS)
            if v is None or v.text is None:
                continue
            try:
                old = int(v.text)
            except Exception:
                continue
            if old in mapping:
                v.text = str(mapping[old])
                changed = True
        if changed:
            ws_tree.write(ws_file, encoding="utf-8", xml_declaration=True)

    new_sst = ET.Element(f"{{{NS['main']}}}sst")
    for old in used_sorted:
        new_sst.append(copy.deepcopy(sis[old]))
    new_sst.attrib["count"] = str(len(used_sorted))
    new_sst.attrib["uniqueCount"] = new_sst.attrib["count"]

    ET.ElementTree(new_sst).write(sst_path, encoding="utf-8", xml_declaration=True)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", required=True, type=str)
    ap.add_argument("--template", required=True, type=str)
    ap.add_argument("--output", required=False, type=str)
    ap.add_argument("--output-unique", required=False, type=str)
    ap.add_argument("--output-duplicates", required=False, type=str)
    args = ap.parse_args()

    inp = Path(args.input)
    tpl = Path(args.template)
    outp = Path(args.output) if args.output else None
    out_unique = Path(args.output_unique) if args.output_unique else None
    out_dups = Path(args.output_duplicates) if args.output_duplicates else None
    if not outp and not (out_unique and out_dups):
        raise SystemExit(2)
    if outp:
        outp.parent.mkdir(parents=True, exist_ok=True)
    if out_unique:
        out_unique.parent.mkdir(parents=True, exist_ok=True)
    if out_dups:
        out_dups.parent.mkdir(parents=True, exist_ok=True)

    products = _read_input_products(inp)
    if not products:
        raise SystemExit(2)

    if outp:
        _write_output(tpl, products, outp)
        return 0

    uniq, dups = _split_products_by_dup_title(products)
    uniq = _apply_title_rules(uniq, use_image_color_for_dups=False)
    dups = _apply_title_rules(dups, use_image_color_for_dups=True)
    _write_output(tpl, uniq, out_unique)
    _write_output(tpl, dups, out_dups)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
