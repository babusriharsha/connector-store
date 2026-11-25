#!/usr/bin/env python3
"""Generate ConvertSignal's binary demo sample (sample.docx) locally.

The .docx is a binary file, so it is not shipped in the repo. This
script rebuilds an equivalent one — a minimal valid .docx (a zip with
[Content_Types].xml, _rels/.rels and word/document.xml) holding two
paragraphs of fictional text — using only the standard library.

Run once if the sample is missing:

    python3 bin/make_samples.py

Demo mode (convert.py --demo) calls ensure_samples() automatically,
so running this by hand is only needed outside demo mode.
"""
from __future__ import annotations
import os, zipfile

SAMPLES = os.path.join(os.path.dirname(os.path.abspath(__file__)), "samples")

CONTENT_TYPES = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Default Extension="xml" ContentType="application/xml"/><Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/></Types>
"""

RELS = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/></Relationships>
"""

PARAGRAPHS = [
    "Sample DOCX heading",
    "This paragraph was extracted from a real .docx zip structure.",
]

DOCUMENT = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"><w:body>
""" + "\n".join(
    f"<w:p><w:r><w:t>{p}</w:t></w:r></w:p>" for p in PARAGRAPHS
) + """
</w:body></w:document>
"""


def build_docx(path):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as z:
        for name, text in (("[Content_Types].xml", CONTENT_TYPES),
                           ("_rels/.rels", RELS),
                           ("word/document.xml", DOCUMENT)):
            info = zipfile.ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            z.writestr(info, text)


BUILDERS = {"sample.docx": build_docx}


def ensure_samples():
    """Create any missing generated samples; return the paths created."""
    created = []
    for name, build in BUILDERS.items():
        path = os.path.join(SAMPLES, name)
        if not os.path.isfile(path):
            build(path)
            created.append(path)
    return created


if __name__ == "__main__":
    made = ensure_samples()
    for p in made:
        print(f"created {p}")
    if not made:
        print("all generated samples already present")
