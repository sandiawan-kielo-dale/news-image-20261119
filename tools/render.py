#!/usr/bin/env python3
"""Render 'The World on Thursday - 19 November 2026' as a 1024x1024 PNG.

Pure Python standard library only. No external files are read, no network.
Output is deterministic: identical bytes on every run (fixed zlib level,
no timestamps, no random data).

Layout: black masthead, six colour-coded story panels in a 2x3 grid,
sources footer. Text is drawn with a small 5x7 bitmap font defined below.
"""
import os
import struct
import sys
import zlib

W, H = 1024, 1024

# ---------------------------------------------------------------------------
# 5x7 bitmap font. Each glyph is 7 rows of 5 cells; '#' is ink, '.' is blank.
# Written from scratch for this entry. Covers A-Z, a-z, 0-9 and punctuation.
# ---------------------------------------------------------------------------
FONT = {
    "A": (".###.", "#...#", "#...#", "#####", "#...#", "#...#", "#...#"),
    "B": ("####.", "#...#", "#...#", "####.", "#...#", "#...#", "####."),
    "C": (".####", "#....", "#....", "#....", "#....", "#....", ".####"),
    "D": ("####.", "#...#", "#...#", "#...#", "#...#", "#...#", "####."),
    "E": ("#####", "#....", "#....", "####.", "#....", "#....", "#####"),
    "F": ("#####", "#....", "#....", "####.", "#....", "#....", "#...."),
    "G": (".####", "#....", "#....", "#.###", "#...#", "#...#", ".###."),
    "H": ("#...#", "#...#", "#...#", "#####", "#...#", "#...#", "#...#"),
    "I": ("#####", "..#..", "..#..", "..#..", "..#..", "..#..", "#####"),
    "J": ("..###", "...#.", "...#.", "...#.", "...#.", "#..#.", ".##.."),
    "K": ("#...#", "#..#.", "#.#..", "##...", "#.#..", "#..#.", "#...#"),
    "L": ("#....", "#....", "#....", "#....", "#....", "#....", "#####"),
    "M": ("#...#", "##.##", "#.#.#", "#.#.#", "#...#", "#...#", "#...#"),
    "N": ("#...#", "##..#", "##..#", "#.#.#", "#..##", "#..##", "#...#"),
    "O": (".###.", "#...#", "#...#", "#...#", "#...#", "#...#", ".###."),
    "P": ("####.", "#...#", "#...#", "####.", "#....", "#....", "#...."),
    "Q": (".###.", "#...#", "#...#", "#...#", "#.#.#", "#..#.", ".##.#"),
    "R": ("####.", "#...#", "#...#", "####.", "#.#..", "#..#.", "#...#"),
    "S": (".####", "#....", "#....", ".###.", "....#", "....#", "####."),
    "T": ("#####", "..#..", "..#..", "..#..", "..#..", "..#..", "..#.."),
    "U": ("#...#", "#...#", "#...#", "#...#", "#...#", "#...#", ".###."),
    "V": ("#...#", "#...#", "#...#", "#...#", "#...#", ".#.#.", "..#.."),
    "W": ("#...#", "#...#", "#...#", "#.#.#", "#.#.#", "##.##", "#...#"),
    "X": ("#...#", "#...#", ".#.#.", "..#..", ".#.#.", "#...#", "#...#"),
    "Y": ("#...#", "#...#", ".#.#.", "..#..", "..#..", "..#..", "..#.."),
    "Z": ("#####", "....#", "...#.", "..#..", ".#...", "#....", "#####"),
    "0": (".###.", "#...#", "#..##", "#.#.#", "##..#", "#...#", ".###."),
    "1": ("..#..", ".##..", "..#..", "..#..", "..#..", "..#..", ".###."),
    "2": (".###.", "#...#", "....#", "...#.", "..#..", ".#...", "#####"),
    "3": ("####.", "....#", "....#", ".###.", "....#", "....#", "####."),
    "4": ("...#.", "..##.", ".#.#.", "#..#.", "#####", "...#.", "...#."),
    "5": ("#####", "#....", "####.", "....#", "....#", "#...#", ".###."),
    "6": (".###.", "#....", "#....", "####.", "#...#", "#...#", ".###."),
    "7": ("#####", "....#", "...#.", "...#.", "..#..", "..#..", "..#.."),
    "8": (".###.", "#...#", "#...#", ".###.", "#...#", "#...#", ".###."),
    "9": (".###.", "#...#", "#...#", ".####", "....#", "....#", ".###."),
    "a": (".....", ".....", ".###.", "....#", ".####", "#...#", ".####"),
    "b": ("#....", "#....", "####.", "#...#", "#...#", "#...#", "####."),
    "c": (".....", ".....", ".####", "#....", "#....", "#....", ".####"),
    "d": ("....#", "....#", ".####", "#...#", "#...#", "#...#", ".####"),
    "e": (".....", ".....", ".###.", "#...#", "#####", "#....", ".###."),
    "f": ("..##.", ".#..#", ".#...", "####.", ".#...", ".#...", ".#..."),
    "g": (".....", ".....", ".####", "#...#", "#...#", ".####", ".###."),
    "h": ("#....", "#....", "####.", "#...#", "#...#", "#...#", "#...#"),
    "i": ("..#..", ".....", ".##..", "..#..", "..#..", "..#..", ".###."),
    "j": ("...#.", ".....", "..##.", "...#.", "...#.", "...#.", ".##.."),
    "k": ("#....", "#....", "#..#.", "#.#..", "##...", "#.#..", "#..#."),
    "l": (".##..", "..#..", "..#..", "..#..", "..#..", "..#..", ".###."),
    "m": (".....", ".....", "##.#.", "#.#.#", "#.#.#", "#.#.#", "#.#.#"),
    "n": (".....", ".....", "####.", "#...#", "#...#", "#...#", "#...#"),
    "o": (".....", ".....", ".###.", "#...#", "#...#", "#...#", ".###."),
    "p": (".....", ".....", "####.", "#...#", "#...#", "####.", "#...."),
    "q": (".....", ".....", ".####", "#...#", "#...#", ".####", "....#"),
    "r": (".....", ".....", "#.##.", "##..#", "#....", "#....", "#...."),
    "s": (".....", ".....", ".####", "#....", ".###.", "....#", "####."),
    "t": (".#...", ".#...", "####.", ".#...", ".#...", ".#...", "..##."),
    "u": (".....", ".....", "#...#", "#...#", "#...#", "#..##", ".##.#"),
    "v": (".....", ".....", "#...#", "#...#", "#...#", ".#.#.", "..#.."),
    "w": (".....", ".....", "#...#", "#.#.#", "#.#.#", "#.#.#", ".#.#."),
    "x": (".....", ".....", "#...#", ".#.#.", "..#..", ".#.#.", "#...#"),
    "y": (".....", ".....", "#...#", "#...#", "#...#", ".####", "....#"),
    "z": (".....", ".....", "#####", "...#.", "..#..", ".#...", "#####"),
    " ": (".....", ".....", ".....", ".....", ".....", ".....", "....."),
    ".": (".....", ".....", ".....", ".....", ".....", ".##..", ".##.."),
    ",": (".....", ".....", ".....", ".....", ".##..", ".##..", ".#..."),
    ":": (".....", ".##..", ".##..", ".....", ".##..", ".##..", "....."),
    ";": (".....", ".##..", ".##..", ".....", ".##..", ".##..", ".#..."),
    "-": (".....", ".....", ".....", ".###.", ".....", ".....", "....."),
    "'": ("..#..", "..#..", ".#...", ".....", ".....", ".....", "....."),
    "(": ("...#.", "..#..", ".#...", ".#...", ".#...", "..#..", "...#."),
    ")": (".#...", "..#..", "...#.", "...#.", "...#.", "..#..", ".#..."),
    "/": ("....#", "....#", "...#.", "..#..", ".#...", "#....", "#...."),
    "&": (".###.", "#...#", "#.#..", ".#...", "#.#.#", "#..#.", ".##.#"),
    "%": ("##..#", "##.#.", "...#.", "..#..", ".#...", "#..##", "#..##"),
    "+": (".....", "..#..", "..#..", ".###.", "..#..", "..#..", "....."),
    "=": (".....", ".....", ".###.", ".....", ".###.", ".....", "....."),
    "?": (".###.", "#...#", "....#", "...#.", "..#..", ".....", "..#.."),
    "!": ("..#..", "..#..", "..#..", "..#..", "..#..", ".....", "..#.."),
    '"': (".#.#.", ".#.#.", ".#.#.", ".....", ".....", ".....", "....."),
    "*": (".....", ".#.#.", ".###.", "#####", ".###.", ".#.#.", "....."),
    "#": (".#.#.", ".#.#.", "#####", ".#.#.", "#####", ".#.#.", ".#.#."),
    "@": (".###.", "#...#", "#.###", "#.#.#", "#.###", "#....", ".###."),
    "$": ("..#..", ".####", "#.#..", ".###.", "..#.#", "####.", "..#.."),
    "[": (".###.", ".#...", ".#...", ".#...", ".#...", ".#...", ".###."),
    "]": (".###.", "...#.", "...#.", "...#.", "...#.", "...#.", ".###."),
    "_": (".....", ".....", ".....", ".....", ".....", ".....", "#####"),
    "~": (".....", ".....", ".##.#", "#.#.#", ".....", ".....", "....."),
    "<": ("...#.", "..#..", ".#...", "#....", ".#...", "..#..", "...#."),
    ">": (".#...", "..#..", "...#.", "....#", "...#.", "..#..", ".#..."),
    "|": ("..#..", "..#..", "..#..", "..#..", "..#..", "..#..", "..#.."),
    "\\": ("#....", "#....", ".#...", "..#..", "...#.", "....#", "....#"),
    "^": ("..#..", ".#.#.", ".....", ".....", ".....", ".....", "....."),
    "`": (".#...", "..#..", "...#.", ".....", ".....", ".....", "....."),
    "{": ("...##", "..#..", "..#..", ".##..", "..#..", "..#..", "...##"),
    "}": ("##...", "..#..", "..#..", "..##.", "..#..", "..#..", "##..."),
}

