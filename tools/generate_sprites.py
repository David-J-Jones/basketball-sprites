#!/usr/bin/env python3
"""
Procedural pixel-art generator for the basketball player sprites.

The player is drawn at 1x with hard pixels and a dark outline, then split
into layers that the game colors at runtime with React Native's
<Image tintColor> (which paints every visible pixel one flat color):

    skin    white mask   -> tinted with the player's skin tone
    jersey  white mask   -> tinted with the team's jersey color
    trim    white mask   -> tinted with the team's trim color
    detail  full color   -> outlines, black shorts, grey shoes, socks, eyes,
                            plus see-through shading over the tinted parts
    facial  per facial-hair type: white mask (tinted hair color) + detail
    hair    per hair style: white mask (tinted hair color) + detail

Draw order: skin, jersey, trim, detail, facial mask, facial detail,
hair mask, hair detail.

There are 15 bodies: 5 height classes x 3 weight classes. Every piece is
trimmed, de-duplicated, scaled up SCALE times (nearest neighbour, so it
stays crisp) and packed into atlas pages. Each body gets its own pages, so
the app only decodes the bodies that are on court; hair and facial hair
share a common set of pages.

Run:  python3 tools/generate_sprites.py
"""
import hashlib
import json
import multiprocessing
import zlib
import math
import os
import random
import shutil

from PIL import Image, ImageDraw

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SPRITE_DIR = os.path.join(ROOT, "sprites")
RN_DIR = os.path.join(ROOT, "integration", "react-native", "playerSprites")
PREVIEW_DIR = os.path.join(ROOT, "previews")

# virtual frame (the same canvas for every frame, build and layer), at 1x
FRAME_W, FRAME_H = 64, 80
ANCHOR_X, ANCHOR_Y = FRAME_W // 2, FRAME_H   # bottom centre, at the feet
GROUND = FRAME_H - 2      # last row of sole pixels; the outline sits on the bottom row
HIP_X = ANCHOR_X
SCALE = 3                 # detail layers: atlas pixels per art pixel (crisp outlines)
MASK_RES = 2              # tint masks: texels per art pixel (edges hide under outlines)
PAGE_PX = 2040            # max atlas page width/height in pixels
PAD = 1                   # gap between atlas pieces, in stored units

LIGHT = (-0.6, -0.8)      # light from the upper-left
BALL_R = 4.8
BALL_CELL = 11

# ---------------------------------------------------------------- colors
# Pixels are drawn as tags. Fixed tags always have the same color; tinted
# tags become a white mask pixel plus (optionally) a shading overlay.
FIXED = {
    "outline": (28, 22, 32, 255),
    "eye": (22, 16, 24, 255),
    "smear": (255, 255, 255, 150),
}
TINTED = {  # tag -> (slot, shading overlay drawn over the flat tint, mask alpha)
    "skin0": ("skin", None, 255),
    "skin1": ("skin", (72, 26, 12, 70), 255),
    "skin2": ("skin", (72, 26, 12, 118), 255),
    "skin3": ("skin", (48, 14, 8, 150), 255),
    "jersey0": ("jersey", None, 255),
    "jersey1": ("jersey", (16, 18, 44, 58), 255),
    "trim0": ("trim", None, 255),
    "trim1": ("trim", (16, 18, 44, 70), 255),
    "hair0": ("hair", None, 255),
    "hair1": ("hair", (0, 0, 0, 95), 255),
    "hairF": ("hair", None, 140),        # faded sides: see-through hair
    "fh0": ("facial", None, 255),
    "fh1": ("facial", (0, 0, 0, 95), 255),
    "stub": ("facial", None, 105),       # stubble: see-through hair color
    # outfit: always tinted, so park-mode cosmetics can recolor them. The
    # league defaults (DEFAULT_OUTFIT) reproduce black shorts, white socks
    # and grey shoes.
    "shorts0": ("shorts", None, 255),
    "shorts1": ("shorts", (0, 0, 0, 74), 255),
    "shorts2": ("shorts", (0, 0, 0, 107), 255),
    "sock0": ("sock", None, 255),
    "sock1": ("sock", (16, 18, 44, 58), 255),
    "shoe0": ("shoe", None, 255),
    "shoe1": ("shoe", (0, 0, 0, 64), 255),
    "sole": ("sole", None, 255),
    "hw0": ("headwear", None, 255),
    "hw1": ("headwear", (0, 0, 0, 80), 255),
}
BODY_SLOTS = ["skin", "jersey", "trim", "shorts", "sock", "shoe", "sole"]
DEFAULT_OUTFIT = {"shorts": "#3E3E46", "sock": "#F2F2F6", "shoe": "#AAACB4", "sole": "#484852"}

# Wear regions: skin areas an outfit can cover. A skin tag carries them as a
# suffix ("skin0@sa.sb"); each region becomes an extra mask the app draws
# over the skin, tinted with the item's color, only when it's worn.
WEAR_REGIONS = ["sa", "sb", "sn", "sf", "wr", "tl", "sh"]
WEAR_NAMES = {"sa": "sleeveShort", "sb": "sleeveLong", "sn": "armSleeveNear", "sf": "armSleeveFar",
              "wr": "wristband", "tl": "shortsLong", "sh": "sockTall"}
_SPLIT = {}


def split_tag(tag):
    """'skin0@sa.sb' -> ('skin0', ('sa', 'sb'))."""
    r = _SPLIT.get(tag)
    if r is None:
        base, _, regs = tag.partition("@")
        r = _SPLIT[tag] = (base, tuple(regs.split(".")) if regs else ())
    return r


def wear(tag, *regions):
    return tag + "@" + ".".join(regions) if regions else tag
WHITE = (255, 255, 255, 255)

# ---------------------------------------------------------------- builds
# 5 height classes scale the bone lengths, 3 weight classes scale the
# thickness. The head is the same size on every body, so taller players
# look lankier, not just bigger.
BASE_BODY = dict(thigh=8.0, shin=8.0, upper=6.0, fore=6.0, shoulder=10.0, neck=12.0,
                 torso_r=4.7, hip_r=4.5, thigh_r=2.1, shin_r=1.6, arm_r=1.5, neck_r=1.6)
HEIGHT_CLASSES = {1: 0.84, 2: 0.89, 3: 0.945, 4: 1.0, 5: 1.055, 6: 1.11, 7: 1.17}
WEIGHT_CLASSES = {"slim": 0.8, "lean": 0.9, "average": 1.0, "solid": 1.15, "heavy": 1.3}
LENGTHS = ("thigh", "shin", "upper", "fore", "shoulder", "neck")


def _make_body(h, w):
    b = {}
    for k, v in BASE_BODY.items():
        b[k] = v * (HEIGHT_CLASSES[h] if k in LENGTHS else WEIGHT_CLASSES[w])
    b["belly"] = w == "heavy"
    return b


BODIES = {"h%d-%s" % (h, w): _make_body(h, w) for h in HEIGHT_CLASSES for w in WEIGHT_CLASSES}
MID_BODY = "h4-average"
B = BODIES[MID_BODY]


def use_body(name):
    global B
    B = BODIES[name]


def vec(deg, length=1.0):
    """Limb direction. 0 = straight down, 90 = forward (right), 180 = up."""
    r = math.radians(deg)
    return (math.sin(r) * length, math.cos(r) * length)


def add(a, b):
    return (a[0] + b[0], a[1] + b[1])


def lit(ox, oy):
    return ox * LIGHT[0] + oy * LIGHT[1]


# ---------------------------------------------------------------- layers
class Layer:
    """A sparse set of pixels that gets outlined as one shape."""

    def __init__(self):
        self.px = {}

    def capsule(self, a, b, r, color_fn):
        ax, ay = a
        bx, by = b
        dx, dy = bx - ax, by - ay
        seg2 = dx * dx + dy * dy
        for y in range(int(math.floor(min(ay, by) - r)) - 1, int(math.ceil(max(ay, by) + r)) + 2):
            for x in range(int(math.floor(min(ax, bx) - r)) - 1, int(math.ceil(max(ax, bx) + r)) + 2):
                px, py = x + 0.5, y + 0.5
                t = 0.0 if seg2 == 0 else max(0.0, min(1.0, ((px - ax) * dx + (py - ay) * dy) / seg2))
                cx, cy = ax + dx * t, ay + dy * t
                ox, oy = px - cx, py - cy
                if math.hypot(ox, oy) <= r:
                    self.pos = (px, py)   # for color functions that need it
                    c = color_fn(t, ox / r, oy / r)
                    if c is not None:
                        self.px[(x, y)] = c

    def outline(self):
        out = {}
        for (x, y) in self.px:
            for nx, ny in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)):
                if (nx, ny) not in self.px:
                    out[(nx, ny)] = "outline"
        return out


def shaded(base, shade, thr=0.3):
    def fn(t, ox, oy):
        return shade if lit(ox, oy) < -thr else base
    return fn


# ---------------------------------------------------------------- heads & hair
# Head templates sit on a 15 x 19 grid; the bald skull is at offset (2, 4).
HEAD_GRID_W, HEAD_GRID_H = 15, 19
HEAD_ANCHOR = (7, 15)     # grid pixel that sits on the neck point
SKULL_OFF = (2, 4)
SKULL = [
    "...SSSSS...",
    ".SSSSSSSSs.",
    "SSSSSSSSSSs",
    "SSSSSSSSSSS",
    "sSSSSSSSSSS",
    "sSSSSSSeeS.",
    "ssSSSSSESSS",
    "sSsSSSSESSS",
    ".sSSSSSSSS.",
    "..sSSSSSMS.",
    "..ssSSSSS..",
    "....sss....",
]
SKULL_TAGS = {"S": "skin0", "s": "skin1", "E": "eye", "e": "skin3", "M": "skin3"}

# Hair and facial hair are painted over the skull on the head grid.
# Template chars: H hair, h hair shade, f faded (see-through) hair; for
# facial hair B beard, b beard shade, t stubble. '.' lets the skull show.
HAIR_CHARS = {"H": "hair0", "h": "hair1", "f": "hairF"}
FACIAL_CHARS = {"B": "fh0", "b": "fh1", "t": "stub"}

CREW_SRC = [
    "...hhhhh...",
    ".hhHHHHHhh.",
    "hhHHHHHHHHh",
    "hHHHHHHHHHH",
    "hhHHHH....h",
    "hhhH.......",
    "hh.........",
    "hh.........",
    ".h.........",
]
BUZZ_SRC = [
    "...hhhhh...",
    ".hhhHHhhh..",
    "hhHHHHHHh..",
    "hhhhhhhh...",
    "hhh........",
    "hh.........",
    "h..........",
]
FADE_SRC = [
    "..hHHHHHh..",
    ".hHHHHHHHh.",
    "hhHHHHHHHHh",
    "fhHHHHHHHHH",
    "ffhHHH....h",
    "fff........",
    "ff.........",
    "f..........",
]
CORNROWS_SRC = [
    "...hhhhh...",
    ".hHhHhHhh..",
    "hhHhHhHhHh.",
    "hHhHhHhHhHh",
    "hhHhHh....h",
    "hhhH.......",
    "hh.........",
    "hh.........",
    ".h.........",
]


def _from_src(src, chars=HAIR_CHARS, extra=()):
    m = {}
    for r, row in enumerate(src):
        for c, ch in enumerate(row):
            if ch in chars:
                m[(c + SKULL_OFF[0], r + SKULL_OFF[1])] = chars[ch]
    for c, r, tag in extra:           # extra pixels in head-grid coords
        m[(c, r)] = tag
    return m


def _skull_pixels():
    return {(c + SKULL_OFF[0], r + SKULL_OFF[1])
            for r, row in enumerate(SKULL) for c, ch in enumerate(row) if ch != "."}


def _afro():
    m = {}
    cx, cy, rx, ry = 6.3, 7.2, 6.8, 7.0
    for r in range(HEAD_GRID_H):
        for c in range(HEAD_GRID_W):
            dx, dy = (c + 0.5 - cx) / rx, (r + 0.5 - cy) / ry
            if dx * dx + dy * dy > 1:
                continue
            if c >= 7 and r >= 8:        # keep the face clear
                continue
            if r >= 13 and c >= 4:       # and the jaw
                continue
            shade = lit(dx, dy) < -0.3 or (c * 3 + r * 5) % 7 == 0
            m[(c, r)] = "hair1" if shade else "hair0"
    return m


def _locs():
    m = _from_src(CROWN_VOLUME_SRC)
    # rope-like locs hanging down the back to the shoulders
    for r, c0, c1 in [(7, 1, 1), (8, 0, 2), (9, 0, 2), (10, 0, 3), (11, 0, 3), (12, 0, 4),
                      (13, 1, 4), (14, 1, 5), (15, 1, 5), (16, 2, 5), (17, 2, 5), (18, 3, 4)]:
        for c in range(c0, c1 + 1):
            twist = (r + c) % 3 == 0
            m[(c, r)] = "hair1" if (c % 2 == 1 or twist or c == c1) else "hair0"
    return m


CROWN_VOLUME_SRC = [
    "..hHHHHHh..",
    ".hHHhHHhHh.",
    "hHhHHhHHhHh",
    "hHHhHHhHHHH",
    "hhHHhH....h",
    "hhhH.......",
    "hh.........",
    "hh.........",
    ".h.........",
]

MOHAWK_SRC = [
    "...HHHHH...",
    ".ffHHHHHhf.",
    "fff......f.",
    "ff.........",
    "f..........",
]
FLOW_SRC = [
    "...hhhhh...",
    ".hhHHHHHhh.",
    "hHHHhHHHHHh",
    "hHHHHHHHHHH",
    "hhHHHHH...h",
    "hhHH.......",
    "hhh........",
    "hhh........",
    ".hh........",
]


def _mohawk():
    m = _from_src(MOHAWK_SRC)
    for r, c0, c1 in [(1, 6, 9), (2, 5, 10), (3, 4, 11)]:          # the fin above the skull
        for c in range(c0, c1 + 1):
            m[(c, r)] = "hair1" if (c + r) % 3 == 0 else "hair0"
    return m


def _high_top():
    m = _from_src(CREW_SRC)
    for r in range(0, 4):                                        # tall flat box on top
        for c in range(4, 12):
            m[(c, r)] = "hair1" if c in (4, 11) or r == 0 else ("hair0" if (c + r) % 4 else "hair1")
    return m


def _twists():
    m = _from_src(CREW_SRC)
    for c in range(4, 12):                                       # short twists poke up
        if c % 2 == 0:
            m[(c, 3)] = "hair1"
    for (c, r), tag in list(m.items()):
        if tag == "hair0" and c % 2 == 1:
            m[(c, r)] = "hair1"
    return m


def _curly():
    m = {}
    cx, cy, rx, ry = 7.0, 6.6, 5.6, 4.4
    for r in range(HEAD_GRID_H):
        for c in range(HEAD_GRID_W):
            dx, dy = (c + 0.5 - cx) / rx, (r + 0.5 - cy) / ry
            if dx * dx + dy * dy > 1 or (c >= 8 and r >= 8):
                continue
            m[(c, r)] = "hair1" if lit(dx, dy) < -0.25 or (c * 5 + r * 3) % 4 == 0 else "hair0"
    for (c, r), tag in _from_src(CREW_SRC).items():             # keep the back and sideburns
        m.setdefault((c, r), tag)
    return m


def _flow():
    m = _from_src(FLOW_SRC)
    for r, c0, c1 in [(8, 1, 2), (9, 1, 2), (10, 1, 3), (11, 1, 3), (12, 2, 4), (13, 2, 4), (14, 3, 4)]:
        for c in range(c0, c1 + 1):
            m[(c, r)] = "hair1" if c == c1 or r >= 13 else "hair0"
    return m


HAIR_STYLES = {
    "buzz": _from_src(BUZZ_SRC),
    "fade": _from_src(FADE_SRC, extra=[(c, 3, "hair1") for c in range(5, 10)]),
    "crew": _from_src(CREW_SRC),
    "cornrows": _from_src(CORNROWS_SRC, extra=[(1, 12, "hair1"), (1, 13, "hair0"), (2, 14, "hair1")]),
    "afro": _afro(),
    "locs": _locs(),
    "mohawk": _mohawk(),
    "high_top": _high_top(),
    "twists": _twists(),
    "curly": _curly(),
    "flow": _flow(),
}

# facial hair, in skull coordinates (face on the right, mouth at row 9 col 8)
STUBBLE_SRC = [
    "", "", "", "", "", "",
    "....t......",
    "....t......",
    "....tttttt.",
    "...ttttt.t.",
    "...tttttt..",
    "....ttt....",
]
MUSTACHE_SRC = [
    "", "", "", "", "", "", "", "",
    ".......BBB.",
    ".........b.",
]
GOATEE_SRC = [
    "", "", "", "", "", "", "", "",
    ".......BBB.",
    ".........b.",
    "......BBB..",
    "....BBb....",
    ".....bb....",
]
BEARD_SRC = [
    "", "", "", "", "",
    "....b......",
    "....B......",
    "...bB......",
    "...BBBBBBB.",
    "..bBBBBB.b.",
    "..bBBBBBB..",
    "..bBBBBbb..",
    "...bbbb....",
    "....bb.....",
]
CHINSTRAP_SRC = [
    "", "", "", "", "", "",
    "....b......",
    "...bb......",
    "..bb.......",
    "..b........",
    "..bb....b..",
    "...bbbbb...",
]
LONG_BEARD_SRC = [
    "", "", "", "", "",
    "....b......",
    "....B......",
    "...bB......",
    "...BBBBBBB.",
    "..bBBBBB.b.",
    "..bBBBBBB..",
    "..bBBBBBb..",
    "...BBBBB...",
    "...bBBBb...",
    "....bBb....",
    ".....b.....",
]
FACIAL_HAIR = {
    "stubble": _from_src(STUBBLE_SRC, FACIAL_CHARS),
    "mustache": _from_src(MUSTACHE_SRC, FACIAL_CHARS),
    "goatee": _from_src(GOATEE_SRC, FACIAL_CHARS),
    "beard": _from_src(BEARD_SRC, FACIAL_CHARS),
    "chinstrap": _from_src(CHINSTRAP_SRC, FACIAL_CHARS),
    "long_beard": _from_src(LONG_BEARD_SRC, FACIAL_CHARS),
}


def _headwear(rows, tails=()):
    """Headbands sit across the forehead just above the eyes, from one pixel
    behind the skull (so they wrap over hair) to the brow."""
    skull = _skull_pixels()
    m = {}
    for r in rows:
        for c in range(1, HEAD_GRID_W):
            if (c, r) in skull or c == 1:
                m[(c, r)] = "hw1" if c <= 4 else "hw0"
    for c, r in tails:
        m[(c, r)] = "hw1" if (c + r) % 2 else "hw0"
    return m


HEADWEAR = {
    "headband": _headwear([8]),
    "wide_headband": _headwear([7, 8]),
    "tied_headband": _headwear([8], tails=[(0, 8), (0, 9), (1, 9), (0, 10), (0, 11), (1, 12)]),
}


