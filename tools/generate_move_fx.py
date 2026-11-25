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

from PIL import Image, ImageDraw

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


EFFECTS = {
    # id: (label, w, h, frames, fps, loop, anchor, fn)
    "dust_step": ("Step dust", 20, 11, 5, 18, False, (15, 10), fx_dust_step),
    "dust_skid": ("Skid cloud", 32, 16, 7, 16, False, (6, 15), fx_dust_skid),
    "cut_burst": ("Cut burst", 30, 15, 6, 18, False, (24, 14), fx_cut_burst),
    "land_puff": ("Landing puff", 28, 11, 6, 16, False, (14, 10), fx_land_puff),
    "speed_lines": ("Speed lines", 26, 30, 6, 14, True, (25, 15), fx_speed_lines),
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
