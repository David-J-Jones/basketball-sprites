#!/usr/bin/env python3
"""
Retro pixel-art team logos for the league.

Each logo is drawn on a 64 x 64 pixel grid from simple shapes. Every shape
gets automatic 3-tone shading (light from the upper-left) and a dark
outline, the same look as the player sprites. A logo is a round badge:
cream centre, team-color ring, the team's icon, and a ribbon banner with
the team name.

Outputs (integration/react-native/teamLogos/):
    png/<ID>.png        badge, 512 x 512 (8 px per art pixel)
    png/<ID>_icon.png   icon only, transparent, 384 x 384
    svg/<ID>.svg        badge as crisp vector squares
    teams.json          ids, names, colors
    index.ts            require() map for React Native
It also writes the same 30 teams into playerSprites/palettes.json so the
in-game jerseys match the logos. Team colors are defined here, in TEAMS.
plus previews/logos.png.

Run:  python3 tools/generate_logos.py
"""
import json
import math
import os
import shutil

from PIL import Image, ImageDraw

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "integration", "react-native", "teamLogos")
PREVIEW = os.path.join(ROOT, "previews", "logos.png")

N = 64                # art pixels per side
SCALE = 8             # png pixels per art pixel
OUTLINE = "#1c1620"
CREAM = "#f4ebd0"
LIGHT = (-0.6, -0.8)


# ------------------------------------------------------------------ colors
def rgb(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def hexc(c):
    return "#%02x%02x%02x" % tuple(max(0, min(255, int(round(v)))) for v in c)


def mix(a, b, t):
    a, b = rgb(a), rgb(b)
    return hexc(tuple(x + (y - x) * t for x, y in zip(a, b)))


def ramp(base):
    """(highlight, base, shade) for a color, with a slightly warm shadow."""
    return mix(base, "#ffffff", 0.3), base, mix(base, "#2a1020", 0.35)


# ------------------------------------------------------------------ shapes
def ellipse(cx, cy, rx, ry):
    return {(x, y) for y in range(int(cy - ry) - 1, int(cy + ry) + 2)
            for x in range(int(cx - rx) - 1, int(cx + rx) + 2)
            if ((x + 0.5 - cx) / rx) ** 2 + ((y + 0.5 - cy) / ry) ** 2 <= 1}


def rect(x0, y0, x1, y1):
    return {(x, y) for y in range(y0, y1 + 1) for x in range(x0, x1 + 1)}


def poly(pts):
    xs = [p[0] for p in pts]
    ys = [p[1] for p in pts]
    out = set()
    for y in range(int(min(ys)), int(max(ys)) + 1):
        for x in range(int(min(xs)), int(max(xs)) + 1):
            px, py = x + 0.5, y + 0.5
            inside = False
            j = len(pts) - 1
            for i in range(len(pts)):
                xi, yi = pts[i]
                xj, yj = pts[j]
                if (yi > py) != (yj > py) and px < (xj - xi) * (py - yi) / (yj - yi) + xi:
                    inside = not inside
                j = i
            if inside:
                out.add((x, y))
    return out


def line(p0, p1, w=1.0):
    (x0, y0), (x1, y1) = p0, p1
    dx, dy = x1 - x0, y1 - y0
    seg = dx * dx + dy * dy or 1
    r = w / 2
    out = set()
    for y in range(int(min(y0, y1) - r) - 1, int(max(y0, y1) + r) + 2):
        for x in range(int(min(x0, x1) - r) - 1, int(max(x0, x1) + r) + 2):
            px, py = x + 0.5, y + 0.5
            t = max(0, min(1, ((px - x0) * dx + (py - y0) * dy) / seg))
            if math.hypot(px - (x0 + dx * t), py - (y0 + dy * t)) <= r:
                out.add((x, y))
    return out


def arc(cx, cy, r, a0, a1, w=1.0):
    """Thick circular arc, angles in degrees (0 = right, 90 = down)."""
    out = set()
    steps = max(8, int(abs(a1 - a0) / 4))
    pts = [(cx + r * math.cos(math.radians(a0 + (a1 - a0) * i / steps)),
            cy + r * math.sin(math.radians(a0 + (a1 - a0) * i / steps))) for i in range(steps + 1)]
    for a, b in zip(pts, pts[1:]):
        out |= line(a, b, w)
    return out


# ------------------------------------------------------------------ drawing
class Logo:
    """Parts are painted in order. Each part gets its own outline, so parts
    painted later are outlined against the ones below (retro cel look)."""

    def __init__(self):
        self.px = {}

    def part(self, pixels, color, shade=True, outline=True, flat=False):
        pixels = set(pixels)
        if not pixels:
            return
        if outline:
            for (x, y) in pixels:
                for n in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)):
                    if n not in pixels:
                        self.px[n] = OUTLINE
        hi, base, sh = ramp(color)
        xs = [x for x, _ in pixels]
        ys = [y for _, y in pixels]
        cx, cy = (min(xs) + max(xs) + 1) / 2, (min(ys) + max(ys) + 1) / 2
        hw, hh = max(1, (max(xs) - min(xs) + 1) / 2), max(1, (max(ys) - min(ys) + 1) / 2)
        for (x, y) in pixels:
            c = base
            if shade and not flat:
                l = (x + 0.5 - cx) / hw * LIGHT[0] + (y + 0.5 - cy) / hh * LIGHT[1]
                if l > 0.55:
                    c = hi
                elif l < -0.45:
                    c = sh
            self.px[(x, y)] = c

    def paint(self, pixels, color):
        """Paint pixels with no shading or outline (details, highlights)."""
        for p in pixels:
            self.px[p] = color

    def dots(self, pts, color):
        for p in pts:
            self.px[p] = color


