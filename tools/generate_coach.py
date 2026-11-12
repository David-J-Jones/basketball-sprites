#!/usr/bin/env python3
"""The coach: a front-view pixel-art portrait in the headshot style, for the
pop-up messages in the menus ("You've been playing well...").

A gruff old coach in a ball cap and a team polo, with a whistle, grey
sideburns and a grey mustache. He talks: the mouth has four shapes
(closed, small, open, wide) and there's a blink frame. The cap and the polo
are tint masks, so they take the team's colors in the app.

Writes integration/react-native/coach/:
  base.png          the face and body, 5 frames side by side (transparent
                    where the cap and polo are tinted)
  cap_mask.png      white where the cap is (tint with the team color)
  cap_detail.png    cap shading and the patch on the front
  shirt_mask.png    white where the polo is (tint with the team color)
  shirt_detail.png  polo shading, the collar and the whistle
and previews/coach.png, previews/coach_talking.gif, previews/coach_popup.png.
"""
import math
import os
import sys

from PIL import Image, ImageDraw

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import generate_logos as lg  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "integration", "react-native", "coach")
PREVIEW = os.path.join(ROOT, "previews")
N = 64                   # art px per side
SCALE = 4                # png px per art px
CX = 32
FRAMES = ["closed", "small", "open", "wide", "blink"]

OUTLINE = (28, 22, 32)
WARM_DARK = (72, 26, 12)


def mix(a, b, t):
    return tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(3))


