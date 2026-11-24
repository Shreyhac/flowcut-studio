"""OmniRoute: the CTA payload for vid92 (keyword ROUTE), "never hit your AI limit again".

Typesets vid92/ROUTE-doc-draft.md, researched 2026-10-01 against the live repo README, the
GitHub API and the npm registry (claims in vid92/FACTS.md), so the doc and the research
cannot drift.  What the doc says that the reel could not: tokens not words, Node 22/24,
free tiers belong to the providers and can change, 13 providers flagged "avoid".

House rules: no em dashes anywhere, sentence case, no emojis.
Run:  python3 make_doc_vid92.py
"""
import asyncio
import os
import re
import sys

from docx import Document
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Inches, Pt, RGBColor

SRC, OUT_BASE = sys.argv[1], sys.argv[2]           # gkit: python3 gkit/make_doc.py <draft.md> <out/base-name>
OUT_DOCX, OUT_PDF = OUT_BASE + ".docx", OUT_BASE + ".pdf"

INK = RGBColor(0x1F, 0x22, 0x19)
MUTE = RGBColor(0x6B, 0x6F, 0x66)
ACC = RGBColor(0xB0, 0x38, 0x18)      # the film's marker red (#D9451F), darkened for paper text
LINK = RGBColor(0x0B, 0x5C, 0xAD)

md = open(SRC, encoding="utf-8").read()
if re.search("[–—]", md):
    sys.exit("make_doc: an en or em dash is in the doc; house rule says none")

doc = Document()
s = doc.sections[0]
s.page_width, s.page_height = Inches(8.5), Inches(11)
s.left_margin = s.right_margin = Inches(1.15)
s.top_margin = s.bottom_margin = Inches(0.9)
normal = doc.styles["Normal"]
normal.font.name = "Calibri"
normal.font.size = Pt(11)
normal.font.color.rgb = INK
normal.paragraph_format.space_after = Pt(7)
normal.paragraph_format.line_spacing = 1.15

TOKEN = re.compile(r"\*\*(.+?)\*\*|\[([^\]]+)\]\(([^)]+)\)|`([^`]+)`")


def _link(p, text, url):
    part = p.part
    rid = part.relate_to(url, "http://schemas.openxmlformats.org/officeDocument/2006/relationships/hyperlink",
                         is_external=True)
    h = OxmlElement("w:hyperlink")
    h.set(qn("r:id"), rid)
    r = OxmlElement("w:r")
    rpr = OxmlElement("w:rPr")
    for tag, val in (("w:color", "0B5CAD"), ("w:u", "single")):
        e = OxmlElement(tag)
        e.set(qn("w:val"), val)
        rpr.append(e)
    r.append(rpr)
    t = OxmlElement("w:t")
    t.text = text
    t.set(qn("xml:space"), "preserve")
    r.append(t)
    h.append(r)
    p._p.append(h)


def runs(p, text, size=11, color=INK):
    pos = 0
    for m in TOKEN.finditer(text):
        if m.start() > pos:
            r = p.add_run(text[pos:m.start()])
            r.font.size, r.font.color.rgb = Pt(size), color
        if m.group(1):
            r = p.add_run(m.group(1))
            r.font.bold, r.font.size, r.font.color.rgb = True, Pt(size), color
        elif m.group(4):
            r = p.add_run(m.group(4))
            r.font.name, r.font.size, r.font.color.rgb = "Menlo", Pt(size - 1), color
        else:
            _link(p, m.group(2), m.group(3))
        pos = m.end()
    if pos < len(text):
        r = p.add_run(text[pos:])
        r.font.size, r.font.color.rgb = Pt(size), color


def html_inline(text):
    t = text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    t = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", t)
    t = re.sub(r"`([^`]+)`", r"<code>\1</code>", t)
    return re.sub(r"\[([^\]]+)\]\(([^)]+)\)", r'<a href="\2">\1</a>', t)


HTML, in_ul, in_ol = [], False, False


def close_lists():
    global in_ul, in_ol
    if in_ul:
        HTML.append("</ul>")
    if in_ol:
        HTML.append("</ol>")
    in_ul = in_ol = False