def blit_head(layer, origin, style=None, facial=None, headwear=None):
    ox, oy = origin
    for r, row in enumerate(SKULL):
        for c, ch in enumerate(row):
            if ch != ".":
                layer.px[(ox + c + SKULL_OFF[0], oy + r + SKULL_OFF[1])] = SKULL_TAGS[ch]
    if facial:
        for (c, r), tag in FACIAL_HAIR[facial].items():
            layer.px[(ox + c, oy + r)] = tag
    if style:
        for (c, r), tag in HAIR_STYLES[style].items():
            layer.px[(ox + c, oy + r)] = tag
    if headwear:
        for (c, r), tag in HEADWEAR[headwear].items():
            layer.px[(ox + c, oy + r)] = tag

# ---------------------------------------------------------------- ball (separate sheet)
BALL_COLORS = {
    "ball": (234, 116, 38, 255), "ball_light": (252, 166, 92, 255),
    "ball_shade": (178, 72, 24, 255), "ball_seam": (58, 26, 14, 255),
}


def ball_layer(center, rot_deg=0.0, squash=0.0):
    """Shaded basketball with seams; rot_deg spins the seams (180 deg period)."""
    cx, cy = center
    rx = BALL_R * (1 + 0.18 * squash)
    ry = BALL_R * (1 - 0.22 * squash)
    L = (-0.45, -0.6, 0.66)
    th = math.radians(rot_deg)
    tilt_x = math.radians(-20)
    layer = Layer()
    for y in range(int(cy - ry) - 2, int(cy + ry) + 3):
        for x in range(int(cx - rx) - 2, int(cx + rx) + 3):
            nx = (x + 0.5 - cx) / rx
            ny = (y + 0.5 - cy) / ry
            d2 = nx * nx + ny * ny
            if d2 > 1.0:
                continue
            nz = math.sqrt(max(0.0, 1 - d2))
            light = nx * L[0] + ny * L[1] + nz * L[2]
            u = nx * math.cos(th) + nz * math.sin(th)
            w = -nx * math.sin(th) + nz * math.cos(th)
            v = ny
            v, w = v * math.cos(tilt_x) - w * math.sin(tilt_x), v * math.sin(tilt_x) + w * math.cos(tilt_x)
            seam = abs(u) < 0.12 or abs(v) < 0.12 or abs(abs(u) - 0.66 - 0.3 * v * v) < 0.07
            if seam and d2 < 0.9:
                c = BALL_COLORS["ball_seam"]
            elif light > 0.72:
                c = BALL_COLORS["ball_light"]
            elif light > 0.12:
                c = BALL_COLORS["ball"]
            else:
                c = BALL_COLORS["ball_shade"]
            layer.px[(x, y)] = c
    return layer


# ---------------------------------------------------------------- body
def draw_leg(layer, hip, thigh_deg, shin_deg, foot_rot, far):
    skin, skin_s = ("skin1", "skin2") if far else ("skin0", "skin1")
    cloth, cloth_s = ("shorts1", "shorts2") if far else ("shorts0", "shorts1")
    sock, sock_s = ("sock1", "sock1") if far else ("sock0", "sock1")
    knee = add(hip, vec(thigh_deg, B["thigh"]))
    ankle = add(knee, vec(shin_deg, B["shin"]))

    def shin_fn(t, ox, oy):
        if t > 0.62:
            return sock_s if lit(ox, oy) < -0.4 else sock
        tag = skin_s if lit(ox, oy) < -0.3 else skin
        return wear(tag, "sh") if t > 0.18 else tag      # tall socks
    layer.capsule(knee, ankle, B["shin_r"], shin_fn)

    def thigh_fn(t, ox, oy):
        if t < 0.55:
            return cloth_s if lit(ox, oy) < -0.2 else cloth
        return wear(skin_s if lit(ox, oy) < -0.3 else skin, "tl")     # long shorts
    layer.capsule(hip, knee, B["thigh_r"], thigh_fn)
    # shorts leg opening is a touch wider than the thigh
    layer.capsule(hip, add(hip, vec(thigh_deg, B["thigh"] * 0.5)), B["thigh_r"] + 0.6,
                  shaded(cloth, cloth_s, 0.2))
    # shoe
    fr = math.radians(foot_rot)
    fwd = (math.cos(fr), math.sin(fr))
    down = (-math.sin(fr), math.cos(fr))
    base = add(ankle, (down[0] * 1.2, down[1] * 1.2))
    heel = add(base, (-fwd[0] * 1.5, -fwd[1] * 1.5))
    toe = add(base, (fwd[0] * 3.2, fwd[1] * 3.2))
    upper = "shoe1" if far else "shoe0"

    def shoe_fn(t, ox, oy):
        side = ox * down[0] + oy * down[1]
        if side > 0.35:
            return "sole"
        if side < -0.5 and t < 0.5:
            return "shoe1"
        return upper
    layer.capsule(heel, toe, 1.55, shoe_fn)
    return ankle


def arm_points(shoulder, upper_deg, fore_deg, reach=1.0):
    elbow = add(shoulder, vec(upper_deg, B["upper"] * reach))
    return elbow, add(elbow, vec(fore_deg, B["fore"] * reach))


def draw_arm(layer, shoulder, upper_deg, fore_deg, far, reach=1.0):
    skin, skin_s = ("skin1", "skin2") if far else ("skin0", "skin1")
    elbow, hand = arm_points(shoulder, upper_deg, fore_deg, reach)
    near = ("sf",) if far else ("sn",)          # one-arm shooting sleeve

    def upper_fn(t, ox, oy):
        tag = skin_s if lit(ox, oy) < -0.3 else skin
        return wear(tag, "sa") if t < 0.5 else wear(tag, "sb", *near)

    def fore_fn(t, ox, oy):
        tag = skin_s if lit(ox, oy) < -0.3 else skin
        return wear(tag, "sb", *near, "wr") if t > 0.72 else wear(tag, "sb", *near)
    layer.capsule(shoulder, elbow, B["arm_r"], upper_fn)
    layer.capsule(elbow, hand, B["arm_r"] - 0.15, fore_fn)
    layer.capsule(hand, hand, 1.7, shaded(skin, skin_s, 0.5))
    return hand


def render(pose, style=None, stand_hip_y=None, facial=None):
    """Render one pose. Returns (pixels, info): pixels maps (x, y) in the
    virtual frame to a color tag."""
    lean = pose.get("lean", 8)
    hip = (HIP_X + pose.get("dx", 0), 100.0)
    tdir = vec(180 - lean)  # up the torso; positive lean tips it forward
    shoulder_up = B["shoulder"] + pose.get("shrug", 0)
    shoulder = add(hip, (tdir[0] * shoulder_up, tdir[1] * shoulder_up))
    neck = add(hip, (tdir[0] * B["neck"], tdir[1] * B["neck"]))

    far_leg, near_leg, body = Layer(), Layer(), Layer()
    far_arm, near_arm, head = Layer(), Layer(), Layer()

    fl, nl = pose["far_leg"], pose["near_leg"]
    draw_leg(far_leg, add(hip, (-0.5, 0)), fl[0], fl[1], fl[2] if len(fl) > 2 else 0, True)
    draw_leg(near_leg, add(hip, (0.5, 0)), nl[0], nl[1], nl[2] if len(nl) > 2 else 0, False)

    # torso: jersey, then the shorts waist over its bottom
    chest_lo = add(hip, (tdir[0] * 2.0, tdir[1] * 2.0))
    chest_hi = add(hip, (tdir[0] * (B["shoulder"] - 1), tdir[1] * (B["shoulder"] - 1)))

    def jersey_fn(t, ox, oy):
        if t > 0.93 and abs(ox) < 0.45:
            return "trim0"          # collar / arm-hole trim
        return "jersey1" if lit(ox, oy) < -0.35 else "jersey0"
    body.capsule(chest_lo, chest_hi, B["torso_r"], jersey_fn)
    if B["belly"]:
        fwd = vec(90 - lean)
        bl = add(hip, (tdir[0] * 3.2 + fwd[0] * 1.4, tdir[1] * 3.2 + fwd[1] * 1.4))
        body.capsule(bl, add(bl, (tdir[0] * 1.5, tdir[1] * 1.5)), B["torso_r"] * 0.8, jersey_fn)

    waist = 2.6   # distance up the torso from the hip to the top of the shorts

    def shorts_fn(t, ox, oy):
        px, py = body.pos
        along = (px - hip[0]) * tdir[0] + (py - hip[1]) * tdir[1]
        if along > waist:
            return None             # above the waist: leave the jersey
        if along > waist - 1:
            return "trim0"          # waistband
        return "shorts1" if lit(ox, oy) < -0.35 else "shorts0"
    body.capsule(add(hip, (tdir[0] * -1.0, tdir[1] * -1.0)), add(hip, (tdir[0] * 1.5, tdir[1] * 1.5)),
                 B["hip_r"], shorts_fn)
    body.capsule(shoulder, add(shoulder, (tdir[0] * 1.2, tdir[1] * 1.2)), 2.0,
                 lambda t, ox, oy: "jersey0")
    # neck + head (rebuilt cheaply for each hair / facial-hair variant)
    hx = int(round(neck[0])) - HEAD_ANCHOR[0] + pose.get("head_dx", 0)
    hy = int(round(neck[1])) - HEAD_ANCHOR[1] + pose.get("head_dy", 0)
    neck_r = B["neck_r"]

    def make_head(st, fac, hw=None):
        h = Layer()
        h.capsule(add(neck, (tdir[0] * -1.5, tdir[1] * -1.5)), neck, neck_r, shaded("skin0", "skin1", 0.1))
        blit_head(h, (hx, hy), st, fac, hw)
        return h
    head = make_head(style, facial)

    reach = pose.get("reach", 1.0)
    fa, na = pose["far_arm"], pose["near_arm"]
    far_hand = draw_arm(far_arm, add(shoulder, (-0.3, 0.3)), fa[0], fa[1], True, reach)
    near_hand = draw_arm(near_arm, shoulder, na[0], na[1], False, reach)

    # motion smear: the path the near hand swept through since earlier poses
    smear = {}
    if pose.get("smear"):
        path = [arm_points(shoulder, u, f, reach)[1] for u, f in pose["smear"]] + [near_hand]
        for (ax, ay), (bx, by) in zip(path, path[1:]):
            steps = int(max(abs(bx - ax), abs(by - ay)) * 2) + 1
            for k in range(steps + 1):
                t = k / steps
                x, y = ax + (bx - ax) * t, ay + (by - ay) * t
                for ox, oy in ((0, 0), (1, 0), (0, 1), (1, 1), (-1, 0), (0, -1)):
                    smear[(int(x + ox - 0.5), int(y + oy - 0.5))] = "smear"

    # vertical placement: grounded poses stand on the floor, 'lift' poses
    # are raised relative to the standing hip height
    legs_bottom = max(y for (_, y) in list(far_leg.px) + list(near_leg.px))
    if "lift" in pose and stand_hip_y is not None:
        dy = (stand_hip_y - pose["lift"]) - hip[1]
    else:
        dy = GROUND - legs_bottom
    dy = int(round(dy))
    # bob > 0 sinks the upper body (legs stay planted); bob < 0 lifts it all
    bob = pose.get("bob", 0)
    dy_legs = dy + min(bob, 0)
    dy += bob

    if pose.get("arms_behind_head"):
        # arms straight up would hide the face, so tuck them behind the head
        order = [far_arm, far_leg, near_leg, body, near_arm, head]
    else:
        order = [far_arm, far_leg, near_leg, body, head, near_arm]

    # outlines of everything but the head are computed once and reused
    cached = {id(l): (l.outline(), l.px) for l in order if l is not head}
    behind = pose.get("arms_behind_head")
    skull_top = hy + SKULL_OFF[1] + 1

    def paint(grid, layers, head_layer):
        clipped = False
        for layer in layers:
            shift = dy_legs if layer in (far_leg, near_leg) else dy
            srcs = (head_layer.outline(), head_layer.px) if layer is head else cached[id(layer)]
            for src in srcs:
                for (x, y), tag in src.items():
                    y2 = y + shift
                    if 0 <= x < FRAME_W and 0 <= y2 < FRAME_H:
                        grid[(x, y2)] = tag
                    else:
                        clipped = True
        return clipped

    # everything drawn before the head is stacked once
    split = order.index(head)
    under = {}
    for (x, y), tag in smear.items():
        if 0 <= x < FRAME_W and 0 <= y + dy < FRAME_H:
            under[(x, y + dy)] = tag
    under_clipped = paint(under, order[:split], None)

    def compose(head_layer):
        grid = dict(under)
        clipped = paint(grid, order[split:], head_layer) or under_clipped
        if behind:
            # hands raised above the skull stay in front of big hair (afro etc.)
            for layer in (far_arm, near_arm):
                for src in cached[id(layer)]:
                    for (x, y), tag in src.items():
                        if y < skull_top and 0 <= x < FRAME_W and 0 <= y + dy < FRAME_H:
                            grid[(x, y + dy)] = tag
        return grid, clipped

    grid, clipped = compose(head)

    def ball_spot(spec):
        """Ball centre (before the vertical shift) and depth for a ball spec.
        Depth: +1 near (camera) side, 0 centred in front, -1 far side."""
        kind, a, b = spec[:3]
        d = spec[3] if len(spec) > 3 else BALL_DEPTH[kind]
        if kind == "near":
            pt = add(near_hand, (a, b))
        elif kind == "far":
            pt = add(far_hand, (a, b))
        elif kind == "between":
            pt = add(((near_hand[0] + far_hand[0]) / 2, (near_hand[1] + far_hand[1]) / 2), (a, b))
        elif kind == "hip":
            pt = add(hip, (a, b))
        else:                    # "ground": resting on the floor, x relative to the hip
            pt = (hip[0] + a, GROUND + 1 - BALL_R - dy)
        return pt, d

    ball = None
    depth = None
    if pose.get("ball"):
        if pose["ball"][0] == "lerp":           # in-between frame: blend two specs
            _, spec_a, spec_b, t = pose["ball"]
            (pa, da), (pb, db) = ball_spot(spec_a), ball_spot(spec_b)
            ball = (pa[0] + (pb[0] - pa[0]) * t, pa[1] + (pb[1] - pa[1]) * t)
            depth = round(da + (db - da) * t, 2)
        else:
            ball, depth = ball_spot(pose["ball"])
        ball = [ball[0], ball[1] + dy]

    info = {
        "hip": [hip[0], hip[1] + dy],
        "near_hand": [near_hand[0], near_hand[1] + dy],
        "far_hand": [far_hand[0], far_hand[1] + dy],
        "ball": ball,
        "ball_depth": depth,
        "lift": max(0, GROUND - (legs_bottom + dy_legs)),
        "clipped": clipped,
        "head_origin": (hx, hy + dy),
        # same pose with a different hair style / facial hair, without redrawing the body
        "restyle": lambda st, fac, hw=None: compose(make_head(st, fac, hw))[0],
    }
    return grid, info


# ---------------------------------------------------------------- animations
BALL_DEPTH = {"near": 0.5, "far": -0.5, "between": 0.0, "hip": 0.5, "ground": 0.5}


def P(near_leg, far_leg, near_arm, far_arm, **kw):
    d = {"near_leg": near_leg, "far_leg": far_leg, "near_arm": near_arm, "far_arm": far_arm}
    d.update(kw)
    return d


def lerp_pose(a, b, t):
    """In-between of two poses: joint angles and offsets blend linearly,
    on/off switches come from the nearer pose, and the ball blends too."""
    out = dict(a if t < 0.5 else b)
    for k in ("near_leg", "far_leg", "near_arm", "far_arm"):
        ta, tb = list(a[k]), list(b[k])
        n = max(len(ta), len(tb))
        ta += [0] * (n - len(ta))
        tb += [0] * (n - len(tb))
        out[k] = tuple(x + (y - x) * t for x, y in zip(ta, tb))
    for k, default in (("lean", 8), ("dx", 0), ("shrug", 0), ("reach", 1.0)):
        if k in a or k in b:
            out[k] = a.get(k, default) + (b.get(k, default) - a.get(k, default)) * t
    for k in ("bob", "head_dx", "head_dy"):
        if k in a or k in b:
            out[k] = int(round(a.get(k, 0) + (b.get(k, 0) - a.get(k, 0)) * t))
    if a.get("ball") and b.get("ball"):
        out["ball"] = a["ball"] if t == 0 else ("lerp", a["ball"], b["ball"], t)
    return out


def resample(keys, n, loop=True):
    """n evenly spaced poses through a list of key poses."""
    span = len(keys) if loop else len(keys) - 1
    out = []
    for i in range(n):
        pos = i * span / (n if loop else n - 1)
        k = int(pos)
        t = pos - k
        a = keys[k % len(keys)]
        b = keys[(k + 1) % len(keys)] if (loop or k + 1 < len(keys)) else a
        out.append(lerp_pose(a, b, t) if t > 1e-6 else dict(a))
    return out


def swap_sides(pose, legs=True):
    """Mirror a pose through the body: near and far limbs trade places and
    the ball moves to the other side (depth flips)."""
    p = dict(pose)
    p["near_arm"], p["far_arm"] = pose["far_arm"], pose["near_arm"]
    if legs:
        p["near_leg"], p["far_leg"] = pose["far_leg"], pose["near_leg"]
    if pose.get("ball"):
        b = pose["ball"]
        kind = {"near": "far", "far": "near"}.get(b[0], b[0])
        depth = b[3] if len(b) > 3 else BALL_DEPTH[b[0]]
        p["ball"] = (kind, b[1], b[2], -depth)
    return p


# Run cycle: (thigh, shin, foot_rot) per frame for the near leg. The far leg
# uses the same table shifted by half a cycle; arms swing opposite the legs.
RUN_LEG = [
    (34, 12, -6),     # contact, heel strike
    (18, -8, 0),      # down / weight on it
    (0, -22, 10),     # passing under the body
    (-24, -48, 30),   # push off
    (-32, -96, 50),   # kick back
    (-4, -98, 40),    # recovery, heel under butt
    (32, -48, 10),    # knee drive
    (44, -4, -10),    # reach
]
RUN_ARM = [  # (upper, forearm) for the near arm
    (-30, 50), (-20, 60), (0, 80), (25, 115),
    (40, 135), (30, 120), (5, 85), (-25, 55),
]
RUN_BOB = [0, 1, 0, -1, -1, 0, 0, -1]


def idle_frames():
    return [P((8, -4, 0), (-6, -2, 0), (22 - b * 2, 50 - b * 4), (-14, 20), lean=4, bob=b)
            for b in [0, 0, 1, 1]]


RUN_FRAMES = 12   # locomotion cycles are 12 frames: 8 key poses + in-betweens