def hexrgb(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


SKIN = hexrgb("#D9A778")
SK = {"hi": mix(SKIN, (255, 255, 255), 0.16), "base": SKIN, "s1": mix(SKIN, WARM_DARK, 0.24),
      "s2": mix(SKIN, WARM_DARK, 0.42), "s3": mix(SKIN, (42, 12, 6), 0.62),
      "lip": mix(mix(SKIN, WARM_DARK, 0.3), (176, 70, 74), 0.22)}
GREY = {"hi": (214, 210, 204), "base": (168, 162, 154), "s1": (128, 122, 116), "s2": (92, 88, 84)}
EYE_WHITE, PUPIL, MOUTH_IN, TEETH = (241, 235, 226), (40, 30, 26), (70, 20, 24), (238, 232, 220)
WHISTLE = {"hi": (240, 242, 246), "base": (196, 200, 210), "s1": (130, 134, 146)}
CORD = (220, 40, 40)


def ellipse(cx, cy, rx, ry):
    out = set()
    for y in range(int(cy - ry) - 1, int(cy + ry) + 2):
        for x in range(int(cx - rx) - 1, int(cx + rx) + 2):
            if ((x + 0.5 - cx) / rx) ** 2 + ((y + 0.5 - cy) / ry) ** 2 <= 1:
                out.add((x, y))
    return out


def lit(x, y, cx, cy, rx, ry):
    """-1 (shadow) .. 1 (lit), light from the upper left."""
    return -((x + 0.5 - cx) / rx) * 0.6 - ((y + 0.5 - cy) / ry) * 0.8


class Art:
    def __init__(self):
        self.base = {}          # full color
        self.cap = {}           # tint mask: pixel -> shading overlay (rgba) or None
        self.shirt = {}
        self.cap_px = {}        # opaque pixels drawn over the tinted cap (the patch)
        self.shirt_px = {}      # opaque pixels drawn over the polo (whistle, buttons)


def draw(mouth="closed"):
    a = Art()
    # ---- polo: broad shoulders, open collar, placket
    body = set()
    for y in range(46, N):
        u = min(1.0, (y - 46) / 8)
        hw = 13 + 18 * math.sqrt(u)
        for x in range(N):
            if abs(x + 0.5 - CX) <= hw:
                body.add((x, y))
    neck_skin = set()
    for (x, y) in body:
        dx = abs(x + 0.5 - CX)
        if y < 52 and dx < 7 - (y - 46) * 0.9:
            neck_skin.add((x, y))                         # the open collar shows the neck
    for (x, y) in body - neck_skin:
        l = -((x + 0.5 - CX) / 30) * 0.7 - ((y - 46) / 18) * 0.2
        a.shirt[(x, y)] = (0, 0, 0, 70) if l < -0.25 else (255, 255, 255, 40) if l > 0.4 else None
    # collar: two lighter flaps either side of the opening
    for side in (-1, 1):
        for k in range(6):
            for j in range(3 + (k > 2)):
                x = int(CX + side * (5 + k * 0.9 + j) - (1 if side < 0 else 0))
                y = 46 + k
                a.shirt[(x, y)] = (255, 255, 255, 90) if j < 2 else (0, 0, 0, 60)
    for y in range(52, 59):                               # placket and buttons
        a.shirt[(CX - 1, y)] = (0, 0, 0, 55)
        if y in (54, 57):
            a.shirt_px[(CX, y)] = (238, 236, 230)
    # whistle on a red cord
    for t in range(16):
        y = 46 + t
        for side in (-1, 1):
            x = int(CX + side * (7 - t * 0.3)) - (1 if side < 0 else 0)
            if y < 58:
                a.shirt_px[(x, y)] = CORD
    for (x, y) in ellipse(CX + 0.5, 59.5, 2.6, 1.8):
        l = lit(x, y, CX + 0.5, 59.5, 2.6, 1.8)
        a.shirt_px[(x, y)] = WHISTLE["hi"] if l > 0.4 else WHISTLE["s1"] if l < -0.3 else WHISTLE["base"]
    for x in range(CX + 3, CX + 6):
        a.shirt_px[(x, 59)] = WHISTLE["s1"]
    a.shirt_px[(CX - 1, 59)] = (60, 60, 70)              # the whistle's hole
    # neck, in the shadow of the chin
    for y in range(38, 52):
        for x in range(CX - 6, CX + 6):
            if (x, y) in neck_skin or y < 46:
                l = -((x + 0.5 - CX) / 6)
                a.base[(x, y)] = SK["s2"] if y < 44 else (SK["base"] if l > -0.3 else SK["s1"])
    # ---- head
    hcx, hcy, hrx, hry = CX, 28.5, 11.5, 13.0
    head = ellipse(hcx, hcy, hrx, hry)
    head = {(x, y) for (x, y) in head if y >= 17}
    for (x, y) in head:
        l = lit(x, y, hcx, hcy, hrx, hry)
        c = SK["hi"] if l > 0.55 else SK["s1"] if l < -0.35 else SK["base"]
        if y > 36 and abs(x + 0.5 - CX) > 6:
            c = SK["s1"]                                   # jaw shadow
        a.base[(x, y)] = c
    # ears
    for side in (-1, 1):
        ex = CX + side * 12
        for (x, y) in ellipse(ex, 29.5, 2.0, 3.2):
            a.base[(x, y)] = SK["s1"] if side > 0 else SK["base"]
        a.base[(int(ex) - (1 if side < 0 else 0), 29)] = SK["s2"]
    # grey sideburns and the hair at the back under the cap
    for side in (-1, 1):                                  # short, by the ears
        for y in range(23, 29):
            x = int(CX + side * 11) - (1 if side < 0 else 0)
            a.base[(x, y)] = GREY["s1"] if y > 25 else GREY["base"]
            if y < 26:
                a.base[(x - side, y)] = GREY["base"]
    # brows: thick and grey, slightly furrowed
    for side in (-1, 1):
        for k in range(5):
            x = int(CX + side * (2 + k)) - (1 if side < 0 else 0)
            y = 25 + (1 if k == 0 else 0)
            a.base[(x, y)] = GREY["s1"]
            a.base[(x, y - 1)] = GREY["base"] if k > 0 else a.base.get((x, y - 1), SK["base"])
    # eyes
    for side in (-1, 1):
        x0 = int(CX + side * 4) - (2 if side < 0 else 0)
        if mouth == "blink":
            for x in range(x0, x0 + 3):
                a.base[(x, 28)] = SK["s3"]
        else:
            a.base[(x0, 28)] = EYE_WHITE
            a.base[(x0 + 1, 28)] = PUPIL
            a.base[(x0 + 2, 28)] = EYE_WHITE
            for x in range(x0, x0 + 3):
                a.base[(x, 27)] = SK["s2"]                 # heavy lids
        a.base[(x0 + (3 if side > 0 else -1), 29)] = SK["s1"]   # crow's feet
    # nose
    for y in range(28, 33):
        a.base[(CX, y)] = SK["base"] if y < 32 else SK["s1"]
        a.base[(CX - 1, y)] = SK["hi"] if y < 31 else SK["base"]
    a.base[(CX - 2, 33)] = SK["s2"]
    a.base[(CX + 1, 33)] = SK["s2"]
    a.base[(CX - 1, 33)] = SK["s1"]
    a.base[(CX, 33)] = SK["s1"]
    # mouth (under the mustache)
    my = 37
    if mouth in ("closed", "blink"):
        for x in range(CX - 3, CX + 3):
            a.base[(x, my)] = SK["s3"]
        a.base[(CX - 1, my + 1)] = SK["lip"]
        a.base[(CX, my + 1)] = SK["lip"]
    else:
        h = {"small": 1, "open": 2, "wide": 3}[mouth]
        w = {"small": 2, "open": 3, "wide": 3}[mouth]
        for y in range(my, my + h):
            for x in range(CX - w, CX + w):
                a.base[(x, y)] = MOUTH_IN
        if h >= 2:
            for x in range(CX - w + 1, CX + w - 1):
                a.base[(x, my)] = TEETH                    # top teeth
        for x in range(CX - w + 1, CX + w - 1):
            a.base[(x, my + h)] = SK["lip"]                # bottom lip
    # grey mustache over the top lip
    for x in range(CX - 5, CX + 5):
        a.base[(x, 35)] = GREY["base"] if x < CX + 2 else GREY["s1"]
        if CX - 4 <= x < CX + 4:
            a.base[(x, 34)] = GREY["hi"] if x < CX else GREY["base"]
    a.base[(CX - 5, 36)] = GREY["s1"]
    a.base[(CX + 4, 36)] = GREY["s2"]
    # cheek lines (he's seen a lot of games)
    for side in (-1, 1):
        a.base[(int(CX + side * 6) - (1 if side < 0 else 0), 34)] = SK["s1"]
        a.base[(int(CX + side * 6) - (1 if side < 0 else 0), 35)] = SK["s1"]
    # ---- ball cap: a rounded crown and a curved brim, with a patch
    crown = ellipse(CX, 21, 12.8, 10.5)
    crown = {(x, y) for (x, y) in crown if y <= 22}
    for (x, y) in crown:
        l = lit(x, y, CX, 15, 12.8, 8)
        a.cap[(x, y)] = (255, 255, 255, 70) if l > 0.5 else (0, 0, 0, 80) if l < -0.35 else None
        a.base.pop((x, y), None)
    for x in (CX - 5, CX + 4):                             # panel seams
        for y in range(12, 22):
            if (x, y) in crown:
                a.cap[(x, y)] = (0, 0, 0, 50)
    a.cap[(CX, 10)] = (0, 0, 0, 60)                        # the button on top
    a.cap[(CX - 1, 10)] = (0, 0, 0, 60)
    brim = set()
    for x in range(CX - 14, CX + 14):
        dx = (x + 0.5 - CX) / 14
        y0 = 21 + int(round(dx * dx * 1.5))
        for y in range(y0, y0 + 3):
            brim.add((x, y))
    for (x, y) in brim:
        bottom = (x, y + 1) not in brim
        a.cap[(x, y)] = (0, 0, 0, 120) if bottom else (0, 0, 0, 30) if x > CX + 4 else (255, 255, 255, 30)
        a.base.pop((x, y), None)
    for x in range(CX - 11, CX + 11):                      # shade under the brim on the forehead
        y = max(yy for (xx, yy) in brim if xx == x) + 1
        if (x, y) in a.base and a.base[(x, y)] not in (GREY["s1"], GREY["base"]):
            a.base[(x, y)] = SK["s2"]
    # the patch: a cream circle with a little basketball
    for (x, y) in ellipse(CX, 16.5, 3.6, 3.6):
        a.cap_px[(x, y)] = (240, 230, 206)
    for (x, y) in ellipse(CX, 16.5, 2.3, 2.3):
        a.cap_px[(x, y)] = (232, 120, 40)
    seam = (80, 36, 20)                                    # ball seams: a line across and two curves
    for x in range(CX - 2, CX + 2):
        a.cap_px[(x, 16)] = seam
    for p in ((CX - 2, 15), (CX - 2, 17), (CX + 1, 15), (CX + 1, 17), (CX - 1, 14), (CX - 1, 18), (CX, 14), (CX, 18)):
        a.cap_px[p] = seam if p[1] not in (14, 18) else (232, 120, 40)
    return a


def outline(a):
    """One dark outline around everything (headshot style)."""
    filled = set(a.base) | set(a.cap) | set(a.shirt) | set(a.cap_px) | set(a.shirt_px)
    out = set()
    for (x, y) in filled:
        for n in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)):
            if n not in filled and 0 <= n[0] < N and 0 <= n[1] < N:
                out.add(n)
    return out


