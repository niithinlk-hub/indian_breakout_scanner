"""Read-only status site (stockbreak.up.railway.app): build status and the committed
reports rendered as static HTML. No data access, no compute at request time.

`build_site` renders the pages once (at image build time); `serve` answers only the
known paths from memory, so nothing on disk is ever exposed by URL.
"""

from __future__ import annotations

import html
import logging
import re
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import markdown

LOGGER = logging.getLogger(__name__)

REPORTS = {
    "step1.html": ("reports/step1_data_report.md", "Step 1: data layer and QA"),
    "step2.html": ("reports/step2_baserate.md", "Step 2: base-rate study"),
}
LINK_MAP = {
    "reports/step1_data_report.md": "step1.html",
    "reports/step2_baserate.md": "step2.html",
    "reports/": "index.html",
}

CSS = """
:root { --bg:#ffffff; --fg:#1b1f24; --muted:#59636e; --line:#d8dee4; --head:#f3f5f7; --accent:#0b5cad;
        --note-bg:#fff8e6; --note-line:#e6c36a; }
@media (prefers-color-scheme: dark) {
  :root { --bg:#0f1217; --fg:#e6e9ed; --muted:#9aa4af; --line:#2c333b; --head:#171c22; --accent:#6cb0ff;
          --note-bg:#2a2412; --note-line:#8a6d1f; }
}
* { box-sizing: border-box; }
body { margin: 0; background: var(--bg); color: var(--fg);
       font: 15px/1.55 -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif; }
main { max-width: 1120px; margin: 0 auto; padding: 20px 16px 48px; }
nav { font-size: 14px; margin-bottom: 8px; }
nav a { margin-right: 14px; }
a { color: var(--accent); }
h1 { font-size: 1.6rem; margin: 0.4em 0 0.6em; }
h2 { font-size: 1.2rem; margin: 1.8em 0 0.6em; padding-top: 0.6em; border-top: 1px solid var(--line); }
code { font-size: 0.9em; background: var(--head); padding: 1px 4px; border-radius: 4px; }
.note { background: var(--note-bg); border: 1px solid var(--note-line); border-radius: 8px; padding: 10px 14px; }
.table-wrap { overflow-x: auto; margin: 0.8em 0; }
table { border-collapse: collapse; font-size: 13px; min-width: 60%; }
th, td { border: 1px solid var(--line); padding: 4px 8px; text-align: left; white-space: nowrap; }
th { background: var(--head); }
.wrap-cells td { white-space: normal; }
details { margin: 0.8em 0; }
summary { cursor: pointer; color: var(--accent); }
footer { margin-top: 3em; color: var(--muted); font-size: 13px; }
"""


def render_markdown(text: str) -> str:
    """Markdown -> HTML; markdown inside <details> is rendered; tables scroll sideways."""

    text = text.replace("<details>", '<details markdown="1">')
    for source, target in LINK_MAP.items():
        text = text.replace(f"[`{source}`]({source})", f"[report]({target})")
        text = text.replace(f"]({source})", f"]({target})")
    body = markdown.markdown(text, extensions=["tables", "fenced_code", "md_in_html"], output_format="html")
    return body.replace("<table>", '<div class="table-wrap"><table>').replace("</table>", "</table></div>")


def page(title: str, body: str, git_sha: str, body_class: str = "") -> str:
    nav = '<nav><a href="index.html">Status</a>' + "".join(
        f'<a href="{name}">{html.escape(label)}</a>' for name, (_, label) in REPORTS.items()) + "</nav>"
    return (
        "<!doctype html>\n<html lang=\"en\"><head><meta charset=\"utf-8\">"
        "<meta name=\"viewport\" content=\"width=device-width, initial-scale=1\">"
        f"<title>{html.escape(title)} · NSE breakout scanner</title><style>{CSS}</style></head>"
        f"<body class=\"{body_class}\"><main>{nav}{body}<footer>Read-only status page. Built from git <code>{html.escape(git_sha)}</code>. "
        "Nothing here is a trade recommendation or a return expectation.</footer></main></body></html>\n"
    )


