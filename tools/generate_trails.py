#!/usr/bin/env python3
"""Ball trail effects: the basketball with an animated trail behind it.

Each trail is a looping strip of frames with the ball moving to the right and
the effect streaming out to the left. The app rotates the whole frame to the
ball's velocity (about the ball's centre), so one strip covers every
direction. Art is drawn at 1 px = 1 ball-sprite px and stored at SCALE x with
nearest-neighbour upscaling, like the player sprites.

Writes integration/react-native/ballTrails/ (one PNG per trail plus
trails.json and trails.ts) and previews/trails.png + previews/trails/*.gif.
"""
import colorsys
import json
import math
import os
import random
import sys

from PIL import Image, ImageDraw

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from generate_sprites import FIXED, PREVIEW_DIR, ROOT, ball_layer  # noqa: E402

OUT_DIR = os.path.join(ROOT, "integration", "react-native", "ballTrails")
W, H = 60, 20                  # frame size in art pixels
BX, BY = W - 7, H // 2         # ball centre
FRAMES = 8
SCALE = 3
TAIL = BX - 5                  # the trail runs from x = TAIL back to x = 0


# ---------------------------------------------------------------- drawing helpers
class Canvas:
    def __init__(self):
        self.px = {}

    def put(self, x, y, c):
        """Blend an RGBA color over whatever is there."""
        x, y = int(math.floor(x)), int(math.floor(y))
        if not (0 <= x < W and 0 <= y < H) or c[3] <= 0:
            return
        a = c[3] / 255
        d = self.px.get((x, y), (0, 0, 0, 0))
        da = d[3] / 255
        oa = a + da * (1 - a)
        if oa <= 0:
            return
        rgb = tuple((c[i] * a + d[i] * da * (1 - a)) / oa for i in range(3))
        self.px[(x, y)] = tuple(int(round(v)) for v in rgb) + (int(round(oa * 255)),)

    def disc(self, cx, cy, r, c):
        for y in range(int(cy - r) - 1, int(cy + r) + 2):
            for x in range(int(cx - r) - 1, int(cx + r) + 2):
                if (x + 0.5 - cx) ** 2 + (y + 0.5 - cy) ** 2 <= r * r:
                    self.put(x, y, c)

    def ring(self, cx, cy, r, c):
        for y in range(int(cy - r) - 1, int(cy + r) + 2):
            for x in range(int(cx - r) - 1, int(cx + r) + 2):
                d = math.hypot(x + 0.5 - cx, y + 0.5 - cy)
                if r - 0.8 <= d <= r + 0.2:
                    self.put(x, y, c)

    def rect(self, x0, y0, w, h, c):
        for y in range(int(round(y0)), int(round(y0)) + h):
            for x in range(int(round(x0)), int(round(x0)) + w):
                self.put(x, y, c)

    def line(self, a, b, c):
        n = int(max(abs(b[0] - a[0]), abs(b[1] - a[1]))) + 1
        for k in range(n + 1):
            t = k / n
            self.put(a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t, c)

    def image(self):
        img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        for (x, y), c in self.px.items():
            img.putpixel((x, y), c)
        return img


def rgba(hex_or_rgb, a=255):
    if isinstance(hex_or_rgb, str):
        h = hex_or_rgb.lstrip("#")
        return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4)) + (a,)
    return tuple(hex_or_rgb[:3]) + (a,)


def mix(c1, c2, t):
    return tuple(int(round(c1[i] + (c2[i] - c1[i]) * t)) for i in range(4))


def ramp(stops, t):
    """Color along a list of (t, color) stops."""
    t = max(0.0, min(1.0, t))
    for (t0, c0), (t1, c1) in zip(stops, stops[1:]):
        if t <= t1:
            return mix(c0, c1, (t - t0) / (t1 - t0) if t1 > t0 else 0)
    return stops[-1][1]


def dither(x, y, a):
    """Ordered-dither keep test for a fade (a = 0..1)."""
    bayer = [[0, 8, 2, 10], [12, 4, 14, 6], [3, 11, 1, 9], [15, 7, 13, 5]]
    return a * 16 > bayer[y % 4][x % 4] + 0.5


def particles(seed, n):
    """Particles that each travel once down the trail per loop (u in 0..1),
    so every effect loops seamlessly."""
    rnd = random.Random(seed)
    return [dict(u=rnd.random(), y=rnd.gauss(0, 1), k=rnd.random(), s=rnd.random()) for _ in range(n)]


def travel(p, i, speed=1.0):
    return (p["u"] + speed * i / FRAMES) % 1.0


def tail_x(u):
    return TAIL - u * (TAIL - 1)