def to_img(px, rgba=False):
    img = Image.new("RGBA", (N, N), (0, 0, 0, 0))
    for (x, y), c in px.items():
        if 0 <= x < N and 0 <= y < N and c is not None:
            img.putpixel((x, y), c if rgba else c + (255,))
    return img.resize((N * SCALE, N * SCALE), Image.NEAREST)


def layers(mouth):
    a = draw(mouth)
    line = outline(a)
    base = dict(a.base)
    for p in line:
        base[p] = OUTLINE
    for p in list(base):
        if p in a.cap or p in a.cap_px or p in a.shirt or p in a.shirt_px:
            if base[p] != OUTLINE:
                base.pop(p)
    return a, base


def build():
    os.makedirs(OUT, exist_ok=True)
    strip = Image.new("RGBA", (N * SCALE * len(FRAMES), N * SCALE), (0, 0, 0, 0))
    for i, f in enumerate(FRAMES):
        a, base = layers(f)
        strip.alpha_composite(to_img(base), (i * N * SCALE, 0))
    strip.save(os.path.join(OUT, "base.png"), optimize=True)
    a, _ = layers("closed")
    to_img({p: (255, 255, 255, 255) for p in a.cap}, True).save(os.path.join(OUT, "cap_mask.png"), optimize=True)
    cap_detail = {p: c for p, c in a.cap.items() if c}
    cap_detail.update({p: c + (255,) for p, c in a.cap_px.items()})
    to_img(cap_detail, True).save(os.path.join(OUT, "cap_detail.png"), optimize=True)
    to_img({p: (255, 255, 255, 255) for p in a.shirt}, True).save(os.path.join(OUT, "shirt_mask.png"), optimize=True)
    shirt_detail = {p: c for p, c in a.shirt.items() if c}
    shirt_detail.update({p: c + (255,) for p, c in a.shirt_px.items()})
    to_img(shirt_detail, True).save(os.path.join(OUT, "shirt_detail.png"), optimize=True)