def _status_section(readme: str) -> str:
    match = re.search(r"^## Status\n(.*?)(?=^## )", readme, flags=re.S | re.M)
    if not match:
        raise ValueError("scanner/README.md has no '## Status' section")
    return match.group(1).strip()


def _data_asof(step1: str) -> str:
    match = re.search(r"Latest session in the data: \*\*(\d{4}-\d{2}-\d{2})\*\*", step1)
    if not match:
        raise ValueError("step-1 report has no 'Latest session in the data' line")
    return match.group(1)


def build_pages(root: Path, git_sha: str) -> dict[str, str]:
    """Render every page from the committed README and reports under `root` (the scanner dir)."""

    readme = (root / "README.md").read_text(encoding="utf-8")
    sources = {name: (root / path).read_text(encoding="utf-8") for name, (path, _) in REPORTS.items()}
    index_md = "\n".join([
        "# NSE breakout scanner",
        "",
        '<div class="note" markdown="1">',
        "",
        "**No trading signals yet.** The strategy rules (step 3) have not been written. The reports below cover "
        "data quality and a *random-entry baseline*: the numbers any future strategy has to beat out of sample. "
        "They are not the strategy's results.",
        "",
        "</div>",
        "",
        "End-of-day, long-only scanner for Nifty 500 + Nifty Microcap 250 that looks for momentum leaders "
        "breaking out of tight bases. It is being built and validated step by step.",
        "",
        "## Build status",
        "",
        _status_section(readme),
        "",
        "## Reports",
        "",
        f"* [Step 1: data layer and QA](step1.html): Yahoo data for 750 symbols, calendar and QA findings "
        f"(data to {_data_asof(sources['step1.html'])}).",
        "* [Step 2: base-rate study](step2.html): what random liquid entries do under the planned exits and "
        "costs.",
    ])
    pages = {"index.html": page("Status", render_markdown(index_md), git_sha, body_class="wrap-cells")}
    for name, (_, label) in REPORTS.items():
        pages[name] = page(label, render_markdown(sources[name]), git_sha)
    return pages


def build_site(root: Path, out_dir: Path, git_sha: str) -> list[Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    written = []
    for name, content in build_pages(root, git_sha).items():
        path = out_dir / name
        path.write_text(content, encoding="utf-8")
        written.append(path)
    return written


def make_handler(pages: dict[str, bytes]) -> type[BaseHTTPRequestHandler]:
    routes = {f"/{name}": body for name, body in pages.items()}
    routes["/"] = pages["index.html"]
    routes["/healthz"] = b"ok"

    class Handler(BaseHTTPRequestHandler):
        server_version = "stockbreak"
        sys_version = ""

        def _respond(self, include_body: bool) -> None:
            path = self.path.split("?", 1)[0].split("#", 1)[0]
            body = routes.get(path)
            if body is None:
                self.send_error(HTTPStatus.NOT_FOUND)
                return
            self.send_response(HTTPStatus.OK)
            self.send_header("Content-Type", "text/plain; charset=utf-8" if path == "/healthz"
                             else "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-cache")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("Referrer-Policy", "no-referrer")
            self.end_headers()
            if include_body:
                self.wfile.write(body)

        def do_GET(self) -> None:  # noqa: N802 (http.server naming)
            self._respond(include_body=True)

        def do_HEAD(self) -> None:  # noqa: N802
            self._respond(include_body=False)

        def log_message(self, fmt: str, *args) -> None:
            LOGGER.info("%s %s", self.address_string(), fmt % args)

    return Handler


def serve(site_dir: Path, port: int, host: str = "0.0.0.0") -> None:
    pages = {path.name: path.read_bytes() for path in sorted(site_dir.glob("*.html"))}
    if "index.html" not in pages:
        raise FileNotFoundError(f"{site_dir}/index.html missing; run `python -m nsescan site` first")
    server = ThreadingHTTPServer((host, port), make_handler(pages))
    LOGGER.info("serving %d pages on %s:%d", len(pages), host, port)
    server.serve_forever()
