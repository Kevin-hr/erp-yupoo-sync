import argparse
import json
import re
import zipfile
from dataclasses import dataclass
from pathlib import Path
from xml.etree import ElementTree as ET


NS = {
    "main": "http://schemas.openxmlformats.org/spreadsheetml/2006/main",
    "rel": "http://schemas.openxmlformats.org/officeDocument/2006/relationships",
    "pkgrel": "http://schemas.openxmlformats.org/package/2006/relationships",
}


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


_CELL_RE = re.compile(r"^([A-Z]+)(\d+)$")


def _parse_cell_ref(r: str) -> tuple[int, int] | None:
    m = _CELL_RE.match(r or "")
    if not m:
        return None
    return int(m.group(2)), _col_to_index(m.group(1))


def _load_shared_strings(z: zipfile.ZipFile) -> list[str]:
    try:
        xml = z.read("xl/sharedStrings.xml")
    except KeyError:
        return []
    root = ET.fromstring(xml)
    out: list[str] = []
    for si in root.findall("main:si", NS):
        t = si.find("main:t", NS)
        if t is not None and t.text is not None:
            out.append(t.text)
            continue
        parts = []
        for r in si.findall("main:r", NS):
            tt = r.find("main:t", NS)
            if tt is not None and tt.text is not None:
                parts.append(tt.text)
        out.append("".join(parts))
    return out


@dataclass(frozen=True)
class SheetInfo:
    name: str
    sheet_id: str
    rid: str
    path: str


def _sheet_infos(z: zipfile.ZipFile) -> list[SheetInfo]:
    wb = ET.fromstring(z.read("xl/workbook.xml"))
    rels = ET.fromstring(z.read("xl/_rels/workbook.xml.rels"))
    rid_to_target: dict[str, str] = {}
    for rel in rels.findall("pkgrel:Relationship", NS):
        rid = rel.attrib.get("Id")
        target = rel.attrib.get("Target")
        if rid and target:
            rid_to_target[rid] = target
    infos: list[SheetInfo] = []
    sheets = wb.find("main:sheets", NS)
    if sheets is None:
        return infos
    for s in sheets.findall("main:sheet", NS):
        name = s.attrib.get("name") or ""
        sheet_id = s.attrib.get("sheetId") or ""
        rid = s.attrib.get(f"{{{NS['rel']}}}id") or ""
        target = rid_to_target.get(rid) or ""
        target = target.lstrip("/")
        if target and not target.startswith("xl/"):
            target = "xl/" + target.lstrip("./")
        infos.append(SheetInfo(name=name, sheet_id=sheet_id, rid=rid, path=target))
    return infos


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


def _extract_rows(z: zipfile.ZipFile, sheet_path: str, sst: list[str], max_rows: int, max_cols: int) -> dict:
    root = ET.fromstring(z.read(sheet_path))
    sheet_data = root.find("main:sheetData", NS)
    rows_out: list[dict[str, str]] = []
    max_r = 0
    max_c = 0
    if sheet_data is None:
        return {"rows": rows_out, "max_row": 0, "max_col": 0}
    for row in sheet_data.findall("main:row", NS):
        r_attr = row.attrib.get("r")
        try:
            r = int(r_attr) if r_attr else 0
        except Exception:
            r = 0
        if r <= 0:
            continue
        if r > max_rows:
            continue
        row_map: dict[str, str] = {}
        for c in row.findall("main:c", NS):
            ref = c.attrib.get("r")
            rc = _parse_cell_ref(ref or "")
            if not rc:
                continue
            rr, cc = rc
            if cc > max_cols:
                continue
            txt = _cell_text(c, sst)
            if txt != "":
                row_map[_index_to_col(cc)] = txt
                max_r = max(max_r, rr)
                max_c = max(max_c, cc)
        if row_map:
            rows_out.append({"r": str(r), "cells": row_map})
    return {"rows": rows_out, "max_row": max_r, "max_col": max_c}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("input", type=str)
    ap.add_argument("--out", type=str, required=True)
    ap.add_argument("--rows", type=int, default=60)
    ap.add_argument("--cols", type=int, default=40)
    args = ap.parse_args()

    inp = Path(args.input)
    outp = Path(args.out)
    outp.parent.mkdir(parents=True, exist_ok=True)

    with zipfile.ZipFile(inp, "r") as z:
        sst = _load_shared_strings(z)
        infos = _sheet_infos(z)
        sheets: list[dict] = []
        for info in infos:
            payload = _extract_rows(z, info.path, sst, max_rows=args.rows, max_cols=args.cols)
            sheets.append(
                {
                    "name": info.name,
                    "sheetId": info.sheet_id,
                    "rid": info.rid,
                    "path": info.path,
                    **payload,
                }
            )
        data = {"input": str(inp), "sheets": sheets}

    outp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
