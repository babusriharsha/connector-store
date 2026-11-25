#!/usr/bin/env python3
"""Generate ImageSignal's binary demo samples locally.

The sample images are binary files, so they are not shipped in the
repo. This script rebuilds equivalents — a small 8x6 test image (a
colour gradient with a white rectangle) written as PNG (encoded by
hand with zlib + struct), 24-bit BMP and binary PPM (P6) — using only
the standard library.

Run once if the samples are missing:

    python3 bin/make_samples.py

Demo mode (image.py --demo) calls ensure_samples() automatically, so
running this by hand is only needed outside demo mode. Note that
samples/sample-out.png is NOT generated here: it is the output the
demo resize command creates.
"""
from __future__ import annotations
import os, struct, zlib

SAMPLES = os.path.join(os.path.dirname(os.path.abspath(__file__)), "samples")
W, H = 8, 6


def pixels():
    """8x6 RGB: red/green gradient with a white rectangle in the middle."""
    px = bytearray(W * H * 3)
    for y in range(H):
        for x in range(W):
            r, g, b = x * 36, y * 51, 128
            if 2 <= x < 6 and 2 <= y < 4:
                r, g, b = 255, 255, 255
            i = (y * W + x) * 3
            px[i:i + 3] = bytes([r, g, b])
    return px


def build_png(path):
    def chunk(typ, data):
        c = struct.pack(">I", len(data)) + typ + data
        return c + struct.pack(">I", zlib.crc32(typ + data) & 0xFFFFFFFF)
    px = pixels()
    raw = b"".join(b"\x00" + bytes(px[y * W * 3:(y + 1) * W * 3]) for y in range(H))
    ihdr = struct.pack(">IIBBBBB", W, H, 8, 2, 0, 0, 0)  # 8-bit, colour type 2 (RGB)
    data = (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", ihdr)
            + chunk(b"IDAT", zlib.compress(raw)) + chunk(b"IEND", b""))
    open(path, "wb").write(data)


def build_bmp(path):
    px = pixels()
    row = ((W * 3 + 3) // 4) * 4
    img = bytearray(row * H)
    for y in range(H):
        sy = H - 1 - y  # BMP rows are bottom-up
        for x in range(W):
            r, g, b = px[(y * W + x) * 3:(y * W + x) * 3 + 3]
            img[sy * row + x * 3: sy * row + x * 3 + 3] = bytes([b, g, r])
    hdr = (b"BM" + struct.pack("<IHHI", 54 + len(img), 0, 0, 54)
           + struct.pack("<IiiHHIIiiII", 40, W, H, 1, 24, 0, len(img), 2835, 2835, 0, 0))
    open(path, "wb").write(hdr + bytes(img))


def build_ppm(path):
    open(path, "wb").write(f"P6\n{W} {H}\n255\n".encode() + bytes(pixels()))


BUILDERS = {"sample.png": build_png, "sample.bmp": build_bmp, "sample.ppm": build_ppm}


def ensure_samples():
    """Create any missing generated samples; return the paths created."""
    created = []
    os.makedirs(SAMPLES, exist_ok=True)
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