in_code, code = False, []
for line in md.splitlines():
    if line.startswith("```"):
        if in_code:
            close_lists()
            p = doc.add_paragraph()
            r = p.add_run("\n".join(code))
            r.font.name, r.font.size, r.font.color.rgb = "Menlo", Pt(9), INK
            esc_ = "\n".join(code).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
            HTML.append("<pre>%s</pre>" % esc_)
            code = []
        in_code = not in_code
        continue
    if in_code:
        code.append(line)
        continue
    if not line.strip():
        continue
    if line.startswith("# "):
        close_lists()
        p = doc.add_paragraph()
        r = p.add_run(line[2:])
        r.font.size, r.font.bold, r.font.color.rgb = Pt(24), True, INK
        HTML.append("<h1>%s</h1>" % html_inline(line[2:]))
    elif line.startswith("## "):
        close_lists()
        p = doc.add_paragraph()
        p.paragraph_format.space_before = Pt(12)
        r = p.add_run(line[3:])
        r.font.size, r.font.bold, r.font.color.rgb = Pt(16), True, ACC
        HTML.append("<h2>%s</h2>" % html_inline(line[3:]))
    elif line.startswith("### "):
        close_lists()
        p = doc.add_paragraph()
        p.paragraph_format.space_before = Pt(8)
        r = p.add_run(line[4:])
        r.font.size, r.font.bold, r.font.color.rgb = Pt(13), True, INK
        HTML.append("<h3>%s</h3>" % html_inline(line[4:]))
    elif re.match(r"^\d+\. ", line):
        if not in_ol:
            close_lists()
            HTML.append('<ol start="%s">' % re.match(r"^(\d+)\. ", line).group(1))   # resume after a code block
            in_ol = True
        body = re.sub(r"^\d+\. ", "", line)
        p = doc.add_paragraph(style="List Number")
        runs(p, body)
        HTML.append("<li>%s</li>" % html_inline(body))
    elif line.startswith("- "):
        if not in_ul:
            close_lists()
            HTML.append("<ul>")
            in_ul = True
        p = doc.add_paragraph(style="List Bullet")
        runs(p, line[2:])
        HTML.append("<li>%s</li>" % html_inline(line[2:]))
    else:
        close_lists()
        p = doc.add_paragraph()
        muted = line.startswith("Checked on")
        runs(p, line, size=10 if muted else 11, color=MUTE if muted else INK)
        HTML.append('<p%s>%s</p>' % (' class="m"' if muted else "", html_inline(line)))
close_lists()

os.makedirs("out", exist_ok=True)
doc.save(OUT_DOCX)
print("wrote " + OUT_DOCX)

CSS = """
@page { size: 8.5in 11in; margin: 0.8in 1.0in; }
body { font-family: -apple-system, 'Helvetica Neue', Arial, sans-serif; color:#1F2219;
       font-size:10.8pt; line-height:1.45; }
h1 { font-size:24pt; font-weight:800; letter-spacing:-.6pt; margin:0 0 4pt; line-height:1.12; }
p.m { color:#6B6F66; font-size:10pt; margin-bottom:14pt; }
h2 { font-size:15pt; font-weight:800; color:#B03818; margin:18pt 0 6pt; }
h3 { font-size:12.5pt; font-weight:800; margin:13pt 0 4pt; page-break-after:avoid; }
p { margin:0 0 8pt; }
ul, ol { margin:0 0 9pt; padding-left:18pt; }
li { margin:0 0 5pt; }
a { color:#0B5CAD; }
code { font-family: Menlo, monospace; font-size:9.5pt; background:#F2EFEA; padding:0 3pt; border-radius:3pt; }
pre { font-family: Menlo, monospace; font-size:8.8pt; background:#F6F3EF; border:1px solid #E4DED9; border-radius:6pt; padding:9pt 11pt; white-space:pre-wrap; }
"""
tmp = os.path.abspath(OUT_BASE + ".tmp.html")
open(tmp, "w", encoding="utf-8").write(
    "<!doctype html><meta charset='utf-8'><style>%s</style>%s" % (CSS, "".join(HTML)))


async def _pdf():
    from playwright.async_api import async_playwright
    async with async_playwright() as pw:
        b = await pw.chromium.launch()
        pg = await b.new_page()
        await pg.goto("file://" + tmp, wait_until="networkidle")
        await pg.pdf(path=OUT_PDF, format="Letter", print_background=True)
        await b.close()


asyncio.run(_pdf())
os.remove(tmp)
print("wrote " + OUT_PDF)