# 3 x 5 pixel font for the banner
FONT = {
    "A": "010101111101101", "B": "110101110101110", "C": "011100100100011", "D": "110101101101110",
    "E": "111100110100111", "F": "111100110100100", "G": "011100101101011", "H": "101101111101101",
    "I": "111010010010111", "J": "001001001101010", "K": "101101110101101", "L": "100100100100111",
    "M": "101111111101101", "N": "110101101101101", "O": "010101101101010", "P": "110101110100100",
    "Q": "010101101110011", "R": "110101110101101", "S": "011100010001110", "T": "111010010010010",
    "U": "101101101101111", "V": "101101101101010", "W": "101101111111101", "X": "101101010101101",
    "Y": "101101010010010", "Z": "111001010100111", " ": "000000000000000", "'": "010010000000000",
}


# letters that need more than 3 columns to read (M, N, W)
WIDE = {
    "M": ["10001", "11011", "10101", "10001", "10001"],
    "W": ["10001", "10001", "10101", "11011", "10001"],
    "N": ["1001", "1101", "1011", "1001", "1001"],
}


def glyph(ch):
    if ch in WIDE:
        return WIDE[ch]
    bits = FONT[ch]
    return [bits[i:i + 3] for i in range(0, 15, 3)]


def text_width(text):
    return sum(len(glyph(ch)[0]) + 1 for ch in text) - 1


def text_pixels(text, x0, y0):
    out = set()
    x = x0
    for ch in text:
        rows = glyph(ch)
        for r, row in enumerate(rows):
            for c, b in enumerate(row):
                if b == "1":
                    out.add((x + c, y0 + r))
        x += len(rows[0]) + 1
    return out


# ------------------------------------------------------------------ icons
# Each icon draws into a Logo inside roughly x 12..52, y 8..42.

def icon_buns(L, t):
    # toasted burger buns rising out of phoenix flames
    for pts, col in [([(14, 36), (18, 18), (22, 28), (26, 10), (32, 24), (38, 8), (42, 26), (46, 16), (50, 36)], "#e85a1c"),
                     ([(18, 36), (22, 24), (26, 30), (30, 18), (34, 28), (38, 16), (41, 30), (46, 26), (46, 36)], "#f7b733")]:
        L.part(poly(pts), col, shade=False)
    L.part(ellipse(32, 29, 16, 10) & {(x, y) for x in range(64) for y in range(29)}, "#d98a3a")
    L.part(rect(17, 30, 47, 31), "#6b3a16", shade=False)                   # toasted edge
    L.part(poly([(17, 33), (47, 33), (46, 38), (18, 38)]), "#d98a3a")
    L.dots([(25, 22), (30, 20), (35, 23), (39, 21), (28, 26), (33, 26), (22, 25), (42, 25)], "#fff3d6")


def icon_soaker(L, t):
    L.part(line((44, 26), (58, 20), 1) | line((52, 30), (57, 27), 1), "#58b8f0", shade=False, outline=False)
    L.part(ellipse(55, 21, 2, 1.6) | ellipse(58, 26, 1.6, 1.6), "#58b8f0")
    L.part(rect(20, 26, 30, 38), "#f58220")                                  # grip
    L.part(rect(15, 22, 46, 29), "#7ed321")                                  # barrel
    L.part(ellipse(28, 17, 8, 6), "#f58220")                                 # tank
    L.part(rect(42, 24, 47, 27), "#3a3a3a", shade=False)                     # nozzle
    L.part(rect(33, 30, 42, 33), "#f5e03a")                                  # pump
    L.paint(rect(24, 15, 25, 16), "#ffffff")


def icon_cow(L, t):
    L.part(poly([(16, 14), (22, 17), (21, 20)]) | poly([(48, 14), (42, 17), (43, 20)]), "#efe3c2")   # horns
    L.part(ellipse(17, 22, 5, 3) | ellipse(47, 22, 5, 3), "#f4f4f0")        # ears
    L.part(ellipse(32, 25, 12, 12), "#f4f4f0")                              # head
    L.paint(ellipse(25, 20, 4, 3) | ellipse(39, 28, 3, 4), "#2a2a2a")       # patches
    L.part(ellipse(32, 35, 10, 6), "#f4a6b8")                               # muzzle
    L.paint(ellipse(28, 35, 1.5, 1.5) | ellipse(36, 35, 1.5, 1.5), "#7a3a4a")
    L.dots([(27, 25), (27, 26), (37, 25), (37, 26)], OUTLINE)