# Map a few typographic characters onto plain ASCII equivalents.
NORMALIZE = {
    "\u2013": "-", "\u2014": "-", "\u2019": "'", "\u2018": "'",
    "\u201c": '"', "\u201d": '"', "\u2026": ".", "\u00b7": ",",
}


def norm_char(ch):
    if ch in FONT:
        return ch
    if ch in NORMALIZE:
        return NORMALIZE[ch]
    return "?"


def text_width(text, scale):
    """Pixel width of text drawn at the given scale (no trailing gap)."""
    if not text:
        return 0
    return (len(text) * 6 - 1) * scale


# ---------------------------------------------------------------------------
# Canvas: an RGB pixel buffer with filled-rect and bitmap-text drawing.
# ---------------------------------------------------------------------------
class Canvas:
    def __init__(self, w, h, bg):
        self.w = w
        self.h = h
        self.pix = bytearray(w * h * 3)
        self.fill_rect(0, 0, w, h, bg)

    def set_px(self, x, y, color):
        if 0 <= x < self.w and 0 <= y < self.h:
            i = (y * self.w + x) * 3
            self.pix[i] = color[0]
            self.pix[i + 1] = color[1]
            self.pix[i + 2] = color[2]

    def fill_rect(self, x, y, w, h, color):
        x0 = max(0, x)
        y0 = max(0, y)
        x1 = min(self.w, x + w)
        y1 = min(self.h, y + h)
        r, g, b = color
        for yy in range(y0, y1):
            base = (yy * self.w + x0) * 3
            for xx in range(x0, x1):
                i = base + (xx - x0) * 3
                self.pix[i] = r
                self.pix[i + 1] = g
                self.pix[i + 2] = b

    def border(self, x, y, w, h, color, t=2):
        self.fill_rect(x, y, w, t, color)
        self.fill_rect(x, y + h - t, w, t, color)
        self.fill_rect(x, y, t, h, color)
        self.fill_rect(x + w - t, y, t, h, color)

    def draw_text(self, x, y, text, scale, color):
        """Draw text with its top-left at (x, y). Returns width drawn."""
        cx = x
        for raw in text:
            ch = norm_char(raw)
            glyph = FONT[ch]
            for gy in range(7):
                row = glyph[gy]
                for gx in range(5):
                    if row[gx] == "#":
                        self.fill_rect(
                            cx + gx * scale, y + gy * scale,
                            scale, scale, color,
                        )
            cx += 6 * scale
        return cx - x - scale if text else 0

    def draw_text_centered(self, cx, y, text, scale, color):
        x = cx - text_width(text, scale) // 2
        self.draw_text(x, y, text, scale, color)

    def wrap(self, text, scale, max_width):
        """Word-wrap text into lines no wider than max_width pixels."""
        words = text.split(" ")
        lines = []
        cur = ""
        for word in words:
            trial = word if not cur else cur + " " + word
            if text_width(trial, scale) <= max_width:
                cur = trial
            else:
                if cur:
                    lines.append(cur)
                # A single over-long word is hard-split by characters.
                while text_width(word, scale) > max_width:
                    cut = max_width // (6 * scale)
                    lines.append(word[:cut])
                    word = word[cut:]
                cur = word
        if cur:
            lines.append(cur)
        return lines


