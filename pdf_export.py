"""Vector PDF export from the same markdown as the UI (readable text, embedded images)."""

from __future__ import annotations

import base64
import re
from html import escape as html_escape
from pathlib import Path

import markdown
from weasyprint import HTML

from config import _output_dir

_IMG_LINK = re.compile(r"!\[([^\]]*)\]\(([^)]+)\)")


def _resolve_image_path(url: str, out_root: Path) -> Path | None:
    u = url.strip()
    marker = "/api/static-output/"
    # Handles ``/api/static-output/...`` and ``https://host/api/static-output/...`` (split deploy).
    if marker in u:
        tail = u.split(marker, 1)[1].split("?")[0].split("#")[0]
        p = out_root / tail
        return p if p.is_file() else None
    if u.startswith("images/") or u.startswith("./images/"):
        rel = u.removeprefix("./")
        p = out_root / rel
        return p if p.is_file() else None
    if u.startswith("file://"):
        p = Path(u.replace("file://", "", 1))
        return p if p.is_file() else None
    return None


def _mime_for_path(path: Path) -> str:
    suf = path.suffix.lower()
    if suf in (".jpg", ".jpeg"):
        return "image/jpeg"
    if suf == ".webp":
        return "image/webp"
    if suf == ".gif":
        return "image/gif"
    if suf == ".svg":
        return "image/svg+xml"
    return "image/png"


def _embed_images_in_markdown(md_ui: str, out_root: Path) -> str:
    """Replace local image links with data URIs so WeasyPrint does not need network or file URLs."""

    def repl(m: re.Match[str]) -> str:
        alt, url = m.group(1), m.group(2).strip()
        path = _resolve_image_path(url, out_root)
        if path is None:
            return m.group(0)
        data = path.read_bytes()
        mime = _mime_for_path(path)
        b64 = base64.standard_b64encode(data).decode("ascii")
        return f"![{alt}](data:{mime};base64,{b64})"

    return _IMG_LINK.sub(repl, md_ui)


def _markdown_to_html_fragment(md_ui: str, out_root: Path) -> str:
    md_embedded = _embed_images_in_markdown(md_ui, out_root)
    md = markdown.Markdown(extensions=["extra", "nl2br"])
    return md.convert(md_embedded)


_WRAPPER_CSS = """
@page { size: A4; margin: 18mm 16mm; }
html { font-size: 11pt; }
body {
  font-family: system-ui, -apple-system, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
  line-height: 1.55;
  color: #1a1a1a;
  word-wrap: break-word;
}
h1 { font-size: 1.65rem; font-weight: 700; margin: 0 0 0.75em; line-height: 1.25; }
h2 { font-size: 1.25rem; font-weight: 650; margin: 1.25em 0 0.5em; }
h3 { font-size: 1.08rem; font-weight: 600; margin: 1em 0 0.4em; }
p { margin: 0 0 0.85em; }
ul, ol { margin: 0 0 1em 1.2em; padding-left: 0.25em; }
li { margin: 0.25em 0; }
blockquote {
  margin: 0.8em 0;
  padding-left: 1em;
  border-left: 3px solid #ccc;
  color: #444;
}
code {
  font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
  font-size: 0.9em;
  background: #f4f4f4;
  padding: 0.12em 0.35em;
  border-radius: 4px;
}
pre {
  background: #f6f8fa;
  border: 1px solid #e8e8e8;
  border-radius: 6px;
  padding: 0.85em 1em;
  overflow-x: auto;
  font-size: 0.88em;
  line-height: 1.45;
}
pre code { background: none; padding: 0; border-radius: 0; }
table {
  border-collapse: collapse;
  width: 100%;
  margin: 1em 0;
  font-size: 0.95em;
}
th, td {
  border: 1px solid #ddd;
  padding: 0.45em 0.65em;
  text-align: left;
  vertical-align: top;
}
th { background: #f0f0f0; font-weight: 600; }
img {
  max-width: 100%;
  height: auto;
  display: block;
  margin: 0.75em auto;
}
hr { border: none; border-top: 1px solid #ddd; margin: 1.5em 0; }
strong { font-weight: 600; }
"""


def markdown_to_pdf_bytes(md_ui: str, title: str = "Report") -> bytes:
    """
    Build a PDF from UI markdown (including ``/api/static-output/...`` image paths).

    Local images under ``BWA_OUTPUT_DIR`` are embedded; remote URLs in markdown are left to WeasyPrint.
    """
    out_root = _output_dir()
    fragment = _markdown_to_html_fragment(md_ui, out_root)
    safe_title = html_escape(title)
    full_html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8"/>
<title>{safe_title}</title>
<style>{_WRAPPER_CSS}</style>
</head>
<body>
<article class="report">{fragment}</article>
</body>
</html>"""
    base = out_root.resolve().as_uri()
    return HTML(string=full_html, base_url=base).write_pdf()


def safe_pdf_filename(title: str) -> str:
    raw = (title or "research-report").strip()
    slug = re.sub(r"[^a-zA-Z0-9\s_-]+", "", raw).strip()
    slug = re.sub(r"\s+", "-", slug)
    slug = re.sub(r"-+", "-", slug)[:96]
    return f"{slug or 'research-report'}.pdf"