def icon_bee(L, t):
    L.part(ellipse(28, 16, 7, 5) | ellipse(38, 15, 6, 4), "#d8f0ff")        # wings
    L.part(poly([(48, 30), (54, 32), (48, 33)]), "#2a2a2a", shade=False)    # stinger
    body = ellipse(35, 30, 13, 8)
    L.part(body, "#f2c12e")
    for x0 in (30, 36, 42):
        L.paint({p for p in body if x0 <= p[0] <= x0 + 2}, "#2a2a2a")
    L.part(ellipse(20, 28, 6, 6), "#2a2a2a")                                # head
    L.paint(ellipse(18, 27, 1.5, 1.5), "#ffffff")
    L.part(line((19, 22), (15, 14), 1) | line((22, 22), (22, 13), 1), "#2a2a2a", shade=False)
    L.part(ellipse(15, 13, 1.5, 1.5) | ellipse(22, 12, 1.5, 1.5), "#2a2a2a")


def icon_rat(L, t):
    L.part(arc(46, 28, 8, -80, 110, 2), "#e79aa6", shade=False)             # tail
    L.part(ellipse(38, 30, 11, 8), "#8a8a92")                               # body
    L.part(poly([(14, 28), (27, 20), (30, 34)]), "#8a8a92")                 # head
    L.part(ellipse(26, 19, 4, 4), "#8a8a92")                                # ear
    L.paint(ellipse(26, 19, 2, 2), "#e79aa6")
    L.part(poly([(16, 33), (28, 44), (32, 34)]), "#f2c14e")                 # pizza slice
    L.paint(line((16, 33), (32, 34), 2), "#c77a2e")
    L.dots([(23, 37), (27, 36), (25, 40)], "#d0342c")
    L.dots([(22, 25), (15, 28)], OUTLINE)


def icon_peach(L, t):
    L.part(ellipse(32, 29, 14, 13), "#f59a6a")
    L.paint(line((32, 18), (30, 38), 1), mix("#f59a6a", "#b0402a", 0.4))  # cleft
    L.paint(ellipse(26, 25, 4, 5), mix("#f59a6a", "#ffd6a0", 0.5))
    L.part(line((32, 17), (33, 11), 2), "#6b3a1a", shade=False)            # stem
    L.part(poly([(33, 13), (44, 8), (46, 13), (38, 16)]), "#4e9a3a")      # leaf


def icon_deli(L, t):
    L.part(poly([(40, 36), (54, 26), (56, 29), (43, 39)]), "#6a9a2e")      # pickle spear
    L.dots([(46, 32), (50, 30), (53, 28)], "#9ac85a")
    L.part(line((24, 11), (24, 22), 1), "#c9a26a", shade=False)            # toothpick + olive
    L.part(ellipse(24, 11, 2.5, 2.5), "#4e7a2e")
    L.part(ellipse(30, 22, 19, 5.5) & {(x, y) for x in range(64) for y in range(23)}, "#d9a05a")  # long roll
    L.paint({(x, 19) for x in range(15, 46, 4)}, "#fff3d6")
    L.part({(x, 23 + (x % 3 == 0)) for x in range(11, 50)} | rect(11, 23, 49, 23), "#4caf50", shade=False)
    L.part(rect(12, 25, 48, 26), "#e05050", shade=False)                  # tomato
    L.part(rect(12, 27, 48, 29), "#f0a0a8", shade=False)                  # meat
    L.part(poly([(12, 30), (48, 30), (45, 32), (15, 32)]), "#f5d142", shade=False)  # cheese
    L.part(poly([(12, 33), (48, 33), (46, 36), (14, 36)]), "#d9a05a")     # bottom


def icon_tourist(L, t):
    L.part(ellipse(32, 29, 11, 12), "#f2b08a")                             # face
    L.paint(ellipse(24, 32, 2.5, 1.5) | ellipse(40, 32, 2.5, 1.5), "#f07a6a")   # sunburn
    L.part(rect(19, 26, 30, 30) | rect(34, 26, 45, 30), "#1f1f28")         # shades
    L.paint(rect(30, 27, 34, 27), "#1f1f28")
    L.dots([(21, 27), (22, 27), (36, 27), (37, 27)], "#9fd8ff")
    L.paint(rect(31, 31, 33, 33), "#ffffff")                               # zinc on the nose
    L.paint(line((28, 36), (36, 36), 1), "#9a3a2a")
    L.part(ellipse(32, 17, 16, 4), "#1bb5a6")                              # bucket hat brim
    L.part(ellipse(32, 14, 10, 6) & {(x, y) for x in range(64) for y in range(16)}, "#ff5c8a")
    L.dots([(26, 12), (30, 10), (35, 12), (38, 14)], "#ffe36e")            # flower print