def run_keys():
    return [P(RUN_LEG[i], RUN_LEG[(i + 4) % 8], RUN_ARM[(i + 4) % 8], RUN_ARM[i],
              lean=14, bob=RUN_BOB[i]) for i in range(8)]


def run_frames():
    return resample(run_keys(), RUN_FRAMES)


def dribble_frames():
    # one bounce per cycle: hand pushes down, ball hits the floor on frame 3
    arm = [(30, 70), (28, 45), (30, 40), (32, 50), (32, 60), (30, 70)]
    ball = [("near", 1.5, 4.5, 1), ("near", 1.5, 5.0, 1), ("hip", 12, 7, 1),
            ("ground", 11, 0, 1), ("hip", 12, 7, 1), ("near", 1.5, 4.8, 1)]
    bob = [0, 1, 1, 1, 0, 0]
    return [P((22, -14, 0), (-14, -34, 12), arm[i], (40, 90), lean=16, bob=bob[i], ball=ball[i])
            for i in range(6)]


def dribble_run_frames():
    # two bounces per stride; the near hand keeps dribbling out in front
    arm = [(32, 72), (30, 45), (30, 38), (32, 60)] * 2
    ball = [("near", 1.5, 4.5, 1), ("hip", 13, 8, 1), ("ground", 13, 0, 1), ("hip", 13, 8, 1)] * 2
    return resample([P(RUN_LEG[i], RUN_LEG[(i + 4) % 8], arm[i], RUN_ARM[i],
                       lean=16, bob=RUN_BOB[i], ball=ball[i]) for i in range(8)], RUN_FRAMES)


def dribble_far_frames():
    # the same dribble with the far hand (after a crossover up the screen)
    return [swap_sides(p) for p in dribble_frames()]


def dribble_run_far_frames():
    # the legs keep the same stride as dribble_run so the two can swap
    # mid-run; only the dribbling hand changes
    arm = [(32, 72), (30, 45), (30, 38), (32, 60)] * 2
    ball = [("far", 1.5, 4.5, -1), ("hip", 13, 8, -1), ("ground", 13, 0, -1), ("hip", 13, 8, -1)] * 2
    return resample([P(RUN_LEG[i], RUN_LEG[(i + 4) % 8], RUN_ARM[(i + 4) % 8], arm[i],
                       lean=16, bob=RUN_BOB[i], ball=ball[i]) for i in range(8)], RUN_FRAMES)


IDLE_POSE = P((8, -4, 0), (-6, -2, 0), (22, 50), (-14, 20), lean=4)
DRIBBLE_POSE = P((22, -14, 0), (-14, -34, 12), (30, 70), (40, 90), lean=16, ball=("near", 1.5, 4.5, 1))


def run_start_frames():
    # from standing into the first stride; ends one step before run frame 0
    return [
        P((10, -10, 0), (-10, -14, 10), (10, 60), (-10, 30), lean=8, bob=1),       # load
        P((26, -16, 0), (-16, -34, 20), (-12, 58), (18, 105), lean=13, bob=1),     # first push
        P((38, 4, -6), (-26, -56, 32), (-26, 52), (34, 125), lean=15),             # stride out
    ]


def run_stop_frames():
    # plant the lead foot, skid, settle into the idle stance
    return [
        P((44, 10, -10), (-20, -50, 30), (-10, 40), (20, 100), lean=4),
        P((46, 20, -12), (-8, -40, 20), (20, 60), (30, 80), lean=-8, bob=1),
        P((30, 2, 0), (-4, -20, 10), (24, 58), (-6, 36), lean=-2, bob=1),
        P((14, -6, 0), (-6, -4, 0), (22, 52), (-12, 22), lean=3),
        dict(IDLE_POSE),
    ]


# Turns flip facing at events.flipAt. The frames either side of the flip are
# square-on and mirror each other, so the switch doesn't read as a jump.
def turn_frames():
    square = dict(near_leg=(0, -2, 0), far_leg=(0, -2, 0), near_arm=(6, 32), far_arm=(-4, 26))
    return [
        dict(IDLE_POSE),
        P((4, -4, 0), (-2, -4, 0), (12, 42), (-8, 28), lean=2, bob=1),          # gather
        P(**square, lean=-1, bob=1, dx=-1),                                     # square up (old facing)
        P(**square, lean=1, bob=1, dx=1),                                       # square up (new facing)
        P((12, -6, 0), (-8, -6, 5), (18, 48), (-12, 24), lean=6),               # settle
        dict(IDLE_POSE),
    ]


def turn_run_frames():
    square = dict(near_leg=(20, -10, 0), far_leg=(10, -20, 0), near_arm=(20, 60), far_arm=(15, 55))
    return [
        P((44, 10, -10), (-20, -50, 30), (-10, 40), (20, 100), lean=2),          # plant
        P((50, 22, -14), (-4, -36, 20), (30, 70), (40, 90), lean=-10, bob=1),    # skid
        P(**square, lean=-3, bob=1, dx=-1),                                      # low and square (old facing)
        P(**square, lean=10, bob=1, dx=1),                                       # push off (new facing)
        P((30, -20, 0), (-24, -50, 30), (-20, 60), (25, 115), lean=16),          # first stride
        run_keys()[0],                                                           # = run frame 0
    ]


def turn_dribble_frames():
    # the ball bounces between the feet while the body squares up, so the
    # flip happens with the ball on the floor under the player
    square = dict(near_leg=(16, -10, 0), far_leg=(4, -18, 0), near_arm=(25, 40), far_arm=(30, 60))
    return [
        dict(DRIBBLE_POSE),
        P((30, -2, -6), (-10, -30, 15), (28, 45), (40, 80), lean=2, bob=1, ball=("hip", 8, 8, 0.6)),
        P(**square, lean=-2, bob=1, dx=-1, ball=("ground", 0, 0, 0.3)),
        P(**square, lean=4, bob=1, dx=1, ball=("ground", 0, 0, 0.3)),
        P((24, -12, 0), (-12, -30, 10), (28, 45), (40, 85), lean=12, ball=("hip", 10, 8, 1)),
        dict(DRIBBLE_POSE),
    ]


def crossover_up_frames():
    """Crossover from the near hand to the far hand. The near side faces the
    camera, so the player cuts up the screen (away from the camera). Facing
    right that is a cross to his left; flipped to face left it is still up."""
    return [
        # 0 dribbling with the near hand
        P((22, -14, 0), (-14, -34, 12), (30, 70), (40, 90), lean=16, ball=("near", 1.5, 4.5, 1)),
        # 1 sink low and push the ball down across the body
        P((30, -20, 0), (-22, -44, 15), (42, 40), (35, 75), lean=22, bob=1, ball=("hip", 11, 9, 0.5)),
        # 2 ball bounces in front, between the feet
        P((30, -20, 0), (-22, -44, 15), (22, 40), (38, 55), lean=24, bob=1, ball=("ground", 10, 0, 0)),
        # 3 far hand catches it; near foot plants and pushes off
        P((-5, -24, 18), (34, -4, -4), (0, 60), (35, 50), lean=22, bob=1, ball=("far", 1.5, 4.5, -0.6)),
        # 4 far hand dribbles it away, step through
        P((10, -30, 10), (30, -10, -4), (40, 90), (30, 55), lean=18, ball=("far", 1.5, 5.0, -1)),
        # 5 settled, dribbling with the far hand
        swap_sides(P((22, -14, 0), (-14, -34, 12), (30, 70), (40, 90), lean=16, ball=("near", 1.5, 4.5, 1))),
    ]


def crossover_down_frames():
    """Crossover from the far hand back to the near hand: the player cuts
    down the screen, toward the camera. The mirror image of crossover_up."""
    return [swap_sides(p) for p in crossover_up_frames()]


def shoot_frames():
    return [
        # 0 gather: ball at the chest, knees bent
        P((40, -12, 0), (30, -18, 0), (20, 140), (30, 120), lean=-12, ball=("near", 3.0, -1.5)),
        # 1 dip
        P((56, -18, 0), (48, -22, 0), (10, 130), (22, 115), lean=-18, ball=("near", 3.2, -1.5)),
        # 2 rise: legs extend, ball comes up in front of the face
        P((10, -4, 35), (0, -10, 40), (75, 165), (60, 150), lean=-4, head_dx=-2,
          ball=("near", 1.0, -4.5)),
        # 3 airborne, set point above the forehead
        P((20, -12, 25), (8, -20, 30), (88, 180), (80, 170), lean=2, lift=6, head_dx=-2,
          ball=("near", 0.5, -4.5)),
        # 4 release: arm extends up and out
        P((22, -14, 25), (10, -22, 30), (118, 148), (95, 150), lean=0, lift=8, head_dx=-1,
          ball=("near", 2.0, -4.0)),
        # 5 follow-through
        P((22, -14, 25), (10, -22, 30), (122, 140), (100, 130), lean=0, lift=8, head_dx=-2),
        # 6 hang / descend, wrist still flicked
        P((14, -8, 20), (4, -16, 25), (108, 112), (80, 100), lean=-2, lift=4, head_dx=-1),
        # 7 land
        P((48, -16, 0), (40, -22, 0), (60, 80), (30, 60), lean=-16),
    ]


def layup_frames():
    # one-handed layup, always with the near (camera-side) hand
    return [
        # 0 gather the ball at the hip mid-stride
        P((34, 12, -6), (-24, -48, 30), (20, 110), (25, 100), lean=16, ball=("near", 2.5, 0.0)),
        # 1 second step: far foot plants, ball to the chest
        P((-20, -60, 30), (36, 14, -6), (15, 140), (25, 125), lean=10, ball=("near", 3.0, -1.5)),
        # 2 take-off: near knee drives up, ball rising
        P((80, -5, 10), (-12, -18, 40), (95, 160), (80, 140), lean=4, ball=("near", 1.5, -4.0)),
        # 3 rising, ball hand extends toward the rim
        P((88, 5, 5), (-4, -24, 35), (122, 150), (70, 100), lean=0, lift=8, head_dx=-1,
          ball=("near", 1.5, -4.0)),
        # 4 release at the peak
        P((80, 0, 5), (0, -26, 30), (135, 150), (70, 100), lean=-2, lift=11, head_dx=-2,
          ball=("near", 2.0, -4.0)),
        # 5 follow-through
        P((50, -10, 10), (4, -24, 30), (138, 125), (60, 95), lean=0, lift=9, head_dx=-2),
        # 6 dropping
        P((20, -6, 15), (4, -14, 20), (100, 100), (50, 80), lean=2, lift=4),
        # 7 land
        P((48, -16, 0), (40, -22, 0), (50, 80), (30, 60), lean=16),
    ]


def pass_frames():
    # two-hand chest pass
    return [
        P((20, -5, 0), (-10, -22, 8), (15, 140), (25, 125), lean=10, ball=("near", 3.0, -1.5)),
        P((34, 8, -4), (-16, -36, 16), (5, 135), (15, 120), lean=14, ball=("near", 3.0, -1.5)),
        P((36, 10, -4), (-18, -40, 18), (60, 100), (55, 95), lean=18, ball=("near", 3.0, 0.0)),
        P((36, 10, -4), (-18, -40, 18), (85, 92), (80, 88), lean=20),
        P((34, 8, -4), (-16, -38, 16), (80, 70), (75, 65), lean=16),
        P((22, -4, 0), (-10, -24, 8), (30, 70), (20, 60), lean=10),
    ]


def steal_frames():
    windup = (228, 205)
    return [
        # 0 ready: low stance, hands out
        P((46, -8, 0), (-14, -40, 12), (45, 75), (35, 70), lean=26),
        # 1 wind-up: near hand cocked up behind the head
        P((50, -6, 0), (-18, -44, 14), windup, (20, 55), lean=22, arms_behind_head=True),
        # 2 lunge forward, swipe comes through at shoulder height
        P((60, 10, -4), (-30, -56, 22), (100, 96), (5, 40), lean=32, dx=2, smear=[windup, (150, 150)]),
        # 3 swipe through the ball, arm fully extended
        P((62, 14, -4), (-34, -60, 24), (62, 58), (-5, 30), lean=36, dx=3, smear=[(100, 96)]),
        # 4 follow-through low
        P((60, 12, -4), (-32, -58, 22), (28, 30), (0, 35), lean=34, dx=3, smear=[(62, 58)]),
        # 5 recover back to the stance
        P((48, -6, 0), (-18, -42, 12), (40, 70), (30, 65), lean=28, dx=1),
    ]


def block_frames():
    up = dict(arms_behind_head=True, reach=1.3, shrug=3)
    return [
        P((64, -18, 0), (58, -22, 0), (-30, 10), (-36, 6), lean=26),                      # load
        P((6, -2, 45), (-4, -8, 50), (95, 120), (88, 112), lean=6),                        # explode up
        P((14, -10, 35), (2, -18, 40), (158, 162), (196, 194), lean=2, lift=8, **up),      # rising
        P((22, -8, 30), (8, -16, 35), (160, 164), (198, 196), lean=0, lift=11, **up),      # peak
        P((16, -6, 20), (4, -14, 25), (155, 160), (194, 192), lean=2, lift=6, **up),       # coming down
        P((58, -18, 0), (50, -24, 0), (60, 90), (40, 70), lean=22),                        # land
    ]


def rebound_frames():
    up = dict(arms_behind_head=True, reach=1.2, shrug=2)
    return [
        P((62, -20, 0), (56, -24, 0), (-40, 10), (-46, 6), lean=26),                       # crouch
        P((6, -2, 45), (-4, -8, 50), (100, 125), (95, 120), lean=8),                       # take-off
        P((20, -20, 30), (8, -30, 35), (150, 160), (170, 175), lean=4, lift=7, **up),      # reaching
        P((50, -30, 20), (36, -40, 25), (155, 165), (165, 172), lean=2, lift=9,
          ball=("between", 0.0, -3.0), **up),                                              # catch
        P((30, -20, 15), (18, -26, 20), (60, 150), (50, 140), lean=6, lift=5,
          ball=("near", 3.0, -1.5)),                                                        # pull it down
        P((58, -18, 0), (50, -24, 0), (40, 140), (35, 130), lean=22, ball=("near", 3.0, -1.5)),  # land
    ]


def dunk_basic_frames():
    # one-hand dunk off a layup-style approach, near (camera-side) hand
    up = dict(arms_behind_head=True, reach=1.25, shrug=2)
    return [
        # 0 gather at the hip mid-stride
        P((34, 12, -6), (-24, -48, 30), (20, 110), (25, 100), lean=16, ball=("near", 2.5, 0.0)),
        # 1 plant, ball to the chest
        P((-20, -60, 30), (36, 14, -6), (15, 140), (25, 125), lean=10, ball=("near", 3.0, -1.5)),
        # 2 take-off, knee drive, ball coming up
        P((80, -5, 10), (-12, -18, 40), (95, 160), (80, 140), lean=4, ball=("near", 1.5, -4.0)),
        # 3 rising, ball cocked high over the head
        P((88, 5, 5), (-4, -24, 35), (172, 178), (70, 100), lean=0, lift=12,
          ball=("near", 0.5, -4.0), **up),
        # 4 slam: arm whips forward and down through the rim
        P((70, 0, 5), (0, -26, 30), (138, 118), (65, 95), lean=4, lift=14, head_dx=-1,
          ball=("near", 3.0, -1.0)),
        # 5 after the slam, arm follows through
        P((40, -8, 10), (4, -20, 25), (100, 70), (55, 85), lean=6, lift=10),
        # 6 dropping
        P((20, -6, 15), (4, -14, 20), (60, 60), (45, 70), lean=4, lift=4),
        # 7 land
        P((48, -16, 0), (40, -22, 0), (40, 70), (30, 60), lean=16),
    ]


def dunk_athletic_frames():
    # two-foot take-off, heels kicked up behind, both hands overhead
    up = dict(arms_behind_head=True, reach=1.3, shrug=3)
    return [
        # 0 last stride, ball in both hands
        P((34, 12, -6), (-24, -48, 30), (15, 140), (25, 125), lean=14, ball=("near", 3.0, -1.5)),
        # 1 two-foot load, ball low
        P((64, -18, 0), (58, -22, 0), (-10, 60), (-15, 55), lean=28, ball=("between", 1.5, 1.0)),
        # 2 explode, ball swinging up
        P((6, -2, 45), (-4, -8, 50), (120, 150), (115, 145), lean=6, ball=("between", 1.0, -3.0)),
        # 3 rising, ball overhead in both hands
        P((60, -40, 20), (48, -50, 25), (168, 176), (182, 182), lean=0, lift=13,
          ball=("between", 0.0, -3.5), **up),
        # 4 peak: feet kicked up behind, fully stretched
        P((40, -110, 30), (26, -118, 35), (170, 178), (188, 186), lean=-6, lift=17,
          ball=("between", 0.0, -3.5), **up),
        # 5 slam with both hands
        P((50, -70, 25), (38, -80, 30), (132, 115), (126, 110), lean=6, lift=15, head_dx=-1,
          ball=("between", 2.0, -1.0)),
        # 6 dropping, legs reach for the floor
        P((18, -6, 15), (4, -14, 20), (80, 70), (70, 60), lean=4, lift=6),
        # 7 land
        P((58, -18, 0), (50, -24, 0), (40, 70), (30, 60), lean=20),
    ]


def dunk_hang_frames():
    # big-man dunk: power it down, then hang on the rim (rim not drawn)
    up = dict(arms_behind_head=True, reach=1.3, shrug=3)
    return [
        # 0 gather with both hands
        P((30, 8, -4), (-18, -40, 20), (15, 140), (25, 125), lean=12, ball=("near", 3.0, -1.5)),
        # 1 two-foot power load
        P((60, -16, 0), (54, -20, 0), (10, 130), (20, 120), lean=22, ball=("near", 3.0, -1.5)),
        # 2 take-off, ball up
        P((8, -4, 40), (-2, -10, 45), (130, 160), (125, 155), lean=6, ball=("between", 1.0, -3.0)),
        # 3 rising, ball overhead
        P((24, -16, 25), (12, -24, 30), (164, 172), (180, 180), lean=2, lift=10,
          ball=("between", 0.0, -3.5), **up),
        # 4 slam: both hands over the rim
        P((20, -10, 20), (8, -18, 25), (150, 160), (160, 165), lean=4, lift=12,
          ball=("between", 1.5, -2.0), **up),
        # 5 hanging on the rim, legs swing forward
        P((26, 16, 10), (14, 8, 15), (172, 180), (186, 184), lean=-4, lift=12, **up),
        # 6 hanging, legs swing back
        P((-12, -22, 20), (-20, -30, 25), (172, 180), (186, 184), lean=6, lift=12, **up),
        # 7 let go and land
        P((58, -18, 0), (50, -24, 0), (60, 90), (40, 70), lean=22),
    ]


# Setting a screen (pick): wide base, knees bent, arms crossed over the chest
SCREEN_ARMS = dict(near_arm=(62, 262), far_arm=(72, 272))
SCREEN_LEGS = dict(near_leg=(34, 2, -4), far_leg=(-30, -14, 8))


