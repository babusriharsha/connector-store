#!/usr/bin/env python3
"""PDFSignal CLI — local PDF tools, Python standard library only.

Commands: info, extract-text, make. Merge/split of arbitrary PDFs is
intentionally NOT implemented in v1 (see CONNECTOR.md) — doing it
correctly needs a heavier PDF engine than the stdlib provides.

extract-text works on PDFs whose content streams are uncompressed or
FlateDecode-compressed and whose text is drawn with Tj/TJ operators
using simple (non-CID) fonts. That covers PDFs produced by this tool's
own `make` and many simple generators; it does not cover scanned/image
PDFs (no OCR) or complex CID-font documents.
"""
from __future__ import annotations
import json, os, re, sys, zlib
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import license_check
BIN = os.path.dirname(os.path.abspath(__file__))
SAMPLES = os.path.join(BIN, "samples")

def emit(p, code=0):
    print(json.dumps(p, indent=2, default=str)); raise SystemExit(code)
def err(msg):
    emit({"ok": False, "error": msg}, 1)

def read_pdf(path):
    if not os.path.isfile(path): err(f"file not found: {path}")
    return open(path, "rb").read()

def decode_pdf_string(raw: bytes) -> str:
    s = raw.decode("latin-1")
    s = s.replace("\\n", "\n").replace("\\r", "\r").replace("\\t", "\t")
    s = re.sub(r"\\([()\\])", r"\1", s)
    s = re.sub(r"\\[0-7]{1,3}", lambda m: chr(int(m.group(0)[1:], 8)), s)
    return s

def cmd_info(path):
    data = read_pdf(path)
    pages = len(re.findall(rb"/Type\s*/Page(?![s\w])", data))
    note = None
    if pages == 0:
        m = re.search(rb"/Type\s*/Pages[^>]*?/Count\s+(\d+)", data, re.S)
        if m: pages = int(m.group(1)); note = "page count from /Pages /Count (no individual /Page objects found)"
    meta = {}
    for key in (b"Title", b"Author", b"Creator", b"Producer", b"Subject", b"Keywords", b"CreationDate", b"ModDate"):
        m = re.search(rb"/" + key + rb"\s*\((?:[^()\\]|\\.)*\)", data)
        if m:
            inner = m.group(0)[len(key) + 3:-1]
            meta[key.decode().lower()] = decode_pdf_string(inner)
    emit({"ok": True, "file": path, "size_bytes": len(data),
          "header": data[:8].decode("latin-1", "replace"), "pages": pages,
          "metadata": meta, "note": note})

def iter_streams(data):
    for m in re.finditer(rb"stream\r?\n", data):
        end = data.find(b"endstream", m.end())
        if end == -1: continue
        raw = data[m.end():end]
        if raw.endswith(b"\r\n"): raw = raw[:-2]
        elif raw.endswith(b"\n"): raw = raw[:-1]
        try: yield zlib.decompress(raw)
        except Exception: yield raw

def cmd_extract(path):
    data = read_pdf(path)
    out = []
    for content in iter_streams(data):
        if b"Tj" not in content and b"TJ" not in content: continue
        # Tokenise string-showing operations in order.
        for m in re.finditer(rb"\((?:[^()\\]|\\.)*\)\s*Tj|\[(?:[^\[\]]|\((?:[^()\\]|\\.)*\))*\]\s*TJ", content):
            tok = m.group(0)
            parts = re.findall(rb"\((?:[^()\\]|\\.)*\)", tok)
            out.append("".join(decode_pdf_string(p[1:-1]) for p in parts))
        if re.search(rb"(T\*|'|\"|Td|TD)\b", content): pass
    text = "\n".join(out)
    emit({"ok": True, "file": path, "characters": len(text), "text": text,
          "limits": "Text from uncompressed/FlateDecode streams with Tj/TJ only; no OCR; CID-font PDFs may extract incompletely."})

