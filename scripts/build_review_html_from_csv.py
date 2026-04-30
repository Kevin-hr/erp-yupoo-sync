#!/usr/bin/env python3
import argparse
import csv
import html
import json
from pathlib import Path


def _read_csv(path: Path) -> list[dict]:
    for enc in ["utf-8-sig", "gb18030", "utf-8", "cp1252", "latin-1"]:
        try:
            with path.open("r", encoding=enc, newline="") as f:
                return list(csv.DictReader(f))
        except UnicodeDecodeError:
            continue
    raise RuntimeError(f"cannot decode csv: {path}")


HTML_TEMPLATE = """<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>{title}</title>
  <style>
    body {{ font-family: system-ui, -apple-system, Segoe UI, Roboto, Helvetica, Arial, "PingFang SC", "Microsoft YaHei", sans-serif; margin: 16px; }}
    .topbar {{ display: flex; gap: 8px; align-items: center; flex-wrap: wrap; margin-bottom: 12px; }}
    .note {{ color: #333; font-size: 13px; line-height: 1.5; }}
    table {{ border-collapse: collapse; width: 100%; table-layout: fixed; }}
    th, td {{ border: 1px solid #ddd; padding: 8px; vertical-align: top; }}
    th {{ background: #f6f6f6; font-weight: 600; }}
    .col-no {{ width: 52px; }}
    .col-img {{ width: 160px; }}
    .col-en {{ width: 360px; }}
    .col-color {{ width: 220px; }}
    .col-cn {{ width: 360px; }}
    img {{ width: 140px; height: 140px; object-fit: cover; background: #fafafa; border: 1px solid #eee; }}
    input[type="text"] {{ width: 100%; box-sizing: border-box; padding: 6px 8px; }}
    select {{ width: 100%; box-sizing: border-box; padding: 6px 8px; }}
    textarea {{ width: 100%; box-sizing: border-box; padding: 6px 8px; height: 72px; }}
    .tag {{ display: inline-block; padding: 2px 6px; border-radius: 10px; font-size: 12px; }}
    .ok {{ background: #e6ffed; color: #167a2e; }}
    .bad {{ background: #ffecec; color: #b42318; }}
    .muted {{ color: #666; font-size: 12px; }}
    .btn {{ padding: 8px 12px; border: 1px solid #ccc; background: #fff; cursor: pointer; border-radius: 6px; }}
    .btn.primary {{ border-color: #1a73e8; color: #1a73e8; }}
    .btn:active {{ transform: translateY(1px); }}
    .search {{ flex: 1; min-width: 220px; }}
    .panel {{ position: fixed; left: 16px; right: 16px; bottom: 16px; z-index: 9999; border: 1px solid #ddd; border-radius: 8px; overflow: hidden; background: #fff; box-shadow: 0 10px 30px rgba(0,0,0,0.12); }}
    .panel-hd {{ background: #f6f6f6; padding: 8px 10px; display: flex; gap: 8px; align-items: center; flex-wrap: wrap; }}
    .panel-bd {{ padding: 8px 10px; }}
    .out {{ width: 100%; height: min(45vh, 420px); box-sizing: border-box; font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", monospace; }}
    .hidden {{ display: none; }}
  </style>
</head>
<body>
  <div class="topbar">
    <button class="btn primary" id="btnExportJson">导出 JSON（给我）</button>
    <button class="btn primary" id="btnExportCsv">导出 CSV（覆盖B列/颜色结论）</button>
    <button class="btn" id="btnShowJson">在页面显示 JSON（可复制）</button>
    <button class="btn" id="btnShowCsv">在页面显示 CSV（可复制）</button>
    <label class="btn">
      导入 JSON（继续上次修改）
      <input type="file" id="fileImport" accept=".json" style="display:none" />
    </label>
    <input class="search" id="search" placeholder="搜索：英文名 / 中文名 / album_id" />
    <span class="muted" id="stat"></span>
  </div>

  <div class="note">
    <div>使用方法：</div>
    <div>1）逐行看 D 列首图 + B 列英文名；2）如果颜色不对：把“颜色正确”改成“不正确”，并在“正确颜色”选择正确值；3）如果英文名不对：直接改“英文名”；4）改完点击“导出 JSON”，把导出的文件发我。</div>
    <div>字段说明：颜色判断只看“首图主色”；如果你希望按“实物颜色”修正，就用“正确颜色”覆盖。</div>
  </div>

  <table id="tbl">
    <thead>
      <tr>
        <th class="col-no">No</th>
        <th class="col-img">首图</th>
        <th class="col-en">英文名（可改）</th>
        <th class="col-color">颜色审查</th>
        <th class="col-cn">中文名/备注</th>
      </tr>
    </thead>
    <tbody id="tbody">
      {rows_html}
    </tbody>
  </table>

  <div class="panel hidden" id="panel">
    <div class="panel-hd">
      <span class="muted" id="panelTitle"></span>
      <button class="btn" id="btnCopy">复制</button>
      <button class="btn" id="btnSelect">全选</button>
      <button class="btn" id="btnClose">关闭</button>
    </div>
    <div class="panel-bd">
      <textarea class="out" id="out" spellcheck="false"></textarea>
    </div>
  </div>

  <script>
    const COLORS = ["", "Black", "White", "Gray", "Red", "Blue", "Green", "Yellow", "Brown", "Multicolor"];

    function detectColorFromName(name) {{
      const s = (name || "").trim();
      const parts = s.split(/\\s+/).filter(Boolean);
      const last = parts.length ? parts[parts.length - 1] : "";
      return COLORS.includes(last) ? last : "";
    }}

    function refreshRow(tr) {{
      const en = tr.querySelector("input.en");
      const okSel = tr.querySelector("select.ok");
      const colorSel = tr.querySelector("select.color");
      const badge = tr.querySelector(".tag");
      const hint = tr.querySelector(".hint");

      const detected = detectColorFromName(en.value || "");
      hint.textContent = `检测颜色(来自B末尾)：${{detected}}`;

      const ok = okSel.value === "true";
      badge.className = "tag " + (ok ? "ok" : "bad");
      if (ok) {{
        badge.textContent = "已确认：颜色正确";
      }} else {{
        const c = (colorSel.value || "").trim();
        badge.textContent = c ? `需要修正：正确颜色=${{c}}` : "需要修正：请选正确颜色";
      }}
    }}

    function refreshStat() {{
      const rows = Array.from(document.querySelectorAll("#tbody tr"));
      const total = rows.length;
      const bad = rows.filter(tr => (tr.querySelector("select.ok")?.value || "true") === "false").length;
      const ok = total - bad;
      document.getElementById("stat").textContent = `总数=${{total}} | 颜色正确=${{ok}} | 颜色不正确=${{bad}}`;
    }}

    function exportJson() {{
      const text = buildJsonText();
      downloadText(text, "application/json", "{export_json_name}");
      showPanel("JSON（复制后发我）", text);
    }}

    function exportCsv() {{
      const text = buildCsvText();
      downloadText("\\ufeff" + text, "text/csv;charset=utf-8", "{export_csv_name}");
      showPanel("CSV（复制后发我）", text);
    }}

    function getRowsData() {{
      const out = [];
      const rows = Array.from(document.querySelectorAll("#tbody tr"));
      for (const tr of rows) {{
        const A = tr.dataset.a || tr.querySelector("td")?.textContent?.trim() || "";
        const B = tr.querySelector("input.en")?.value || "";
        const C = tr.querySelector("textarea.cn")?.value || "";
        const D = tr.querySelector("img")?.getAttribute("src") || "";
        const E = tr.querySelector("textarea.other")?.value || "";
        const album_id = tr.dataset.albumId || "";
        const detected_color = detectColorFromName(B);
        const color_ok = (tr.querySelector("select.ok")?.value || "true") === "true";
        const correct_color = tr.querySelector("select.color")?.value || "";
        out.push({{ A, B, C, D, E, album_id, detected_color, color_ok, correct_color }});
      }}
      return out;
    }}

    function buildJsonText() {{
      return JSON.stringify(getRowsData(), null, 2);
    }}

    function buildCsvText() {{
      const headers = ["A","B","C","D","E","album_id","detected_color","color_ok","correct_color"];
      const lines = [];
      lines.push(headers.join(","));
      for (const x of getRowsData()) {{
        const row = headers.map(h => {{
          const v = (x[h] ?? "").toString();
          const s = v.replace(/\"/g,"\"\"");
          return `"${{s}}"`;
        }}).join(",");
        lines.push(row);
      }}
      return lines.join("\\n");
    }}

    function downloadText(text, mime, filename) {{
      try {{
        const blob = new Blob([text], {{type: mime}});
        const a = document.createElement("a");
        a.href = URL.createObjectURL(blob);
        a.download = filename;
        a.click();
        URL.revokeObjectURL(a.href);
      }} catch (e) {{
      }}
    }}

    function showPanel(title, text) {{
      const panel = document.getElementById("panel");
      panel.classList.remove("hidden");
      document.getElementById("panelTitle").textContent = title;
      const out = document.getElementById("out");
      out.value = text;
      out.focus();
      out.setSelectionRange(0, out.value.length);
    }}

    async function copyOut() {{
      const out = document.getElementById("out");
      const text = out.value || "";
      try {{
        await navigator.clipboard.writeText(text);
      }} catch (e) {{
      }}
      out.focus();
      out.setSelectionRange(0, out.value.length);
    }}

    function selectOut() {{
      const out = document.getElementById("out");
      out.focus();
      out.setSelectionRange(0, out.value.length);
    }}

    document.getElementById("btnExportJson").addEventListener("click", exportJson);
    document.getElementById("btnExportCsv").addEventListener("click", exportCsv);
    document.getElementById("btnShowJson").addEventListener("click", () => showPanel("JSON（复制后发我）", buildJsonText()));
    document.getElementById("btnShowCsv").addEventListener("click", () => showPanel("CSV（复制后发我）", buildCsvText()));
    document.getElementById("btnCopy").addEventListener("click", copyOut);
    document.getElementById("btnSelect").addEventListener("click", selectOut);
    document.getElementById("btnClose").addEventListener("click", () => document.getElementById("panel").classList.add("hidden"));
    document.getElementById("fileImport").addEventListener("change", async (ev) => {{
      const file = ev.target.files && ev.target.files[0];
      if (!file) return;
      const text = await file.text();
      const arr = JSON.parse(text);
      if (!Array.isArray(arr)) return;
      const rows = Array.from(document.querySelectorAll("#tbody tr"));
      for (let i = 0; i < Math.min(rows.length, arr.length); i++) {{
        const src = arr[i] || {{}};
        const tr = rows[i];
        if (src.B !== undefined) tr.querySelector("input.en").value = src.B;
        if (src.C !== undefined) tr.querySelector("textarea.cn").value = src.C;
        if (src.color_ok !== undefined) tr.querySelector("select.ok").value = String(!!src.color_ok);
        if (src.correct_color !== undefined) tr.querySelector("select.color").value = src.correct_color || "";
        refreshRow(tr);
      }}
      refreshStat();
    }});

    document.getElementById("search").addEventListener("input", (ev) => {{
      const q = (ev.target.value || "").trim().toLowerCase();
      const tbody = document.getElementById("tbody");
      for (const tr of tbody.children) {{
        const hay = `${{tr.querySelector("input.en")?.value || ""}} ${{tr.querySelector("textarea.cn")?.value || ""}} ${{tr.dataset.albumId || ""}}`.toLowerCase();
        tr.style.display = q && !hay.includes(q) ? "none" : "";
      }}
    }});

    window.addEventListener("error", (ev) => {{
      const msg = (ev && ev.message) ? ev.message : "unknown_error";
      document.getElementById("stat").textContent = `页面脚本错误：${{msg}}`;
    }});

    for (const tr of document.querySelectorAll("#tbody tr")) {{
      tr.querySelector("input.en").addEventListener("input", () => {{ refreshRow(tr); refreshStat(); }});
      tr.querySelector("select.ok").addEventListener("change", () => {{ refreshRow(tr); refreshStat(); }});
      tr.querySelector("select.color").addEventListener("change", () => {{ refreshRow(tr); refreshStat(); }});
      tr.querySelector("textarea.cn").addEventListener("input", () => {{ refreshStat(); }});
      refreshRow(tr);
    }}
    refreshStat();
  </script>
</body>
</html>
"""


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", required=True, type=str)
    ap.add_argument("--output", required=True, type=str)
    args = ap.parse_args()

    inp = Path(args.input)
    out = Path(args.output)
    rows = _read_csv(inp)

    color_options = "".join(
        [
            '<option value="">（空）</option>',
            '<option value="Black">Black</option>',
            '<option value="White">White</option>',
            '<option value="Gray">Gray</option>',
            '<option value="Red">Red</option>',
            '<option value="Blue">Blue</option>',
            '<option value="Green">Green</option>',
            '<option value="Yellow">Yellow</option>',
            '<option value="Brown">Brown</option>',
            '<option value="Multicolor">Multicolor</option>',
        ]
    )

    rows_html_parts = []
    for idx, r in enumerate(rows, start=1):
        a = (r.get("A") or str(idx)).strip() or str(idx)
        b = (r.get("B") or "").strip()
        c = (r.get("C") or "").strip()
        d = (r.get("D") or "").strip()
        e = (r.get("E") or "").strip()
        album_id = (r.get("album_id") or "").strip()

        rows_html_parts.append(
            "\n".join(
                [
                    f'<tr data-a="{html.escape(a)}" data-album-id="{html.escape(album_id)}">',
                    f"  <td>{html.escape(a)}</td>",
                    "  <td>",
                    f'    <a href="{html.escape(d)}" target="_blank"><img loading="lazy" referrerpolicy="no-referrer" src="{html.escape(d)}" /></a>',
                    "  </td>",
                    "  <td>",
                    f'    <input class="en" type="text" value="{html.escape(b)}" />',
                    f'    <div class="muted">album_id={html.escape(album_id)}</div>',
                    "  </td>",
                    "  <td>",
                    '    <select class="ok"><option value="true">颜色正确</option><option value="false">颜色不正确</option></select>',
                    f'    <select class="color">{color_options}</select>',
                    '    <div class="tag" style="margin-top:6px"></div>',
                    '    <div class="muted hint" style="margin-top:6px"></div>',
                    "  </td>",
                    "  <td>",
                    f"    <textarea class=\"cn\">{html.escape(c)}</textarea>",
                    f"    <textarea class=\"other\" style=\"display:none\">{html.escape(e)}</textarea>",
                    "  </td>",
                    "</tr>",
                ]
            )
        )
    rows_html = "\n".join(rows_html_parts)

    out.parent.mkdir(parents=True, exist_ok=True)
    html_text = HTML_TEMPLATE.format(
        title=html.escape(out.name),
        rows_html=rows_html,
        export_json_name=html.escape(out.with_suffix(".feedback.json").name),
        export_csv_name=html.escape(out.with_suffix(".feedback.csv").name),
    )
    out.write_text(html_text, encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
