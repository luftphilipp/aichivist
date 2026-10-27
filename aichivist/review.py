"""Review a filing plan in the browser: one row per file with a checkbox and a link to open the document.

`aichivist plan review plan.md` starts a small page on 127.0.0.1 (only this computer), approves the ticked rows when
the person clicks the button, and stops. Applying stays a separate step.
"""
import html
import threading
import webbrowser
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from typing import List
from urllib.parse import parse_qs

from . import plan
from .i18n import language, t

STYLE = (
    "body{font:15px -apple-system,Segoe UI,Helvetica,Arial,sans-serif;margin:32px;color:#24292f;max-width:1100px}"
    "h1{font-size:22px}table{border-collapse:collapse;width:100%}"
    "td,th{padding:10px;border-bottom:1px solid #d0d7de;text-align:left;vertical-align:top}"
    ".old{color:#57606a}.new{color:#1a7f37;font-weight:600}.trash{color:#cf222e;font-weight:600}"
    ".folder,.reason{color:#57606a;font-size:13px}"
    "button{margin-top:20px;padding:10px 22px;font-size:15px;background:#1a7f37;color:#fff;border:0;"
    "border-radius:8px;cursor:pointer}"
)
PAGE = (
    '<!doctype html><html lang="{lang}"><meta charset="utf-8"><title>aichivist – {title}</title>'
    "<style>" + STYLE + "</style><h1>{heading}</h1><p>{intro}</p>"
    '<form method="post"><table><tr><th></th><th>{document}</th><th>{target}</th><th>{why}</th></tr>'
    '{rows}</table><button type="submit">{button}</button></form></html>'
)
DONE = (
    '<!doctype html><html><meta charset="utf-8">'
    '<body style="font:16px -apple-system,Segoe UI,sans-serif;margin:40px"><h2>{heading}</h2><p>{text}</p>'
    "</body></html>"
)


def _fill(page: str, **parts: str) -> str:
    """str.replace instead of str.format: the CSS is full of braces."""
    for key, value in parts.items():
        page = page.replace("{" + key + "}", value)
    return page

def _short(folder: Path) -> str:
    home = str(Path.home())
    return "~" + str(folder)[len(home):] if str(folder).startswith(home) else str(folder)


def _row(i: int, row: plan.Row) -> str:
    src = Path(row.source)
    if row.target == plan.TRASH:
        target = f'<span class="trash">{t("Trash")}</span>'
    else:
        dst = Path(row.target)
        target = (f'<span class="new">{html.escape(dst.name)}</span><br>'
                  f'<span class="folder">{html.escape(_short(dst.parent))}</span>')
    return (f'<tr><td><input type="checkbox" name="row" value="{i}" checked></td>'
            f'<td><a class="old" href="{html.escape(src.as_uri())}">{html.escape(src.name)}</a></td>'
            f'<td>{target}</td><td class="reason">{html.escape(row.reason)}</td></tr>')


def render(plan_file) -> str:
    proposed = [(i, r) for i, r in enumerate(plan.read(plan_file), 1) if r.mark == "?"]
    rows = "\n".join(_row(i, r) for i, r in proposed)
    return _fill(PAGE, lang=language(), title=t("review plan"),
                 heading=html.escape(t("Filing plan – {n} proposals", n=len(proposed))),
                 intro=html.escape(t("Untick what you do not want. Nothing moves before you confirm here and the plan "
                                     "is applied.")),
                 document=t("Document"), target=t("New name and place"), why=t("Why"),
                 button=t("Approve ticked rows"), rows=rows)


def done_page(n: int) -> str:
    return _fill(DONE, heading=html.escape(t("{n} rows approved.", n=n)),
                 text=t("You can close this tab. Tell your AI to apply the plan (or run <code>aichivist plan "
                        "apply</code>)."))


def approve_from_form(plan_file, body: str) -> int:
    rows = [int(v) for v in parse_qs(body).get("row", []) if v.isdigit()]
    return plan.approve(plan_file, rows) if rows else 0


def serve(plan_file, open_browser: bool = True, block: bool = True) -> str:
    """Start the review page; returns its URL. With block=True, returns after the person submitted the form."""
    plan_file = Path(plan_file)
    result: List[int] = []

    class Handler(BaseHTTPRequestHandler):
        def _send(self, text: str) -> None:
            data = text.encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        def do_GET(self) -> None:  # noqa: N802 (http.server API)
            self._send(render(plan_file))

        def do_POST(self) -> None:  # noqa: N802
            body = self.rfile.read(int(self.headers.get("Content-Length", 0))).decode("utf-8")
            result.append(approve_from_form(plan_file, body))
            self._send(done_page(result[-1]))
            threading.Thread(target=server.shutdown, daemon=True).start()

        def log_message(self, *args) -> None:  # keep the terminal quiet
            pass

    server = HTTPServer(("127.0.0.1", 0), Handler)
    url = f"http://127.0.0.1:{server.server_address[1]}/"
    if open_browser:
        webbrowser.open(url)
    if block:
        server.serve_forever()
        server.server_close()
    else:
        threading.Thread(target=server.serve_forever, daemon=True).start()
    return url