def screen_set_frames():
    return [
        P((30, -10, 0), (-20, -44, 25), (-10, 60), (20, 100), lean=12),                 # last step in
        P((30, -8, 0), (-22, -24, 12), (10, 120), (20, 140), lean=10, bob=1),           # plant
        P(**SCREEN_LEGS, near_arm=(50, 200), far_arm=(58, 215), lean=7, bob=1),        # arms come in
        P(**SCREEN_LEGS, **SCREEN_ARMS, lean=5, bob=2),                                 # set
    ]


def screen_hold_frames():
    # braced and still; just a small breath so it doesn't look frozen
    return [P(**SCREEN_LEGS, **SCREEN_ARMS, lean=l, bob=b) for l, b in ((5, 2), (5, 2), (6, 3), (6, 3))]


def screen_contact_frames():
    # the defender runs into him: absorb it, then back to the set stance
    return [
        P(**SCREEN_LEGS, **SCREEN_ARMS, lean=5, bob=2),
        P((30, 0, -4), (-26, -12, 8), near_arm=(56, 256), far_arm=(66, 266), lean=-5, bob=3, dx=-1),  # hit
        P((32, 1, -4), (-28, -13, 8), near_arm=(59, 259), far_arm=(69, 269), lean=0, bob=3),
        P(**SCREEN_LEGS, **SCREEN_ARMS, lean=5, bob=2),
    ]


# ---------------------------------------------------------------- walking
WALK_LEG = [(24, 16, -8), (12, 6, 0), (0, -4, 4), (-12, -14, 10),
            (-20, -30, 20), (-6, -34, 18), (12, -18, 6), (24, 6, -6)]
WALK_ARM = [(-18, -6), (-10, 4), (0, 14), (10, 26), (18, 34), (10, 26), (0, 14), (-10, 4)]


def walk_keys(lean=6):
    return [P(WALK_LEG[i], WALK_LEG[(i + 4) % 8], WALK_ARM[(i + 4) % 8], WALK_ARM[i], lean=lean)
            for i in range(8)]


def walk_frames():
    return resample(walk_keys(), RUN_FRAMES)


def _walk_dribble(far):
    # 3 bounces per 12-frame walk cycle (one every 0.35 s at 11.43 fps)
    legs = resample(walk_keys(lean=12), RUN_FRAMES)
    arm = [(32, 72), (30, 45), (30, 38), (32, 60)] * 3
    ball = [("near", 1.5, 4.5, 1), ("hip", 12, 8, 1), ("ground", 12, 0, 1), ("hip", 12, 8, 1)] * 3
    out = []
    for i, p in enumerate(legs):
        p = dict(p)
        p["near_arm"] = arm[i]
        p["far_arm"] = (35, 80)
        p["ball"] = ball[i]
        out.append(swap_sides(p, legs=False) if far else p)
    return out


def walk_dribble_frames():
    return _walk_dribble(False)


def walk_dribble_far_frames():
    return _walk_dribble(True)


def backpedal_frames():
    # moving backward while still facing forward (defender giving ground)
    keys = [P(WALK_LEG[i], WALK_LEG[(i + 4) % 8], (40, 80), (30, 70), lean=10)
            for i in reversed(range(8))]
    return keys


# ---------------------------------------------------------------- idles
def idle_hips_frames():
    # hands on hips, waiting
    arms = dict(near_arm=(-35, 70), far_arm=(-30, 75))
    return [P((10, -4, 0), (-10, -4, 0), **arms, lean=l, bob=b) for l, b in ((2, 0), (2, 0), (3, 1), (3, 1))]


def idle_knees_frames():
    # bent over, hands on knees, catching his breath
    return [P((34, -6, 0), (22, -14, 0), (0, 10), (4, 12), lean=l, bob=b)
            for l, b in ((38, 1), (40, 2), (40, 2), (38, 1))]


# ---------------------------------------------------------------- defense
D_LEGS_WIDE = dict(near_leg=(32, -10, 0), far_leg=(-28, -30, 10))
D_ARMS = dict(near_arm=(50, 70), far_arm=(162, 176), reach=1.2)   # low hand at the ball, high hand up


def defense_stance_frames():
    return [P(**D_LEGS_WIDE, **D_ARMS, lean=18, bob=b) for b in (2, 2, 3, 3)]


def defense_slide_frames():
    # shuffle: feet together, then wide again (two shuffles per loop)
    legs = [((32, -10, 0), (-28, -30, 10)), ((22, -12, 0), (-18, -26, 8)), ((10, -10, 0), (-6, -18, 4)),
            ((22, -12, 0), (-18, -26, 8))] * 2
    return [P(n, f, **D_ARMS, lean=18, bob=(2 if i % 2 == 0 else 3)) for i, (n, f) in enumerate(legs)]


def defense_hands_up_frames():
    up = dict(arms_behind_head=True, reach=1.2, shrug=2)
    return [P(**D_LEGS_WIDE, near_arm=(165, 172), far_arm=(190, 186), lean=6, bob=b, **up) for b in (1, 1, 2, 2)]


# ---------------------------------------------------------------- more finishes
def layup_finger_roll_frames():
    frames = layup_frames()
    frames[3] = P((88, 5, 5), (-4, -24, 35), (100, 120), (70, 100), lean=0, lift=8, ball=("near", 2.0, -2.5))
    frames[4] = P((80, 0, 5), (0, -26, 30), (118, 125), (70, 100), lean=-2, lift=11, head_dx=-1,
                  ball=("near", 2.5, -3.0))                                 # palm up, rolls it off
    frames[5] = P((50, -10, 10), (4, -24, 30), (125, 150), (60, 95), lean=0, lift=9, head_dx=-1)
    return frames


def layup_euro_frames():
    return [
        P((34, 12, -6), (-24, -48, 30), (20, 110), (25, 100), lean=16, ball=("near", 2.5, 0.0, 1)),     # gather
        P((44, 20, -8), (-30, -56, 34), (15, 140), (25, 125), lean=14, ball=("near", 3.0, -1.5, 0.6)),  # step one way
        P((-26, -50, 30), (52, 24, -10), (40, 120), (10, 130), lean=22, bob=1,
          ball=("far", 3.0, -1.0, -0.6)),                                                          # long step back across
        P((80, -5, 10), (-12, -18, 40), (95, 160), (80, 140), lean=4, ball=("near", 1.5, -4.0, 0.3)),  # take-off
        P((88, 5, 5), (-4, -24, 35), (122, 150), (70, 100), lean=0, lift=8, head_dx=-1,
          ball=("near", 1.5, -4.0, 0.5)),
        P((80, 0, 5), (0, -26, 30), (135, 150), (70, 100), lean=-2, lift=11, head_dx=-2,
          ball=("near", 2.0, -4.0, 0.5)),                                                          # release
        P((20, -6, 15), (4, -14, 20), (100, 100), (50, 80), lean=2, lift=4),
        P((48, -16, 0), (40, -22, 0), (50, 80), (30, 60), lean=16),
    ]


def dunk_windmill_frames():
    up = dict(arms_behind_head=True, reach=1.3, shrug=3)
    return [
        P((34, 12, -6), (-24, -48, 30), (15, 140), (25, 125), lean=14, ball=("near", 3.0, -1.5)),       # gather
        P((64, -18, 0), (58, -22, 0), (10, 60), (-15, 55), lean=26, ball=("near", 2.0, 2.0)),         # load
        P((6, -2, 45), (-4, -8, 50), (-20, 0), (100, 130), lean=6, ball=("near", 1.0, 3.0)),          # jump, ball low
        P((50, -30, 20), (36, -40, 25), (-60, -40), (130, 150), lean=2, lift=10,
          ball=("near", -1.0, 2.0)),                                                              # swing back
        P((50, -30, 20), (36, -40, 25), (235, 225), (150, 160), lean=0, lift=14,
          ball=("near", -1.5, -2.0, 0.2), **up),                                                  # over the top
        P((40, -20, 20), (26, -30, 25), (175, 178), (150, 160), lean=0, lift=17,
          ball=("near", 1.0, -4.0), **up),                                                        # peak
        P((50, -40, 25), (38, -50, 30), (130, 110), (100, 110), lean=6, lift=15, head_dx=-1,
          ball=("near", 3.0, -1.0)),                                                              # slam
        P((58, -18, 0), (50, -24, 0), (40, 70), (30, 60), lean=20),                               # land
    ]


def dunk_tomahawk_frames():
    up = dict(arms_behind_head=True, reach=1.3, shrug=3)
    return [
        P((34, 12, -6), (-24, -48, 30), (15, 140), (25, 125), lean=14, ball=("near", 3.0, -1.5)),
        P((64, -18, 0), (58, -22, 0), (10, 130), (20, 120), lean=26, ball=("near", 3.0, -1.5)),
        P((6, -2, 45), (-4, -8, 50), (150, 170), (145, 165), lean=6, ball=("between", 0.0, -3.0), **up),
        P((60, -40, 20), (48, -50, 25), (215, 200), (222, 205), lean=-8, lift=13,
          ball=("between", -2.0, -2.0, 0), **up),                                                 # cocked behind the head
        P((60, -60, 20), (48, -70, 25), (205, 190), (212, 195), lean=-10, lift=17,
          ball=("between", -2.0, -2.5, 0), **up),                                                 # peak, arched back
        P((50, -40, 25), (38, -50, 30), (132, 112), (126, 106), lean=8, lift=15, head_dx=-1,
          ball=("between", 2.0, -1.0)),                                                           # slam
        P((58, -18, 0), (50, -24, 0), (40, 70), (30, 60), lean=20),
    ]


# ---------------------------------------------------------------- more dribble moves
def behind_back_up_frames():
    """Near hand to far hand around the back: cuts up the screen, like crossover_up."""
    return [
        dict(DRIBBLE_POSE),
        P((26, -12, 0), (-18, -38, 14), (-30, 20), (40, 90), lean=16, bob=1, ball=("hip", -7, 5, 0.3)),   # swing it back
        P((28, -12, 0), (-20, -40, 15), (-40, 0), (20, 60), lean=18, bob=1, ball=("hip", -5, 10, -0.4)),  # behind the back
        P((28, -12, 0), (-20, -40, 15), (-10, 40), (30, 45), lean=18, bob=1, ball=("ground", 5, 0, -0.7)),
        P((24, -14, 0), (-16, -36, 12), (35, 80), (30, 55), lean=16, ball=("far", 1.5, 5.0, -1)),        # far hand has it
        swap_sides(dict(DRIBBLE_POSE)),
    ]


def behind_back_down_frames():
    return [swap_sides(p) for p in behind_back_up_frames()]


def between_legs_up_frames():
    """Near hand to far hand through the legs (wide stance)."""
    wide = dict(near_leg=(32, -6, 0), far_leg=(-26, -28, 10))
    return [
        dict(DRIBBLE_POSE),
        P(**wide, near_arm=(30, 40), far_arm=(40, 85), lean=20, bob=2, ball=("hip", 5, 10, 0.5)),       # push down
        P(**wide, near_arm=(20, 30), far_arm=(25, 50), lean=22, bob=2, ball=("ground", 1, 0, 0)),       # between the feet
        P(**wide, near_arm=(35, 75), far_arm=(15, 40), lean=20, bob=2, ball=("far", 1.0, 4.5, -0.7)),   # far hand catches
        P((24, -14, 0), (-16, -36, 12), (40, 90), (30, 55), lean=16, ball=("far", 1.5, 5.0, -1)),
        swap_sides(dict(DRIBBLE_POSE)),
    ]


def between_legs_down_frames():
    return [swap_sides(p) for p in between_legs_up_frames()]


def hesitation_frames():
    """Hesi: rise up tall to sell the stop, then burst forward (same hand)."""
    return [
        dict(DRIBBLE_POSE),
        P((10, -4, 0), (-8, -12, 6), (30, 60), (35, 70), lean=4, ball=("near", 1.5, 3.5, 1)),            # rise up
        P((8, -4, 0), (-8, -10, 6), (32, 55), (35, 70), lean=2, head_dy=-1, ball=("hip", 12, 7, 1)),     # sell it
        P((34, -10, 0), (-26, -52, 30), (30, 40), (-20, 60), lean=26, bob=1, ball=("ground", 13, 0, 1)),  # burst
        P((40, 4, -6), (-30, -60, 34), (32, 60), (-26, 52), lean=22, ball=("hip", 13, 8, 1)),
        P(RUN_LEG[0], RUN_LEG[4], (32, 72), RUN_ARM[0], lean=16, ball=("near", 1.5, 4.5, 1)),         # into dribble_run
    ]


def hesitation_far_frames():
    return [swap_sides(p, legs=False) for p in hesitation_frames()]


def shoot_pullup_frames(base=None):
    """Jumper off the move toward the basket: brake from a run, rise, drift forward."""
    base = base or shoot_frames()
    frames = [
        P(RUN_LEG[7], RUN_LEG[3], (20, 140), (30, 120), lean=14, ball=("near", 3.0, -1.5)),   # gather on the run
        P((50, -16, 0), (40, -22, 0), (10, 130), (22, 115), lean=2, bob=1, dx=1,
          ball=("near", 3.2, -1.5)),                                                        # hop-stop, braking
    ]
    frames[0]["near_arm"], frames[0]["far_arm"] = base[0]["near_arm"], base[0]["far_arm"]
    frames[0]["ball"] = base[0].get("ball")
    frames[1]["near_arm"], frames[1]["far_arm"] = base[1]["near_arm"], base[1]["far_arm"]
    frames[1]["ball"] = base[1].get("ball")
    for i, p in enumerate(base[2:]):
        p = dict(p)
        p["dx"] = 2 + min(i, 3)                                                              # momentum carries forward
        p["lean"] = p.get("lean", 8) + 3
        frames.append(p)
    return frames


def shoot_fade_frames(base=None):
    """Fadeaway: rise leaning back, drifting away from the basket."""
    base = base or shoot_frames()
    frames = [dict(base[0]), dict(base[1])]
    for i, (p, lean, dx) in enumerate(zip(base[2:], (-6, -12, -16, -14, -8, -2), (-1, -2, -3, -4, -5, -5))):
        p = dict(p)
        p["lean"] = lean
        p["dx"] = dx
        if i == 4:                                   # legs reach forward to land going backward
            p["near_leg"], p["far_leg"] = (24, 10, 10), (14, 2, 15)
        frames.append(p)
    return frames


# ---------------------------------------------------------------- run styles
def _run_style(lean, stride, shin_bias, knee_drive, arm_swing, arm_bend, bob):
    """A run cycle in the same 12-frame rhythm as `run`, so styles can swap
    without breaking the stride."""
    keys = []
    for i in range(8):
        def leg(k):
            th, sh, fr = RUN_LEG[k]
            th = th * stride + (knee_drive if k in (6, 7) else 0)
            return (th, sh * stride + shin_bias, fr)

        def arm(k):
            up, fo = RUN_ARM[k]
            return (up * arm_swing, up * arm_swing + arm_bend)
        keys.append(P(leg(i), leg((i + 4) % 8), arm((i + 4) % 8), arm(i), lean=lean, bob=bob[i]))
    return resample(keys, RUN_FRAMES)


def run_upright_frames():
    # tall, smooth, long strides
    return _run_style(lean=4, stride=1.2, shin_bias=6, knee_drive=0, arm_swing=1.35, arm_bend=60,
                      bob=[0, 0, 0, -1, -1, 0, 0, -1])


def run_power_frames():
    # heavy, forward-leaning, short choppy strides (big men)
    return _run_style(lean=23, stride=0.75, shin_bias=-14, knee_drive=0, arm_swing=0.8, arm_bend=100,
                      bob=[0, 2, 1, 0, 0, 2, 1, 0])


def run_bounce_frames():
    # springy guard run with a high knee drive
    return _run_style(lean=10, stride=1.0, shin_bias=-6, knee_drive=26, arm_swing=1.2, arm_bend=85,
                      bob=[0, 1, -1, -2, -1, 1, -1, -3])


# ---------------------------------------------------------------- guarding
def guard_on_ball_frames():
    """Pressure defense on the ball handler: low, active hands, chopping feet."""
    near = [(50, 70), (62, 84), (44, 58), (60, 80), (48, 66), (58, 78)]
    far = [(162, 176), (156, 170), (164, 178), (158, 172), (162, 176), (156, 170)]
    legs = [((32, -10, 0), (-28, -30, 10)), ((32, -10, 6), (-28, -30, 10)), ((32, -10, 0), (-28, -30, 16))] * 2
    return [P(legs[i][0], legs[i][1], near[i], far[i], lean=20, reach=1.2, bob=(2 if i % 2 else 3))
            for i in range(6)]


# ---------------------------------------------------------------- extras
def celebrate_frames():
    # fist pumps after a big play
    return [
        dict(IDLE_POSE),
        P((20, -8, 0), (-10, -16, 5), (30, 60), (10, 40), lean=10, bob=1),
        P((6, -2, 20), (-4, -6, 25), (120, 165), (20, 50), lean=0, lift=3),        # pump up
        P((20, -8, 0), (-10, -16, 5), (40, 100), (20, 45), lean=8, bob=1),         # pull down
        P((6, -2, 20), (-4, -6, 25), (122, 168), (25, 55), lean=-2, lift=3),
        P((20, -8, 0), (-10, -16, 5), (40, 100), (20, 45), lean=8, bob=1),
        P((10, -4, 0), (-6, -4, 0), (30, 70), (-10, 25), lean=4),
        dict(IDLE_POSE),
    ]


def point_up_frames():
    # points up and out toward the crowd / sky, arm in front of the face
    return [
        dict(IDLE_POSE),
        P((8, -4, 0), (-6, -2, 0), (100, 140), (-10, 20), lean=0),
        P((8, -4, 0), (-6, -2, 0), (148, 162), (-12, 18), lean=-4, head_dy=-1),
        P((8, -4, 0), (-6, -2, 0), (150, 164), (-12, 18), lean=-5, head_dy=-1),
        P((8, -4, 0), (-6, -2, 0), (100, 140), (-10, 20), lean=-1),
        dict(IDLE_POSE),
    ]


def frustrated_frames():
    # hands on top of the head
    return [
        dict(IDLE_POSE),
        P((8, -4, 0), (-6, -2, 0), (140, 225), (150, 230), lean=-2),
        P((8, -4, 0), (-6, -2, 0), (145, 238), (155, 242), lean=-4, head_dx=-1),
        P((8, -4, 0), (-6, -2, 0), (145, 238), (155, 242), lean=-4),
        P((8, -4, 0), (-6, -2, 0), (140, 225), (150, 230), lean=-2),
        dict(IDLE_POSE),
    ]