def icon_breeze(L, t):
    L.part(ellipse(44, 16, 6, 6), "#ffcf4a", shade=False)                  # sun
    trunk = set()
    for i in range(12):                                                    # trunk bends in the wind
        y = 42 - i * 2.2
        x = 24 + (i / 11) ** 2 * 8
        trunk |= ellipse(x, y, 2.2 - i * 0.05, 1.4)
    L.part(trunk, "#9a6a3a")
    L.paint({(x, y) for x, y in trunk if y % 3 == 0}, "#6b4a2a")
    top = (32, 17)
    for a2, ln in ((190, 13), (215, 14), (245, 12), (285, 11), (320, 13), (350, 14)):
        tip = (top[0] + ln * math.cos(math.radians(a2)), top[1] + ln * 0.8 * math.sin(math.radians(a2)) + 5)
        mid = ((top[0] + tip[0]) / 2, (top[1] + tip[1]) / 2 - 2)
        L.part(line(top, mid, 3) | line(mid, tip, 2.2), "#2e9e5a")
    L.part(ellipse(31, 19, 1.8, 1.8) | ellipse(34, 19, 1.8, 1.8), "#6b4a2a")   # coconuts
    for y, x0, x1 in ((28, 36, 52), (34, 38, 54), (40, 12, 22)):
        L.part(line((x0, y), (x1, y), 1.4), "#ffffff", shade=False)       # breeze lines


def icon_voodoo(L, t):
    L.part(line((40, 14), (50, 8), 1) | line((24, 28), (14, 22), 1), "#c0c0c8", shade=False)   # pins
    L.part(ellipse(50, 8, 2, 2), "#d0342c")
    L.part(ellipse(14, 22, 2, 2), "#7bc043")
    L.part(rect(28, 26, 36, 40) | line((28, 28), (19, 34), 4) | line((36, 28), (45, 34), 4) |
           line((30, 40), (27, 44), 4) | line((34, 40), (37, 44), 4), "#c8a36a")
    L.part(ellipse(32, 18, 9, 9), "#c8a36a")                               # head
    L.paint(line((25, 15), (29, 19), 1) | line((29, 15), (25, 19), 1), "#3a2a2a")  # X eye
    L.part(ellipse(37, 17, 2.2, 2.2), "#7a4ba0")                           # button eye
    L.paint(line((27, 23), (37, 23), 1), "#3a2a2a")                        # stitched mouth
    L.dots([(28, 22), (31, 22), (34, 22), (28, 24), (31, 24), (34, 24)], "#3a2a2a")
    L.paint({(32, y) for y in range(28, 40, 2)}, "#8a6a3a")                # stitching


def icon_nice(L, t):
    L.part(ellipse(32, 26, 15, 15), "#ffd23f")
    L.paint(rect(22, 22, 28, 23) | rect(36, 23, 42, 24), "#6b4a00")        # half-lidded eyes
    L.dots([(24, 24), (25, 24), (38, 25), (39, 25)], OUTLINE)
    L.paint(line((21, 18), (28, 19), 1.4), "#6b4a00")                      # flat brow
    L.paint(line((36, 18), (43, 15), 1.4), "#6b4a00")                      # raised brow
    L.paint(line((24, 33), (36, 33), 1.4) | line((36, 33), (40, 30), 1.4), "#6b4a00")  # smirk


def icon_mouse(L, t):
    L.part(poly([(16, 40), (48, 40), (48, 30)]), "#f4c542")                # cheese wedge
    L.paint(ellipse(36, 37, 1.5, 1.5) | ellipse(43, 35, 1.2, 1.2) | ellipse(29, 38, 1, 1), "#c99a1e")
    L.part(arc(20, 26, 6, 90, 250, 1.4), "#e79aa6", shade=False)           # tail
    L.part(ellipse(30, 26, 7, 5), "#a0a0aa")                               # body
    L.part(ellipse(38, 22, 4.5, 4), "#a0a0aa")                             # head
    L.part(ellipse(36, 17, 3, 3), "#a0a0aa")
    L.paint(ellipse(36, 17, 1.5, 1.5), "#e79aa6")
    L.dots([(40, 21), (43, 23)], OUTLINE)


def icon_pocket(L, t):
    L.part(poly([(40, 10), (44, 12), (42, 20), (38, 18)]), "#d8d8e0")      # rocket peeking out
    L.part(poly([(38, 18), (42, 20), (40, 22)]), "#d0342c")
    L.part(poly([(16, 16), (48, 16), (48, 34), (32, 42), (16, 34)]), "#3b5b8c")
    L.paint({(x, 18) for x in range(18, 47, 2)} | {(x, 20) for x in range(18, 47, 2)}, "#e8a33a")
    L.paint(line((18, 33), (32, 40), 1) | line((32, 40), (46, 33), 1), "#e8a33a")
    L.dots([(18, 17), (46, 17)], "#d8b060")


def icon_junker(L, t):
    L.part(ellipse(52, 26, 3, 2.5) | ellipse(56, 21, 4, 3) | ellipse(58, 15, 3, 2.5), "#b8b8bc")  # smoke
    L.part(poly([(12, 34), (14, 26), (22, 25), (26, 18), (40, 18), (46, 25), (51, 27), (51, 34)]), "#9c4a1e")
    L.part(rect(28, 20, 38, 25), "#9fd0e0")                                # window
    L.paint(line((30, 21), (35, 24), 1), "#ffffff")
    L.part(rect(24, 26, 32, 33), "#5a7a9a")                                # mismatched door
    L.paint(ellipse(42, 30, 2, 1.5), "#6b2a0a")                            # rust hole
    L.part(ellipse(20, 35, 4, 4), "#2a2a2a")
    L.part(ellipse(44, 36, 4, 3), "#2a2a2a")                               # flat tire
    L.paint(ellipse(20, 35, 1.5, 1.5), "#b8bcc4")