# ---------------------------------------------------------------- effects
def fx_fire(c, i):
    core = [(0.0, rgba("#fffbe0")), (0.15, rgba("#ffe45c")), (0.4, rgba("#ff9a1f")),
            (0.7, rgba("#e8411c")), (1.0, rgba("#7a1a12", 0))]
    for p in particles(1, 70):
        u = travel(p, i, 1.0 + p["k"] * 0.6)
        r = (1 - u) * 3.6 + 0.6
        y = BY + p["y"] * (0.8 + u * 2.2) + math.sin(u * 9 + p["k"] * 6) * u * 1.5 - u * 2.0
        c.disc(tail_x(u), y, r, ramp(core, u + p["s"] * 0.15))
    for p in particles(2, 10):          # embers
        u = travel(p, i, 1.3)
        c.put(tail_x(u), BY + p["y"] * 3 - u * 4, rgba("#ffd36b", int(255 * (1 - u))))


def fx_laser(c, i):
    glow = rgba("#ff2d6f", 110)
    edge = rgba("#ff3b7a")
    for x in range(0, TAIL + 3):
        a = min(1.0, x / 14)                                 # fades in from the far end
        pulse = (math.sin((x + i * 4) * 2 * math.pi / 8) + 1) / 2
        for dy, col in ((-2, glow), (2, glow), (-1, edge), (1, edge)):
            if dither(x, BY + dy, a):
                c.put(x, BY + dy, col)
        if dither(x, BY, a):
            c.put(x, BY, mix(rgba("#ffd0dd"), rgba("#ffffff"), pulse))
    for k in range(3):                                       # sparks shed off the beam
        x = (TAIL - (i * 5 + k * 17)) % TAIL
        c.put(x, BY - 3 - k % 2, rgba("#ff9ab8", 200))
        c.put(x + 2, BY + 3 + k % 2, rgba("#ff9ab8", 160))


def fx_bubbles(c, i):
    for p in particles(3, 22):
        u = travel(p, i, 0.7 + p["k"] * 0.5)
        r = 1.0 + p["s"] * 2.2 + u * 0.8
        x = tail_x(u) - 1
        y = BY + p["y"] * 2.2 - u * 3 + math.sin(u * 12 + p["k"] * 7)
        if u > 0.92:                                         # pop
            for ang in range(0, 360, 60):
                c.put(x + math.cos(math.radians(ang)) * (r + 1), y + math.sin(math.radians(ang)) * (r + 1),
                      rgba("#d6f6ff", 180))
            continue
        c.disc(x, y, r, rgba("#7fd8ff", 55))
        c.ring(x, y, r, rgba("#a8ecff", 230))
        c.put(x - r * 0.4, y - r * 0.4, rgba("#ffffff"))


def fx_money(c, i):
    bill, dark, light = rgba("#4caf50"), rgba("#1f6b2a"), rgba("#b9f0a8")
    for p in particles(4, 11):
        u = travel(p, i, 0.8 + p["k"] * 0.4)
        x = tail_x(u) - 2
        y = BY + p["y"] * 2.5 + math.sin(u * 8 + p["k"] * 5) * 1.5
        flip = int((u * 10 + p["k"] * 4) % 3)                # tumbling: flat, tilted, edge-on
        w, h = [(7, 4), (5, 5), (7, 2)][flip]
        c.rect(x - w / 2, y - h / 2, w, h, dark)
        c.rect(x - w / 2 + 1, y - h / 2 + 1, w - 2, max(h - 2, 1), bill)
        if h >= 4:
            c.put(x, y, light)
    for p in particles(5, 8):                                # coins
        u = travel(p, i, 1.1)
        x, y = tail_x(u), BY + p["y"] * 3
        c.disc(x, y, 1.3, rgba("#f7c531"))
        c.put(x - 0.5, y - 0.5, rgba("#fff3b0"))


def fx_lightning(c, i):
    rnd = random.Random(100 + i)
    for bolt, (thick, ofs) in enumerate(((True, 0), (False, 3))):
        pts = [(TAIL + 1, BY)]
        x, y = TAIL + 1, BY
        while x > 2:
            x -= rnd.randint(3, 6)
            y = max(2, min(H - 3, BY + rnd.randint(-4, 4) + (ofs if bolt else 0) * rnd.choice((-1, 1))))
            pts.append((max(x, 1), y))
        for a, b in zip(pts, pts[1:]):
            fade = min(1.0, a[0] / 20)
            if thick:
                for dy in (-1, 1):
                    c.line((a[0], a[1] + dy), (b[0], b[1] + dy), rgba("#3aa0ff", int(200 * fade)))
                c.line(a, b, rgba("#ffffff", int(255 * max(fade, 0.3))))
            else:
                c.line(a, b, rgba("#8fd0ff", int(220 * fade)))
    for k in range(5):
        c.put(rnd.randint(4, TAIL), rnd.randint(2, H - 3), rgba("#e0f4ff"))


