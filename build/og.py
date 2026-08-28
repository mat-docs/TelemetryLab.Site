#!/usr/bin/env python3
"""
Draw the social card, dist/og.png.

There is no image library available here and none is worth adding for one
1200x630 file, so this writes the PNG itself: zlib for the pixel data, struct
for the chunks, and a stamped-disc rasteriser for the trace. It renders at 2x
and box-downsamples, which is what gives the line clean edges.

The card is the lap and nothing else — the same real telemetry the page draws,
coloured by speed. No text: a title rendered without a font library would look
worse than the platform's own, and every surface that shows this card shows the
og:title beside it anyway.
"""

from __future__ import annotations

import json
import os
import struct
import sys
import zlib

HERE = os.path.dirname(os.path.abspath(__file__))
SITE = os.path.join(HERE, "..")
LAP = os.path.join(SITE, "public", "lap.json")
OUT = os.path.join(SITE, "dist", "og.png")

W, H = 1200, 630
SS = 2                                   # supersample factor
GROUND = (0x1F, 0x29, 0x2E)   # MA Grey
DIM = (0x3A, 0x43, 0x47)      # MA Grey, 88% tint
ACCENT = (0xFA, 0x69, 0x14)   # MA Orange
# Sanctioned tints of MA Orange: 100%, 80%, 60%, 40%.
RAMP = [(0xFA, 0x69, 0x14), (0xFB, 0x87, 0x43),
        (0xFC, 0xA5, 0x72), (0xFD, 0xC3, 0xA1)]


def ramp_at(t: float) -> tuple[int, int, int]:
    t = max(0.0, min(1.0, t))
    seg = t * (len(RAMP) - 1)
    i = min(len(RAMP) - 2, int(seg))
    f = seg - i
    a, b = RAMP[i], RAMP[i + 1]
    return tuple(round(a[k] + (b[k] - a[k]) * f) for k in range(3))


class Canvas:
    def __init__(self, w: int, h: int, bg: tuple[int, int, int]):
        self.w, self.h = w, h
        self.buf = bytearray(bytes(bg) * (w * h))

    def px(self, x: int, y: int, c: tuple[int, int, int]) -> None:
        if 0 <= x < self.w and 0 <= y < self.h:
            i = (y * self.w + x) * 3
            self.buf[i:i + 3] = bytes(c)

    def disc(self, cx: float, cy: float, r: float, c: tuple[int, int, int]) -> None:
        x0, x1 = int(cx - r) - 1, int(cx + r) + 1
        y0, y1 = int(cy - r) - 1, int(cy + r) + 1
        rr = r * r
        for y in range(y0, y1 + 1):
            dy = y + 0.5 - cy
            for x in range(x0, x1 + 1):
                dx = x + 0.5 - cx
                if dx * dx + dy * dy <= rr:
                    self.px(x, y, c)

    def segment(self, x0, y0, x1, y1, r, c) -> None:
        """Stamp discs along the segment — gives round caps and joins free."""
        dx, dy = x1 - x0, y1 - y0
        n = max(1, int((dx * dx + dy * dy) ** 0.5 / max(0.4, r * 0.34)))
        for i in range(n + 1):
            t = i / n
            self.disc(x0 + dx * t, y0 + dy * t, r, c)

    def rect(self, x, y, w, h, c) -> None:
        for yy in range(int(y), int(y + h)):
            for xx in range(int(x), int(x + w)):
                self.px(xx, yy, c)

    def downsample(self, factor: int) -> bytearray:
        ow, oh = self.w // factor, self.h // factor
        out = bytearray(ow * oh * 3)
        n = factor * factor
        for y in range(oh):
            for x in range(ow):
                r = g = b = 0
                for sy in range(factor):
                    row = (y * factor + sy) * self.w
                    for sx in range(factor):
                        i = (row + x * factor + sx) * 3
                        r += self.buf[i]; g += self.buf[i + 1]; b += self.buf[i + 2]
                o = (y * ow + x) * 3
                out[o] = r // n; out[o + 1] = g // n; out[o + 2] = b // n
        return out


def write_png(path: str, w: int, h: int, rgb: bytearray) -> None:
    raw = bytearray()
    stride = w * 3
    for y in range(h):
        raw.append(0)                                  # filter type 0
        raw += rgb[y * stride:(y + 1) * stride]

    def chunk(tag: bytes, data: bytes) -> bytes:
        return (struct.pack(">I", len(data)) + tag + data
                + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF))

    png = b"\x89PNG\r\n\x1a\n"
    png += chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0))
    png += chunk(b"IDAT", zlib.compress(bytes(raw), 9))
    png += chunk(b"IEND", b"")
    with open(path, "wb") as f:
        f.write(png)


def main() -> int:
    if not os.path.exists(LAP):
        print("public/lap.json is missing. Run build/refresh_lap.py.", file=sys.stderr)
        return 1
    with open(LAP, encoding="utf-8") as f:
        lap = json.load(f)

    cv = Canvas(W * SS, H * SS, GROUND)
    pts = lap["points"]
    min_x, min_y, max_x, max_y = lap["bounds"]
    span_x = max(1.0, max_x - min_x)
    span_y = max(1.0, max_y - min_y)

    # Symmetric margins. An earlier version reserved a strip down the left for a
    # brand rule; a lone tick mark with no wordmark beside it read as a rendering
    # artefact rather than a mark, so the card is the trace and nothing else.
    pad_l, pad_r, pad_t, pad_b = 110, 110, 92, 92
    box_w = (W - pad_l - pad_r) * SS
    box_h = (H - pad_t - pad_b) * SS
    scale = min(box_w / span_x, box_h / span_y)
    draw_w, draw_h = span_x * scale, span_y * scale
    ox = pad_l * SS + (box_w - draw_w) / 2 - min_x * scale
    oy = pad_t * SS + (box_h + draw_h) / 2 + min_y * scale

    px = lambda p: ox + p["x"] * scale
    py = lambda p: oy - p["y"] * scale

    # the whole circuit, dim, then the speed-graded trace over it
    r_dim, r_hot = 7.5 * SS, 7.0 * SS
    for i in range(len(pts)):
        a, b = pts[i - 1], pts[i]
        cv.segment(px(a), py(a), px(b), py(b), r_dim, DIM)
    for i in range(1, len(pts)):
        a, b = pts[i - 1], pts[i]
        cv.segment(px(a), py(a), px(b), py(b), r_hot, ramp_at(b["v"]))

    write_png(OUT, W, H, cv.downsample(SS))
    print(f"  dist/og.png {os.path.getsize(OUT) / 1024:.1f} kB  ({W}x{H})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