def icon_corn(L, t):
    L.part(poly([(30, 44), (22, 30), (24, 16), (30, 34)]), "#5e8c31")      # husk left
    L.part(ellipse(32, 24, 7, 15), "#f2c230")                              # cob
    for y in range(12, 38, 3):
        L.paint({(x, y) for x in range(26, 39) if (x + y) % 3 == 0}, "#c99a1e")
    L.part(poly([(34, 44), (42, 30), (40, 16), (35, 34)]), "#6fa33a")      # husk right


def icon_grapes(L, t):
    L.part(line((32, 12), (34, 7), 2), "#6b3a1a", shade=False)
    L.part(poly([(33, 10), (44, 6), (46, 12), (38, 14)]), "#6db33f")
    for cx, cy in [(26, 16), (32, 15), (38, 16), (23, 22), (29, 22), (35, 22), (41, 22),
                   (26, 28), (32, 28), (38, 28), (29, 34), (35, 34), (32, 40)]:
        L.part(ellipse(cx, cy, 3.4, 3.4), "#7a3fb0")


def icon_car(L, t):
    for y in (22, 27, 32):
        L.part(line((6, y), (12, y), 1.2), "#ffffff", shade=False)         # speed lines
    L.part(poly([(14, 34), (16, 27), (28, 25), (34, 20), (40, 20), (44, 25), (54, 27), (55, 34)]), "#d22630")
    L.part(poly([(34, 21), (39, 21), (42, 25), (34, 25)]), "#9fd0e0")      # windshield
    L.part(rect(14, 33, 55, 34), "#d8dce4", shade=False)                   # chrome
    L.part(ellipse(22, 35, 4.2, 4.2), "#2a2a2a")
    L.part(ellipse(47, 35, 4.2, 4.2), "#2a2a2a")
    L.paint(ellipse(22, 35, 2.2, 2.2) | ellipse(47, 35, 2.2, 2.2), "#f4f4f4")   # whitewalls


def icon_bridge(L, t):
    L.part(rect(10, 36, 54, 41), "#4a90d9")                                # water
    L.paint({(x, 38) for x in range(12, 54, 4)}, "#cfe8ff")
    cable = arc(32, 44, 26, 205, 335, 1)
    L.part(cable & {(x, y) for x in range(64) for y in range(64)}, "#c9c3b5", shade=False)
    L.part(rect(18, 12, 21, 36) | rect(43, 12, 46, 36), "#2c4f7c")         # towers
    L.paint(rect(18, 18, 21, 18) | rect(43, 18, 46, 18), "#1c3050")
    L.part(rect(10, 30, 54, 32), "#8a8478")                                # deck
    L.paint({(x, y) for x in range(14, 52, 4) for y in range(24, 30) if (x, y) in cable or y > 27}, "#c9c3b5")


def icon_lawyer(L, t):
    L.part(line((38, 16), (54, 32), 3), "#8a5a2e")                         # gavel handle
    L.part(poly([(40, 8), (48, 16), (44, 20), (36, 12)]), "#6b3a1a")       # gavel head
    L.part(rect(24, 18, 32, 22), "#3a2a1a")                                # case handle
    L.part(rect(14, 22, 42, 40), "#5a3a1e")                                # briefcase
    L.part(rect(26, 26, 30, 29), "#c9a227")                                # clasp
    L.paint(line((14, 30), (42, 30), 1), "#3a2412")


def icon_miner(L, t):
    L.part(line((12, 40), (48, 12), 2.5) | line((52, 40), (16, 12), 2.5), "#8a5a2e")   # pick handles
    L.part(arc(14, 22, 10, -70, 30, 3) | arc(50, 22, 10, 150, 250, 3), "#b8bcc4")    # pick heads
    L.part(ellipse(32, 30, 12, 10) & {(x, y) for x in range(64) for y in range(31)}, "#f2b233")
    L.part(rect(18, 30, 46, 33), "#d99a1e")                                # brim
    L.part(ellipse(32, 24, 3.5, 3.5), "#fff6c0")                           # lamp
    L.paint(ellipse(31, 23, 1, 1), "#ffffff")


def icon_loser(L, t):
    L.part(poly([(24, 30), (20, 44), (26, 41), (28, 44), (30, 32)]), "#4a7ad0")   # ribbon tails
    L.part(poly([(40, 30), (44, 44), (38, 41), (36, 44), (34, 32)]), "#4a7ad0")
    rosette = set()
    for a in range(0, 360, 30):
        rosette |= ellipse(32 + 10 * math.cos(math.radians(a)), 23 + 10 * math.sin(math.radians(a)), 3.5, 3.5)
    L.part(rosette | ellipse(32, 23, 10, 10), "#6fa0e8")
    L.part(ellipse(32, 23, 7.5, 7.5), "#f4ebd0")
    L.paint(rect(29, 18, 31, 27) | rect(29, 26, 36, 28), "#d0342c")        # big L