RAINBOW = ["#ff3b3b", "#ff9a2e", "#ffe53b", "#3bd16f", "#3b8cff", "#9b5bff"]


def fx_rainbow(c, i):
    for x in range(0, TAIL + 2):
        a = min(1.0, x / 16)
        wave = math.sin(x * 0.35 - i * 2 * math.pi / FRAMES) * 1.6 * (1 - x / (TAIL + 2)) ** 0.2
        for band, col in enumerate(RAINBOW):
            y = BY - 3 + band + wave
            if dither(x, int(y), a):
                c.put(x, y, rgba(col))
    for p in particles(6, 6):                                # sparkles
        u = travel(p, i, 1.2)
        x, y = tail_x(u), BY + p["y"] * 5
        if int(u * 20) % 2:
            c.put(x, y, rgba("#ffffff"))
            c.put(x - 1, y, rgba("#ffffff", 140))
            c.put(x + 1, y, rgba("#ffffff", 140))


def fx_ice(c, i):
    mist = [(0.0, rgba("#e8fbff", 230)), (0.5, rgba("#9fe3ff", 150)), (1.0, rgba("#6ab8ff", 0))]
    for p in particles(7, 40):
        u = travel(p, i, 0.9 + p["k"] * 0.3)
        r = (1 - u) * 2.6 + 0.5
        c.disc(tail_x(u), BY + p["y"] * (0.6 + u * 1.8), r, ramp(mist, u))
    for p in particles(8, 9):                                # ice crystals
        u = travel(p, i, 0.8)
        x, y = tail_x(u), BY + p["y"] * 3.5
        big = p["s"] > 0.5
        col = rgba("#ffffff", int(255 * (1 - u * 0.6)))
        c.put(x, y, col)
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            c.put(x + dx, y + dy, rgba("#bdf0ff", col[3]))
            if big:
                c.put(x + 2 * dx, y + 2 * dy, rgba("#8fd8ff", col[3] // 2))


def fx_smoke(c, i):
    for p in particles(9, 30):
        u = travel(p, i, 0.8 + p["k"] * 0.3)
        r = 1.2 + u * 3.2
        a = int(200 * (1 - u) ** 1.2)
        col = mix(rgba("#d8d8d8"), rgba("#6c6c74"), u)
        c.disc(tail_x(u) - 1, BY + p["y"] * (0.6 + u * 1.5) - u * 2.5, r, col[:3] + (a,))


def fx_stars(c, i):
    for x in range(0, TAIL + 1):                             # faint golden streak
        a = x / (TAIL + 1)
        for dy in (-1, 0, 1):
            if dither(x, BY + dy, a * (0.9 if dy == 0 else 0.45)):
                c.put(x, BY + dy, rgba("#ffd966", 170))
    for p in particles(10, 12):
        u = travel(p, i, 1.0)
        x, y = tail_x(u), BY + p["y"] * 3.5
        twinkle = (int(u * 16 + p["k"] * 8)) % 3
        size = [2, 1, 3][twinkle] if p["s"] > 0.4 else 1
        col = rgba("#fff6c9") if twinkle != 1 else rgba("#ffd34d")
        c.put(x, y, rgba("#ffffff"))
        for k in range(1, size + 1):
            fade = col[:3] + (int(255 * (1 - k / (size + 1))),)
            for dx, dy in ((k, 0), (-k, 0), (0, k), (0, -k)):
                c.put(x + dx, y + dy, fade)


CONFETTI = ["#ff4d6d", "#ffd23f", "#3bceac", "#3a86ff", "#b15eff", "#ff9f1c"]


def fx_confetti(c, i):
    for n, p in enumerate(particles(11, 46)):
        u = travel(p, i, 0.7 + p["k"] * 0.6)
        x = tail_x(u)
        y = BY + p["y"] * (1 + u * 3) + math.sin(u * 10 + n) * 1.2
        col = rgba(CONFETTI[n % len(CONFETTI)])
        spin = int(u * 12 + n) % 3                          # flipping pieces
        if spin == 0:
            c.rect(x, y, 2, 2 if p["s"] > 0.6 else 1, col)
        elif spin == 1:
            c.rect(x, y, 1, 2, col)
        else:
            c.rect(x, y, 2, 1, mix(col, rgba("#ffffff"), 0.35))


def fx_afterimage(c, i):
    """Retro speed ghosting: fading copies of the ball behind it."""
    for k, a in ((1, 0.55), (2, 0.32), (3, 0.16)):
        ghost = ball_layer((BX - k * 11 + 0.5, BY + 0.5), (i - k) * 22.5)
        for (x, y), col in ghost.px.items():
            c.put(x, y, tuple(col[:3]) + (int(col[3] * a),))


TRAILS = {
    # id: (label, draw fn, fps)
    "none": ("No trail", None, 16),
    "fire": ("Fire", fx_fire, 16),
    "laser": ("Laser", fx_laser, 16),
    "bubbles": ("Bubbles", fx_bubbles, 12),
    "money": ("Money", fx_money, 12),
    "lightning": ("Lightning", fx_lightning, 14),
    "rainbow": ("Rainbow", fx_rainbow, 14),
    "ice": ("Ice", fx_ice, 14),
    "smoke": ("Smoke", fx_smoke, 12),
    "stars": ("Stars", fx_stars, 14),
    "confetti": ("Confetti", fx_confetti, 14),
    "afterimage": ("Afterimage", fx_afterimage, 16),
}


def frame(trail, i):
    c = Canvas()
    fn = TRAILS[trail][1]
    if fn:
        fn(c, i)
    img = c.image()
    ball = ball_layer((BX + 0.5, BY + 0.5), i * 22.5)        # the ball spins through the loop
    for src in (ball.outline(), ball.px):
        for (x, y), col in src.items():
            if 0 <= x < W and 0 <= y < H:
                img.putpixel((x, y), FIXED[col] if isinstance(col, str) else col)
    return img


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    os.makedirs(os.path.join(PREVIEW_DIR, "trails"), exist_ok=True)
    meta = {
        "_comment": "AUTO-GENERATED by tools/generate_trails.py. Positions are strip pixels.",
        "scale": SCALE,
        "frameWidth": W * SCALE,
        "frameHeight": H * SCALE,
        "frames": FRAMES,
        "ballCenter": [(BX + 0.5) * SCALE, (BY + 0.5) * SCALE],
        "ballDiameter": 11 * SCALE,
        "trails": {},
    }
    bg = (34, 40, 58, 255)
    sheet = Image.new("RGBA", (W * 2 * FRAMES, len(TRAILS) * (H * 2 + 12)), bg)
    d = ImageDraw.Draw(sheet)
    for row, (tid, (label, _, fps)) in enumerate(TRAILS.items()):
        frames = [frame(tid, i) for i in range(FRAMES)]
        strip = Image.new("RGBA", (W * FRAMES, H), (0, 0, 0, 0))
        for i, f in enumerate(frames):
            strip.paste(f, (i * W, 0))
        strip.resize((strip.width * SCALE, strip.height * SCALE), Image.NEAREST).save(
            os.path.join(OUT_DIR, "%s.png" % tid), optimize=True)
        meta["trails"][tid] = {"label": label, "fps": fps}
        y = row * (H * 2 + 12)
        d.text((4, y + 1), label, fill=(255, 255, 255, 255))
        gif = []
        for i, f in enumerate(frames):
            big = f.resize((W * 2, H * 2), Image.NEAREST)
            sheet.alpha_composite(big, (i * W * 2, y + 12))
            g = Image.new("RGBA", (W * 4, H * 4), bg)
            g.alpha_composite(f.resize((W * 4, H * 4), Image.NEAREST))
            gif.append(g.convert("RGB"))
        gif[0].save(os.path.join(PREVIEW_DIR, "trails", tid + ".gif"), save_all=True, append_images=gif[1:],
                    duration=int(1000 / fps), loop=0)
    sheet.save(os.path.join(PREVIEW_DIR, "trails.png"))
    with open(os.path.join(OUT_DIR, "trails.json"), "w") as f:
        json.dump(meta, f, indent=1)
    lines = [
        "// AUTO-GENERATED by tools/generate_trails.py - do not edit by hand.",
        "import type { ImageSourcePropType } from 'react-native';",
        "import type { TrailId } from './trails';",
        "",
        "/** One strip per trail, required lazily so only trails in use are loaded. */",
        "export const TRAIL_IMAGES: Record<TrailId, () => ImageSourcePropType> = {",
    ]
    lines += ["  %s: () => require('./%s.png')," % (t, t) for t in TRAILS]
    lines += ["};", ""]
    with open(os.path.join(OUT_DIR, "trailImages.ts"), "w") as f:
        f.write("\n".join(lines))
    print("wrote %d trails to %s" % (len(TRAILS), OUT_DIR))


if __name__ == "__main__":
    main()