# ---------------------------------------------------------------------------
# PNG writer: fixed chunks, zlib level 9, no ancillary/time chunks.
# ---------------------------------------------------------------------------
def _chunk(tag, data):
    return (
        struct.pack(">I", len(data))
        + tag
        + data
        + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)
    )


def write_png(path, canvas):
    ihdr = struct.pack(">IIBBBBB", canvas.w, canvas.h, 8, 2, 0, 0, 0)
    raw = bytearray()
    row_len = canvas.w * 3
    for y in range(canvas.h):
        raw.append(0)  # filter type 0 (none)
        raw.extend(canvas.pix[y * row_len:(y + 1) * row_len])
    png = (
        b"\x89PNG\r\n\x1a\n"
        + _chunk(b"IHDR", ihdr)
        + _chunk(b"IDAT", zlib.compress(bytes(raw), 9))
        + _chunk(b"IEND", b"")
    )
    with open(path, "wb") as fh:
        fh.write(png)
    return len(png)


# ---------------------------------------------------------------------------
# Content and layout.
# ---------------------------------------------------------------------------
PAPER = (244, 241, 232)
INK = (17, 17, 17)
BODY = (51, 51, 51)
MUTED = (85, 85, 85)
WHITE = (255, 255, 255)
BLACK = (10, 10, 10)
GOLD = (232, 185, 35)
PANEL_BG = (255, 255, 255)
PANEL_BORDER = (216, 216, 216)
FOOTER_BG = (238, 235, 226)