def icon_bear(L, t):
    L.part(ellipse(20, 14, 5, 5) | ellipse(44, 14, 5, 5), "#6b4226")
    L.paint(ellipse(20, 14, 2.5, 2.5) | ellipse(44, 14, 2.5, 2.5), "#c48a5a")
    L.part(ellipse(32, 26, 14, 13), "#6b4226")
    L.part(ellipse(32, 31, 7, 5.5), "#c48a5a")                             # muzzle
    L.part(ellipse(32, 28, 3, 2), "#2a1a12")                               # nose
    L.paint(line((32, 30), (32, 33), 1) | line((29, 34), (35, 34), 1), "#2a1a12")
    L.dots([(26, 22), (26, 23), (38, 22), (38, 23)], OUTLINE)


def icon_trees(L, t):
    for cx, top, w, col in ((22, 14, 10, "#2f6b3a"), (40, 8, 13, "#1f5a33")):
        L.part(rect(cx - 1, 38, cx + 1, 42), "#7a4e2a")
        for i, (y0, y1) in enumerate(((top, top + 12), (top + 7, top + 21), (top + 14, 38))):
            half = w * (0.55 + 0.25 * i)
            L.part(poly([(cx, y0), (cx + half, y1), (cx - half, y1)]), col)


def icon_tent(L, t):
    L.part(line((32, 8), (32, 14), 1), "#3a3a3a", shade=False)             # pole + flag
    L.part(poly([(32, 8), (39, 10), (32, 12)]), "#b8322b")
    L.part(poly([(32, 13), (52, 40), (12, 40)]), "#e26a2c")
    L.part(poly([(32, 20), (38, 40), (26, 40)]), "#3a2412")                # open flap
    L.paint(line((32, 13), (32, 40), 1), mix("#e26a2c", "#2a1020", 0.35))
    L.part(line((12, 40), (8, 44), 1) | line((52, 40), (56, 44), 1), "#b59b6a", shade=False)   # guy lines


def icon_texas(L, t):
    # Texas (panhandle, Red River, Gulf coast, Rio Grande), fitted to the badge
    raw = [(18, 8), (24, 8), (24, 17), (32, 18), (38, 19), (44, 19), (47, 21), (47, 31), (44, 35),
           (40, 38), (36, 42), (35, 47), (31, 44), (28, 38), (24, 33), (20, 31), (16, 28), (12, 24),
           (10, 22), (18, 22)]
    tx = [(12 + (x - 10) * 1.0, 8 + (y - 8) * 0.88) for x, y in raw]
    L.part(poly(tx), "#c9a26a")
    L.part(arc(31, 26, 16, 0, 360, 3.2), "#d32f2f", shade=False)           # "no" sign
    L.part(line((20, 15), (42, 37), 3.2), "#d32f2f", shade=False)


def icon_spoons(L, t):
    for flip in (1, -1):
        cx = 32
        L.part(line((cx - 14 * flip, 42), (cx + 6 * flip, 18), 2.5), "#a7a9ac")
        L.part(ellipse(cx + 9 * flip, 14, 5, 6.5), "#c9ccd0")
        L.paint(ellipse(cx + 8 * flip, 12, 1.5, 2.5), "#ffffff")


def icon_water(L, t):
    L.part(poly([(32, 8), (42, 24), (22, 24)]) | ellipse(32, 27, 10, 10), "#2a6fdb")
    L.paint(ellipse(28, 26, 2, 4), "#bde3f5")
    for y, off in ((38, 0), (42, 2)):
        wave = set()
        for x in range(12, 53):
            wave.add((x, y + int(round(math.sin((x + off) / 2.2)))))
        L.part(wave, "#5aaae8", shade=False)


def icon_pierogi(L, t):
    for x in (24, 32, 40):
        L.part(arc(x, 12, 3, 90, 270, 1.2), "#ffffff", shade=False)        # steam
    L.part(ellipse(32, 32, 18, 12) & {(x, y) for x in range(64) for y in range(33)}, "#f2ddb0")
    L.part(rect(14, 32, 50, 34), "#e8c890")
    L.dots([(x, 33) for x in range(15, 50, 2)], "#c9a26a")                 # crimped edge
    L.dots([(26, 26), (34, 24), (40, 28)], "#c98a4a")                      # browned bits


def icon_ribs(L, t):
    for x in (18, 44):
        L.part(ellipse(x, 12, 2, 3), "#d0d0d0", shade=False)               # smoke
    L.part(poly([(12, 22), (52, 18), (52, 34), (12, 38)]), "#8b2e16")
    for i, x in enumerate(range(16, 52, 6)):
        y0 = 21 - i * 0.6
        L.part(rect(x, int(y0) - 5, x + 1, int(y0) - 1), "#f4ecd8")        # bone ends
        L.paint(line((x, y0), (x + 1, y0 + 15), 1), "#6a1e0a")
    L.paint(ellipse(28, 26, 6, 2), "#b8401e")                              # sauce shine


