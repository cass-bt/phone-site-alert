#!/usr/bin/env python3
"""Converte docs/tutorial.md -> docs/tutorial.pdf (markdown + weasyprint)."""
import markdown, pathlib
from weasyprint import HTML

HERE = pathlib.Path(__file__).parent
md_text = (HERE / "tutorial.md").read_text(encoding="utf-8")

html_body = markdown.markdown(
    md_text,
    extensions=["tables", "fenced_code", "toc", "sane_lists"],
)

CSS = """
@page {
  size: A4; margin: 2cm 1.8cm;
  @bottom-center { content: "Smart Site Alert — " counter(page) " / " counter(pages);
                   font-size: 8pt; color: #888; }
}
* { box-sizing: border-box; }
body { font-family: "DejaVu Sans", "Noto Sans", sans-serif; font-size: 10.5pt;
       line-height: 1.5; color: #1f2430; }
h1 { color: #e8550d; font-size: 22pt; margin: 0 0 2pt; border-bottom: 3px solid #e8550d;
     padding-bottom: 4pt; }
h1 + h2 { color: #555; font-size: 13pt; font-weight: 400; border: none; margin-top: 2pt; }
h2 { color: #c8470b; font-size: 15pt; margin-top: 22pt; border-bottom: 1px solid #f0c9b0;
     padding-bottom: 3pt; }
h3 { color: #2c3340; font-size: 12pt; margin-top: 14pt; }
p { margin: 6pt 0; }
a { color: #c8470b; text-decoration: none; }
code { font-family: "DejaVu Sans Mono", monospace; font-size: 9pt;
       background: #f4f1ee; padding: 1px 4px; border-radius: 3px; color: #b5350a; }
pre { background: #2b2b33; color: #e6e6e6; padding: 10pt 12pt; border-radius: 6px;
      font-size: 8.5pt; line-height: 1.4; overflow-x: auto; page-break-inside: avoid; }
pre code { background: none; color: #e6e6e6; padding: 0; font-size: 8.5pt; }
table { border-collapse: collapse; width: 100%; margin: 10pt 0; font-size: 9.5pt;
        page-break-inside: avoid; }
th { background: #e8550d; color: #fff; text-align: left; padding: 5pt 8pt; }
td { border: 1px solid #e3ddd6; padding: 5pt 8pt; vertical-align: top; }
tr:nth-child(even) td { background: #faf7f4; }
blockquote { border-left: 4px solid #e8550d; background: #fdf6f1; margin: 8pt 0;
             padding: 6pt 12pt; color: #5a4a40; }
hr { border: none; border-top: 1px solid #e3ddd6; margin: 16pt 0; }
strong { color: #1f2430; }
"""

full_html = f"<html><head><meta charset='utf-8'></head><body>{html_body}</body></html>"
out = HERE / "tutorial.pdf"
HTML(string=full_html).write_pdf(str(out), stylesheets=[__import__("weasyprint").CSS(string=CSS)])
print(f"[+] PDF gerado: {out}  ({out.stat().st_size//1024} KB)")