# ---------------------------------------------------------------- post moves
# Post-ups are drawn with the player's back to the basket: the art faces
# right and the basket is behind him (to the left). Play them facing away
# from the basket. Moves with events.flipAt turn him around to face it.
POST_LEGS = dict(near_leg=(30, -8, 0), far_leg=(-24, -34, 12))
POST_BAR = (-58, -40)             # far arm: arm bar back into the defender
CHIN = dict(near_arm=(38, 150), far_arm=(48, 140))   # ball chinned at the chest


def post_up_frames():
    """Backing down: low and wide, pounding a low dribble on the near side,
    arm bar back, and a bump step into the defender every other bounce."""
    arm = [(22, 40), (18, 22), (20, 20), (22, 34), (22, 40), (18, 22), (20, 20), (22, 34)]
    ball = [("near", 1.0, 4.5, 1), ("hip", 9, 9, 1), ("ground", 8, 0, 1), ("hip", 9, 9, 1)] * 2
    legs = [((30, -8, 0), (-24, -34, 12)), ((30, -8, 0), (-30, -44, 18)),     # far foot slides back
            ((26, -10, 0), (-32, -40, 14)), ((26, -10, 0), (-28, -36, 12)),   # bump
            ((30, -8, 0), (-24, -34, 12)), ((18, -26, 8), (-24, -34, 12)),    # near foot gathers
            ((22, -14, 0), (-24, -34, 12)), ((28, -8, 0), (-24, -34, 12))]
    bar = [POST_BAR, POST_BAR, (-66, -50), (-62, -46)] * 2
    dx = [0, 0, -1, -1, 0, 0, 0, 0]
    bob = [2, 2, 3, 3, 2, 2, 2, 2]
    return [P(legs[i][0], legs[i][1], arm[i], bar[i], lean=14 + (2 if dx[i] else 0), bob=bob[i], dx=dx[i],
              ball=ball[i]) for i in range(8)]


def post_hook_frames():
    """Hook shot over the shoulder: step back toward the basket with the far
    foot, drive the near knee, sweep the near arm up and over the head."""
    return [
        P(**POST_LEGS, **CHIN, lean=14, bob=2, ball=("near", 2.5, -1.5)),                        # 0 gather
        P((34, -4, 0), (-36, -40, 10), (40, 130), (-20, 20), lean=2, bob=1, dx=-2,
          ball=("near", 2.5, -2.0)),                                                             # 1 step back
        P((70, -10, 10), (-12, -22, 35), (120, 170), (-50, -30), lean=-6, dx=-3, lift=3,
          ball=("near", 1.0, -4.0)),                                                             # 2 take-off
        P((84, 0, 10), (-6, -24, 35), (172, 190), (-70, -50), lean=-12, dx=-4, lift=8,
          ball=("near", 0.0, -4.5), arms_behind_head=True),                                                             # 3 rising, arm up
        P((80, -4, 10), (-4, -24, 35), (204, 214), (-72, -52), lean=-16, dx=-4, lift=10,
          ball=("near", -2.0, -4.0)),                                                            # 4 release over the head
        P((60, -12, 10), (-4, -20, 30), (214, 236), (-60, -40), lean=-14, dx=-4, lift=9),       # 5 wrist flick
        P((30, -10, 15), (0, -14, 20), (176, 200), (-30, -10), lean=-6, dx=-4, lift=4,
          arms_behind_head=True),         # 6 dropping
        P((34, -10, 0), (-20, -26, 8), (40, 80), (10, 40), lean=8, dx=-4),                       # 7 land
    ]


def post_fadeaway_frames():
    """Turnaround fadeaway ("the fader"): chin the ball, pivot to face the
    basket (flipAt), then rise leaning well back and drifting away."""
    square = dict(near_leg=(6, -6, 0), far_leg=(2, -8, 0), near_arm=(44, 132), far_arm=(40, 128))
    base = shoot_frames()
    frames = [
        P(**POST_LEGS, **CHIN, lean=14, bob=2, ball=("near", 2.5, -1.5)),                        # 0 chin it
        P((24, -10, 0), (-14, -28, 10), (40, 145), (46, 136), lean=8, bob=2, dx=-1,
          ball=("near", 2.5, -1.5)),                                                             # 1 start the pivot
        P(**square, lean=-1, bob=2, dx=-1, ball=("between", 0.0, -1.5, 0)),                     # 2 square (back to basket)
        P(**square, lean=1, bob=2, dx=1, ball=("between", 0.0, -1.5, 0)),                       # 3 square (facing it)
        dict(base[1], dx=0),                                                                     # 4 dip
    ]
    for i, (lean, dx) in enumerate(zip((-10, -18, -24, -20, -10, -2), (-1, -2, -3, -4, -5, -5))):
        p = dict(base[2 + i], lean=lean, dx=dx)
        if i in (2, 3):                              # near leg kicks out for balance
            p["near_leg"] = (46, 26, 0)
        if i == 4:
            p["near_leg"], p["far_leg"] = (26, 10, 10), (14, 2, 15)
        frames.append(p)
    return frames                                    # rise 5, release 7


def post_fade_one_leg_frames():
    """One-legged fadeaway: face up, hop onto the far foot, near knee up
    toward the defender, rise and fall back on the one leg."""
    return [
        P((24, -10, 0), (-14, -26, 10), (20, 140), (30, 120), lean=6, bob=2,
          ball=("near", 3.0, -1.5)),                                                             # 0 gather
        P((52, 10, 0), (-6, -20, 10), (14, 132), (24, 116), lean=-6, bob=2,
          ball=("near", 3.2, -1.5)),                                                             # 1 near knee lifts
        P((82, 10, 10), (-2, -6, 38), (75, 165), (60, 150), lean=-12, head_dx=-2, dx=-1,
          ball=("near", 1.0, -4.5)),                                                             # 2 rise off the far foot
        P((88, 20, 10), (0, -6, 35), (90, 180), (80, 170), lean=-18, lift=6, head_dx=-2, dx=-2,
          ball=("near", 0.5, -4.5)),                                                             # 3 set point
        P((80, 34, 10), (2, -8, 35), (118, 148), (95, 150), lean=-22, lift=8, head_dx=-1, dx=-3,
          ball=("near", 2.0, -4.0)),                                                             # 4 release
        P((74, 30, 10), (2, -8, 35), (122, 140), (100, 130), lean=-20, lift=7, head_dx=-2, dx=-4),  # 5 follow-through
        P((66, 20, 10), (4, -6, 25), (108, 112), (80, 100), lean=-14, lift=3, dx=-5),           # 6 falling back
        P((50, 6, 10), (6, -14, 5), (60, 80), (30, 60), lean=-6, bob=1, dx=-5),                 # 7 land on the far foot
        P((30, -12, 0), (8, -18, 5), (40, 70), (20, 50), lean=2, dx=-5),                        # 8 settle
    ]


def spin_move_frames():
    """Spin out of the post: plant, spin toward the basket (flipAt) and
    come out of it on a dribble going to the rim, ending on dribble_run."""
    square = dict(near_leg=(12, -12, 0), far_leg=(0, -18, 0))
    return [
        post_up_frames()[0],                                                                     # 0 backing down
        P((34, -6, 0), (-20, -36, 12), (26, 40), (-30, 10), lean=20, bob=2, dx=-1,
          ball=("hip", 8, 6, 1)),                                                                # 1 plant, drop the shoulder
        P((18, -22, 6), (-30, -44, 16), (40, 90), (70, 110), lean=10, bob=2, dx=-3,
          ball=("near", 1.5, 3.0, 0.6), smear=[(26, 40)]),                                       # 2 spinning
        P(**square, near_arm=(40, 100), far_arm=(60, 120), lean=2, bob=1, dx=-4,
          ball=("hip", 9, 4, 0.2), smear=[(40, 90)]),                                            # 3 square (back to basket)
        P(**square, near_arm=(40, 100), far_arm=(60, 120), lean=6, bob=1, dx=4,
          ball=("hip", 9, 4, 0.2), smear=[(60, 120)]),                                           # 4 square (facing it)
        P((44, 10, -8), (-30, -60, 30), (30, 40), (-20, 60), lean=22, bob=1, dx=5,
          ball=("ground", 13, 0, 1)),                                                            # 5 long step through, bounce
        P((30, -2, -4), (-26, -70, 34), (30, 50), (-24, 56), lean=20, dx=5,
          ball=("hip", 13, 8, 1)),                                                               # 6
        P(RUN_LEG[0], RUN_LEG[4], (32, 72), RUN_ARM[0], lean=16, dx=5,
          ball=("near", 1.5, 4.5, 1)),                                                           # 7 = dribble_run
    ]


# ---------------------------------------------------------------- signature styles
# Selectable per player (see animStyles.ts). Every style keeps the frame
# count and event frames of its classic version, so the game logic is the
# same whichever style a player picks.

def run_glide_frames():
    # long, low, gliding strides
    return _run_style(lean=18, stride=1.3, shin_bias=0, knee_drive=6, arm_swing=1.0, arm_bend=70,
                      bob=[1, 2, 1, 0, 1, 2, 1, 0])


def run_loose_frames():
    # relaxed lope, arms hanging low
    return _run_style(lean=8, stride=1.0, shin_bias=4, knee_drive=-6, arm_swing=0.5, arm_bend=20,
                      bob=[0, 0, -1, -1, 0, 0, -1, -1])


# Standing dribble styles: (legs per frame or one pair, lean, near arm per
# frame, far arm, ball per frame, bob per frame). The bounce is on frame 3.
def _stand_dribble(legs, lean, arm, far, ball, bob):
    if not isinstance(legs[0][0], tuple):
        legs = [legs] * 6
    return [P(legs[i][0], legs[i][1], arm[i], far if isinstance(far[0], (int, float)) else far[i],
              lean=lean, bob=bob[i], ball=ball[i]) for i in range(6)]


def _bounce_at(hx, hy, gx, top=(1.5, 4.5)):
    return [("near", top[0], top[1], 1), ("near", top[0], top[1] + 0.5, 1), ("hip", hx, hy, 1),
            ("ground", gx, 0, 1), ("hip", hx, hy, 1), ("near", top[0], top[1] + 0.3, 1)]


def dribble_low_frames():
    # crouched, quick hard pounds below the knee, off arm out in front
    return _stand_dribble(((34, -20, 0), (-26, -46, 14)), 24,
                          [(20, 40), (18, 26), (18, 20), (20, 24), (20, 34), (20, 40)], (60, 100),
                          _bounce_at(9, 11, 9, (1.0, 4.5)), [2, 3, 3, 3, 2, 2])


def dribble_high_frames():
    # tall and casual, a high, lazy dribble out to the side
    return _stand_dribble(((12, -6, 0), (-8, -16, 8)), 6,
                          [(40, 90), (34, 62), (34, 56), (36, 64), (38, 80), (40, 90)], (-10, 16),
                          _bounce_at(14, 4, 14), [0, 0, 0, 0, 0, 0])


def dribble_rhythm_frames():
    # bouncy, rocking with the dribble, feet never still
    legs = [((22, -14, 0), (-14, -34, 12)), ((26, -10, 0), (-10, -30, 14)), ((18, -20, 4), (-16, -38, 10)),
            ((22, -14, 0), (-20, -40, 14)), ((28, -6, 0), (-12, -32, 10)), ((22, -14, 0), (-14, -34, 12))]
    far = [(30, 70), (36, 78), (40, 84), (36, 78), (30, 70), (26, 64)]
    return _stand_dribble(legs, 14, [(30, 72), (28, 46), (30, 40), (32, 50), (32, 62), (30, 72)], far,
                          _bounce_at(12, 7, 11), [0, 1, 2, 1, 0, -1])


def dribble_protect_frames():
    # wide stance, ball kept back on the hip, off arm up as a shield
    return _stand_dribble(((36, -10, 0), (-30, -40, 14)), 20,
                          [(14, 40), (10, 22), (12, 18), (12, 26), (14, 34), (14, 40)], (82, 116),
                          _bounce_at(6, 10, 6, (1.0, 4.5)), [2, 2, 3, 3, 2, 2])


def _run_dribble(lean, stride, knee_drive, arm, ball, far, bob, far_hand=False):
    """12-frame dribble_run variant (bounces on frames 3 and 9, same leg
    phase as `run`, so the stride clock carries over)."""
    def leg(k):
        th, sh, fr = RUN_LEG[k]
        return (th * stride + (knee_drive if k in (6, 7) else 0), sh * stride, fr)
    keys = []
    for i in range(8):
        f = RUN_ARM[i] if far is None else far
        keys.append(P(leg(i), leg((i + 4) % 8), arm[i % 4], f, lean=lean, bob=bob[i], ball=ball[i % 4]))
    if far_hand:
        keys = [swap_sides(k, legs=False) for k in keys]
    return resample(keys, RUN_FRAMES)


def _run_ball(hx, hy, gx):
    return [("near", 1.5, 4.5, 1), ("hip", hx, hy, 1), ("ground", gx, 0, 1), ("hip", hx, hy, 1)]


RUN_DRIBBLES = {
    # style: kwargs for _run_dribble
    "low": dict(lean=22, stride=0.85, knee_drive=0, arm=[(24, 40), (22, 26), (22, 22), (24, 34)],
                ball=_run_ball(11, 10, 11), far=(50, 90), bob=[1, 2, 1, 0, 1, 2, 1, 0]),
    "high": dict(lean=12, stride=1.15, knee_drive=0, arm=[(50, 82), (48, 62), (46, 58), (50, 70)],
                 ball=_run_ball(17, 6, 18), far=None, bob=RUN_BOB),
    "rhythm": dict(lean=16, stride=1.0, knee_drive=20, arm=[(32, 72), (30, 45), (30, 38), (32, 60)],
                   ball=_run_ball(13, 8, 13), far=None, bob=[0, 1, -1, -2, -1, 1, -1, -2]),
    "protect": dict(lean=18, stride=0.95, knee_drive=0, arm=[(18, 44), (14, 26), (14, 22), (16, 34)],
                    ball=_run_ball(9, 9, 9), far=(80, 114), bob=RUN_BOB),
}


# Jump-shot styles: 8 frames each, gather 0 / rise 2 / release 4 like `shoot`.
def shoot_quick_frames():
    # one-motion, low set point, barely leaves the floor
    return [
        P((40, -12, 0), (30, -18, 0), (20, 140), (30, 120), lean=-12, ball=("near", 3.0, -1.5)),
        P((48, -14, 0), (40, -18, 0), (30, 150), (34, 128), lean=-14, ball=("near", 2.6, -2.5)),
        P((14, -6, 30), (4, -12, 35), (96, 162), (70, 150), lean=-4, head_dx=-1, ball=("near", 1.5, -4.2)),
        P((18, -10, 25), (6, -16, 30), (110, 156), (84, 150), lean=0, lift=3, head_dx=-1,
          ball=("near", 1.8, -4.2)),
        P((18, -10, 25), (6, -16, 30), (122, 146), (92, 146), lean=0, lift=4, ball=("near", 2.2, -4.0)),
        P((18, -10, 25), (6, -16, 30), (126, 138), (96, 128), lean=0, lift=4),
        P((12, -6, 20), (4, -12, 25), (110, 112), (80, 100), lean=-2, lift=2),
        P((40, -14, 0), (32, -20, 0), (60, 80), (30, 60), lean=-12),
    ]


def shoot_high_frames():
    # high release: ball set well above the forehead, big straight-up jump, high arc
    return [
        P((40, -12, 0), (30, -18, 0), (20, 140), (30, 120), lean=-12, ball=("near", 3.0, -1.5)),
        P((60, -20, 0), (52, -24, 0), (10, 130), (22, 115), lean=-20, ball=("near", 3.2, -1.5)),
        P((6, -2, 40), (-4, -8, 45), (120, 176), (104, 166), lean=-2, head_dx=-2, ball=("near", 1.0, -4.5)),
        P((16, -10, 30), (4, -18, 35), (140, 182), (124, 176), lean=2, lift=10, head_dx=-2,
          ball=("near", 0.5, -4.5)),
        P((18, -12, 30), (6, -20, 35), (148, 166), (130, 168), lean=0, lift=12, head_dx=-1,
          ball=("near", 1.5, -4.5)),
        P((18, -12, 30), (6, -20, 35), (148, 150), (128, 150), lean=0, lift=11, head_dx=-1),
        P((12, -6, 20), (4, -14, 25), (116, 116), (90, 100), lean=-2, lift=5),
        P((50, -16, 0), (42, -22, 0), (60, 80), (30, 60), lean=-16),
    ]


def shoot_kick_frames():
    # legs kick out forward on the release
    base = shoot_frames()
    base[4] = dict(base[4], near_leg=(64, 44, 0), far_leg=(-6, -30, 30), lean=-4)
    base[5] = dict(base[5], near_leg=(70, 50, 0), far_leg=(-10, -36, 30), lean=-6)
    base[6] = dict(base[6], near_leg=(44, 20, 5), far_leg=(0, -20, 25), lean=-4)
    return base


def shoot_push_frames():
    # old-school push: ball at the chin in both hands, pushed out on a low arc
    return [
        P((40, -12, 0), (30, -18, 0), (30, 140), (38, 132), lean=-10, ball=("between", 1.0, -2.0, 0.3)),
        P((52, -18, 0), (44, -22, 0), (36, 150), (42, 142), lean=-16, ball=("between", 1.0, -2.5, 0.3)),
        P((14, -6, 30), (4, -12, 35), (58, 158), (62, 152), lean=-6, head_dx=-1,
          ball=("between", 1.5, -3.0, 0.3)),
        P((18, -10, 25), (6, -16, 30), (80, 150), (82, 146), lean=-2, lift=4,
          ball=("between", 2.0, -3.0, 0.3)),
        P((18, -10, 25), (6, -16, 30), (104, 124), (100, 122), lean=0, lift=5,
          ball=("between", 2.5, -2.0, 0.3)),
        P((18, -10, 25), (6, -16, 30), (112, 112), (108, 110), lean=0, lift=5),
        P((12, -6, 20), (4, -12, 25), (96, 100), (84, 90), lean=-2, lift=2),
        P((44, -14, 0), (36, -20, 0), (50, 80), (30, 60), lean=-12),
    ]


# Layups: 8 frames, gather 0 / take-off 2 / release as noted.
def layup_reverse_frames():
    # carries under the rim and flips it back over the head (release 4)
    up = dict(arms_behind_head=True)
    base = layup_frames()
    return base[:3] + [
        P((88, 5, 5), (-4, -24, 35), (160, 196), (70, 100), lean=2, lift=9, dx=1, head_dx=-1,
          ball=("near", 0.0, -4.5), **up),
        P((70, 0, 5), (0, -26, 30), (196, 222), (60, 90), lean=-4, lift=11, dx=2, head_dx=-2,
          ball=("near", -2.0, -3.5), **up),
        P((50, -10, 10), (4, -24, 30), (206, 236), (60, 90), lean=-4, lift=9, dx=3, **up),
        P((20, -6, 15), (4, -14, 20), (100, 100), (50, 80), lean=2, lift=4, dx=3),
        P((48, -16, 0), (40, -22, 0), (50, 80), (30, 60), lean=12, dx=3),
    ]