# (kicker, headline, body, accent colour)
PANELS = [
    (
        "SUMMIT",
        "TRUMP-XI-PUTIN SUMMIT",
        "The three leaders held a first-ever 90-minute meeting in "
        "Shenzhen and pledged dialogue on nuclear risks and stable "
        "energy flows. Ukraine and Iran were discussed, but no major "
        "deal was reached.",
        (30, 64, 175),
    ),
    (
        "ICJ RULING",
        "MYANMAR GENOCIDE RULING",
        "The UN's top court ruled Myanmar committed state-sponsored "
        "genocide against the Rohingya, the first ruling of its kind. "
        "About 10,000 were killed in 2017; the court ordered probes, "
        "compensation and return of the displaced.",
        (185, 28, 28),
    ),
    (
        "BANGLADESH",
        "YUNUS HOME SET ABLAZE",
        "Nobel laureate Muhammad Yunus's ancestral home was set ablaze "
        "as violence spread to 28 districts. Four people were killed "
        "amid a nationwide opposition shutdown.",
        (194, 65, 12),
    ),
    (
        "GULF WAR",
        "US HITS IRAN; RIYADH HIT",
        "The US struck Iran's Qeshm island, and a Houthi missile "
        "damaged the PIF Tower in Riyadh. Trump said the US would "
        "'see what happens' after 1 January 2027.",
        (107, 33, 168),
    ),
    (
        "UKRAINE",
        "STRIKES KILL 5, CUT POWER",
        "Russian strikes killed at least five people and hit power "
        "infrastructure, cutting electricity in Dnipropetrovsk, "
        "Zhytomyr, Zaporizhzhia, Mykolaiv and Sumy regions.",
        (161, 98, 7),
    ),
    (
        "COP31",
        "CLIMATE TALKS STALL",
        "Final-stage talks in Antalya, Turkey, stalled over "
        "fossil-fuel language - 'transition away' versus phaseout - "
        "and climate finance.",
        (22, 101, 52),
    ),
]