def composite(frame, cap, shirt):
    """What the app draws: polo, base frame, cap (tinted masks + details)."""
    def tint(name, color):
        m = Image.open(os.path.join(OUT, name))
        solid = Image.new("RGBA", m.size, hexrgb(color) + (255,))
        solid.putalpha(m.getchannel("A"))
        return solid
    s = N * SCALE
    img = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    img.alpha_composite(tint("shirt_mask.png", shirt))
    img.alpha_composite(Image.open(os.path.join(OUT, "shirt_detail.png")))
    img.alpha_composite(Image.open(os.path.join(OUT, "base.png")).crop((frame * s, 0, frame * s + s, s)))
    img.alpha_composite(tint("cap_mask.png", cap))
    img.alpha_composite(Image.open(os.path.join(OUT, "cap_detail.png")))
    return img


def previews():
    s = N * SCALE
    looks = [("#1D4FB8", "#1D4FB8"), ("#D22630", "#1E1E22"), ("#2E6B3A", "#E8C44A"), ("#1E1E1E", "#F4A6B8")]
    sheet = Image.new("RGBA", (s * len(FRAMES), s * 2), (236, 236, 242, 255))
    for i in range(len(FRAMES)):
        sheet.alpha_composite(composite(i, *looks[0]), (i * s, 0))
    for i, (cap, shirt) in enumerate(looks):
        sheet.alpha_composite(composite(0, cap, shirt), (i * s, s))
    sheet.save(os.path.join(PREVIEW, "coach.png"))
    # talking gif: the cycle the app plays while text types, then a blink
    cycle = [1, 2, 3, 2, 1, 0, 2, 3, 1, 0, 0, 0, 4, 0]
    gif = [composite(f, "#1D4FB8", "#1D4FB8").convert("RGB") for f in cycle]
    bg = Image.new("RGB", (s, s), (24, 20, 58))
    frames = []
    for im in gif:
        b = bg.copy()
        b.paste(im, (0, 0))
        frames.append(b.resize((s // 2, s // 2), Image.NEAREST))
    frames[0].save(os.path.join(PREVIEW, "coach_talking.gif"), save_all=True, append_images=frames[1:],
                   duration=110, loop=0)
    # the pop-up as the app lays it out (retro box, portrait on the left)
    W, H = 720, 300
    pop = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(pop)
    d.rectangle((0, 0, W - 1, H - 1), fill=(24, 20, 58))
    d.rectangle((6, 6, W - 7, H - 7), outline=(244, 235, 208), width=4)
    d.rectangle((14, 14, W - 15, H - 15), outline=(242, 194, 48), width=2)
    port = composite(2, "#1D4FB8", "#1D4FB8").resize((224, 224), Image.NEAREST)
    d.rectangle((26, 36, 26 + 232, 36 + 232), fill=(48, 30, 104))
    pop.alpha_composite(port, (30, 40))
    d.rectangle((26, 36, 26 + 232, 36 + 232), outline=(244, 235, 208), width=3)
    lines = ["COACH", "", "CONGRATS KID. YOU HAVE", "BEEN PLAYING WELL. WE", "ARE GOING TO GET YOU", "SOME MORE MINUTES."]
    y = 44
    for ln in lines:
        px = lg.text_pixels(ln.replace(".", " "), 0, 0)
        for (x, yy) in px:
            for i in range(4):
                for j in range(4):
                    pop.putpixel((280 + x * 4 + i, y + yy * 4 + j),
                                 (242, 194, 48, 255) if ln == "COACH" else (244, 235, 208, 255))
        y += 30 if ln else 14
    for (x, yy) in lg.text_pixels("CONTINUE", 0, 0):
        for i in range(3):
            for j in range(3):
                pop.putpixel((560 + x * 3 + i, 252 + yy * 3 + j), (242, 194, 48, 255))
    pop.save(os.path.join(PREVIEW, "coach_popup.png"))


if __name__ == "__main__":
    build()
    previews()
    print("wrote", OUT)