def layup_scoop_frames():
    # underhand scoop from down low, palm up (release 4)
    base = layup_frames()
    return base[:2] + [
        P((80, -5, 10), (-12, -18, 40), (20, 60), (60, 110), lean=10, ball=("near", 2.0, 0.5)),
        P((88, 5, 5), (-4, -24, 35), (60, 80), (70, 110), lean=4, lift=8, ball=("near", 2.5, -1.0)),
        P((80, 0, 5), (0, -26, 30), (104, 120), (70, 100), lean=0, lift=11, head_dx=-1,
          ball=("near", 2.5, -3.0)),
        P((50, -10, 10), (4, -24, 30), (130, 150), (60, 95), lean=0, lift=9, head_dx=-1),
        base[6], base[7],
    ]


def layup_floater_frames():
    # teardrop: early, soft, high release off one foot (release 3)
    return [
        P((34, 12, -6), (-24, -48, 30), (20, 110), (25, 100), lean=16, ball=("near", 2.5, 0.0)),
        P((-10, -40, 20), (30, 8, -4), (20, 140), (30, 125), lean=6, ball=("near", 3.0, -1.5)),
        P((50, 0, 10), (-8, -14, 40), (110, 166), (80, 140), lean=0, ball=("near", 1.0, -4.5)),
        P((56, 6, 5), (-2, -18, 35), (140, 172), (70, 110), lean=-2, lift=6, head_dx=-1,
          ball=("near", 1.0, -4.5)),
        P((50, 4, 5), (0, -18, 30), (150, 150), (60, 100), lean=-2, lift=7, head_dx=-1),
        P((40, -2, 10), (2, -16, 25), (140, 140), (55, 90), lean=0, lift=5),
        P((20, -6, 15), (4, -14, 20), (100, 100), (50, 80), lean=2, lift=2),
        P((40, -14, 0), (32, -20, 0), (50, 80), (30, 60), lean=10),
    ]


def dunk_reverse_frames():
    # two feet, back to the rim, both hands reach back over the head (dunk 5)
    up = dict(arms_behind_head=True, reach=1.3, shrug=3)
    return [
        P((34, 12, -6), (-24, -48, 30), (15, 140), (25, 125), lean=14, ball=("near", 3.0, -1.5)),
        P((64, -18, 0), (58, -22, 0), (10, 130), (20, 120), lean=26, ball=("near", 3.0, -1.5)),
        P((6, -2, 45), (-4, -8, 50), (130, 160), (125, 155), lean=4, ball=("between", 1.0, -3.0)),
        P((30, -20, 25), (18, -28, 30), (178, 186), (184, 190), lean=-6, lift=13,
          ball=("between", 0.0, -3.5), **up),
        P((36, -10, 20), (24, -18, 25), (204, 214), (208, 218), lean=-14, lift=16,
          ball=("between", -1.5, -3.0), **up),
        P((40, 0, 15), (28, -8, 20), (226, 250), (230, 254), lean=-16, lift=15,
          ball=("between", -3.5, -1.0, 0), **up),
        P((20, -6, 15), (4, -14, 20), (170, 190), (175, 195), lean=-6, lift=6, **up),
        P((58, -18, 0), (50, -24, 0), (40, 70), (30, 60), lean=18),
    ]


def dunk_two_hand_frames():
    # power two-hander straight up off two feet (dunk 4)
    up = dict(arms_behind_head=True, reach=1.3, shrug=3)
    return [
        P((34, 12, -6), (-24, -48, 30), (15, 140), (25, 125), lean=14, ball=("near", 3.0, -1.5)),
        P((70, -20, 0), (64, -24, 0), (10, 120), (20, 110), lean=30, bob=1, ball=("between", 2.0, -1.0)),
        P((6, -2, 45), (-4, -8, 50), (140, 170), (135, 165), lean=6, ball=("between", 0.5, -3.0), **up),
        P((24, -16, 25), (12, -24, 30), (176, 196), (182, 200), lean=-2, lift=12,
          ball=("between", -0.5, -3.5), **up),
        P((30, -12, 20), (18, -20, 25), (130, 112), (124, 108), lean=8, lift=14, head_dx=-1,
          ball=("between", 2.0, -1.0)),
        P((24, -10, 20), (12, -18, 25), (96, 72), (90, 66), lean=8, lift=10),
        P((18, -6, 15), (4, -14, 20), (70, 60), (60, 55), lean=6, lift=5),
        P((62, -20, 0), (56, -26, 0), (40, 70), (30, 60), lean=22),
    ]


def dunk_cradle_frames():
    # rock the cradle: ball swung down and back, then up and slammed (dunk 6)
    up = dict(arms_behind_head=True, reach=1.3, shrug=3)
    return [
        P((34, 12, -6), (-24, -48, 30), (15, 140), (25, 125), lean=14, ball=("near", 3.0, -1.5)),
        P((64, -18, 0), (58, -22, 0), (20, 70), (-15, 55), lean=26, ball=("near", 2.0, 2.0)),
        P((6, -2, 45), (-4, -8, 50), (-10, 10), (100, 130), lean=6, ball=("near", 1.0, 3.0)),
        P((50, -30, 20), (36, -40, 25), (-50, -30), (120, 140), lean=4, lift=10, ball=("near", -1.0, 2.0)),
        P((50, -30, 20), (36, -40, 25), (60, 110), (150, 160), lean=2, lift=15, ball=("near", 2.5, 0.0)),
        P((40, -20, 20), (26, -30, 25), (176, 184), (150, 160), lean=0, lift=17,
          ball=("near", 0.5, -4.0), **up),
        P((50, -40, 25), (38, -50, 30), (132, 112), (100, 110), lean=6, lift=15, head_dx=-1,
          ball=("near", 3.0, -1.0)),
        P((58, -18, 0), (50, -24, 0), (40, 70), (30, 60), lean=20),
    ]



# ---------------------------------------------------------------- celebrations (park mode)
# Dances loop; victory poses play once and end on the pose (events.hold is
# the frame to freeze on).
STAND_L = ((8, -4, 0), (-6, -2, 0))


def dance_two_step_frames():
    # side-to-side two-step with the arms swinging along
    keys = [
        P((6, -4, 0), (-4, -6, 4), (24, 100), (-14, 40), lean=4, bob=1),
        P((26, 2, -6), (-8, -12, 8), (48, 120), (-26, 30), lean=0, dx=1, head_dx=1),
        P((6, -4, 0), (-4, -6, 4), (24, 100), (-14, 40), lean=4, bob=1),
        P((-8, -12, 8), (26, 2, -6), (-26, 30), (48, 120), lean=0, dx=-1, head_dx=-1),
    ]
    return resample(keys, 8)


def dance_shimmy_frames():
    # fists at the chest, shoulders shimmying, knees bouncing
    keys = [
        P((14, -6, 0), (-6, -10, 4), (40, 150), (54, 140), lean=6, bob=1, shrug=1, dx=1),
        P((10, -8, 0), (-4, -12, 4), (48, 138), (44, 152), lean=2, bob=2, shrug=-1),
        P((14, -6, 0), (-6, -10, 4), (40, 150), (54, 140), lean=6, bob=1, shrug=1, dx=-1),
        P((10, -8, 0), (-4, -12, 4), (48, 138), (44, 152), lean=2, bob=2, shrug=-1),
    ]
    return resample(keys, 8)


def dance_robot_frames():
    # stiff, snapping arm positions, two frames each
    legs = dict(near_leg=(4, 0, 0), far_leg=(-4, 0, 0))
    poses = [
        P(**dict(legs, near_arm=(90, 90), far_arm=(-10, -10)), lean=0, head_dx=1),
        P(**dict(legs, near_arm=(0, 90), far_arm=(90, 90)), lean=0, head_dx=-1),
        P(**dict(legs, near_arm=(90, 0), far_arm=(0, 90)), lean=0, dx=1),
        P(**dict(legs, near_arm=(40, 130), far_arm=(90, 0)), lean=0, dx=-1, bob=1),
    ]
    return [dict(p) for p in poses for _ in range(2)]


def victory_flex_frames():
    # double-biceps flex
    return [
        dict(IDLE_POSE),
        P(*STAND_L, (40, 90), (60, 120), lean=0),
        P((14, -2, 0), (-12, -4, 0), (56, 108), (92, 178), lean=-4, shrug=1),
        P((16, -2, 0), (-14, -4, 0), (60, 116), (94, 184), lean=-6, shrug=2, bob=1),
        P((16, -2, 0), (-14, -4, 0), (60, 114), (94, 182), lean=-6, shrug=2),
    ]


def victory_arms_up_frames():
    # both arms raised in a V, chest out
    up = dict(arms_behind_head=True, reach=1.3, shrug=2)
    return [
        dict(IDLE_POSE),
        P(*STAND_L, (100, 150), (110, 160), lean=0),
        P((12, -2, 0), (-10, -4, 0), (146, 160), (190, 196), lean=-6, head_dy=-1, **up),
        P((12, -2, 0), (-10, -4, 0), (150, 164), (196, 202), lean=-8, head_dy=-1, **up),
        P((12, -2, 0), (-10, -4, 0), (148, 162), (194, 200), lean=-8, head_dy=-1, **up),
    ]


def victory_bow_frames():
    # a slow bow to the crowd, one arm across the waist, one behind the back
    return [
        dict(IDLE_POSE),
        P(*STAND_L, (30, 90), (-20, -30), lean=10),
        P((10, -6, 0), (-6, -4, 0), (40, 110), (-40, -70), lean=26),
        P((12, -8, 0), (-6, -6, 0), (50, 120), (-50, -80), lean=42),
        P((12, -8, 0), (-6, -6, 0), (50, 120), (-50, -80), lean=44),
    ]


def victory_cool_frames():
    # arms folded, leaning back, chin up
    return [
        dict(IDLE_POSE),
        P(*STAND_L, (40, 180), (50, 190), lean=0),
        P((10, -2, 0), (-12, -6, 0), (62, 262), (72, 272), lean=-4, head_dy=-1),
        P((10, -2, 0), (-12, -6, 0), (62, 262), (72, 272), lean=-6, head_dy=-1),
    ]


def victory_roar_frames():
    # wide stance, fists flexed down, head forward in a roar
    return [
        dict(IDLE_POSE),
        P((22, -8, 0), (-18, -24, 8), (30, 90), (40, 100), lean=8, bob=1),
        P((32, -12, 0), (-28, -40, 12), (40, 10), (50, 20), lean=14, bob=3, shrug=2, head_dx=1),
        P((34, -12, 0), (-30, -42, 12), (46, 6), (56, 16), lean=16, bob=3, shrug=3, head_dx=1),
        P((34, -12, 0), (-30, -42, 12), (44, 8), (54, 18), lean=16, bob=3, shrug=2, head_dx=1),
    ]


CELEBRATIONS = ["dance_two_step", "dance_shimmy", "dance_robot", "victory_flex", "victory_arms_up",
                "victory_bow", "victory_cool", "victory_roar"]

DRIBBLE_STYLES = ["low", "high", "rhythm", "protect"]
SHOT_STYLES = ["quick", "high", "kick", "push"]
SIGNATURE_ANIMS = [
    ("run_glide", run_glide_frames, 17, True, {}),
    ("run_loose", run_loose_frames, 17, True, {}),
]
for _s in DRIBBLE_STYLES:
    _stand = globals()["dribble_%s_frames" % _s]
    _fps = {"low": 24, "high": 13.33}.get(_s, round(6 / 0.35, 2))
    SIGNATURE_ANIMS += [
        ("dribble_%s" % _s, _stand, _fps, True, {"bounce": 3}),
        ("dribble_%s_far" % _s, (lambda f: lambda: [swap_sides(p) for p in f()])(_stand), _fps, True,
         {"bounce": 3}),
        ("dribble_run_%s" % _s, (lambda k: lambda: _run_dribble(**k))(RUN_DRIBBLES[_s]),
         round(RUN_FRAMES / 0.70, 2), True, {"bounce": 3, "bounce2": 9}),
        ("dribble_run_%s_far" % _s, (lambda k: lambda: _run_dribble(far_hand=True, **k))(RUN_DRIBBLES[_s]),
         round(RUN_FRAMES / 0.70, 2), True, {"bounce": 3, "bounce2": 9}),
    ]
for _s in SHOT_STYLES:
    _base = globals()["shoot_%s_frames" % _s]
    _fps = 15 if _s == "quick" else 12
    _ev = {"gather": 0, "rise": 2, "release": 4}
    SIGNATURE_ANIMS += [
        ("shoot_%s" % _s, _base, _fps, False, _ev),
        ("shoot_%s_pullup" % _s, (lambda b: lambda: shoot_pullup_frames(b()))(_base), _fps, False, _ev),
        ("shoot_%s_fade" % _s, (lambda b: lambda: shoot_fade_frames(b()))(_base), _fps, False, _ev),
    ]
SIGNATURE_ANIMS += [
    ("dance_two_step", dance_two_step_frames, 8, True, {}),
    ("dance_shimmy", dance_shimmy_frames, 10, True, {}),
    ("dance_robot", dance_robot_frames, 8, True, {}),
    ("victory_flex", victory_flex_frames, 8, False, {"hold": 4}),
    ("victory_arms_up", victory_arms_up_frames, 8, False, {"hold": 4}),
    ("victory_bow", victory_bow_frames, 6, False, {"hold": 4}),
    ("victory_cool", victory_cool_frames, 7, False, {"hold": 3}),
    ("victory_roar", victory_roar_frames, 8, False, {"hold": 4}),
    ("layup_reverse", layup_reverse_frames, 12, False, {"gather": 0, "takeoff": 2, "release": 4}),
    ("layup_scoop", layup_scoop_frames, 12, False, {"gather": 0, "takeoff": 2, "release": 4}),
    ("layup_floater", layup_floater_frames, 12, False, {"gather": 0, "takeoff": 2, "release": 3}),
    ("dunk_reverse", dunk_reverse_frames, 11, False, {"gather": 0, "takeoff": 2, "dunk": 5}),
    ("dunk_two_hand", dunk_two_hand_frames, 12, False, {"gather": 0, "takeoff": 2, "dunk": 4}),
    ("dunk_cradle", dunk_cradle_frames, 11, False, {"gather": 0, "takeoff": 2, "dunk": 6}),
]

# Which atlas page group each animation lives in. The app only decodes the
# pages of groups that are actually drawn, so rarely used animations don't
# cost memory until they play.
ANIM_GROUP = {
    "run_upright": "run_upright", "run_power": "run_power", "run_bounce": "run_bounce",
    "celebrate": "extras", "point_up": "extras", "frustrated": "extras",
    "post_up": "post", "post_hook": "post", "post_fadeaway": "post", "post_fade_one_leg": "post",
    "spin_move": "post",
}
for _n in ("crossover_up", "crossover_down", "behind_back_up", "behind_back_down", "between_legs_up",
           "between_legs_down", "hesitation", "hesitation_far", "screen_set", "screen_hold",
           "screen_contact", "pass", "steal"):
    ANIM_GROUP[_n] = "moves"
for _n in ("shoot", "shoot_pullup", "shoot_fade", "block", "rebound"):
    ANIM_GROUP[_n] = "finish"
for _n in ("layup", "layup_finger_roll", "layup_euro", "layup_reverse", "layup_scoop", "layup_floater"):
    ANIM_GROUP[_n] = "layups"
for _n in ("dunk_basic", "dunk_athletic", "dunk_hang", "dunk_windmill", "dunk_tomahawk", "dunk_reverse",
           "dunk_two_hand", "dunk_cradle"):
    ANIM_GROUP[_n] = "dunks"
ANIM_GROUP.update({"run_glide": "run_glide", "run_loose": "run_loose"})
ANIM_GROUP.update({n: "celebrations" for n in CELEBRATIONS})
for _s in DRIBBLE_STYLES:
    for _n in ("dribble_%s", "dribble_%s_far", "dribble_run_%s", "dribble_run_%s_far"):
        ANIM_GROUP[_n % _s] = "dribble_" + _s
for _s in SHOT_STYLES:
    for _n in ("shoot_%s", "shoot_%s_pullup", "shoot_%s_fade"):
        ANIM_GROUP[_n % _s] = "shot_" + _s


def anim_group(name):
    return ANIM_GROUP.get(name, "core")