def icon_sorry(L, t):
    leaf = [(32, 6), (35, 13), (40, 11), (38, 21), (46, 16), (47, 20), (52, 19), (49, 26), (53, 28),
            (41, 35), (42, 39), (33, 37), (33, 44), (31, 44), (31, 37), (22, 39), (23, 35), (11, 28),
            (15, 26), (12, 19), (17, 20), (18, 16), (26, 21), (24, 11), (29, 13)]
    L.part(poly(leaf), "#d52b1e")
    L.dots([(27, 23), (27, 24), (37, 23), (37, 24)], OUTLINE)              # sheepish eyes
    L.paint(line((25, 20), (29, 21), 1) | line((39, 20), (35, 21), 1), "#7a1010")
    L.paint(line((29, 30), (35, 29), 1), "#7a1010")
    L.part(ellipse(45, 12, 1.5, 2.2), "#9fd8ff")                           # sweat drop


# ------------------------------------------------------------------ league
TEAMS = [
    # id, city, name, jersey, trim, icon
    ("PHX", "Phoenix", "Buns", "#E56020", "#5A2D12", icon_buns),
    ("SLC", "Salt Lake", "Soakers", "#1FA2D6", "#F5E03A", icon_soaker),
    ("CHI", "Chicago", "Cows", "#1E1E1E", "#F4A6B8", icon_cow),
    ("CHA", "Charlotte", "Bees", "#F2C12E", "#1A1A1A", icon_bee),
    ("NY", "New York", "Rats", "#6E6E78", "#D0342C", icon_rat),
    ("GA", "Georgia", "Peaches", "#F59A6A", "#4E9A3A", icon_peach),
    ("BOS", "Boston", "Deli", "#2E6B3A", "#E8C44A", icon_deli),
    ("ORL", "Orlando", "Tourists", "#1BB5A6", "#FF5C8A", icon_tourist),
    ("MIA", "Miami", "Breeze", "#6EC6F0", "#FF8C5A", icon_breeze),
    ("NO", "New Orleans", "Voodoo", "#4B2A6B", "#7BC043", icon_voodoo),
    ("PHI", "Philadelphia", "Nice People", "#1D4FB8", "#FFD23F", icon_nice),
    ("BKN", "Brooklyn", "Mice", "#3A3A40", "#F4C542", icon_mouse),
    ("HOU", "Houston", "Pockets", "#3B5B8C", "#E8A33A", icon_pocket),
    ("DET", "Detroit", "Junkers", "#9C4A1E", "#B8BCC4", icon_junker),
    ("IND", "Indiana", "Corn", "#3F7D2B", "#F2C230", icon_corn),
    ("SF", "San Francisco", "Fruit", "#5B2A86", "#6DB33F", icon_grapes),
    ("LAC", "Los Angeles", "Cars", "#D22630", "#C0C6CF", icon_car),
    ("LAB", "Los Angeles", "Bridges", "#2C4F7C", "#C9C3B5", icon_bridge),
    ("DC", "DC", "Lawyers", "#14213D", "#C9A227", icon_lawyer),
    ("DEN", "Denver", "Miners", "#B8733A", "#2B2B2B", icon_miner),
    ("DAL", "Dallas", "Losers", "#4A5568", "#C0C6CF", icon_loser),
    ("SAC", "Sacramento", "Bears", "#6B4226", "#E8A23A", icon_bear),
    ("MIL", "Milwaukee", "Trees", "#1F5A33", "#7A4E2A", icon_trees),
    ("POR", "Portland", "Tents", "#B59B6A", "#B8322B", icon_tent),
    ("OKC", "Oklahoma", "Texans", "#3B8FD6", "#D32F2F", icon_texas),
    ("SA", "San Antonio", "Spoons", "#1B9AAA", "#C0C6CF", icon_spoons),
    ("MIN", "Minnesota", "Water", "#2A6FDB", "#BDE3F5", icon_water),
    ("CLE", "Cleveland", "Pierogies", "#7A1F3D", "#F2DDB0", icon_pierogi),
    ("MEM", "Memphis", "Ribs", "#8B2E16", "#B0A89E", icon_ribs),
    ("TOR", "Toronto", "Sorries", "#D52B1E", "#F5F5F5", icon_sorry),
]


def badge(team):
    tid, city, name, jersey, trim, icon = team
    L = Logo()
    # ring and cream centre
    L.part(ellipse(32, 30, 28, 28), jersey, shade=False)
    L.paint(ellipse(32, 30, 28, 28) - ellipse(32, 30, 26.5, 26.5), mix(jersey, "#2a1020", 0.3))
    L.part(ellipse(32, 30, 24, 24), trim, shade=False)
    L.part(ellipse(32, 30, 22.5, 22.5), CREAM, shade=False)
    L.paint(ellipse(32, 30, 22.5, 22.5) - ellipse(32, 30, 21, 21), mix(CREAM, "#b0a080", 0.35))
    icon(L, team)
    draw_banner(L, name.upper(), jersey, trim)
    return L


def draw_banner(L, text, jersey, trim):
    dark = mix(jersey, "#2a1020", 0.45)
    L.part(poly([(1, 47), (8, 47), (8, 57), (1, 57), (4, 52)]), dark, shade=False)      # tails
    L.part(poly([(63, 47), (56, 47), (56, 57), (63, 57), (60, 52)]), dark, shade=False)
    L.part(rect(6, 44, 57, 54), jersey, shade=False)
    L.paint(rect(6, 44, 57, 44), mix(jersey, "#ffffff", 0.3))
    L.paint(rect(6, 54, 57, 54), dark)
    w = text_width(text)
    x0 = 32 - (w + 1) // 2
    txt = text_pixels(text, x0, 47)
    # 1px drop shadow keeps the letters readable on any jersey color
    L.paint({(x + 1, y + 1) for x, y in txt}, dark)
    L.paint(txt, CREAM if sum(rgb(jersey)) < 480 else "#1c1620")


