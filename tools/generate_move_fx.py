#!/usr/bin/env python3
"""Movement effects drawn around a player: dust kicked up by the feet, a skid
cloud when he plants, a burst on an explosive first step, a puff when he
lands, and speed lines behind a sprinter.

Each effect is a strip of frames drawn for a player facing right (so dust and
speed lines stream out to the left, behind him); the app mirrors it for a
player facing left. Art is drawn at 1 px = 1 player-sprite px and stored at
SCALE x with nearest-neighbour upscaling, like the sprites, so it sits on the
same pixel grid when drawn at the sprite's scale.

Writes integration/react-native/moveFx/ (one PNG per effect, moveFx.json,
fxImages.ts) and previews/move_fx.png + previews/move_fx/*.gif.

Run:  python3 tools/generate_move_fx.py
"""
import json
import math
import os
import random
import sys

from PIL import Image, ImageDraw

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from generate_logos import text_pixels, text_width  # noqa: E402  (the league's 3 x 5 pixel font)

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT_DIR = os.path.join(ROOT, "integration", "react-native", "moveFx")
PREVIEW_DIR = os.path.join(ROOT, "previews")
SCALE = 3

# hardwood dust: a warm light tan with a darker rim so it reads on the floor
DUST = (236, 226, 204)
DUST_SHADE = (196, 182, 156)
DUST_RIM = (128, 112, 92)
STREAK = (255, 255, 255)


class Canvas:
    def __init__(self, w, h):
        self.w, self.h = w, h
        self.px = {}

    def put(self, x, y, c, a=255):
        x, y = int(math.floor(x)), int(math.floor(y))
        if not (0 <= x < self.w and 0 <= y < self.h) or a <= 0:
            return
        old = self.px.get((x, y))
        if old is None or old[3] <= a:
            self.px[(x, y)] = tuple(c[:3]) + (int(a),)

    def puff(self, cx, cy, r, a):
        """A pixel dust ball: rim, body, a shaded lower half. Fades with `a`."""
        if r < 0.6 or a <= 0:
            return
        r_out = r + 0.9
        for y in range(int(cy - r_out) - 1, int(cy + r_out) + 2):
            for x in range(int(cx - r_out) - 1, int(cx + r_out) + 2):
                d = math.hypot(x + 0.5 - cx, y + 0.5 - cy)
                if d <= r:
                    col = DUST_SHADE if (y + 0.5 - cy) > r * 0.35 else DUST
                    self.put(x, y, col, a)
                elif d <= r_out and (x, y) not in self.px:
                    self.put(x, y, DUST_RIM, a * 0.8)

    def image(self):
        img = Image.new("RGBA", (self.w, self.h), (0, 0, 0, 0))
        for (x, y), c in self.px.items():
            img.putpixel((x, y), c)
        return img


def ease_out(t):
    return 1 - (1 - t) ** 2


# Each effect: (w, h, frames, fps, loop, anchor, draw(canvas, frame, n)).
# anchor is the strip pixel that sits on the player's foot (or, for speed
# lines, on his back at hip height).

def fx_dust_step(c, f, n):
    """Small puff kicked back off the toe as a foot pushes off."""
    t = (f + 1) / n
    rng = random.Random(11)
    ax, ay = c.w - 5, c.h - 1
    for k in range(4):
        ang = math.radians(rng.uniform(150, 175))          # back and a little up
        dist = (2 + k * 2.2) * ease_out(t)
        r = (1.2 + k * 0.35) * (0.7 + t * 0.6) * (1 - t * 0.45)
        x = ax + math.cos(ang) * dist * 1.4
        y = ay - r - 0.5 - math.sin(ang) * dist * 0.5 - t * (1.5 + k * 0.6)
        c.puff(x, y, r, 255 * (1 - t ** 1.6))


def fx_dust_skid(c, f, n):
    """Cloud thrown up in front of a planted foot (stops, turns)."""
    t = (f + 1) / n
    rng = random.Random(23)
    ax, ay = 6, c.h - 1
    for k in range(7):
        ang = math.radians(rng.uniform(5, 45))             # forward and up
        dist = (3 + k * 2.4) * ease_out(t)
        r = (1.3 + rng.uniform(0, 1.2)) * (0.8 + t * 0.9) * (1 - t * 0.35)
        x = ax + math.cos(ang) * dist
        y = ay - r - 0.5 - math.sin(ang) * dist * 0.6 - t * 3.5
        c.puff(x, y, r, 255 * (1 - t ** 1.8))
    # skid streak on the floor right under the foot, gone by mid-cloud
    if t < 0.6:
        for x in range(ax - 4, ax + int(10 * ease_out(t))):
            c.put(x, ay, DUST_RIM, 200 * (1 - t / 0.6))


