"""Catalog page: every catalog of an area as one searchable web page – for people who never open a Markdown file.

`aichivist catalog-page ~/Cloud/Personal --open` writes a single HTML file into aichivist's own folder (not into the
area) and opens it. Typing filters all rows at once; file names open the document. Nothing leaves the computer.
"""
import html
import os
import re
import webbrowser
from pathlib import Path
from typing import List, NamedTuple, Optional

from . import config
from .catalog import CATALOG_NAMES, SEPARATOR, resolve
from .config import full_path
from .i18n import language, t


class Table(NamedTuple):
    folder: str            # the heading above the table, else the catalog's folder relative to the area
    header: List[str]
    rows: List[List[str]]  # first cell: file path relative to the catalog's folder
    base: Path             # the catalog's folder, for links


def _cells(line: str) -> List[str]:
    return [c.strip().strip("`").strip() for c in line.strip().strip("|").split("|")]


def read_tables(catalog_file: Path, area: Path) -> List[Table]:
    tables: List[Table] = []
    header: Optional[List[str]] = None
    base, section = catalog_file.parent, ""
    for line in catalog_file.read_text(encoding="utf-8").splitlines():
        if line.startswith("## "):
            section = line[3:].strip()
        if not line.lstrip().startswith("|"):
            header = None
            continue
        cells = _cells(line)
        if all(SEPARATOR.match(c) for c in cells if c):
            continue
        if header is None:
            header = cells
            tables.append(Table(section or base.relative_to(area).as_posix(), header, [], base))
        elif cells and cells[0]:
            tables[-1].rows.append([resolve(base, section, cells[0]), *cells[1:]])
    return tables


def find_catalogs(area: Path) -> List[Path]:
    found = []
    for dirpath, dirnames, filenames in os.walk(area):
        dirnames[:] = sorted(d for d in dirnames if not d.startswith("."))
        found += [Path(dirpath) / f for f in sorted(filenames) if f.lower() in CATALOG_NAMES]
    return found


PAGE = """<!doctype html><html lang="__LANG__"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>__TITLE__</title><style>
:root{--bg:#fff;--fg:#24292f;--muted:#57606a;--line:#d0d7de;--soft:#f6f8fa;--accent:#1a7f37}
@media (prefers-color-scheme:dark){:root{--bg:#0d1117;--fg:#e6edf3;--muted:#8b949e;--line:#30363d;--soft:#161b22;
--accent:#7ee787}}
body{margin:0;background:var(--bg);color:var(--fg);font:15px/1.5 -apple-system,Segoe UI,Helvetica,Arial,sans-serif}
main{max-width:1100px;margin:0 auto;padding:24px 16px}h1{margin:0 0 4px}p.sub{color:var(--muted);margin:0 0 16px}
input{width:100%;box-sizing:border-box;padding:12px 14px;font-size:16px;border:1px solid var(--line);
border-radius:10px;background:var(--soft);color:var(--fg)}
h2{font-size:15px;color:var(--muted);margin:28px 0 8px}.wrap{overflow-x:auto}
table{border-collapse:collapse;width:100%}th,td{text-align:left;padding:6px 10px;border-bottom:1px solid var(--line);
vertical-align:top}th{background:var(--soft);font-weight:600}a{color:var(--accent)}
.count{color:var(--muted);margin:10px 0 0}</style></head><body><main>
<h1>__TITLE__</h1><p class="sub">__SUBTITLE__</p>
<input id="q" type="search" placeholder="__SEARCH__" autofocus>
<p class="count" id="count"></p>__TABLES__</main><script>
const fold=s=>s.normalize("NFD").replace(/[\\u0300-\\u036f]/g,"").toLowerCase();
const rows=[...document.querySelectorAll("tbody tr")];rows.forEach(r=>r.dataset.t=fold(r.textContent));
function filter(){const words=fold(document.getElementById("q").value).split(/\\s+/).filter(Boolean);let n=0;
rows.forEach(r=>{const hit=words.every(w=>r.dataset.t.includes(w));r.hidden=!hit;if(hit)n++});
document.querySelectorAll("section").forEach(s=>s.hidden=!s.querySelector("tbody tr:not([hidden])"));
document.getElementById("count").textContent="__COUNT__".replace("{n}",n).replace("{total}",rows.length);}
document.getElementById("q").addEventListener("input",filter);filter();</script></body></html>
"""


def _cell(table: Table, i: int, value: str) -> str:
    text = html.escape(value)
    if i == 0:
        target = table.base / value.rstrip("/")
        if target.exists():
            return f'<a href="{html.escape(target.as_uri())}">{text}</a>'
    return text


def render(area, tables: List[Table]) -> str:
    root = full_path(area)
    sections = []
    for table in tables:
        head = "".join(f"<th>{html.escape(h)}</th>" for h in table.header)
        body = "".join("<tr>" + "".join(f"<td>{_cell(table, i, c)}</td>" for i, c in enumerate(r)) + "</tr>"
                       for r in table.rows)
        title = root.name if table.folder == "." else table.folder
        sections.append(f'<section><h2>{html.escape(title)}</h2><div class="wrap"><table><thead><tr>{head}</tr>'
                        f"</thead><tbody>{body}</tbody></table></div></section>")
    entries = sum(len(table.rows) for table in tables)
    subtitle = t("{entries} entries from {catalogs} catalog(s) in {area}", entries=entries,
                 catalogs=len({table.base for table in tables}), area=root)
    parts = {"__LANG__": language(), "__TITLE__": html.escape(t("Catalog – {area}", area=root.name)),
             "__SUBTITLE__": html.escape(subtitle), "__SEARCH__": html.escape(t("Search: issuer, subject, year …")),
             "__COUNT__": t("{n} of {total} entries").replace('"', ""), "__TABLES__": "".join(sections)}
    page = PAGE
    for key, value in parts.items():
        page = page.replace(key, value)
    return page


def default_target(area) -> Path:
    name = re.sub(r"[^\w .-]", "_", full_path(area).name) or "catalog"
    return config.home_dir() / "pages" / f"{name}.html"


def write(area, target=None, open_page: bool = False) -> Path:
    root = full_path(area)
    tables = [t for c in find_catalogs(root) for t in read_tables(c, root)]
    out = full_path(target) if target else default_target(root)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(render(root, tables), encoding="utf-8")
    if open_page:
        webbrowser.open(out.as_uri())
    return out
