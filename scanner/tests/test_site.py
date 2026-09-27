"""Status site: renders the committed README/reports, serves only known routes."""

from __future__ import annotations

import threading
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer
from pathlib import Path

import pytest

from nsescan.site import build_pages, make_handler, render_markdown

SCANNER_ROOT = Path(__file__).resolve().parents[1]


def test_render_markdown_tables_details_and_links():
    text = ("[`reports/step1_data_report.md`](reports/step1_data_report.md)\n\n"
            "<details><summary>All</summary>\n\n| a | b |\n| --- | --- |\n| 1 | 2 |\n\n</details>\n")
    out = render_markdown(text)
    assert '<a href="step1.html">report</a>' in out
    assert '<div class="table-wrap"><table>' in out and "<td>1</td>" in out
    assert "| a |" not in out


def test_pages_render_from_committed_reports():
    pages = build_pages(SCANNER_ROOT, "abc1234")
    assert set(pages) == {"index.html", "step1.html", "step2.html"}
    index = pages["index.html"]
    assert "No trading signals yet" in index and "abc1234" in index
    assert "Build status" in index and "step2.html" in index
    for name, body in pages.items():
        assert "| --- |" not in body, f"raw markdown table left in {name}"
        assert ".md\"" not in body, f"link to a .md file left in {name}"


@pytest.fixture
def server():
    pages = {name: body.encode() for name, body in build_pages(SCANNER_ROOT, "abc1234").items()}
    httpd = ThreadingHTTPServer(("127.0.0.1", 0), make_handler(pages))
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    yield f"http://127.0.0.1:{httpd.server_address[1]}"
    httpd.shutdown()


def _get(url: str) -> tuple[int, str]:
    try:
        with urllib.request.urlopen(url, timeout=5) as response:
            return response.status, response.read().decode()
    except urllib.error.HTTPError as err:
        return err.code, ""


def test_server_routes(server):
    assert _get(server + "/")[0] == 200
    assert _get(server + "/step2.html?utm=x")[0] == 200
    assert _get(server + "/healthz") == (200, "ok")
    for path in ("/README.md", "/../README.md", "/site/index.html", "/nsescan/cli.py"):
        assert _get(server + path)[0] == 404