def fx_cut_burst(c, f, n):
    """Explosive first step: dust sprays back and short kick lines fly out."""
    t = (f + 1) / n
    rng = random.Random(5)
    ax, ay = c.w - 6, c.h - 1
    for k in range(6):
        ang = math.radians(rng.uniform(140, 178))
        dist = (3 + k * 2.6) * ease_out(t)
        r = (1.0 + rng.uniform(0, 1.1)) * (0.8 + t * 0.7) * (1 - t * 0.5)
        x = ax + math.cos(ang) * dist * 1.3
        y = ay - r - 0.5 - math.sin(ang) * dist * 0.5 - t * 2.5
        c.puff(x, y, r, 255 * (1 - t ** 1.5))
    # three kick lines streaking backward, longest first
    if t < 0.75:
        for k, (row, ln) in enumerate(((3, 9), (6, 6), (9, 7))):
            x0 = ax - 3 - int(t * 10) - k
            for i in range(int(ln * (1 - t))):
                c.put(x0 - i, ay - row, STREAK, 230 * (1 - t / 0.75) * (1 - i / max(1, ln)))


def fx_land_puff(c, f, n):
    """Dust ring squeezed out both ways when he lands from a jump."""
    t = (f + 1) / n
    ax, ay = c.w / 2, c.h - 1
    for side in (-1, 1):
        for k in range(3):
            dist = (2 + k * 3.2) * ease_out(t)
            r = (1.6 - k * 0.3) * (0.8 + t * 0.6) * (1 - t * 0.5)
            c.puff(ax + side * (dist + 1.5), ay - r - 0.5 - t * (1.5 + k * 0.8), r, 255 * (1 - t ** 1.7))


def fx_speed_lines(c, f, n):
    """Streaks behind a sprinter: a looping strip, anchored at his back."""
    rng = random.Random(3)
    lines = [(3 + k * 4 + rng.randint(-1, 1), rng.randint(7, 16), (k * 0.37) % 1.0) for k in range(6)]
    for row, ln, ph in lines:
        # each line slides back and fades, then restarts: a seamless loop
        u = (f / n + ph) % 1.0
        x_end = c.w - 2 - int(u * 14)
        a = 210 * math.sin(math.pi * u)
        for i in range(ln):
            c.put(x_end - i, row, STREAK, a * (1 - i / ln) ** 0.8)


# ---------------------------------------------------------------- success effects
FLASH = (255, 255, 255)
GOLD = (255, 214, 64)
HOT = (255, 140, 40)
INK = (28, 22, 32)


def burst(c, cx, cy, t, rays, r0, r1, width, cols, seed):
    """Rays shooting out from a point and thinning as they go."""
    rng = random.Random(seed)
    for k in range(rays):
        ang = 2 * math.pi * k / rays + rng.uniform(-0.15, 0.15)
        ln = r1 * (0.7 + rng.random() * 0.3)
        start, end = r0 + (ln - r0) * max(0, t - 0.25), r0 + (ln - r0) * ease_out(min(1, t * 1.6))
        steps = int(end - start) + 1
        for i in range(steps):
            d = start + i
            w = width * (1 - i / max(1, steps)) * (1 - t * 0.5)
            col = cols[0] if d < r0 + (ln - r0) * 0.45 else cols[1]
            for j in range(-int(w), int(w) + 1):
                x = cx + math.cos(ang) * d - math.sin(ang) * j * 0.6
                y = cy + math.sin(ang) * d + math.cos(ang) * j * 0.6
                c.put(x, y, col, 255 * (1 - t ** 2))


def sparks(c, cx, cy, t, n, dist, cols, seed):
    rng = random.Random(seed)
    for k in range(n):
        ang = rng.uniform(0, 2 * math.pi)
        d = dist * (0.5 + rng.random() * 0.5) * ease_out(t)
        x, y = cx + math.cos(ang) * d, cy + math.sin(ang) * d + 6 * t * t       # fall a little
        if t < 0.9:
            c.put(x, y, cols[k % len(cols)], 255 * (1 - t))
            if t < 0.5:
                c.put(x + 1, y, cols[k % len(cols)], 200 * (1 - t))


