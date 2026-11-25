#!/usr/bin/env python3
"""Arena themes: swappable pixel-art surroundings for the court.

Each arena is a set of layers the game draws around its own court:

  backdrop.png     everything behind the far sideline (walls, rafters, sky,
                   stands), 480 x 64 art px: the band above the court (about
                   the top 40% of a 16:9 screen), wider than the screen so the
                   camera can pan across it
  team.png         white mask over the backdrop's team-colored parts
                   (banners, seat stripes, LED ribbon); tint with the home color
  crowd.png        the fans, 3 frames side by side (sitting, bobbing,
                   cheering), drawn over the backdrop
  crowd_home.png / crowd_away.png
                   white masks over the fans' shirts in the home and away
                   colors; same 3 frames; tint with each team's color
  floor.png        a tileable floor texture, 64 x 64 art px
  overlay.png      full-screen lighting (16:9, 270 x 152 art px, transparent)

All PNGs are stored at SCALE x with nearest-neighbour upscaling so they stay
crisp. Writes integration/react-native/arenas/ (PNGs per arena, arenas.json,
arenaImages.ts) and previews/arenas.png plus previews/arenas/<id>.png
mockups in the game's layout.

Run:  python3 tools/generate_arenas.py   (after generate_sprites.py and generate_logos.py)
"""
import json
import math
import os
import random
import shutil
import sys

from PIL import Image, ImageDraw

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import generate_logos as _lg  # noqa: E402
from generate_logos import text_pixels, text_width  # noqa: E402,F401

for _d, _bits in (("0", "111101101101111"), ("4", "101101111001001")):   # scoreboard digits
    _lg.FONT.setdefault(_d, _bits)

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "integration", "react-native", "arenas")
PREVIEW = os.path.join(ROOT, "previews")
SCALE = 4
BW, BH = 480, 64           # backdrop, art px: the band above the far sideline
FT = 64                    # floor tile
OW, OH = 270, 152          # overlay / screen, art px
CROWD_FRAMES = 3


