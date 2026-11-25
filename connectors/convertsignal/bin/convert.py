#!/usr/bin/env python3
"""ConvertSignal CLI — local document conversion, stdlib only.

Formats: .txt, .md, .html, .docx (read/extract only — a .docx is a
zip of XML; this tool extracts its text, it does not write .docx).
md->html is an honest subset: headings (#..######), bold, italic,
inline code, links, unordered/ordered lists, fenced code blocks,
paragraphs. No tables, no nested lists, no images in v1.
The binary demo sample (sample.docx) is not shipped; it is generated
by bin/make_samples.py, which demo mode runs automatically if missing.
"""
from __future__ import annotations
import html as htmlmod, json, os, re, sys, zipfile
import xml.etree.ElementTree as ET
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import license_check, make_samples
BIN = os.path.dirname(os.path.abspath(__file__)); SAMPLES = os.path.join(BIN, "samples")
W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"

def emit(p, code=0):
    print(json.dumps(p, indent=2, default=str)); raise SystemExit(code)
def err(m): emit({"ok": False, "error": m}, 1)
def read_text(path):
    if not os.path.isfile(path): err(f"file not found: {path}")
    return open(path, encoding="utf-8", errors="replace").read()
def ext(path): return os.path.splitext(path)[1].lower()

def docx_text(path):
    if not os.path.isfile(path): err(f"file not found: {path}")
    with zipfile.ZipFile(path) as z:
        if "word/document.xml" not in z.namelist(): err("not a valid docx (no word/document.xml)")
        root = ET.fromstring(z.read("word/document.xml"))
    paras = []
    for p in root.iter(W + "p"):
        paras.append("".join(t.text or "" for t in p.iter(W + "t")))
    return "\n\n".join(paras)

def html_to_text(h):
    h = re.sub(r"(?is)<(script|style).*?</\1>", "", h)
    h = re.sub(r"(?i)<br\s*/?>", "\n", h)
    h = re.sub(r"(?i)</(p|div|li|h[1-6]|tr)>", "\n\n", h)
    h = re.sub(r"<[^>]+>", "", h)
    return re.sub(r"\n{3,}", "\n\n", htmlmod.unescape(h)).strip()

def inline_md_to_html(s):
    s = htmlmod.escape(s)
    s = re.sub(r"`([^`]+)`", r"<code>\1</code>", s)
    s = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", s)
    s = re.sub(r"(?<!\*)\*([^*\n]+)\*(?!\*)", r"<em>\1</em>", s)
    s = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", r'<a href="\2">\1</a>', s)
    return s

def md_to_html(md):
    out = []; in_code = False; code = []; list_tag = None
    def close_list():
        nonlocal list_tag
        if list_tag: out.append(f"</{list_tag}>"); list_tag = None
    for line in md.splitlines():
        if line.strip().startswith("```"):
            if in_code: out.append("<pre><code>" + htmlmod.escape("\n".join(code)) + "</code></pre>"); code = []; in_code = False
            else: close_list(); in_code = True
            continue
        if in_code: code.append(line); continue
        m = re.match(r"^(#{1,6})\s+(.*)", line)
        if m: close_list(); out.append(f"<h{len(m.group(1))}>{inline_md_to_html(m.group(2))}</h{len(m.group(1))}>"); continue
        m = re.match(r"^\s*[-*]\s+(.*)", line)
        if m:
            if list_tag != "ul": close_list(); out.append("<ul>"); list_tag = "ul"
            out.append(f"<li>{inline_md_to_html(m.group(1))}</li>"); continue
        m = re.match(r"^\s*\d+[.)]\s+(.*)", line)
        if m:
            if list_tag != "ol": close_list(); out.append("<ol>"); list_tag = "ol"
            out.append(f"<li>{inline_md_to_html(m.group(1))}</li>"); continue
        if line.strip() == "": close_list(); continue
        close_list(); out.append(f"<p>{inline_md_to_html(line)}</p>")
    close_list()
    if in_code: out.append("<pre><code>" + htmlmod.escape("\n".join(code)) + "</code></pre>")
    return "<!DOCTYPE html>\n<html><head><meta charset=\"utf-8\"></head><body>\n" + "\n".join(out) + "\n</body></html>\n"

def md_to_text(md):
    md = re.sub(r"```.*?```", lambda m: m.group(0)[3:-3], md, flags=re.S)
    md = re.sub(r"^#{1,6}\s+", "", md, flags=re.M)
    md = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", md)
    md = re.sub(r"[*_`]+", "", md)
    md = re.sub(r"^\s*[-*]\s+", "", md, flags=re.M)
    return md.strip()

def to_plain(path):
    e = ext(path)
    if e == ".docx": return docx_text(path)
    t = read_text(path)
    if e == ".html": return html_to_text(t)
    if e == ".md": return md_to_text(t)
    return t

def cmd_info(path):
    e = ext(path)
    if e == ".docx":
        text = docx_text(path)
        with zipfile.ZipFile(path) as z: parts = len(z.namelist())
        emit({"ok": True, "file": path, "format": "docx", "size_bytes": os.path.getsize(path), "zip_parts": parts,
              "paragraphs": len([p for p in text.split("\n\n") if p.strip()]), "characters": len(text), "words": len(text.split())})
    elif e in (".txt", ".md", ".html"):
        t = read_text(path)
        emit({"ok": True, "file": path, "format": e[1:], "size_bytes": os.path.getsize(path),
              "lines": len(t.splitlines()), "characters": len(t), "words": len(t.split())})
    else: err(f"unsupported format: {e} (v1: txt, md, html, docx)")

def flag(argv, name): return argv[argv.index(name) + 1] if name in argv else None

def main(argv):
    demo = "--demo" in argv; argv = [a for a in argv if a != "--demo"]
    if demo: make_samples.ensure_samples()  # binary samples are generated, not shipped
    if not demo: license_check.enforce()
    if len(argv) < 2: err("usage: convert.py [--demo] info|extract|to-md|to-html|to-txt <file> [--out <file>]")
    cmd = argv[1]
    files = [a for i, a in enumerate(argv[2:], start=2) if not a.startswith("--") and argv[i - 1] != "--out"]
    default = {"info": "sample.md", "extract": "sample.docx", "to-md": "sample.txt", "to-html": "sample.md", "to-txt": "sample.md"}
    path = files[0] if files else (os.path.join(SAMPLES, default.get(cmd, "sample.md")) if demo else err(f"{cmd} needs a file"))
    if cmd == "info": cmd_info(path)
    elif cmd == "extract":
        if ext(path) != ".docx": err("extract is for .docx files")
        emit({"ok": True, "file": path, "text": docx_text(path)})
    elif cmd in ("to-md", "to-html", "to-txt"):
        outp = flag(argv, "--out")
        target = {"to-md": ".md", "to-html": ".html", "to-txt": ".txt"}[cmd]
        if not outp:
            outp = os.path.join(SAMPLES, "converted" + target) if demo else err(f"{cmd} needs --out")
        if cmd == "to-html":
            result = md_to_html(read_text(path) if ext(path) == ".md" else to_plain(path))
        elif cmd == "to-md":
            if ext(path) == ".md": result = read_text(path)
            elif ext(path) == ".html": result = html_to_text(read_text(path))
            else: result = to_plain(path)
        else:
            result = to_plain(path)
        open(outp, "w", encoding="utf-8").write(result if result.endswith("\n") else result + "\n")
        emit({"ok": True, "command": cmd, "source": path, "created": outp, "characters": len(result)})
    else: err(f"unknown command: {cmd}")

if __name__ == "__main__":
    main(sys.argv)
