"""Builds docs/en/schedops-bench-en.html from the two English benchmark documents.

Usage (from the repo root):  python docs/en/build_pdf.py
Then render with headless Chrome:
  chrome --headless=new --disable-gpu --no-pdf-header-footer --print-to-pdf=docs/schedops-bench-en.pdf
         file:///.../docs/en/schedops-bench-en.html
"""
import pathlib

import markdown

HERE = pathlib.Path(__file__).resolve().parent
CSS = """
@page { size: A4; margin: 16mm 14mm; }
body { font-family: "Segoe UI", Arial, sans-serif; font-size: 9.6pt; line-height: 1.42; color: #1b2430; }
h1 { font-size: 19pt; margin: 0 0 6pt; color: #12305a; page-break-before: always; }
.cover + h1, h1:first-of-type { page-break-before: avoid; }
h2 { font-size: 13pt; margin: 16pt 0 5pt; color: #12305a; border-bottom: 1px solid #c9d3df; padding-bottom: 2pt; }
h3 { font-size: 10.8pt; margin: 11pt 0 4pt; color: #1d4c8a; }
p, li { orphans: 3; widows: 3; }
code { font-family: Consolas, monospace; font-size: 8.4pt; background: #eef2f6; padding: 0 2pt; border-radius: 2pt; }
pre { background: #f2f5f8; border: 1px solid #d5dde6; border-radius: 3pt; padding: 6pt 8pt; white-space: pre-wrap; word-break: break-word; page-break-inside: avoid; }
pre code { background: none; padding: 0; }
table { border-collapse: collapse; width: 100%; margin: 6pt 0 10pt; font-size: 8pt; table-layout: auto; }
th { background: #12305a; color: #fff; text-align: left; padding: 3pt 5pt; }
td { border-bottom: 1px solid #d5dde6; padding: 3pt 5pt; vertical-align: top; word-break: break-word; }
table:has(th:nth-child(5):last-child) { table-layout: fixed; }
th:first-child:nth-last-child(5) { width: 21%; }
th:nth-child(2):nth-last-child(4) { width: 8%; }
th:nth-child(3):nth-last-child(3) { width: 10%; }
th:nth-child(4):nth-last-child(2) { width: 29%; }
td:first-child:nth-last-child(5) code { font-size: 7.2pt; }
td:nth-child(2):nth-last-child(4), td:nth-child(3):nth-last-child(3) { word-break: normal; }
tr { page-break-inside: avoid; }
thead { display: table-header-group; }
.cover { height: 250mm; display: flex; flex-direction: column; justify-content: center; }
.cover .k { letter-spacing: 2pt; font-size: 9pt; color: #1d4c8a; }
.cover .t { font-size: 34pt; font-weight: 700; color: #12305a; margin: 8pt 0 4pt; }
.cover .s { font-size: 13pt; color: #3a4a5c; max-width: 150mm; }
.cover .m { margin-top: 22pt; font-size: 9.5pt; color: #55657a; }
"""
COVER = """<div class="cover"><div class="k">VARDIYA · OPEN HARNESS · AIOPS</div>
<div class="t">SchedOps-Bench</div>
<div class="s">A live benchmark for language model agents that operate batch job schedulers: description, results and the catalogue of all 165 scenarios.</div>
<div class="m">English edition · github.com/Proaiml/vardiya · Apache 2.0</div></div>"""


def main():
    md = markdown.Markdown(extensions=["tables", "fenced_code", "sane_lists"])
    parts = []
    for name in ("schedops-bench.md", "schedops-bench-scenarios.md"):
        parts.append(md.reset().convert((HERE / name).read_text(encoding="utf-8")))
    out = (f'<!doctype html><html lang="en"><head><meta charset="utf-8"><title>SchedOps-Bench</title>'
           f"<style>{CSS}</style></head><body>{COVER}{''.join(parts)}</body></html>")
    (HERE / "schedops-bench-en.html").write_text(out, encoding="utf-8")
    print("wrote", HERE / "schedops-bench-en.html", len(out))


if __name__ == "__main__":
    main()