def hexc(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def mix(a, b, t):
    return tuple(int(round(x + (y - x) * t)) for x, y in zip(a, b))


class Layer:
    def __init__(self, w, h):
        self.w, self.h = w, h
        self.px = {}

    def put(self, x, y, c, a=255):
        x, y = int(x), int(y)
        if not (0 <= x < self.w and 0 <= y < self.h) or a <= 0:
            return
        if a >= 255 or (x, y) not in self.px:
            self.px[(x, y)] = tuple(c[:3]) + (int(a),)
        else:                                               # blend over what's there
            old = self.px[(x, y)]
            t = a / 255
            self.px[(x, y)] = mix(old[:3], c[:3], t) + (max(old[3], int(a)),)

    def rect(self, x0, y0, x1, y1, c, a=255):
        for y in range(int(y0), int(y1) + 1):
            for x in range(int(x0), int(x1) + 1):
                self.put(x, y, c, a)

    def disc(self, cx, cy, r, c, a=255):
        for y in range(int(cy - r) - 1, int(cy + r) + 2):
            for x in range(int(cx - r) - 1, int(cx + r) + 2):
                if (x + 0.5 - cx) ** 2 + (y + 0.5 - cy) ** 2 <= r * r:
                    self.put(x, y, c, a)

    def line(self, x0, y0, x1, y1, c, a=255):
        n = int(max(abs(x1 - x0), abs(y1 - y0))) + 1
        for i in range(n + 1):
            t = i / max(1, n)
            self.put(round(x0 + (x1 - x0) * t), round(y0 + (y1 - y0) * t), c, a)

    def vgrad(self, y0, y1, top, bottom):
        for y in range(y0, y1 + 1):
            c = mix(top, bottom, (y - y0) / max(1, y1 - y0))
            for x in range(self.w):
                self.put(x, y, c)

    def image(self, scale=SCALE):
        img = Image.new("RGBA", (self.w, self.h), (0, 0, 0, 0))
        for (x, y), c in self.px.items():
            img.putpixel((x, y), c)
        return img.resize((self.w * scale, self.h * scale), Image.NEAREST) if scale != 1 else img


WHITE = (255, 255, 255)
SKINS = [hexc(c) for c in ("#f1c7a5", "#d9a577", "#b07a52", "#8a5a3b", "#5e3b28", "#3f2719")]
HAIRS = [hexc(c) for c in ("#1a1618", "#2c1e14", "#5a3a22", "#8a5a2a", "#c9a24a", "#9a9aa2")]
NEUTRAL_SHIRTS = [hexc(c) for c in ("#f4f1ea", "#2a2a30", "#6e6e78", "#3a5a8a", "#8a3a3a", "#4a7a4a", "#c9a24a")]


# ------------------------------------------------------------------ crowd
def crowd(rows, density, seed, glow=None, standing=False):
    """Fans in rows. rows: [(y_top_of_head, x0, x1)]. Returns (detail, home
    mask, away mask) Layers, each 3 frames wide."""
    rng = random.Random(seed)
    det = Layer(BW * CROWD_FRAMES, BH)
    home = Layer(BW * CROWD_FRAMES, BH)
    away = Layer(BW * CROWD_FRAMES, BH)
    for (y0, x0, x1) in rows:
        x = x0 + rng.randint(0, 3)
        while x < x1:
            if rng.random() < density:
                skin, hair = rng.choice(SKINS), rng.choice(HAIRS)
                r = rng.random()
                team = "home" if r < 0.5 else "away" if r < 0.65 else None
                shirt = rng.choice(NEUTRAL_SHIRTS)
                bobs, cheers = rng.random() < 0.5, rng.random() < 0.35
                bald, hat = rng.random() < 0.12, rng.random() < 0.1
                light = glow and rng.random() < 0.3
                for f in range(CROWD_FRAMES):
                    ox = f * BW + x
                    dy = -1 if (f == 1 and bobs) or (f == 2 and cheers) else 0
                    hy = y0 + dy + rng.choice((0, 0, 1)) * 0
                    # head 4 x 4 with hair on top
                    for yy in range(4):
                        for xx in range(4):
                            if (xx, yy) in ((0, 0), (3, 0)):
                                continue
                            c = hair if (yy == 0 and not bald) or (yy == 1 and xx in (0, 3) and not bald) else skin
                            if hat and yy == 0:
                                c = shirt
                            det.put(ox + xx, hy + yy, c)
                    det.put(ox + 2, hy + 2, (30, 20, 20))           # an eye, looking at the court
                    # shoulders and shirt
                    body_h = 5 if standing else 4
                    for yy in range(body_h):
                        for xx in range(-1, 5):
                            if yy == 0 and xx in (-1, 4):
                                continue
                            p = (ox + xx, hy + 4 + yy)
                            det.put(*p, shirt)
                            if team == "home":
                                home.put(*p, WHITE)
                            elif team == "away":
                                away.put(*p, WHITE)
                    if f == 2 and cheers:                           # arms up
                        for yy in range(4):
                            det.put(ox - 1, hy + 1 - yy + 2, skin)
                            det.put(ox + 4, hy + 1 - yy + 2, skin)
                        if light:
                            det.put(ox - 1, hy - 2, glow[(x // 7) % len(glow)])
                            det.put(ox + 4, hy - 2, glow[(x // 5) % len(glow)])
                    elif light and f != 2:
                        det.put(ox + 4, hy + 5, glow[(x // 7) % len(glow)])  # phone / glow stick
            x += rng.randint(6, 8)
    return det, home, away


def seats(L, y0, y1, c, row_h=8, stripe=None, team=None):
    """Rows of seats behind the fans (with an optional team-colored stripe)."""
    for y in range(y0, y1 + 1):
        k = (y - y0) % row_h
        col = mix(c, (0, 0, 0), 0.35) if k == row_h - 1 else c if k > 2 else mix(c, (255, 255, 255), 0.08)
        for x in range(L.w):
            L.put(x, y, col)
        if stripe is not None and k == 3:
            for x in range(L.w):
                if team is not None:
                    team.put(x, y, WHITE)


# ------------------------------------------------------------------ themes
# Each backdrop is BH (64) art px tall: the band the game shows above the far
# sideline (about the top 40% of the screen), so everything here is on screen.

def pro_arena():
    L, T = Layer(BW, BH), Layer(BW, BH)
    L.vgrad(0, 15, hexc("#0b0f1e"), hexc("#18203a"))
    for x in range(BW):                                             # truss
        L.put(x, 1, (70, 76, 96))
        L.put(x, 4, (70, 76, 96))
        if x % 4 < 2:
            L.put(x, 2 + (x // 2) % 2, (56, 60, 78))
    for cx in range(24, BW, 48):                                    # light rigs
        if 206 < cx < 274:
            continue
        L.rect(cx - 5, 5, cx + 5, 6, (40, 44, 58))
        for k in range(-4, 5, 2):
            L.put(cx + k, 7, (255, 250, 220))
            L.put(cx + k, 8, (255, 236, 170), 120)
    L.rect(212, 0, 268, 18, (24, 26, 34))                            # jumbotron
    L.rect(214, 2, 266, 15, (18, 54, 112))
    for (x, y) in text_pixels("DEFENSE", 240 - text_width("DEFENSE") // 2, 4):
        L.put(x, y, (255, 214, 64))
    for x in range(216, 265, 3):
        L.put(x, 12, (90, 170, 255))
    L.rect(214, 16, 266, 17, (200, 200, 205))
    T.rect(214, 16, 266, 17, WHITE)
    for bx in range(6, BW, 40):                                     # banners in team color
        if 200 < bx < 274:
            continue
        L.rect(bx, 6, bx + 6, 14, (200, 200, 205))
        T.rect(bx, 6, bx + 6, 14, WHITE)
        L.rect(bx + 2, 8, bx + 4, 8, (250, 250, 250))
        L.rect(bx + 1, 10, bx + 5, 12, (250, 250, 250))
    seats(L, 16, 33, hexc("#232a48"))                                # upper deck
    L.rect(0, 34, BW, 37, (14, 16, 26))                              # LED ribbon board
    L.rect(0, 35, BW, 36, (220, 220, 230))
    T.rect(0, 35, BW, 36, WHITE)
    for x in range(0, BW, 6):
        L.put(x, 35, (255, 255, 255))
    seats(L, 38, 58, hexc("#2c355a"))                                # lower bowl
    L.rect(0, 59, BW, 63, (22, 24, 34))
    L.rect(0, 59, BW, 59, (60, 66, 90))
    rows = [(17, 0, BW), (25, 0, BW), (39, 0, BW), (47, 0, BW)]
    return L, T, crowd(rows, 0.9, 1)


def retro_gym():
    L, T = Layer(BW, BH), Layer(BW, BH)
    brick, mortar = hexc("#9a5a3a"), hexc("#c9a68a")
    for y in range(0, 31):
        for x in range(BW):
            row = y // 4
            edge = y % 4 == 3 or (x + (row % 2) * 4) % 8 == 0
            L.put(x, y, mortar if edge else mix(brick, (60, 30, 20), ((x * 7 + row * 13) % 5) / 20))
    for wx in range(14, BW, 64):                                    # high windows with daylight
        if 196 < wx < 280:
            continue
        L.rect(wx, 2, wx + 26, 15, (60, 50, 40))
        L.rect(wx + 1, 3, wx + 25, 14, (170, 210, 235))
        for k in (9, 17):
            L.rect(wx + k, 3, wx + k, 14, (60, 50, 40))
        L.rect(wx + 1, 9, wx + 25, 9, (60, 50, 40))
        L.rect(wx + 2, 4, wx + 6, 7, (235, 248, 255))
    for px in range(0, BW, 12):                                     # pennants on a string
        L.line(px, 17, px + 12, 17, (230, 220, 200))
        for k in range(6):
            for j in range(-(5 - k) // 2, (5 - k) // 2 + 1):
                L.put(px + 6 + j, 18 + k, (220, 220, 220))
                T.put(px + 6 + j, 18 + k, WHITE)
    L.rect(212, 0, 268, 28, (20, 20, 22))                            # bulb scoreboard
    L.rect(213, 1, 267, 27, (34, 30, 30))
    for (txt, x0) in (("HOME", 217), ("GUEST", 243)):
        for (x, y) in text_pixels(txt, x0, 3):
            L.put(x, y, (240, 220, 170))
    for x0 in (219, 247):
        for (x, y) in text_pixels("00", x0, 11):
            for dx in (0, 1):
                for dy in (0, 1):
                    L.put(x * 2 - x0 + dx, y * 2 - 11 + dy, (255, 80, 50))
    L.rect(236, 20, 244, 25, (60, 60, 60))
    for (x, y) in text_pixels("Q4", 237, 21):
        L.put(x, y, (120, 255, 120))
    for y in range(31, 59):                                         # wooden bleachers
        k = (y - 31) % 7
        c = hexc("#c98a4a") if k < 2 else hexc("#a86a34") if k < 6 else hexc("#5a3a1e")
        for x in range(BW):
            L.put(x, y, c)
    L.rect(0, 59, BW, 63, (200, 200, 205))                           # wall pads in team color
    T.rect(0, 59, BW, 63, WHITE)
    for x in range(0, BW, 24):
        L.rect(x, 59, x, 63, (60, 60, 64))
    rows = [(32, 0, BW), (39, 0, BW), (46, 0, BW)]
    return L, T, crowd(rows, 0.45, 2)


def street():
    L, T = Layer(BW, BH), Layer(BW, BH)
    L.vgrad(0, 40, hexc("#3a2a6a"), hexc("#ff9a5a"))
    L.disc(300, 11, 9, (255, 214, 120))
    L.disc(300, 11, 6, (255, 240, 180))
    rng = random.Random(5)
    x = 0
    while x < BW:                                                   # skyline
        w, h = rng.randint(12, 26), rng.randint(10, 30)
        c = mix(hexc("#2a1a40"), hexc("#4a2a5a"), rng.random())
        L.rect(x, 40 - h, x + w, 40, c)
        for wy in range(40 - h + 2, 39, 3):
            for wx in range(x + 2, x + w - 1, 3):
                if rng.random() < 0.3:
                    L.put(wx, wy, (255, 210, 120))
        if rng.random() < 0.3:
            L.rect(x + w // 2, 40 - h - 5, x + w // 2, 40 - h, c)
        x += w + rng.randint(0, 3)
    for cx in (16, 118, 362, 460):                                  # trees
        L.rect(cx - 1, 30, cx + 1, 46, (70, 46, 30))
        for (dx, dy, r) in ((0, 22, 9), (-6, 28, 7), (6, 28, 7), (0, 16, 6)):
            L.disc(cx + dx, dy, r, mix(hexc("#1f5a33"), hexc("#3f8a3a"), (dx + 6) / 12))
    L.rect(0, 41, BW, 58, hexc("#5a6a52"))                          # grass behind the fence
    for x in range(0, BW, 3):
        L.put(x, 41 + (x * 7) % 4, hexc("#4a5a42"))
    L.rect(0, 59, BW, 63, hexc("#9a9a96"))                          # curb
    L.rect(0, 59, BW, 59, hexc("#c9c9c4"))
    det, home, away = crowd([(40, 0, BW), (47, 0, BW)], 0.42, 3, standing=True)
    fence = Layer(BW * CROWD_FRAMES, BH)                            # chain-link, over the fans
    for f in range(CROWD_FRAMES):
        for y in range(24, 59):
            for x in range(BW):
                if (x + y) % 6 == 0 or (x - y) % 6 == 0:
                    fence.put(f * BW + x, y, (176, 182, 186), 140)
        for x in range(0, BW, 40):
            fence.rect(f * BW + x, 21, f * BW + x + 1, 58, (120, 124, 128))
        fence.rect(f * BW, 22, f * BW + BW - 1, 23, (130, 134, 138))
    for p, c in fence.px.items():
        det.px[p] = c if c[3] == 255 or p not in det.px else mix(det.px[p][:3], c[:3], c[3] / 255) + (255,)
    return L, T, (det, home, away)


def neon():
    L, T = Layer(BW, BH), Layer(BW, BH)
    L.vgrad(0, 63, hexc("#07040f"), hexc("#160a2a"))
    for x in range(BW):                                             # synth grid on the back wall
        for y in range(0, 22):
            if x % 20 == 0 or y % 7 == 0:
                L.put(x, y, (56, 18, 86))

    def tube(pts, c):
        for (x0, y0), (x1, y1) in zip(pts, pts[1:]):
            n = int(max(abs(x1 - x0), abs(y1 - y0))) + 1
            for i in range(n + 1):
                t = i / max(1, n)
                x, y = x0 + (x1 - x0) * t, y0 + (y1 - y0) * t
                for dx, dy in ((2, 0), (-2, 0), (0, 2), (0, -2), (1, 1), (-1, -1), (1, -1), (-1, 1)):
                    L.put(x + dx, y + dy, c, 80)
                for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                    L.put(x + dx, y + dy, c, 220)
                L.put(x, y, WHITE)
    pink, cyan, gold = (255, 60, 190), (60, 230, 255), (255, 214, 64)
    tube([(x, 4 + (5 if (x // 16) % 2 else 0)) for x in range(-16, BW + 32, 16)], gold)
    tube([(0, 16), (BW - 1, 16)], pink)
    tube([(0, 20), (BW - 1, 20)], cyan)
    orange = (255, 140, 40)
    tube([(240 + 9 * math.cos(2 * math.pi * k / 24), 10 + 8 * math.sin(2 * math.pi * k / 24)) for k in range(25)],
         orange)
    tube([(231, 10), (249, 10)], orange)
    tube([(240, 2), (240, 18)], orange)
    seats(L, 23, 58, hexc("#120c22"))
    L.rect(0, 59, BW, 63, (10, 6, 18))                              # LED strip in team color
    L.rect(0, 60, BW, 61, (230, 230, 240))
    T.rect(0, 60, BW, 61, WHITE)
    rows = [(24, 0, BW), (32, 0, BW), (40, 0, BW), (48, 0, BW)]
    glow = [pink, cyan, (255, 240, 120), (140, 255, 120)]
    det, home, away = crowd(rows, 0.82, 4, glow=glow)
    for p, c in list(det.px.items()):                               # silhouettes in the dark, lit by glow sticks
        if c[:3] not in [g for g in glow]:
            det.px[p] = mix(c[:3], (22, 12, 40), 0.86) + (255,)
    return L, T, (det, home, away)


def beach():
    L, T = Layer(BW, BH), Layer(BW, BH)
    L.vgrad(0, 18, hexc("#4ab0f0"), hexc("#bde8ff"))
    L.disc(430, 6, 6, (255, 240, 170))
    L.disc(430, 6, 4, (255, 252, 220))
    rng = random.Random(9)
    for cx in (90, 180, 300):                                       # clouds
        for k in range(4):
            L.disc(cx + k * 5 + rng.randint(-1, 1), 7 + rng.randint(-1, 1), 3 + rng.randint(0, 1), (250, 252, 255))
    L.vgrad(18, 28, hexc("#1f78c8"), hexc("#3ab0d8"))               # ocean
    for y in range(19, 28, 3):
        for x in range((y * 7) % 11, BW, 13):
            L.rect(x, y, x + 3, y, (230, 248, 255))
    for y in range(28, 64):                                         # sand
        for x in range(BW):
            c = mix(hexc("#f2d69a"), hexc("#d8b070"), (y - 28) / 36)
            if (x * 13 + y * 7) % 17 == 0:
                c = mix(c, (150, 110, 60), 0.4)
            L.put(x, y, c)
    L.rect(0, 59, BW, 63, hexc("#b08a5a"))                          # boardwalk edge
    for x in range(0, BW, 10):
        L.rect(x, 59, x, 63, hexc("#8a6a42"))

    def palm(bx, lean):
        for k in range(50):                                         # curved trunk
            x = bx + lean * (k / 50) ** 2 * 12
            L.rect(x, 58 - k, x + 2, 58 - k, (130, 90, 50) if k % 4 else (100, 66, 36))
        tx, ty = bx + lean * 12, 9
        for a in (-170, -130, -60, -15, 200, 100, 30):
            for i in range(16):
                r = math.radians(a)
                x, y = tx + math.cos(r) * i, ty + math.sin(r) * i * 0.45 + (i * i) / 36
                L.rect(x, y, x + 1, y + 1, (40, 140, 60) if i % 3 else (30, 110, 50))
        L.disc(tx, ty + 2, 2, (110, 70, 30))
    palm(30, 1)
    palm(116, 1)
    palm(362, -1)
    palm(448, -1)
    L.rect(296, 12, 320, 17, (220, 50, 50))                          # lifeguard tower
    L.rect(296, 12, 320, 12, (250, 250, 250))
    L.rect(298, 18, 318, 25, (250, 250, 250))
    L.rect(300, 20, 316, 23, (90, 150, 200))
    for x in (299, 317):
        L.line(x, 25, x + (-3 if x < 308 else 3), 44, (200, 190, 170))
    for ux in (60, 150, 222, 268, 340, 420):                        # umbrellas in team color
        L.rect(ux, 34, ux, 50, (120, 120, 120))
        for k in range(8):
            for j in range(-k - 1, k + 2):
                if k > 1:
                    stripe = ((j + 20) // 3) % 2 == 0
                    L.put(ux + j, 27 + k, (200, 200, 205) if stripe else (250, 250, 250))
                    if stripe:
                        T.put(ux + j, 27 + k, WHITE)
    rows = [(41, 0, BW), (50, 0, BW)]
    return L, T, crowd(rows, 0.36, 6)


def rooftop():
    L, T = Layer(BW, BH), Layer(BW, BH)
    L.vgrad(0, 44, hexc("#0a0f2a"), hexc("#2a2f5a"))
    rng = random.Random(11)
    for _ in range(80):
        L.put(rng.randrange(BW), rng.randrange(20), (255, 255, 230) if rng.random() < 0.3 else (170, 180, 220))
    L.disc(150, 8, 5, (240, 240, 220))
    L.disc(152, 7, 4, hexc("#0c1230"))                               # crescent moon
    x = 0
    while x < BW:                                                   # skyline with lit windows
        w, h = rng.randint(14, 30), rng.randint(12, 36)
        c = mix(hexc("#14183a"), hexc("#22285a"), rng.random())
        L.rect(x, 44 - h, x + w, 44, c)
        for wy in range(44 - h + 2, 43, 3):
            for wx in range(x + 2, x + w - 1, 3):
                if rng.random() < 0.38:
                    L.put(wx, wy, (255, 214, 120) if rng.random() < 0.8 else (140, 220, 255))
        x += w + 1
    for wt in (330, 70):                                            # water towers
        L.rect(wt, 6, wt + 16, 20, (60, 44, 34))
        L.rect(wt + 2, 3, wt + 14, 6, (50, 36, 28))
        for lx in (wt + 2, wt + 14):
            L.line(lx, 20, lx + (-3 if lx < wt + 8 else 3), 34, (50, 36, 28))
        for y in range(8, 20, 3):
            L.rect(wt, y, wt + 16, y, (44, 32, 24))
    for (x0, x1, sag) in ((0, 160, 7), (160, 320, 8), (320, 479, 7)):     # string lights
        for x in range(x0, x1 + 1):
            t = (x - x0) / (x1 - x0)
            y = 22 + sag * 4 * t * (1 - t)
            L.put(x, y, (40, 40, 40))
            if (x - x0) % 7 == 3:
                L.put(x, y + 1, (255, 220, 140))
                L.put(x, y + 2, (255, 200, 100), 150)
    L.rect(0, 46, BW, 58, hexc("#3a2a2a"))                          # brick parapet
    for y in range(46, 58):
        for x in range(BW):
            if y % 4 == 1 or (x + (y // 4) % 2 * 4) % 9 == 0:
                L.put(x, y, hexc("#2a1e1e"))
    L.rect(0, 44, BW, 45, (200, 200, 205))                           # team-color rail
    T.rect(0, 44, BW, 45, WHITE)
    L.rect(0, 59, BW, 63, hexc("#2a2a30"))
    det, home, away = crowd([(36, 0, BW), (45, 0, BW)], 0.46, 7, standing=True)
    return L, T, (det, home, away)


# ------------------------------------------------------------------ floors and light
def floor(kind):
    F = Layer(FT, FT)
    rng = random.Random(hash(kind) & 0xffff)
    if kind in ("maple", "honey", "boards"):
        base = {"maple": hexc("#d9a066"), "honey": hexc("#c98238"), "boards": hexc("#dcc79a")}[kind]
        for y in range(FT):
            strip = y // 4
            off = (strip * 23) % FT
            tone = ((strip * 37) % 7 - 3) / 60
            for x in range(FT):
                c = mix(base, (255, 255, 255) if tone > 0 else (0, 0, 0), abs(tone))
                if y % 4 == 3:
                    c = mix(c, (60, 30, 10), 0.18)                  # board seam
                if (x + off) % 32 == 0:
                    c = mix(c, (60, 30, 10), 0.3)                   # board end
                if (x * 3 + y * 11 + strip) % 19 == 0:
                    c = mix(c, (120, 70, 30), 0.12)                 # grain
                if kind == "boards" and rng.random() < 0.02:
                    c = mix(c, (200, 170, 110), 0.6)                # sand in the cracks
                F.put(x, y, c)
        if kind == "honey":
            for _ in range(6):                                      # scuffs on an old floor
                x, y = rng.randrange(FT), rng.randrange(FT)
                for k in range(5):
                    F.put(x + k, y, mix(F.px.get((x + k, y), base + (255,))[:3], (90, 60, 40), 0.35))
    elif kind == "concrete":
        for y in range(FT):
            for x in range(FT):
                v = rng.random()
                F.put(x, y, mix(hexc("#8e8e8a"), hexc("#6e6e6a") if v < 0.5 else hexc("#a8a8a2"), abs(v - 0.5)))
        x, y = 10, 0
        while y < FT:                                               # a crack across the slab
            F.put(x, y, (60, 60, 58))
            x = (x + rng.choice((-1, 0, 1))) % FT
            y += 1
    elif kind == "glossy":
        for y in range(FT):
            for x in range(FT):
                c = mix(hexc("#14102a"), hexc("#1e1840"), ((x + y * 2) % 16) / 32)
                if (x - y) % 32 == 0:
                    c = mix(c, (120, 80, 200), 0.25)                # reflection streak
                F.put(x, y, c)
    elif kind == "painted":
        for y in range(FT):
            for x in range(FT):
                v = rng.random()
                c = hexc("#2f6b5a")
                if v < 0.08:
                    c = mix(c, (0, 0, 0), 0.25)
                elif v > 0.93:
                    c = mix(c, (255, 255, 255), 0.15)
                F.put(x, y, c)
    return F


def overlay(kind):
    O = Layer(OW, OH)
    if kind == "spotlights":
        for cx in (70, 200):
            for y in range(0, OH):
                half = 6 + y * 0.45
                for x in range(int(cx - half), int(cx + half)):
                    O.put(x, y, (255, 250, 230), int(26 * (1 - y / OH)))
    elif kind == "sunbeams":
        for x0 in (30, 100, 170, 240):
            for y in range(0, OH):
                for x in range(x0 + y // 2, x0 + y // 2 + 10):
                    O.put(x, y, (255, 236, 190), int(30 * (1 - y / OH)))
    elif kind == "sunset":
        for y in range(OH):
            a = int(60 * (1 - y / OH) ** 2)
            for x in range(OW):
                O.put(x, y, (255, 140, 80), a)
    elif kind == "neon":
        for y in range(OH):
            for x in range(OW):
                dl, dr = math.hypot(x, y) / 160, math.hypot(OW - x, y) / 160
                if dl < 1:
                    O.put(x, y, (255, 60, 190), int(50 * (1 - dl) ** 2))
                if dr < 1:
                    O.put(x, y, (60, 230, 255), int(50 * (1 - dr) ** 2))
        for (x0, x1) in ((20, 180), (250, 90), (120, 270)):         # lasers
            for y in range(0, 80):
                x = x0 + (x1 - x0) * y / 80
                O.put(x, y, (255, 255, 255), 90)
                O.put(x + 1, y, (255, 60, 190) if x0 < x1 else (60, 230, 255), 70)
    elif kind == "glare":
        for y in range(OH):
            for x in range(OW):
                d = math.hypot(x - 240, y - 4) / 150
                if d < 1:
                    O.put(x, y, (255, 252, 220), int(70 * (1 - d) ** 2))
    elif kind == "night":
        rng = random.Random(3)
        for _ in range(16):                                         # string-light bokeh
            cx, cy, r = rng.randrange(OW), rng.randrange(4, 40), rng.randint(1, 3)
            for y in range(cy - r, cy + r + 1):
                for x in range(cx - r, cx + r + 1):
                    if (x - cx) ** 2 + (y - cy) ** 2 <= r * r:
                        O.put(x, y, (255, 200, 110), 70)
        for y in range(OH):
            for x in range(OW):
                d = max(abs(x - OW / 2) / (OW / 2), abs(y - OH / 2) / (OH / 2))
                if d > 0.75:
                    O.put(x, y, (10, 14, 40), int(90 * (d - 0.75) / 0.25))
    return O


ARENAS = [
    # id, label, description, builder, floor, overlay, court colors
    ("pro_arena", "Pro Arena", "Rafters, light rigs, a jumbotron and a full house", pro_arena, "maple", "spotlights",
     {"line": "#f4f1ea", "apron": "#1c2442", "paint": "#2c355a"}),
    ("retro_gym", "Old School Gym", "Brick walls, high windows, wooden bleachers and a bulb scoreboard", retro_gym,
     "honey", "sunbeams", {"line": "#f4f1ea", "apron": "#7a3a24", "paint": "#9a2a2a"}),
    ("street", "Street Court", "Sunset skyline, chain-link fence and cracked concrete", street, "concrete", "sunset",
     {"line": "#f4f1ea", "apron": "#6a6a66", "paint": "#2a5aa0"}),
    ("neon", "Neon Nights", "Neon tubes, lasers and a glow-stick crowd on a glossy floor", neon, "glossy", "neon",
     {"line": "#3be8f0", "apron": "#0a0616", "paint": "#ff3cbe"}),
    ("beach", "Beach Court", "Ocean, palm trees and a lifeguard tower on sun-bleached boards", beach, "boards", "glare",
     {"line": "#ffffff", "apron": "#e8c88a", "paint": "#1f78c8"}),
    ("rooftop", "Rooftop Night", "City lights, a water tower and string lights over a painted court", rooftop,
     "painted", "night", {"line": "#f4f1ea", "apron": "#2a2a30", "paint": "#c9a227"}),
]


def main():
    shutil.rmtree(os.path.join(OUT, "png"), ignore_errors=True)
    os.makedirs(os.path.join(OUT, "png"))
    meta = {"_comment": "AUTO-GENERATED by tools/generate_arenas.py. Sizes are art px; PNGs are stored at `scale`x.",
            "scale": SCALE, "backdrop": [BW, BH], "floorTile": FT, "overlay": [OW, OH],
            "crowdFrames": CROWD_FRAMES, "crowdLoop": [0, 1, 0, 2], "crowdFps": 4, "arenas": []}
    built = {}
    for aid, label, desc, fn, fl, ov, colors in ARENAS:
        L, T, (det, home, away) = fn()
        F, O = floor(fl), overlay(ov)
        imgs = {"backdrop": L.image(), "team": T.image(), "crowd": det.image(), "crowd_home": home.image(),
                "crowd_away": away.image(), "floor": F.image(), "overlay": O.image()}
        for k, im in imgs.items():
            im.save(os.path.join(OUT, "png", "%s_%s.png" % (aid, k)), optimize=True)
        meta["arenas"].append({"id": aid, "label": label, "description": desc, "floor": fl, "lighting": ov, **colors})
        built[aid] = (L, T, det, home, away, F, O, colors)
    with open(os.path.join(OUT, "arenas.json"), "w") as f:
        json.dump(meta, f, indent=1)
    keys = ("backdrop", "team", "crowd", "crowd_home", "crowd_away", "floor", "overlay")
    lines = ["// AUTO-GENERATED by tools/generate_arenas.py - do not edit by hand.",
             "import type { ImageSourcePropType } from 'react-native';",
             "import type { ArenaId, ArenaLayer } from './arenas';", "",
             "/** Every layer of every arena, required lazily so only the arena in use is loaded. */",
             "export const ARENA_IMAGES: Record<ArenaId, Record<ArenaLayer, () => ImageSourcePropType>> = {"]
    for aid, *_ in ARENAS:
        lines.append("  %s: {" % aid)
        lines += ["    %s: () => require('./png/%s_%s.png')," % (k, aid, k) for k in keys]
        lines.append("  },")
    lines += ["};", ""]
    with open(os.path.join(OUT, "arenaImages.ts"), "w") as f:
        f.write("\n".join(lines))
    mockups(built)
    print("arenas:", ", ".join(a[0] for a in ARENAS))


# ------------------------------------------------------------------ previews in the game's layout
def tinted(mask, color):
    out = Image.new("RGBA", mask.size, color + (0,))
    out.putalpha(mask.getchannel("A"))
    return out


def mockups(built):
    import generate_sprites as G
    teams = json.load(open(os.path.join(ROOT, "integration", "react-native", "teamUniforms", "uniforms.json")))
    os.makedirs(os.path.join(PREVIEW, "arenas"), exist_ok=True)
    G.use_body(G.MID_BODY)
    home_t, away_t = ("POR", "CHI")
    hu, au = teams[home_t]["home"], teams[away_t]["away"]
    players = []
    for k, (anim, i) in enumerate((("dribble_run", 3), ("defense_stance", 0), ("run", 6), ("guard_on_ball", 2),
                                   ("idle", 0), ("run", 2))):
        fn = {n: f for n, f, *_ in G.ANIMS}[anim]
        grid, info = G.render(fn()[i], ["crew", "afro", "fade", "locs", "buzz", "high_top"][k])
        u = hu if k % 2 == 0 else au
        tc = {"skin": SKINS[(k * 2 + 1) % 6], "jersey": hexc(u["jersey"]), "trim": hexc(u["trim"]),
              "shorts": hexc(u["shorts"]), "hair": HAIRS[k % 3], "facial": HAIRS[k % 3]}
        im = Image.new("RGBA", (G.FRAME_W, G.FRAME_H), (0, 0, 0, 0))
        for (x, y), tag in grid.items():
            if 0 <= x < G.FRAME_W and 0 <= y < G.FRAME_H:
                t, _ = G.split_tag(tag)
                if t in G.FIXED:
                    c = G.FIXED[t][:3]
                else:
                    slot = G.TINTED[t][0]
                    c = next((v for kk, v in tc.items() if slot.startswith(kk)), (180, 180, 180))
                im.putpixel((x, y), tuple(c) + (255,))
        if k % 2:
            im = im.transpose(Image.FLIP_LEFT_RIGHT)
        players.append(im)
    logo = Image.open(os.path.join(ROOT, "integration", "react-native", "teamLogos", "png", home_t + "_icon.png"))
    home_c, away_c = hexc(hu["jersey"]), hexc(au["jersey"])
    sheet_tiles = []
    for aid, label, desc, *_ in ARENAS:
        L, T, det, home, away, F, O, colors = built[aid]
        k = 4                                                       # preview px per art px
        W, H = OW * k, OH * k
        scene = Image.new("RGBA", (W, H), (0, 0, 0, 255))
        top = BH                                                    # the whole backdrop is on screen
        bx = (BW - OW) // 2
        bd = L.image(1).crop((bx, BH - top, bx + OW, BH)).resize((OW * k, top * k), Image.NEAREST)
        tm = tinted(T.image(1).crop((bx, BH - top, bx + OW, BH)), home_c).resize((OW * k, top * k), Image.NEAREST)
        f = 2
        cr = det.image(1).crop((f * BW + bx, BH - top, f * BW + bx + OW, BH)).resize((OW * k, top * k), Image.NEAREST)
        ch = tinted(home.image(1).crop((f * BW + bx, BH - top, f * BW + bx + OW, BH)), home_c).resize(
            (OW * k, top * k), Image.NEAREST)
        ca = tinted(away.image(1).crop((f * BW + bx, BH - top, f * BW + bx + OW, BH)), away_c).resize(
            (OW * k, top * k), Image.NEAREST)
        for layer in (bd, tm, cr, ch, ca):
            scene.alpha_composite(layer)
        # the court in perspective: far sideline at the bottom of the backdrop
        fl = F.image(1)
        y0 = top
        line = hexc(colors["line"])
        apron = hexc(colors["apron"])
        court = Image.new("RGBA", (OW, OH - y0), apron + (255,))
        cp = court.load()
        for yy in range(OH - y0):
            p = 0.75 + 0.25 * yy / (OH - y0)                         # boards get wider toward the camera
            for xx in range(OW):
                u = int(((xx - OW / 2) / p + 1000) % FT)
                v = int((yy * 1.6) % FT)
                cp[xx, yy] = fl.getpixel((u, v))
        cd = ImageDraw.Draw(court)
        hgt = OH - y0
        cd.line([(0, 2), (OW, 2)], fill=line, width=1)              # far sideline
        cd.line([(int(OW * 0.47), 2), (int(OW * 0.42), hgt)], fill=line, width=1)   # half-court line
        cd.ellipse([OW * 0.27, hgt * 0.3, OW * 0.6, hgt * 0.78], outline=line, width=1)
        paint = hexc(colors["paint"])
        cd.polygon([(OW * 0.78, hgt * 0.22), (OW * 1.02, hgt * 0.22), (OW * 1.06, hgt * 0.72), (OW * 0.74, hgt * 0.72)],
                   fill=paint, outline=line)
        cd.arc([OW * 0.55, -hgt * 0.25, OW * 1.35, hgt * 1.15], 100, 260, fill=line, width=1)
        lg = logo.resize((40, 26), Image.NEAREST)
        court.alpha_composite(lg, (int(OW * 0.435 - 20), int(hgt * 0.54 - 13)))
        scene.alpha_composite(court.resize((OW * k, hgt * k), Image.NEAREST), (0, y0 * k))
        for i, pl in enumerate(players):                            # a few players, at the game's size
            ps = pl.resize((pl.width * 2, pl.height * 2), Image.NEAREST)
            px = [300, 420, 560, 640, 760, 880][i]
            py = [330, 300, 400, 360, 470, 430][i]
            scene.alpha_composite(ps, (px - ps.width // 2, py - ps.height))
        scene.alpha_composite(O.image(1).resize((W, H), Image.NEAREST))
        d = ImageDraw.Draw(scene)
        tag = "%s  -  %s" % (label.upper(), desc)
        d.rectangle([0, H - 26, 16 + int(d.textlength(tag)), H], fill=(14, 10, 24, 220))
        d.text((8, H - 19), tag, fill=(255, 214, 64))
        scene = scene.convert("RGB")
        scene.save(os.path.join(PREVIEW, "arenas", aid + ".png"))
        sheet_tiles.append(scene)
    sw, sh = sheet_tiles[0].size
    sheet = Image.new("RGB", (sw, sh * 3), (0, 0, 0))
    for i, t in enumerate(sheet_tiles):
        sheet.paste(t.resize((sw // 2, sh // 2), Image.NEAREST), ((i % 2) * sw // 2, (i // 2) * sh // 2))
    sheet.crop((0, 0, sw, sh * 3 // 2)).save(os.path.join(PREVIEW, "arenas.png"))


if __name__ == "__main__":
    main()