def esc(s: str) -> str:
    return s.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")

def build_pdf(lines, out_path, title="PDFSignal document"):
    per_page = 48; pages = [lines[i:i+per_page] for i in range(0, len(lines), per_page)] or [[""]]
    objs = []
    objs.append(b"<< /Type /Catalog /Pages 2 0 R >>")
    kids = " ".join(f"{4+i*2} 0 R" for i in range(len(pages)))
    objs.append(f"<< /Type /Pages /Kids [{kids}] /Count {len(pages)} >>".encode())
    objs.append(b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>")
    for i, page_lines in enumerate(pages):
        content_lines = ["BT /F1 11 Tf 50 750 Td 14 TL"]
        for ln in page_lines:
            content_lines.append(f"({esc(ln)}) Tj T*")
        content_lines.append("ET")
        content = "\n".join(content_lines).encode("latin-1", "replace")
        objs.append(f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Resources << /Font << /F1 3 0 R >> >> /Contents {5+i*2} 0 R >>".encode())
        objs.append(b"<< /Length " + str(len(content)).encode() + b" >>\nstream\n" + content + b"\nendstream")
    info_obj = f"<< /Title ({esc(title)}) /Creator (PDFSignal) /Producer (PDFSignal) >>".encode()
    objs.append(info_obj)
    info_num = len(objs)
    buf = bytearray(b"%PDF-1.4\n"); offsets = []
    for i, body in enumerate(objs, start=1):
        offsets.append(len(buf)); buf += f"{i} 0 obj\n".encode() + body + b"\nendobj\n"
    xref = len(buf)
    buf += f"xref\n0 {len(objs)+1}\n0000000000 65535 f \n".encode()
    for off in offsets: buf += f"{off:010d} 00000 n \n".encode()
    buf += f"trailer\n<< /Size {len(objs)+1} /Root 1 0 R /Info {info_num} 0 R >>\nstartxref\n{xref}\n%%EOF\n".encode()
    with open(out_path, "wb") as fh: fh.write(bytes(buf))
    return len(pages)

def cmd_make(src, out_path):
    if not os.path.isfile(src): err(f"text file not found: {src}")
    lines = []
    for raw in open(src, encoding="utf-8", errors="replace").read().splitlines():
        while len(raw) > 95: lines.append(raw[:95]); raw = raw[95:]
        lines.append(raw)
    n = build_pdf(lines, out_path, title=os.path.basename(src))
    emit({"ok": True, "created": out_path, "pages": n, "source_lines": len(lines),
          "size_bytes": os.path.getsize(out_path)})

def main(argv):
    demo = "--demo" in argv; argv = [a for a in argv if a != "--demo"]
    if not demo: license_check.enforce()
    if len(argv) < 2: err("usage: pdf.py [--demo] info|extract-text <file.pdf> | make --from <txt> --out <pdf>")
    cmd = argv[1]
    if demo:
        default_pdf = os.path.join(SAMPLES, "sample.pdf")
    if cmd == "info":
        cmd_info(argv[2] if len(argv) > 2 else (default_pdf if demo else err("info needs a file")))
    elif cmd == "extract-text":
        cmd_extract(argv[2] if len(argv) > 2 else (default_pdf if demo else err("extract-text needs a file")))
    elif cmd == "make":
        src = outp = None
        i = 2
        while i < len(argv):
            if argv[i] == "--from": src = argv[i+1]; i += 2
            elif argv[i] == "--out": outp = argv[i+1]; i += 2
            else: i += 1
        if demo and not src: src = os.path.join(SAMPLES, "sample.txt")
        if demo and not outp: outp = os.path.join(SAMPLES, "sample-made.pdf")
        if not src or not outp: err("make needs --from and --out")
        cmd_make(src, outp)
    else: err(f"unknown command: {cmd} (merge/split are out of scope for v1 — see CONNECTOR.md)")

if __name__ == "__main__":
    main(sys.argv)