MASTHEAD_H = 118
FOOTER_Y = 968
GRID_TOP = 134
GRID_GAP = 16
MARGIN = 20
PANEL_W = (W - MARGIN * 2 - GRID_GAP) // 2
PANEL_H = (FOOTER_Y - GRID_TOP - GRID_GAP * 2) // 3


def draw_masthead(cv):
    cv.fill_rect(0, 0, W, MASTHEAD_H, BLACK)
    cv.draw_text_centered(W // 2, 26, "THE WORLD ON THURSDAY", 5, WHITE)
    cv.draw_text_centered(W // 2, 76, "19 NOVEMBER 2026", 3, GOLD)
    cv.fill_rect(0, MASTHEAD_H - 4, W, 4, GOLD)


def draw_footer(cv):
    cv.fill_rect(0, FOOTER_Y, W, H - FOOTER_Y, FOOTER_BG)
    cv.fill_rect(0, FOOTER_Y, W, 2, BLACK)
    cv.draw_text_centered(
        W // 2, FOOTER_Y + 21,
        "SOURCES: AP, REUTERS, DPA, JUST SECURITY, IANS", 2, MUTED,
    )


def draw_panel(cv, px, py, index, kicker, headline, body, accent):
    cv.fill_rect(px, py, PANEL_W, PANEL_H, PANEL_BG)
    cv.border(px, py, PANEL_W, PANEL_H, PANEL_BORDER, 2)
    # Colour strip with kicker and story number.
    cv.fill_rect(px, py, PANEL_W, 42, accent)
    cv.draw_text(px + 16, py + 10, kicker, 3, WHITE)
    num = "%02d" % (index + 1)
    cv.draw_text(px + PANEL_W - 16 - text_width(num, 3), py + 10, num, 3, WHITE)
    # Headline, wrapped to at most two lines.
    inner_w = PANEL_W - 32
    head_lines = cv.wrap(headline, 3, inner_w)
    if len(head_lines) > 2:
        print("WARNING: headline overflows panel %d: %r" % (index + 1, headline),
              file=sys.stderr)
        head_lines = head_lines[:2]
    hy = py + 56
    for line in head_lines:
        cv.draw_text(px + 16, hy, line, 3, INK)
        hy += 26
    # Accent rule under the headline.
    cv.fill_rect(px + 16, hy + 6, 64, 5, accent)
    # Body text, wrapped to fit the remaining panel height.
    body_y = hy + 6 + 5 + 14
    max_lines = (py + PANEL_H - 14 - body_y) // 20
    body_lines = cv.wrap(body, 2, inner_w)
    if len(body_lines) > max_lines:
        print("WARNING: body overflows panel %d by %d line(s)"
              % (index + 1, len(body_lines) - max_lines), file=sys.stderr)
        body_lines = body_lines[:max_lines]
    by = body_y
    for line in body_lines:
        cv.draw_text(px + 16, by, line, 2, BODY)
        by += 20


def build():
    cv = Canvas(W, H, PAPER)
    draw_masthead(cv)
    draw_footer(cv)
    for i, (kicker, headline, body, accent) in enumerate(PANELS):
        col = i % 2
        row = i // 2
        px = MARGIN + col * (PANEL_W + GRID_GAP)
        py = GRID_TOP + row * (PANEL_H + GRID_GAP)
        draw_panel(cv, px, py, i, kicker, headline, body, accent)
    return cv


def main():
    out = sys.argv[1] if len(sys.argv) > 1 else os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "..", "entry.png")
    out = os.path.normpath(out)
    cv = build()
    size = write_png(out, cv)
    print("wrote %s (%d bytes, %dx%d)" % (out, size, W, H))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