def fx_impact_star(c, f, n):
    """Steal: a white-hot poke flash at the hand, a gold star burst, sparks."""
    t = f / (n - 1)
    cx, cy = c.w / 2, c.h / 2
    if f <= 1:                                                 # the flash itself
        r = 3.5 if f == 0 else 5
        for y in range(c.h):
            for x in range(c.w):
                if math.hypot(x + 0.5 - cx, y + 0.5 - cy) <= r:
                    c.put(x, y, FLASH if f == 0 else GOLD)
    burst(c, cx, cy, t, 8, 3, c.w / 2 - 1, 1.6, (FLASH, GOLD), 4)
    sparks(c, cx, cy, t, 10, c.w / 2 - 1, (GOLD, FLASH, HOT), 9)


def fx_swat_burst(c, f, n):
    """Block: a shockwave ring, heavy rays and debris where the hand meets the ball."""
    t = f / (n - 1)
    cx, cy = c.w / 2, c.h / 2
    if f == 0:
        for y in range(c.h):
            for x in range(c.w):
                if math.hypot(x + 0.5 - cx, y + 0.5 - cy) <= 6:
                    c.put(x, y, FLASH)
    rr = 4 + (c.w / 2 - 3) * ease_out(t)                       # shockwave ring
    for y in range(c.h):
        for x in range(c.w):
            d = math.hypot(x + 0.5 - cx, y + 0.5 - cy)
            if abs(d - rr) < 1.0 + (1 - t):
                c.put(x, y, FLASH if t < 0.4 else GOLD, 255 * (1 - t ** 1.5))
    burst(c, cx, cy, t, 10, 5, c.w / 2 - 1, 1.8, (FLASH, HOT), 2)
    sparks(c, cx, cy, t, 14, c.w / 2, (HOT, GOLD, FLASH), 13)


def pop_text(c, f, n, text, fill, shade):
    """Pixel lettering that pops in big, settles, floats up and blinks out."""
    scale = [1, 3, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2][min(f, 11)]
    rise = int(f * 0.6)
    if f >= n - 3 and f % 2:                                   # blink out
        return
    a = 255 if f < n - 2 else 150
    w = text_width(text) * scale
    x0, y0 = int(c.w / 2 - w / 2), int(c.h - 4 - 5 * scale - rise)
    glyph = {(x0 + x * scale + i, y0 + y * scale + j) for (x, y) in text_pixels(text, 0, 0)
             for i in range(scale) for j in range(scale)}
    for (x, y) in glyph:                                       # drop shadow + outline
        c.put(x + 1, y + 2, INK, a)
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1), (1, 1), (-1, -1), (1, -1), (-1, 1)):
            if (x + dx, y + dy) not in glyph:
                c.put(x + dx, y + dy, INK, a)
    for (x, y) in glyph:
        c.put(x, y, shade if (y - y0) >= scale * 3 else fill, a)     # two-tone letters


def fx_text_steal(c, f, n):
    pop_text(c, f, n, "STEAL!", GOLD, HOT)


def fx_text_block(c, f, n):
    pop_text(c, f, n, "BLOCKED!", (255, 120, 80), (220, 40, 40))


def fx_cross_swoosh(c, f, n):
    """Crossover: curved air lines whipping around where the ball crosses."""
    t = f / (n - 1)
    cx, cy = c.w / 2, c.h - 2
    arcs = ((6, 200, (255, 79, 179)), (9.5, 192, (59, 232, 240)), (13, 186, (255, 214, 64)))   # magenta, cyan, gold
    for k, (r, a0, col) in enumerate(arcs):
        span = 120 * ease_out(min(1, t * 1.8 + k * 0.08))
        tail = 120 * max(0, (t - 0.3) * 1.4)                 # the back end catches up: the line flies off
        steps = 40
        for i in range(steps + 1):
            a = math.radians(a0 + tail + (span - tail) * i / steps)
            if span - tail <= 0:
                break
            x, y = cx + math.cos(a) * r * 1.5, cy + math.sin(a) * r
            fade = i / steps                                  # brightest at the leading end
            c.put(x, y, STREAK if fade > 0.82 else col, 255 * (0.4 + 0.6 * fade) * (1 - t ** 2))
            if fade > 0.3:                                    # a second row: thicker, punchier lines
                c.put(x, y + 1, col, 200 * fade * (1 - t ** 2))