ANIMS = [
    # name, frames-fn, fps, loop, events (name -> frame index)
    ("idle", idle_frames, 6, True, {}),
    ("run", run_frames, 18, True, {}),
    ("run_start", run_start_frames, 14, False, {}),
    ("run_stop", run_stop_frames, 14, False, {}),
    ("turn", turn_frames, 16, False, {"flipAt": 3}),
    ("turn_run", turn_run_frames, 16, False, {"flipAt": 3}),
    ("turn_dribble", turn_dribble_frames, 16, False, {"flipAt": 3, "bounce": 2}),
    ("dribble", dribble_frames, round(6 / 0.35, 2), True, {"bounce": 3}),
    ("dribble_run", dribble_run_frames, round(RUN_FRAMES / 0.70, 2), True, {"bounce": 3, "bounce2": 9}),
    ("dribble_far", dribble_far_frames, round(6 / 0.35, 2), True, {"bounce": 3}),
    ("dribble_run_far", dribble_run_far_frames, round(RUN_FRAMES / 0.70, 2), True, {"bounce": 3, "bounce2": 9}),
    ("crossover_up", crossover_up_frames, 14, False, {"cross": 2, "catch": 3, "cutStart": 3}),
    ("crossover_down", crossover_down_frames, 14, False, {"cross": 2, "catch": 3, "cutStart": 3}),
    ("shoot", shoot_frames, 12, False, {"gather": 0, "rise": 2, "release": 4}),
    ("layup", layup_frames, 12, False, {"gather": 0, "takeoff": 2, "release": 4}),
    ("pass", pass_frames, 14, False, {"release": 3}),
    ("steal", steal_frames, 14, False, {"activeStart": 2, "activeEnd": 4}),
    ("block", block_frames, 10, False, {"takeoff": 1, "activeStart": 2, "activeEnd": 4}),
    ("rebound", rebound_frames, 10, False, {"takeoff": 1, "catch": 3}),
    ("dunk_basic", dunk_basic_frames, 12, False, {"gather": 0, "takeoff": 2, "dunk": 4}),
    ("dunk_athletic", dunk_athletic_frames, 11, False, {"gather": 0, "takeoff": 2, "dunk": 5}),
    ("screen_set", screen_set_frames, 12, False, {"set": 3}),
    ("screen_hold", screen_hold_frames, 5, True, {}),
    ("screen_contact", screen_contact_frames, 14, False, {"contact": 1}),
    ("run_upright", run_upright_frames, 17, True, {}),
    ("run_power", run_power_frames, 19, True, {}),
    ("run_bounce", run_bounce_frames, 18, True, {}),
    ("guard_on_ball", guard_on_ball_frames, 10, True, {}),
    ("celebrate", celebrate_frames, 12, False, {}),
    ("point_up", point_up_frames, 8, False, {"hold": 3}),
    ("frustrated", frustrated_frames, 6, False, {}),
    ("post_up", post_up_frames, 9, True, {"bounce": 2, "bounce2": 6}),
    ("post_hook", post_hook_frames, 12, False, {"gather": 0, "takeoff": 2, "release": 4}),
    ("post_fadeaway", post_fadeaway_frames, 12, False, {"flipAt": 3, "rise": 5, "release": 7}),
    ("post_fade_one_leg", post_fade_one_leg_frames, 12, False, {"gather": 0, "rise": 2, "release": 4}),
    ("spin_move", spin_move_frames, 14, False, {"flipAt": 4, "bounce": 5}),
    ("walk", walk_frames, 12, True, {}),
    ("walk_dribble", walk_dribble_frames, round(RUN_FRAMES / 1.05, 2), True, {"bounce": 2, "bounce2": 6, "bounce3": 10}),
    ("walk_dribble_far", walk_dribble_far_frames, round(RUN_FRAMES / 1.05, 2), True,
     {"bounce": 2, "bounce2": 6, "bounce3": 10}),
    ("backpedal", backpedal_frames, 10, True, {}),
    ("idle_hips", idle_hips_frames, 4, True, {}),
    ("idle_knees", idle_knees_frames, 4, True, {}),
    ("defense_stance", defense_stance_frames, 6, True, {}),
    ("defense_slide", defense_slide_frames, 12, True, {}),
    ("defense_hands_up", defense_hands_up_frames, 6, True, {}),
    ("shoot_pullup", shoot_pullup_frames, 12, False, {"gather": 0, "rise": 2, "release": 4}),
    ("shoot_fade", shoot_fade_frames, 12, False, {"gather": 0, "rise": 2, "release": 4}),
    ("layup_finger_roll", layup_finger_roll_frames, 12, False, {"gather": 0, "takeoff": 2, "release": 4}),
    ("layup_euro", layup_euro_frames, 12, False, {"gather": 0, "takeoff": 3, "release": 5}),
    ("dunk_windmill", dunk_windmill_frames, 12, False, {"gather": 0, "takeoff": 2, "dunk": 6}),
    ("dunk_tomahawk", dunk_tomahawk_frames, 11, False, {"gather": 0, "takeoff": 2, "dunk": 5}),
    ("behind_back_up", behind_back_up_frames, 14, False, {"cross": 3, "catch": 4, "cutStart": 4}),
    ("behind_back_down", behind_back_down_frames, 14, False, {"cross": 3, "catch": 4, "cutStart": 4}),
    ("between_legs_up", between_legs_up_frames, 14, False, {"cross": 2, "catch": 3, "cutStart": 3}),
    ("between_legs_down", between_legs_down_frames, 14, False, {"cross": 2, "catch": 3, "cutStart": 3}),
    ("hesitation", hesitation_frames, 12, False, {"burst": 3}),
    ("hesitation_far", hesitation_far_frames, 12, False, {"burst": 3}),
    ("dunk_hang", dunk_hang_frames, 10, False,
     {"gather": 0, "takeoff": 2, "dunk": 4, "hangStart": 5, "hangEnd": 6}),
] + SIGNATURE_ANIMS