def icon_only(team):
    L = Logo()
    team[5](L, team)
    return L


# ------------------------------------------------------------------ output
def to_image(px, size=N, crop=None):
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    pix = img.load()
    for (x, y), c in px.items():
        if 0 <= x < size and 0 <= y < size:
            pix[x, y] = rgb(c) + (255,)
    if crop:
        img = img.crop(crop)
    return img


def to_svg(px, tid):
    rows = {}
    for (x, y), c in px.items():
        if 0 <= x < N and 0 <= y < N:
            rows.setdefault(y, {})[x] = c
    paths = {}
    for y, cols in rows.items():
        xs = sorted(cols)
        i = 0
        while i < len(xs):
            x, c = xs[i], cols[xs[i]]
            j = i
            while j + 1 < len(xs) and xs[j + 1] == xs[j] + 1 and cols[xs[j + 1]] == c:
                j += 1
            n = j - i + 1
            paths.setdefault(c, []).append("M%d %dh%dv1h-%dz" % (x, y, n, n))
            i = j + 1
    body = "".join('<path fill="%s" d="%s"/>' % (c, "".join(d)) for c, d in sorted(paths.items()))
    return ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 %d %d" width="512" height="512" '
            'shape-rendering="crispEdges"><g id="logo-%s">%s</g></svg>' % (N, N, tid, body))


def main():
    shutil.rmtree(OUT, ignore_errors=True)
    for sub in ("png", "svg"):
        os.makedirs(os.path.join(OUT, sub))
    meta = []
    tiles = []
    for team in TEAMS:
        tid, city, name, jersey, trim, _ = team
        b = badge(team)
        img = to_image(b.px)
        img.resize((N * SCALE, N * SCALE), Image.NEAREST).save(os.path.join(OUT, "png", tid + ".png"), optimize=True)
        icon = to_image(icon_only(team).px, crop=(8, 4, 56, 52))
        icon.resize((48 * SCALE, 48 * SCALE), Image.NEAREST).save(os.path.join(OUT, "png", tid + "_icon.png"), optimize=True)
        with open(os.path.join(OUT, "svg", tid + ".svg"), "w") as f:
            f.write(to_svg(b.px, tid))
        meta.append({"id": tid, "city": city, "name": name, "fullName": "%s %s" % (city, name),
                     "jersey": jersey, "trim": trim})
        tiles.append((tid, city, name, img))
    with open(os.path.join(OUT, "teams.json"), "w") as f:
        json.dump(meta, f, indent=2)
    # keep the sprite jerseys in step with the logos: one team list
    pal_path = os.path.join(ROOT, "integration", "react-native", "playerSprites", "palettes.json")
    with open(pal_path) as f:
        pal = json.load(f)
    pal["teams"] = [{"id": m["id"], "name": m["fullName"], "jersey": m["jersey"], "trim": m["trim"]} for m in meta]
    with open(pal_path, "w") as f:
        json.dump(pal, f, indent=2)
        f.write("\n")
    lines = ["// AUTO-GENERATED by tools/generate_logos.py - do not edit by hand.",
             "import type { ImageSourcePropType } from 'react-native';",
             "import teams from './teams.json';", "",
             "export type LeagueTeam = (typeof teams)[number];",
             "export const LEAGUE_TEAMS: LeagueTeam[] = teams;", "",
             "/** Full round badge (512 x 512). */",
             "export const TEAM_LOGOS: Record<string, ImageSourcePropType> = {"]
    lines += ["  %s: require('./png/%s.png')," % (json.dumps(t[0]), t[0]) for t in TEAMS]
    lines += ["};", "", "/** Icon only, transparent (384 x 384). */",
              "export const TEAM_ICONS: Record<string, ImageSourcePropType> = {"]
    lines += ["  %s: require('./png/%s_icon.png')," % (json.dumps(t[0]), t[0]) for t in TEAMS]
    lines += ["};", ""]
    with open(os.path.join(OUT, "index.ts"), "w") as f:
        f.write("\n".join(lines))

    # preview sheet
    cols, cell = 6, 64 * 3
    sheet = Image.new("RGBA", (cols * cell, (len(tiles) + cols - 1) // cols * (cell + 28)), (40, 70, 170, 255))
    d = ImageDraw.Draw(sheet)
    for i, (tid, city, name, img) in enumerate(tiles):
        x, y = (i % cols) * cell, (i // cols) * (cell + 28)
        sheet.alpha_composite(img.resize((cell, cell), Image.NEAREST), (x, y))
        label = "%s %s" % (city, name)
        d.text((x + (cell - d.textlength(label)) / 2, y + cell + 6), label, fill=(255, 255, 255, 255))
    os.makedirs(os.path.dirname(PREVIEW), exist_ok=True)
    sheet.save(PREVIEW)
    print("wrote %d logos" % len(TEAMS))


if __name__ == "__main__":
    main()