EFFECTS = {
    # id: (label, w, h, frames, fps, loop, anchor, fn)
    "dust_step": ("Step dust", 20, 11, 5, 18, False, (15, 10), fx_dust_step),
    "dust_skid": ("Skid cloud", 32, 16, 7, 16, False, (6, 15), fx_dust_skid),
    "cut_burst": ("Cut burst", 30, 15, 6, 18, False, (24, 14), fx_cut_burst),
    "land_puff": ("Landing puff", 28, 11, 6, 16, False, (14, 10), fx_land_puff),
    "speed_lines": ("Speed lines", 26, 30, 6, 14, True, (25, 15), fx_speed_lines),
    "cross_swoosh": ("Cross whoosh", 44, 18, 6, 20, False, (22, 16), fx_cross_swoosh),
    "impact_star": ("Steal flash", 32, 32, 7, 20, False, (16, 16), fx_impact_star),
    "swat_burst": ("Block burst", 36, 36, 8, 20, False, (18, 18), fx_swat_burst),
    "text_steal": ("STEAL! pop-up", 76, 28, 12, 12, False, (38, 27), fx_text_steal),
    "text_block": ("BLOCKED! pop-up", 104, 28, 12, 12, False, (52, 27), fx_text_block),
}


def strip(fid):
    _, w, h, n, _, _, _, fn = EFFECTS[fid]
    frames = []
    for f in range(n):
        c = Canvas(w, h)
        fn(c, f, n)
        frames.append(c.image())
    out = Image.new("RGBA", (w * n, h), (0, 0, 0, 0))
    for i, im in enumerate(frames):
        out.alpha_composite(im, (i * w, 0))
    return out, frames


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    os.makedirs(os.path.join(PREVIEW_DIR, "move_fx"), exist_ok=True)
    meta = {"_comment": "AUTO-GENERATED by tools/generate_move_fx.py. Sizes and anchors are art pixels "
                        "(= player-sprite frame pixels); the PNGs are stored at `scale`x.",
            "scale": SCALE, "effects": {}}
    bg = (176, 124, 72, 255)    # hardwood, for the previews
    rows = []
    for fid, (label, w, h, n, fps, loop, anchor, _) in EFFECTS.items():
        img, frames = strip(fid)
        img.resize((img.width * SCALE, img.height * SCALE), Image.NEAREST).save(os.path.join(OUT_DIR, fid + ".png"))
        meta["effects"][fid] = {"label": label, "width": w, "height": h, "frames": n, "fps": fps, "loop": loop,
                                "anchor": list(anchor)}
        gif = []
        for im in frames:
            f = Image.new("RGBA", im.size, bg)
            f.alpha_composite(im)
            gif.append(f.resize((w * 6, h * 6), Image.NEAREST).convert("RGB"))
        gif[0].save(os.path.join(PREVIEW_DIR, "move_fx", fid + ".gif"), save_all=True, append_images=gif[1:],
                    duration=int(1000 / fps), loop=0)
        rows.append((fid, frames))
    with open(os.path.join(OUT_DIR, "moveFx.json"), "w") as f:
        json.dump(meta, f, indent=1)
    with open(os.path.join(OUT_DIR, "fxImages.ts"), "w") as f:
        f.write("// AUTO-GENERATED by tools/generate_move_fx.py - do not edit by hand.\n")
        f.write("import type { ImageSourcePropType } from 'react-native';\n")
        f.write("import type { MoveFxId } from './moveFx';\n\n")
        f.write("/** One strip per effect, required lazily so only effects in use are loaded. */\n")
        f.write("export const FX_IMAGES: Record<MoveFxId, () => ImageSourcePropType> = {\n")
        for fid in EFFECTS:
            f.write("  %s: () => require('./%s.png'),\n" % (fid, fid))
        f.write("};\n")

    # preview sheet: every frame of every effect, 6x, on hardwood
    k = 6
    cell_w = max(EFFECTS[r][1] for r, _ in rows) * k + 8
    cell_h = max(EFFECTS[r][2] for r, _ in rows) * k + 8
    ncol = max(len(fr) for _, fr in rows)
    sheet = Image.new("RGBA", (120 + ncol * cell_w, len(rows) * cell_h), bg)
    d = ImageDraw.Draw(sheet)
    for r, (fid, frames) in enumerate(rows):
        d.text((6, r * cell_h + 8), EFFECTS[fid][0], fill=(255, 255, 255))
        for i, im in enumerate(frames):
            sheet.alpha_composite(im.resize((im.width * k, im.height * k), Image.NEAREST),
                                  (120 + i * cell_w, r * cell_h + 4))
    sheet.convert("RGB").save(os.path.join(PREVIEW_DIR, "move_fx.png"))
    print("move fx:", ", ".join(EFFECTS))


if __name__ == "__main__":
    main()