# ---------------------------------------------------------------- layer split
def to_mask_res(mask, covered):
    """Upsample a 1x mask to MASK_RES texels and grow it one texel (half an
    art pixel) into pixels that later layers cover. The mask is shown with
    smooth scaling, so its soft edge then sits under the covering layer
    (usually the crisp outline) instead of showing a seam or a halo."""
    r = MASK_RES
    tex = {}
    for (x, y), c in mask.items():
        for i in range(r):
            for j in range(r):
                tex[(x * r + i, y * r + j)] = c
    grow = {}
    for (tx, ty), c in tex.items():
        for n in ((tx + 1, ty), (tx - 1, ty), (tx, ty + 1), (tx, ty - 1)):
            if n not in tex and (n[0] // r, n[1] // r) in covered:
                grow[n] = c
    tex.update(grow)
    return tex


def body_layers(grid):
    masks = {s: {} for s in BODY_SLOTS}
    regions = {r: {} for r in WEAR_REGIONS}
    detail = {}
    for p, tag in grid.items():
        tag, regs = split_tag(tag)
        for r in regs:
            regions[r][p] = WHITE
        if tag in TINTED:
            slot, over, alpha = TINTED[tag]
            masks[slot][p] = (255, 255, 255, alpha)
            if over:
                detail[p] = over
        else:
            detail[p] = FIXED[tag]
    opaque = {p for p, c in detail.items() if c[3] == 255}
    out = {}
    for i, slot in enumerate(BODY_SLOTS):
        covered = set(opaque)
        for later in BODY_SLOTS[i + 1:]:
            covered |= set(masks[later])
        out[slot] = to_mask_res(masks[slot], covered)
    for r in WEAR_REGIONS:
        out[r] = to_mask_res(regions[r], opaque)
    return out, detail


def overlay_layers(bald, styled, slot, where):
    """Hair / facial-hair overlay = every pixel that differs from the plain
    render, so it already has holes wherever an arm passes in front."""
    mask, detail = {}, {}
    for p, tag in styled.items():
        if bald.get(p) == tag:
            continue
        tag = split_tag(tag)[0]
        if tag in TINTED and TINTED[tag][0] == slot:
            _, over, alpha = TINTED[tag]
            mask[p] = (255, 255, 255, alpha)
            if over:
                detail[p] = over
        elif tag in FIXED:
            detail[p] = FIXED[tag]
        else:
            raise ValueError("%s: hair overlay would contain %s" % (where, tag))
    missing = [p for p in bald if p not in styled]
    if missing:
        raise ValueError("%s: hair render lost %d pixels" % (where, len(missing)))
    mask = to_mask_res(mask, {p for p, c in detail.items() if c[3] == 255})
    return mask, detail



# ---------------------------------------------------------------- atlas
def cut_piece(pixels, kind):
    """Trim a layer to its bounding box. Returns (key, size, x0, y0, zbytes)
    or None. Runs in the worker processes; zbytes keeps the transfer small."""
    if not pixels:
        return None
    xs = [x for x, _ in pixels]
    ys = [y for _, y in pixels]
    x0, y0 = min(xs), min(ys)
    img = Image.new("RGBA", (max(xs) - x0 + 1, max(ys) - y0 + 1), (0, 0, 0, 0))
    pix = img.load()
    for (x, y), c in pixels.items():
        pix[x - x0, y - y0] = c
    raw = img.tobytes()
    key = hashlib.sha1(kind.encode() + raw + bytes(str(img.size), "ascii")).hexdigest()
    return key, img.size, x0, y0, zlib.compress(raw, 1)


class Atlas:
    """Detail pieces are stored at 1x and upscaled to SCALE (nearest) when
    packed; mask pieces are stored at MASK_RES and drawn scaled up by the
    app. Pages are packed per (group, kind), where a group is a body's
    animation group ("h4-average/core") or one hair / facial-hair style
    ("hair/afro"), so the app only decodes pages that are actually drawn."""

    UPSCALE = {"detail": SCALE, "mask": 1}        # stored units -> page pixels
    PER_UNIT = {"detail": 1, "mask": MASK_RES}    # stored units per art pixel

    def __init__(self):
        self.images = []
        self.keys = []      # (group, kind)
        self.index = {}

    def put(self, group, kind, key, size, zbytes):
        k = (group, kind, key)
        if k not in self.index:
            self.index[k] = len(self.images)
            self.images.append(Image.frombytes("RGBA", size, zlib.decompress(zbytes)))
            self.keys.append((group, kind))
        return self.index[k]

    def pack(self):
        """Shelf-pack pieces into pages. Returns (page images, page groups,
        page scales, rects); a page scale says how many frame pixels one page
        pixel covers."""
        rects = [None] * len(self.images)
        pages, page_groups, page_scales = [], [], []
        for group, kind in dict.fromkeys(self.keys):
            limit = PAGE_PX // self.UPSCALE[kind]
            order = sorted((i for i, g in enumerate(self.keys) if g == (group, kind)),
                           key=lambda i: -self.images[i].height)
            page = None
            x = y = shelf_h = 0
            for i in order:
                w, h = self.images[i].size
                if page is not None and x + w + PAD > limit:
                    x, y, shelf_h = PAD, y + shelf_h + PAD, 0
                if page is None or y + h + PAD > limit:
                    page = len(pages)
                    pages.append([0, 0, kind])
                    page_groups.append(group)
                    page_scales.append(SCALE / (self.PER_UNIT[kind] * self.UPSCALE[kind]))
                    x, y, shelf_h = PAD, PAD, 0
                rects[i] = (page, x, y, w, h)
                pages[page][0] = max(pages[page][0], x + w + PAD)
                pages[page][1] = max(pages[page][1], y + h + PAD)
                x += w + PAD
                shelf_h = max(shelf_h, h)
        out = [Image.new("RGBA", (pw, ph), (0, 0, 0, 0)) for pw, ph, _ in pages]
        for i, (page, px, py, w, h) in enumerate(rects):
            out[page].paste(self.images[i], (px, py))
        ups = [self.UPSCALE[kind] for _, _, kind in pages]
        out = [im.resize((im.width * u, im.height * u), Image.NEAREST) for im, u in zip(out, ups)]
        rects = [[p, px * ups[p], py * ups[p], w * ups[p], h * ups[p]] for p, px, py, w, h in rects]
        return out, page_groups, page_scales, rects


# ---------------------------------------------------------------- previews (emulate the app)
def hex_rgb(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def tinted(img, rgb):
    """What <Image tintColor> does: every pixel becomes the tint, alpha kept."""
    solid = Image.new("RGBA", img.size, rgb + (255,))
    solid.putalpha(img.getchannel("A"))
    return solid


class Compositor:
    def __init__(self, data, bodies, pages):
        self.data = data
        self.bodies = bodies
        self.pages = pages
        self.cache = {}

    def piece(self, table, idx, tint):
        key = (id(table), idx, tint)
        if key not in self.cache:
            p, sx, sy, w, h = table[idx]
            img = self.pages[p].crop((sx, sy, sx + w, sy + h))
            k = self.data["pageScale"][p]
            if k != 1:
                img = img.resize((round(w * k), round(h * k)), Image.BILINEAR)
            self.cache[key] = tinted(img, tint) if tint else img
        return self.cache[key]

    def frame(self, body, anim, i, look, colors):
        """look: skin, hair, facial, hairColor, and optionally outfit (see
        OUTFIT_KEYS: shorts/sock/shoe/sole colors, wear {region: color},
        headwear (kind, color))."""
        f = frame_obj(self.bodies, body, anim, i)
        own = self.bodies[body]["pieces"]
        shared = self.data["pieces"]
        out = dict(DEFAULT_OUTFIT, **(look.get("outfit") or {}))
        canvas = Image.new("RGBA", (self.data["frameWidth"], self.data["frameHeight"]), (0, 0, 0, 0))
        layers = [(f["skin"], look["skin"])]
        worn = out.get("wear") or {}
        for ref, name in zip(f["wear"] or [], self.data["wearRegions"]):
            if name in worn:
                layers.append((ref, worn[name]))
        layers += [(f["jersey"], colors["jersey"]), (f["trim"], colors["trim"])]
        layers += [(f[k], out[k]) for k in ("shorts", "sock", "shoe", "sole")]
        layers.append((f["detail"], None))
        oset, hx, hy = f["head"]
        ids = self.data["overlays"][oset]
        styles = self.data["hairStyles"] + self.data["facialHair"] + self.data["headwear"]
        head_layers = []
        wanted = [(look.get("facial"), look.get("hairColor")), (look.get("hair"), look.get("hairColor"))]
        if out.get("headwear"):
            wanted.append(tuple(out["headwear"]))
        for style, tint in wanted:
            if style:
                pid = ids[styles.index(style)]
                if pid >= 0:
                    m, d = self.data["overlayPairs"][pid]
                    head_layers += [(m, tint), (d, None)]
        for ref, tint in layers:
            if ref:
                canvas.alpha_composite(self.piece(own, ref[0], hex_rgb(tint) if tint else None),
                                       (round(ref[1]), round(ref[2])))
        for ref, tint in head_layers:
            if ref:
                canvas.alpha_composite(self.piece(shared, ref[0], hex_rgb(tint) if tint else None),
                                       (round(ref[1] + hx), round(ref[2] + hy)))
        return canvas


# ---------------------------------------------------------------- output
def build_ball_sheet():
    size = BALL_CELL
    frames = []
    for i in range(8):
        img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
        _blit_rgba(img, ball_layer((5.5, 5.5), i * 22.5))
        frames.append(("spin_%d" % i, img))
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    _blit_rgba(img, ball_layer((5.5, 6.5), 0, 1))
    frames.append(("squash", img))
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    ImageDraw.Draw(img).ellipse((1, 7, 9, 10), fill=(0, 0, 0, 90))
    frames.append(("shadow", img))

    sheet = Image.new("RGBA", (size * len(frames), size), (0, 0, 0, 0))
    meta = {"frames": {}, "meta": {"image": "ball.png", "size": {"w": sheet.width, "h": size},
                                   "frameTags": [
                                       {"name": "spin", "from": 0, "to": 7, "fps": 16},
                                       {"name": "squash", "from": 8, "to": 8},
                                       {"name": "shadow", "from": 9, "to": 9},
                                   ]}}
    for i, (name, img) in enumerate(frames):
        sheet.paste(img, (i * size, 0))
        meta["frames"]["ball_" + name] = {"frame": {"x": i * size, "y": 0, "w": size, "h": size}}
    return sheet, meta


def _blit_rgba(img, layer):
    pix = img.load()
    for src in (layer.outline(), layer.px):
        for (x, y), c in src.items():
            if 0 <= x < img.width and 0 <= y < img.height:
                pix[x, y] = FIXED[c] if isinstance(c, str) else c


def _pt(p):
    return None if p is None else [round(p[0] * SCALE, 1), round(p[1] * SCALE, 1)]


STAND_POSE = P((0, 0, 0), (0, 0, 0), (0, 0), (0, 0), lean=0)
FRAME_FIELDS = ["skin", "jersey", "trim", "detail", "head", "nearHand", "farHand", "ball", "ballDepth", "lift",
                "shorts", "sock", "shoe", "sole", "wear"]


def frame_obj(bodies, body, anim, i):
    """Expand a compact frame record into a dict (same as frameData() in TS)."""
    return dict(zip(FRAME_FIELDS, bodies[body]["frames"][anim][i]))
UNIT = {"detail": 1, "mask": MASK_RES}


def build_body(body):
    """Everything for one body (runs in a worker process). Returns the cut
    pieces and per-frame references to them."""
    use_body(body)
    stand_grid, stand = render(STAND_POSE, "crew")
    standing = (FRAME_H - min(y for _, y in stand_grid)) * SCALE
    pieces = {}
    frames = {}

    def ref(pixels, kind, group, origin=(0, 0)):
        cut = cut_piece(pixels, kind)
        if cut is None:
            return None
        key, size, x0, y0, z = cut
        pieces.setdefault((group, kind, key), (size, z))
        u = UNIT[kind]
        return (group, kind, key, x0 - origin[0] * u, y0 - origin[1] * u)

    for name, fn, _, _, _ in ANIMS:
        group = "%s/%s" % (body, anim_group(name))
        out = []
        for i, pose in enumerate(fn()):
            where = "%s/%s/%d" % (body, name, i)
            bald, info = render(pose, None, stand["hip"][1])
            if info["clipped"]:
                print("WARNING: %s clipped" % where)
            masks, detail = body_layers(bald)
            rec = {s_: ref(masks[s_], "mask", group) for s_ in BODY_SLOTS}
            rec["wear"] = [ref(masks[r], "mask", group) for r in WEAR_REGIONS]
            rec["detail"] = ref(detail, "detail", group)
            head = info["head_origin"]
            overlays = []
            for style in HAIR_STYLES:
                m, d = overlay_layers(bald, info["restyle"](style, None), "hair", where + "/" + style)
                overlays.append((ref(m, "mask", "hair/" + style, head), ref(d, "detail", "hair/" + style, head)))
            for kind in FACIAL_HAIR:
                m, d = overlay_layers(bald, info["restyle"](None, kind), "facial", where + "/" + kind)
                overlays.append((ref(m, "mask", "facial/" + kind, head), ref(d, "detail", "facial/" + kind, head)))
            for kind in HEADWEAR:
                m, d = overlay_layers(bald, info["restyle"](None, None, kind), "headwear", where + "/" + kind)
                overlays.append((ref(m, "mask", "headwear/" + kind, head), ref(d, "detail", "headwear/" + kind, head)))
            rec["overlays"] = overlays
            rec["headOrigin"] = head
            rec["nearHand"] = _pt(info["near_hand"])
            rec["farHand"] = _pt(info["far_hand"])
            rec["ball"] = _pt(info["ball"])
            rec["ballDepth"] = info["ball_depth"]
            rec["lift"] = info["lift"] * SCALE
            out.append(rec)
        frames[name] = out
    return body, standing, pieces, frames


def build_all():
    with multiprocessing.Pool() as pool:
        results = []
        for r in pool.imap(build_body, BODIES):
            print("built", r[0], flush=True)
            results.append(r)
    atlas = Atlas()
    idx = {}
    for _, _, pieces, _ in results:
        for (group, kind, key), (size, z) in pieces.items():
            idx[(group, kind, key)] = atlas.put(group, kind, key, size, z)

    def conv(r):
        if r is None:
            return None
        group, kind, key, x0, y0 = r
        k = SCALE / UNIT[kind]
        return [idx[(group, kind, key)], round(x0 * k, 2), round(y0 * k, 2)]

    # hair / facial overlays: each unique [mask, detail] pair is stored once,
    # and an overlay set lists one pair index per style (-1 = nothing drawn)
    pairs, overlay_sets = {}, {}
    frames, standing = {}, {}

    def rnd(pt):
        return None if pt is None else [round(pt[0]), round(pt[1])]

    for body, stand_h, _, fr in results:
        standing[body] = stand_h
        frames[body] = {}
        for name, recs in fr.items():
            out = []
            for rec in recs:
                ids = []
                for pair in rec["overlays"]:
                    pair = tuple(tuple(conv(r)) if r else None for r in pair)
                    ids.append(-1 if pair == (None, None) else pairs.setdefault(pair, len(pairs)))
                oi = overlay_sets.setdefault(tuple(ids), len(overlay_sets))
                hx, hy = rec["headOrigin"]
                # compact record; see FRAME_FIELDS for the order
                wear_refs = [conv(r) for r in rec["wear"]]
                out.append([conv(rec["skin"]), conv(rec["jersey"]), conv(rec["trim"]), conv(rec["detail"]),
                            [oi, hx * SCALE, hy * SCALE], rnd(rec["nearHand"]), rnd(rec["farHand"]),
                            rnd(rec["ball"]), rec["ballDepth"], rec["lift"],
                            conv(rec["shorts"]), conv(rec["sock"]), conv(rec["shoe"]), conv(rec["sole"]),
                            wear_refs if any(wear_refs) else None])
            frames[body][name] = out
    pages, page_groups, page_scales, rects = atlas.pack()

    # Piece tables: overlay pieces (hair, facial hair, headwear) are shared by
    # every body; each body's own pieces go in its own file, loaded only when
    # a player with that body is drawn. Refs are indices into those tables.
    shared = {}

    def to_shared(r):
        if r is None:
            return None
        return [shared.setdefault(r[0], len(shared)), r[1], r[2]]
    pair_list = [[to_shared(list(r) if r else None) for r in pair] for pair in pairs]
    bodies = {}
    for body, fr in frames.items():
        local = {}

        def to_local(r):
            if r is None:
                return None
            return [local.setdefault(r[0], len(local)), r[1], r[2]]
        out = {}
        for name, recs in fr.items():
            out[name] = []
            for rec in recs:
                rec = list(rec)
                for k in (0, 1, 2, 3, 10, 11, 12, 13):
                    rec[k] = to_local(rec[k])
                if rec[14]:
                    rec[14] = [to_local(r) for r in rec[14]]
                out[name].append(rec)
        bodies[body] = {"pieces": [rects[g] for g in sorted(local, key=local.get)], "frames": out}
    data = {
        "_comment": "AUTO-GENERATED by tools/generate_sprites.py. All positions are frame pixels.",
        "scale": SCALE,
        "frameWidth": FRAME_W * SCALE,
        "frameHeight": FRAME_H * SCALE,
        "anchorX": ANCHOR_X * SCALE,
        "anchorY": ANCHOR_Y * SCALE,
        "pages": [[p.width, p.height] for p in pages],
        "pageGroups": page_groups,
        "pageScale": page_scales,
        "pieces": [rects[g] for g in sorted(shared, key=shared.get)],
        "hairStyles": list(HAIR_STYLES),
        "facialHair": list(FACIAL_HAIR),
        "headwear": list(HEADWEAR),
        "wearRegions": [WEAR_NAMES[r] for r in WEAR_REGIONS],
        "defaultOutfit": DEFAULT_OUTFIT,
        "frameFields": FRAME_FIELDS,
        "overlayPairs": pair_list,
        "overlays": [list(o) for o in overlay_sets],
        "standingHeight": standing,
        "anims": {name: {"fps": fps, "loop": loop, "frameCount": len(frames[MID_BODY][name]),
                         "group": anim_group(name), "events": ev}
                  for name, _, fps, loop, ev in ANIMS},
    }
    return data, bodies, pages


def write_rn(data, bodies, pages):
    os.makedirs(RN_DIR, exist_ok=True)
    atlas_dir = os.path.join(RN_DIR, "atlas")
    shutil.rmtree(atlas_dir, ignore_errors=True)
    os.makedirs(atlas_dir)
    for i, p in enumerate(pages):
        p.save(os.path.join(atlas_dir, "page%d.png" % i), optimize=True)
    with open(os.path.join(RN_DIR, "spriteData.json"), "w") as f:
        json.dump(data, f, separators=(",", ":"))
    body_dir = os.path.join(RN_DIR, "bodies")
    shutil.rmtree(body_dir, ignore_errors=True)
    os.makedirs(body_dir)
    for body, bd in bodies.items():
        with open(os.path.join(body_dir, body + ".json"), "w") as f:
            json.dump(bd, f, separators=(",", ":"))
    lines = [
        "// AUTO-GENERATED by tools/generate_sprites.py - do not edit by hand.",
        "import type { ImageSourcePropType } from 'react-native';",
        "import type { SpriteData } from './types';",
        "import raw from './spriteData.json';",
        "",
        "export const SPRITES = raw as unknown as SpriteData;",
        "",
        "export const PAGES: ImageSourcePropType[] = [",
    ]
    lines += ["  require('./atlas/page%d.png')," % i for i in range(len(pages))]
    lines += ["];", ""]
    with open(os.path.join(RN_DIR, "spriteData.ts"), "w") as f:
        f.write("\n".join(lines))
    lines = [
        "// AUTO-GENERATED by tools/generate_sprites.py - do not edit by hand.",
        "import type { BodyKey } from './features';",
        "import type { BodyData } from './types';",
        "",
        "/** Per-body frame data, required lazily so only bodies on court are parsed. */",
        "export const BODY_LOADERS: Record<BodyKey, () => BodyData> = {",
    ]
    lines += ["  '%s': () => require('./bodies/%s.json')," % (b, b) for b in bodies]
    lines += ["};", ""]
    with open(os.path.join(RN_DIR, "bodyData.ts"), "w") as f:
        f.write("\n".join(lines))


def body_for(palettes, inches, lbs):
    h = next(c["class"] for c in palettes["heightClasses"]
             if c["maxInches"] is None or inches <= c["maxInches"])
    bmi = 703.0 * lbs / (inches * inches)
    w = next(c["id"] for c in palettes["weightClasses"] if c["maxBmi"] is None or bmi < c["maxBmi"])
    return "h%d-%s" % (h, w)


def write_previews(data, bodies, pages, palettes):
    os.makedirs(PREVIEW_DIR, exist_ok=True)
    comp = Compositor(data, bodies, pages)
    bg = (40, 70, 170, 255)
    fw, fh = FRAME_W * 2, FRAME_H * 2      # previews at 2 px per art pixel
    crop_top = fh // 3
    skins = [s["color"] for s in palettes["skinTones"]]
    hair_c = {h["id"]: h["color"] for h in palettes["hairColors"]}
    base = {"skin": skins[1], "hair": "crew", "hairColor": hair_c["black"]}
    mid = MID_BODY

    def small(img):
        return img.resize((fw, fh), Image.NEAREST)

    def label(d, xy, text):
        d.text(xy, text, fill=(255, 255, 255, 255))

    def cell(body, look, team, anim="idle", i=0):
        return small(comp.frame(body, anim, i, look, team)).crop((0, crop_top, fw, fh))

    # every jersey
    teams = palettes["teams"] + [palettes["white"]]
    cols = 11
    rows = (len(teams) + cols - 1) // cols
    sheet = Image.new("RGBA", (cols * fw, rows * (fh - crop_top + 14)), bg)
    d = ImageDraw.Draw(sheet)
    for i, t in enumerate(teams):
        x, y = (i % cols) * fw, (i // cols) * (fh - crop_top + 14)
        sheet.alpha_composite(cell(mid, base, t), (x, y + 12))
        label(d, (x + 4, y + 1), t["id"])
    sheet.save(os.path.join(PREVIEW_DIR, "jerseys.png"))

    # skin tones x hair styles, then facial hair
    styles = [None] + list(HAIR_STYLES)
    hcols = ["black", "darkBrown", "brown", "auburn", "blond", "bleached"]
    ch = fh - crop_top
    sheet = Image.new("RGBA", (len(styles) * fw + 60, (len(skins) + 1) * ch + 30), bg)
    d = ImageDraw.Draw(sheet)
    team = palettes["teams"][13]
    for c, st in enumerate(styles):
        label(d, (60 + c * fw + 4, 2), st or "bald")
        for r, sk in enumerate(palettes["skinTones"]):
            look = {"skin": sk["color"], "hair": st, "hairColor": hair_c[hcols[(c + r) % 6]]}
            sheet.alpha_composite(cell(mid, look, team), (60 + c * fw, 16 + r * ch))
            if c == 0:
                label(d, (4, 16 + r * ch + 40), sk["id"])
    y = 16 + len(skins) * ch + 14
    for c, fac in enumerate([None] + list(FACIAL_HAIR)):
        look = dict(base, facial=fac, skin=skins[c % 5], hairColor=hair_c[hcols[c % 6]])
        sheet.alpha_composite(cell(mid, look, team), (60 + c * fw, y))
        label(d, (60 + c * fw + 4, y - 12), fac or "clean")
    label(d, (4, y + 40), "facial")
    sheet.save(os.path.join(PREVIEW_DIR, "looks.png"))

    # 5 height classes x 3 weight classes
    sheet = Image.new("RGBA", (len(HEIGHT_CLASSES) * fw + 60, len(WEIGHT_CLASSES) * fh + 24), bg)
    d = ImageDraw.Draw(sheet)
    for c, h in enumerate(HEIGHT_CLASSES):
        label(d, (60 + c * fw + 4, 2), "height %d" % h)
        for r, w in enumerate(WEIGHT_CLASSES):
            img = small(comp.frame("h%d-%s" % (h, w), "idle", 0, base, team))
            sheet.alpha_composite(img, (60 + c * fw, 16 + r * fh))
            if c == 0:
                label(d, (4, 16 + r * fh + fh // 2), w)
    sheet.save(os.path.join(PREVIEW_DIR, "bodies.png"))

    # a random matchup, drawn the way the game will: body from height and
    # weight, then scaled by real height
    rng = random.Random(5)
    home, away = palettes["teams"][13], palettes["teams"][1]
    court = Image.new("RGBA", (10 * 80 + 40, 200), bg)
    d = ImageDraw.Draw(court)
    d.rectangle((0, 170, court.width, court.height), fill=(30, 50, 140, 255))
    for i in range(10):
        inches = rng.randint(72, 87)
        lbs = int(inches * inches * rng.uniform(21.5, 29) / 703)
        body = body_for(palettes, inches, lbs)
        look = {"skin": rng.choice(skins), "hair": rng.choice(styles),
                "facial": rng.choice([None, None] + list(FACIAL_HAIR)),
                "hairColor": hair_c[rng.choice(["black", "black", "darkBrown", "brown", "blond", "auburn"])]}
        img = comp.frame(body, "idle", 0, look, home if i < 5 else away)
        s = (inches * 1.6) / data["standingHeight"][body]      # ~in-game size
        img = img.resize((int(img.width * s), int(img.height * s)), Image.BILINEAR)
        cx = 50 + i * 80 + (20 if i >= 5 else 0)
        court.alpha_composite(img, (cx - img.width // 2, 170 - img.height))
        label(d, (cx - 22, 174), "%d'%d\" %d" % (inches // 12, inches % 12, lbs))
        label(d, (cx - 22, 186), body)
    court.save(os.path.join(PREVIEW_DIR, "matchup.png"))

    # full animation sheet + gifs for one look, with the ball drawn the way
    # the game should: at the frame's ball point, nudged down the screen by
    # ballDepth (toward the camera) and behind the player when depth < 0
    look = {"skin": skins[3], "hair": "locs", "facial": "goatee", "hairColor": hair_c["black"]}
    team = palettes["teams"][9]
    ball_img = Image.new("RGBA", (BALL_CELL, BALL_CELL), (0, 0, 0, 0))
    _blit_rgba(ball_img, ball_layer((5.5, 5.5), 0))
    ball_img = ball_img.resize((BALL_CELL * 2, BALL_CELL * 2), Image.NEAREST)

    def with_ball(img, rec):
        if not rec["ball"]:
            return img
        depth = rec["ballDepth"] or 0
        bx = rec["ball"][0] * 2 / SCALE - BALL_CELL
        by = rec["ball"][1] * 2 / SCALE - BALL_CELL + depth * 4
        out = Image.new("RGBA", img.size, (0, 0, 0, 0))
        layers = [ball_img, img] if depth < 0 else [img, ball_img]
        for layer in layers:
            if layer is ball_img:
                out.alpha_composite(ball_img, (int(round(bx)), int(round(by))))
            else:
                out.alpha_composite(layer)
        return out

    ncols = max(a["frameCount"] for a in data["anims"].values())
    sheet = Image.new("RGBA", (ncols * fw, len(data["anims"]) * fh), bg)
    d = ImageDraw.Draw(sheet)
    for r, name in enumerate(data["anims"]):
        n = data["anims"][name]["frameCount"]
        imgs = []
        for c in range(n):
            img = with_ball(small(comp.frame(mid, name, c, look, team)), frame_obj(bodies, mid, name, c))
            sheet.alpha_composite(img, (c * fw, r * fh))
            f = Image.new("RGBA", img.size, bg)
            f.alpha_composite(img)
            imgs.append(f.convert("RGB"))
        label(d, (4, r * fh + 4), name)
        imgs[0].save(os.path.join(PREVIEW_DIR, name + ".gif"), save_all=True, append_images=imgs[1:],
                     duration=int(1000 / data["anims"][name]["fps"]), loop=0)
    for x in range(0, sheet.width, fw):
        d.line([(x, 0), (x, sheet.height)], fill=(255, 255, 255, 50))
    for y in range(0, sheet.height, fh):
        d.line([(0, y), (sheet.width, y)], fill=(255, 255, 255, 50))
    sheet.save(os.path.join(PREVIEW_DIR, "animations.png"))


def write_outfit_preview(data, bodies, pages, palettes):
    """Park-mode outfits on a few bodies and poses."""
    comp = Compositor(data, bodies, pages)
    bg = (40, 70, 170, 255)
    fw, fh = FRAME_W * 3, FRAME_H * 3
    hair_c = {h["id"]: h["color"] for h in palettes["hairColors"]}
    skins = [t["color"] for t in palettes["skinTones"]]
    fits = [
        ("league", {}, {"jersey": "#1d2a5c", "trim": "#f2c230"}, "crew", None),
        ("tee + long shorts", {"wear": {"sleeveShort": "#d62b2b", "shortsLong": "#26262c"}, "shorts": "#26262c",
                               "shoe": "#f2f2f4", "sole": "#d62b2b"}, {"jersey": "#d62b2b", "trim": "#f2f2f4"},
         "fade", None),
        ("compression + headband", {"wear": {"sleeveShort": "#26262c", "sleeveLong": "#26262c"},
                                    "shorts": "#2c5fd6", "headwear": ("headband", "#f2f2f4"),
                                    "shoe": "#26262c", "sole": "#f2f2f4"}, {"jersey": "#f2f2f4", "trim": "#2c5fd6"},
         "afro", None),
        ("retro tube socks", {"wear": {"sockTall": "#f2f2f4"}, "sock": "#f2f2f4", "shorts": "#f07a1a",
                              "headwear": ("wide_headband", "#f07a1a"), "shoe": "#f2f2f4", "sole": "#26262c"},
         {"jersey": "#1fa6a0", "trim": "#f07a1a"}, "high_top", "mustache"),
        ("sleeve + wristbands", {"wear": {"armSleeveNear": "#f2f2f4", "wristband": "#f2c230"},
                                 "shorts": "#7a3fc4", "shoe": "#f2c230", "sole": "#7a3fc4",
                                 "headwear": ("tied_headband", "#d62b2b")},
         {"jersey": "#7a3fc4", "trim": "#f2c230"}, "cornrows", "goatee"),
        ("long sleeve tee", {"wear": {"sleeveShort": "#2f9e4f", "sleeveLong": "#2f9e4f", "shortsLong": "#9a9ca6",
                                      "wristband": "#f2f2f4"},
                             "shorts": "#9a9ca6", "shoe": "#2f9e4f", "sole": "#f2f2f4"},
         {"jersey": "#2f9e4f", "trim": "#f2f2f4"}, "locs", "beard"),
    ]
    poses = [("idle", 0), ("run", 3), ("shoot", 4), ("dance_two_step", 1), ("victory_arms_up", 4)]
    ch = fh - fh // 4
    sheet = Image.new("RGBA", (len(poses) * fw + 150, len(fits) * ch + 8), bg)
    d = ImageDraw.Draw(sheet)
    for r, (name, outfit, colors, hair, facial) in enumerate(fits):
        look = {"skin": skins[(r + 1) % len(skins)], "hair": hair, "facial": facial,
                "hairColor": hair_c["black"], "outfit": outfit}
        d.text((6, r * ch + ch // 2), name, fill=(255, 255, 255, 255))
        for c, (anim, i) in enumerate(poses):
            img = comp.frame(MID_BODY, anim, i, look, colors).resize((fw, fh), Image.NEAREST)
            sheet.alpha_composite(img.crop((0, fh // 4, fw, fh)), (150 + c * fw, r * ch + 4))
    sheet.save(os.path.join(PREVIEW_DIR, "outfits.png"))
    # headbands on each hair style
    styles = list(HAIR_STYLES)
    sheet = Image.new("RGBA", (len(styles) * FRAME_W * 2, 3 * (FRAME_H * 2 // 2) + 10), bg)
    for r, hw in enumerate(HEADWEAR):
        for c, st in enumerate(styles):
            look = {"skin": skins[c % len(skins)], "hair": st, "hairColor": hair_c["black"],
                    "outfit": {"headwear": (hw, ["#d62b2b", "#f2f2f4", "#2c5fd6"][r])}}
            img = comp.frame(MID_BODY, "idle", 0, look, {"jersey": "#26262c", "trim": "#f2f2f4"})
            img = img.resize((FRAME_W * 2, FRAME_H * 2), Image.NEAREST).crop((0, 56, FRAME_W * 2, FRAME_H + 56))
            sheet.alpha_composite(img, (c * FRAME_W * 2, r * FRAME_H + 4))
    sheet.save(os.path.join(PREVIEW_DIR, "headbands.png"))


def main():
    with open(os.path.join(RN_DIR, "palettes.json")) as f:
        palettes = json.load(f)
    data, bodies, pages = build_all()
    write_rn(data, bodies, pages)
    ball, ball_meta = build_ball_sheet()
    ball.save(os.path.join(SPRITE_DIR, "ball.png"))
    with open(os.path.join(SPRITE_DIR, "ball.json"), "w") as f:
        json.dump(ball_meta, f, indent=2)
    write_previews(data, bodies, pages, palettes)
    write_outfit_preview(data, bodies, pages, palettes)
    per = {}
    for (w, h), g in zip(data["pages"], data["pageGroups"]):
        per[g] = per.get(g, 0) + w * h * 4 / 1e6
    npieces = len(data["pieces"]) + sum(len(b["pieces"]) for b in bodies.values())
    print("pieces: %d  pages: %d  total ~%.0f MB decoded" % (npieces, len(pages), sum(per.values())))
    body_all = {}
    for g, v in per.items():
        b_, grp = g.split("/")
        body_all.setdefault(b_, {})[grp] = round(v, 1)
    print("MB per group for", MID_BODY, body_all[MID_BODY])
    print("hair/facial/headwear MB:", {g: v for g, v in body_all.items() if g in ("hair", "facial", "headwear")})
    sizes = {b: os.path.getsize(os.path.join(RN_DIR, "bodies", b + ".json")) for b in bodies}
    print("data: meta %.1f MB, per body %.2f-%.2f MB" % (
        os.path.getsize(os.path.join(RN_DIR, "spriteData.json")) / 1e6, min(sizes.values()) / 1e6,
        max(sizes.values()) / 1e6))
    print("standing height (atlas px):", data["standingHeight"])


if __name__ == "__main__":
    main()
