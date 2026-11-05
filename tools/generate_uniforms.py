#!/usr/bin/env python3
"""Team uniforms for career mode: home, away and city edition for each of
the 30 league teams.

On court a uniform is the jersey and trim colors plus one of the generator's
uniform patterns (UNIFORM_PATTERNS in generate_sprites.py) in two accent
colors, and the shorts color. For menus each uniform also gets a jersey card
(front with the team logo and wordmark, back with a number), drawn in the
same pixel art as the logos.

Writes integration/react-native/teamUniforms/:
  png/<ID>_<kind>.png   jersey card, front and back, 512 x 320
  uniforms.json         every team's three uniforms
  index.ts              types, getUniform(), UNIFORM_CARDS require map
and previews/uniforms.png (all 90 cards).
Run generate_sprites.py first if the patterns changed.
"""
import json
import math
import os
import shutil
import sys

from PIL import Image, ImageDraw

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import generate_logos as lg  # noqa: E402
import generate_sprites as g  # noqa: E402

OUT = os.path.join(g.ROOT, "integration", "react-native", "teamUniforms")
KINDS = ("home", "away", "city")
WHITE = "#F4F1EA"

# id -> {kind: (pattern, jersey, trim, accent, accent2, shorts[, name])}
# Home is light, away is the team color, and the city edition is themed on
# the city (its name is shown in menus and across the card's chest).
T = {
    "PHX": {"home": ("classic", WHITE, "#E56020", "#E56020", "#5A2D12", WHITE),
            "away": ("flames", "#5A2D12", "#E56020", "#E56020", "#F7B733", "#5A2D12"),
            "city": ("fade", "#2B1B3D", "#F7B733", "#E56020", "#F7B733", "#2B1B3D", "Desert Sunset")},
    "SLC": {"home": ("waves", WHITE, "#1FA2D6", "#1FA2D6", "#F5E03A", WHITE),
            "away": ("classic", "#1FA2D6", "#F5E03A", "#F5E03A", "#0E5F86", "#1FA2D6"),
            "city": ("waves", "#E9F4F7", "#0E5F86", "#7FC8E8", "#0E5F86", "#0E5F86", "Great Salt Lake")},
    "CHI": {"home": ("spots", WHITE, "#F4A6B8", "#1E1E1E", "#F4A6B8", WHITE),
            "away": ("pinstripes", "#1E1E1E", "#F4A6B8", "#3A3A3A", "#F4A6B8", "#1E1E1E"),
            "city": ("skyline", "#1B2A4A", "#F4A6B8", "#0E1626", "#F4D35E", "#1B2A4A", "Windy City")},
    "CHA": {"home": ("honeycomb", "#FFF6DA", "#1A1A1A", "#F2C12E", "#1A1A1A", "#FFF6DA"),
            "away": ("chest_band", "#F2C12E", "#1A1A1A", "#1A1A1A", "#FFF6DA", "#1A1A1A"),
            "city": ("honeycomb", "#1A1A1A", "#F2C12E", "#F2C12E", "#7A4FA0", "#1A1A1A", "Queen City")},
    "NY": {"home": ("pinstripes", WHITE, "#D0342C", "#6E6E78", "#D0342C", WHITE),
           "away": ("classic", "#6E6E78", "#D0342C", "#D0342C", "#1E1E24", "#6E6E78"),
           "city": ("skyline", "#101820", "#D0342C", "#2A3440", "#F2C230", "#101820", "Subway")},
    "GA": {"home": ("classic", WHITE, "#F59A6A", "#F59A6A", "#4E9A3A", WHITE),
           "away": ("fade", "#F59A6A", "#4E9A3A", "#E86A3A", "#4E9A3A", "#F59A6A"),
           "city": ("two_tone", "#FFE1C9", "#4E9A3A", "#F59A6A", "#4E9A3A", "#F59A6A", "Peach State")},
    "BOS": {"home": ("retro", WHITE, "#2E6B3A", "#2E6B3A", "#E8C44A", WHITE),
            "away": ("classic", "#2E6B3A", "#E8C44A", "#E8C44A", WHITE, "#2E6B3A"),
            "city": ("plaid", "#F2E6C8", "#8B2E2E", "#8B2E2E", "#2E6B3A", "#8B2E2E", "Butcher Paper")},
    "ORL": {"home": ("chevron", WHITE, "#1BB5A6", "#1BB5A6", "#FF5C8A", WHITE),
            "away": ("waves", "#1BB5A6", "#FF5C8A", "#FF5C8A", "#FFD23F", "#1BB5A6"),
            "city": ("stars", "#2A1E5C", "#FFD23F", "#3B2A7A", "#FFD23F", "#2A1E5C", "Fireworks")},
    "MIA": {"home": ("waves", WHITE, "#6EC6F0", "#6EC6F0", "#FF8C5A", WHITE),
            "away": ("fade", "#6EC6F0", "#FF8C5A", "#FF8C5A", WHITE, "#6EC6F0"),
            "city": ("fade", "#1A1033", "#3BE8F0", "#FF4FB3", "#3BE8F0", "#1A1033", "Vice Nights")},
    "NO": {"home": ("yoke", WHITE, "#4B2A6B", "#4B2A6B", "#7BC043", WHITE),
           "away": ("two_tone", "#4B2A6B", "#7BC043", "#2E1A44", "#7BC043", "#4B2A6B"),
           "city": ("plaid", "#4B2A6B", "#F2C230", "#7BC043", "#F2C230", "#4B2A6B", "Mardi Gras")},
    "PHI": {"home": ("classic", WHITE, "#1D4FB8", "#1D4FB8", "#FFD23F", WHITE),
            "away": ("chest_band", "#1D4FB8", "#FFD23F", "#FFD23F", WHITE, "#1D4FB8"),
            "city": ("stars", WHITE, "#D0342C", "#1D4FB8", WHITE, "#1D4FB8", "Liberty Bell")},
    "BKN": {"home": ("pinstripes", WHITE, "#3A3A40", "#3A3A40", "#F4C542", WHITE),
            "away": ("yoke", "#3A3A40", "#F4C542", "#F4C542", "#1E1E22", "#3A3A40"),
            "city": ("spots", "#F4C542", "#3A3A40", "#D99A1B", "#3A3A40", "#3A3A40", "Swiss Cheese")},
    "HOU": {"home": ("classic", WHITE, "#3B5B8C", "#3B5B8C", "#E8A33A", WHITE),
            "away": ("retro", "#3B5B8C", "#E8A33A", "#E8A33A", WHITE, "#3B5B8C"),
            "city": ("stars", "#0B1530", "#E8A33A", "#1F3A6E", WHITE, "#0B1530", "Space City")},
    "DET": {"home": ("chest_band", WHITE, "#9C4A1E", "#9C4A1E", "#B8BCC4", WHITE),
            "away": ("classic", "#9C4A1E", "#B8BCC4", "#B8BCC4", "#2B2B2E", "#9C4A1E"),
            "city": ("lightning", "#2B2B2E", "#B8BCC4", "#B8BCC4", "#9C4A1E", "#2B2B2E", "Motor City")},
    "IND": {"home": ("retro", WHITE, "#3F7D2B", "#3F7D2B", "#F2C230", WHITE),
            "away": ("two_tone", "#3F7D2B", "#F2C230", "#F2C230", WHITE, "#3F7D2B"),
            "city": ("pinstripes", "#F2C230", "#3F7D2B", "#3F7D2B", "#3F7D2B", "#3F7D2B", "Cornfield")},
    "SF": {"home": ("classic", WHITE, "#5B2A86", "#5B2A86", "#6DB33F", WHITE),
           "away": ("fade", "#5B2A86", "#6DB33F", "#6DB33F", WHITE, "#5B2A86"),
           "city": ("waves", "#C9CED6", "#E8592A", "#5B2A86", "#E8592A", "#5B2A86", "Fog City")},
    "LAC": {"home": ("lightning", WHITE, "#D22630", "#D22630", "#C0C6CF", WHITE),
            "away": ("classic", "#D22630", "#C0C6CF", "#C0C6CF", "#1E1E22", "#D22630"),
            "city": ("flames", "#141414", "#D22630", "#D22630", "#F7B733", "#141414", "Hot Rod")},
    "LAB": {"home": ("yoke", WHITE, "#2C4F7C", "#2C4F7C", "#C9C3B5", WHITE),
            "away": ("chevron", "#2C4F7C", "#C9C3B5", "#C9C3B5", "#F08A4B", "#2C4F7C"),
            "city": ("fade", "#2C4F7C", "#F4D35E", "#F08A4B", "#F4D35E", "#2C4F7C", "City of Angels")},
    "DC": {"home": ("pinstripes", WHITE, "#14213D", "#14213D", "#C9A227", WHITE),
           "away": ("chest_band", "#14213D", "#C9A227", "#C9A227", WHITE, "#14213D"),
           "city": ("stars", WHITE, "#C9A227", "#14213D", WHITE, "#14213D", "Capitol")},
    "DEN": {"home": ("classic", WHITE, "#B8733A", "#B8733A", "#2B2B2B", WHITE),
            "away": ("yoke", "#B8733A", "#2B2B2B", "#2B2B2B", "#F2C230", "#B8733A"),
            "city": ("chevron", "#1F3A5F", "#F4F1EA", "#F4F1EA", "#B8733A", "#1F3A5F", "Mile High")},
    "DAL": {"home": ("classic", WHITE, "#4A5568", "#4A5568", "#C0C6CF", WHITE),
            "away": ("two_tone", "#4A5568", "#C0C6CF", "#2D3442", "#C0C6CF", "#4A5568"),
            "city": ("stars", "#1A2238", "#E94F37", "#C0C6CF", "#E94F37", "#1A2238", "Lone Star")},
    "SAC": {"home": ("retro", WHITE, "#6B4226", "#6B4226", "#E8A23A", WHITE),
            "away": ("classic", "#6B4226", "#E8A23A", "#E8A23A", WHITE, "#6B4226"),
            "city": ("fade", "#2D5A3D", "#E8A23A", "#E8A23A", "#6B4226", "#2D5A3D", "Gold Rush")},
    "MIL": {"home": ("yoke", WHITE, "#1F5A33", "#1F5A33", "#7A4E2A", WHITE),
            "away": ("pinstripes", "#1F5A33", "#7A4E2A", "#174628", "#C9A26A", "#1F5A33"),
            "city": ("plaid", "#B8322B", "#1A1A1A", "#1A1A1A", "#F2C230", "#1A1A1A", "Northwoods")},
    "POR": {"home": ("chevron", WHITE, "#B8322B", "#B59B6A", "#B8322B", WHITE),
            "away": ("classic", "#B59B6A", "#B8322B", "#B8322B", "#3A2E1E", "#B59B6A"),
            "city": ("waves", "#2F3E46", "#B8322B", "#6C8EA0", "#B8322B", "#2F3E46", "Rain City")},
    "OKC": {"home": ("stars", WHITE, "#3B8FD6", "#3B8FD6", WHITE, WHITE),
            "away": ("classic", "#3B8FD6", "#D32F2F", "#D32F2F", WHITE, "#3B8FD6"),
            "city": ("lightning", "#1B1B3A", "#F2C230", "#F2C230", "#3B8FD6", "#1B1B3A", "Thunder Alley")},
    "SA": {"home": ("classic", WHITE, "#1B9AAA", "#1B9AAA", "#C0C6CF", WHITE),
           "away": ("fade", "#1B9AAA", "#C0C6CF", "#C0C6CF", "#14707C", "#1B9AAA"),
           "city": ("retro", WHITE, "#E94F8A", "#E94F8A", "#1B9AAA", "#1B9AAA", "Fiesta")},
    "MIN": {"home": ("waves", WHITE, "#2A6FDB", "#2A6FDB", "#BDE3F5", WHITE),
            "away": ("yoke", "#2A6FDB", "#BDE3F5", "#BDE3F5", "#14408A", "#2A6FDB"),
            "city": ("fade", "#0E1B2E", "#3BE8A0", "#3BE8A0", "#7A5CFA", "#0E1B2E", "Northern Lights")},
    "CLE": {"home": ("retro", WHITE, "#7A1F3D", "#7A1F3D", "#F2DDB0", WHITE),
            "away": ("classic", "#7A1F3D", "#F2DDB0", "#F2DDB0", WHITE, "#7A1F3D"),
            "city": ("spots", "#F2DDB0", "#7A1F3D", "#7A1F3D", "#7A1F3D", "#7A1F3D", "Polka Party")},
    "MEM": {"home": ("classic", WHITE, "#8B2E16", "#8B2E16", "#B0A89E", WHITE),
            "away": ("flames", "#8B2E16", "#B0A89E", "#E8742A", "#F7B733", "#8B2E16"),
            "city": ("pinstripes", "#1E2A5A", "#6EA3D8", "#2E3E7A", "#F2C230", "#1E2A5A", "Blues City")},
    "TOR": {"home": ("classic", WHITE, "#D52B1E", "#D52B1E", "#1E1E22", WHITE),
            "away": ("chest_band", "#D52B1E", "#F5F5F5", "#F5F5F5", "#1E1E22", "#D52B1E"),
            "city": ("plaid", "#D52B1E", "#1A1A1A", "#1A1A1A", "#F5F5F5", "#1A1A1A", "Lumberjack")},
}


def uniforms():
    teams = {t[0]: t for t in lg.TEAMS}
    out = {}
    for tid, kinds in T.items():
        team = teams[tid]
        out[tid] = {}
        for kind in KINDS:
            pat, jersey, trim, a, b, shorts = kinds[kind][:6]
            name = kinds[kind][6] if len(kinds[kind]) > 6 else ("Home" if kind == "home" else "Away")
            assert pat in g.UNIFORM_PATTERNS, pat
            out[tid][kind] = {"name": name, "pattern": pat, "jersey": jersey, "trim": trim, "accent": a,
                              "accent2": b, "shorts": shorts,
                              "wordmark": (team[1] if kind == "away" else name if kind == "city" else team[2])}
    return out


# ------------------------------------------------------------------ cards
CW, CH = 128, 160            # one side of a card, art px (drawn at 2x)
HW = 44                      # torso half width
NECK_Y, HEM_Y, WAIST_Y, LEG_Y = 10, 104, 106, 150


def hexrgb(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def shade(c, k):
    return tuple(max(0, min(255, int(v * k))) for v in c)


def jersey_hw(y):
    """Half width of the tank top at row y: straps, arm holes, then the body."""
    if y < 26:
        return 26 + (y - NECK_Y) * 0.25
    t = min(1.0, (y - 26) / 20)
    return 30 + (HW - 30) * math.sqrt(1 - (1 - t) ** 2)


def neck(x, y):
    return abs(x) < 15 and y < NECK_Y + 16 * math.sqrt(max(0.0, 1 - (x / 15) ** 2))


def card_side(u, back):
    """One side of a card: dict (x, y) -> (r, g, b)."""
    sfn, kfn = g.UNIFORM_PATTERNS[u["pattern"]][1:]
    cols = {"base": hexrgb(u["jersey"]), "a": hexrgb(u["accent"]), "b": hexrgb(u["accent2"])}
    trim, shorts = hexrgb(u["trim"]), hexrgb(u["shorts"])
    px = {}
    cx = CW // 2
    for y in range(NECK_Y, HEM_Y + 1):
        hw = jersey_hw(y)
        for x in range(-int(hw), int(hw) + 1):
            if neck(x, y - (8 if back else 0)) or (y < 26 and abs(x) < 15):
                continue                                              # neck scoop (shallower at the back)
            h = (HEM_Y - y) / (HEM_Y - NECK_Y)
            ph = math.asin(max(-1.0, min(1.0, x / HW)))
            arc = (math.copysign(g.UNI_ARC, x) - ph * 4.7) if back else ph * 4.7
            r = sfn(h, arc)
            c = cols[r] if r else cols["base"]
            nb = 8 if back else 0
            edge = abs(x) > hw - 2.2 or any(neck(x + ddx, y - nb + ddy) for ddx, ddy in ((0, -2), (2, 0), (-2, 0)))
            px[(cx + x, y)] = trim if edge and y < 52 else c
    for y in range(WAIST_Y, LEG_Y + 1):
        hw = HW + 2 + (y - WAIST_Y) * 0.12
        for x in range(-int(hw), int(hw) + 1):
            if y > WAIST_Y + 22 and abs(x) < 2 + (y - WAIST_Y - 22) * 0.35:
                continue                                              # split between the legs
            if y < WAIST_Y + 4:
                px[(cx + x, y)] = trim                                # waistband
                continue
            h = (y - WAIST_Y) / (LEG_Y - WAIST_Y)
            s = (hw - abs(x)) / 4.0
            r = kfn(h, s)
            px[(cx + x, y)] = cols[r] if r else shorts
    return px


def outline_and_shade(px):
    out = dict(px)
    xs = [x for x, _ in px]
    cx = (min(xs) + max(xs)) / 2
    for (x, y), c in px.items():
        k = 1.0
        d = (x - cx) / HW
        if d > 0.72:
            k = 0.82                                                  # side away from the light
        elif d < -0.72:
            k = 1.08
        out[(x, y)] = shade(c, k)
    for (x, y) in px:
        for n in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)):
            if n not in px:
                out[n] = hexrgb(lg.OUTLINE)
    return out


# 3 x 5 digits for jersey numbers (the logo font only has letters)
DIGITS = {
    "0": "111101101101111", "1": "010110010010111", "2": "111001111100111", "3": "111001111001111",
    "4": "101101111001001", "5": "111100111001111", "6": "111100111101111", "7": "111001001010010",
    "8": "111101111101111", "9": "111101111001111",
}
lg.FONT.update(DIGITS)


def blit_text(px, text, cx, y0, scale, color, shadow, bounds):
    w = lg.text_width(text) * scale
    x0 = cx - w // 2
    for (x, y) in lg.text_pixels(text, 0, 0):
        for i in range(scale):
            for j in range(scale):
                for ddx, ddy in ((1, 1), (1, 0), (0, 1), (-1, 0), (0, -1), (-1, -1), (1, -1), (-1, 1)):
                    q = (x0 + x * scale + i + ddx, y0 + y * scale + j + ddy)
                    if q in bounds:
                        px[q] = shadow                                # outline, readable over any pattern
    for (x, y) in lg.text_pixels(text, 0, 0):
        for i in range(scale):
            for j in range(scale):
                p = (x0 + x * scale + i, y0 + y * scale + j)
                if p in bounds:
                    px[p] = color


def contrast(c):
    return (28, 22, 32) if sum(c) > 470 else (244, 235, 208)


def card(team, u, number):
    front = card_side(u, False)
    back = card_side(u, True)
    base = hexrgb(u["jersey"])
    ink = hexrgb(u["trim"]) if abs(sum(hexrgb(u["trim"])) - sum(base)) > 160 else contrast(base)
    sh = (28, 22, 32) if sum(ink) > 360 else (244, 235, 208)
    # front: wordmark across the chest, the team logo under it, a small number
    word = u["wordmark"].upper()
    scale = 2 if lg.text_width(word) * 2 <= 2 * HW - 12 else 1
    fb = set(front)
    blit_text(front, word, CW // 2, 34, scale, ink, sh, fb)
    logo = lg.icon_only(team).px
    lx = [x for x, _ in logo]
    ly = [y for _, y in logo]
    ox = CW // 2 - (min(lx) + max(lx)) // 2
    oy = 48 - min(ly)
    for (x, y), c in logo.items():
        p = (x + ox, y + oy)
        if p in fb:
            front[p] = hexrgb(c)
    blit_text(front, str(number), CW // 2 + 26, 84, 2, ink, sh, fb)
    # back: the number, big
    bb = set(back)
    blit_text(back, str(number), CW // 2, 40, 6, ink, sh, bb)
    img = Image.new("RGBA", (CW * 2, CH), (0, 0, 0, 0))
    for side, off in ((outline_and_shade(front), 0), (outline_and_shade(back), CW)):
        for (x, y), c in side.items():
            if 0 <= x < CW and 0 <= y < CH:
                img.putpixel((x + off, y), c + (255,))
    return img.resize((CW * 4, CH * 2), Image.NEAREST)


def write_ts(data):
    lines = [
        "// AUTO-GENERATED by tools/generate_uniforms.py - do not edit by hand.",
        "import type { ImageSourcePropType } from 'react-native';",
        "import type { JerseyColors, Outfit, UniformPattern } from '../playerSprites/types';",
        "import uniforms from './uniforms.json';",
        "",
        "export type UniformKind = 'home' | 'away' | 'city';",
        "export const UNIFORM_KINDS: UniformKind[] = ['home', 'away', 'city'];",
        "",
        "export type TeamUniform = {",
        "  /** 'Home', 'Away', or the city edition's name */",
        "  name: string;",
        "  pattern: UniformPattern;",
        "  jersey: string;",
        "  trim: string;",
        "  /** pattern colors */",
        "  accent: string;",
        "  accent2: string;",
        "  shorts: string;",
        "  /** the word across the chest on the jersey card */",
        "  wordmark: string;",
        "};",
        "",
        "export const TEAM_UNIFORMS = uniforms as Record<string, Record<UniformKind, TeamUniform>>;",
        "",
        "/** A team's uniform (falls back to home for an unknown kind). */",
        "export function getUniform(teamId: string, kind: UniformKind = 'home'): TeamUniform | null {",
        "  const t = TEAM_UNIFORMS[teamId];",
        "  return t ? t[kind] ?? t.home : null;",
        "}",
        "",
        "/** PlayerSprite props for a uniform: <PlayerSprite colors={c.colors} outfit={c.outfit} ... /> */",
        "export function uniformSprite(u: TeamUniform): { colors: JerseyColors; outfit: Outfit } {",
        "  return {",
        "    colors: { jersey: u.jersey, trim: u.trim, pattern: u.pattern, accent: u.accent, accent2: u.accent2 },",
        "    outfit: { shorts: { color: u.shorts } },",
        "  };",
        "}",
        "",
        "/** Jersey card art, front and back side by side (512 x 320). */",
        "export const UNIFORM_CARDS: Record<string, Record<UniformKind, ImageSourcePropType>> = {",
    ]
    for tid in data:
        lines.append("  %s: {" % json.dumps(tid))
        for k in KINDS:
            lines.append("    %s: require('./png/%s_%s.png')," % (k, tid, k))
        lines.append("  },")
    lines += ["};", ""]
    with open(os.path.join(OUT, "index.ts"), "w") as f:
        f.write("\n".join(lines))


def write_sprite_preview(data):
    """previews/uniform_sprites.png: every team's three uniforms on court,
    composited from the built sprite atlas (run generate_sprites.py first)."""
    rn = g.RN_DIR
    meta = json.load(open(os.path.join(rn, "spriteData.json")))
    if "uniformPatterns" not in meta:
        print("sprite data has no uniform patterns yet; skipping the sprite preview")
        return
    bodies = {g.MID_BODY: json.load(open(os.path.join(rn, "bodies", g.MID_BODY + ".json")))}
    pages = [Image.open(os.path.join(rn, "atlas", "page%d.png" % i)).convert("RGBA")
             for i in range(len(meta["pages"]))]
    comp = g.Compositor(meta, bodies, pages)
    skins = ["#8d5a3b", "#c68a5e", "#5a3a28"]
    cells = []
    for n, (tid, kinds) in enumerate(data.items()):
        for k in KINDS:
            u = kinds[k]
            img = comp.frame(g.MID_BODY, "idle", 0,
                             {"skin": skins[n % 3], "hair": ["crew", "afro", "fade"][n % 3], "facial": None,
                              "hairColor": "#1a1618", "outfit": {"shorts": u["shorts"]}},
                             {"jersey": u["jersey"], "trim": u["trim"], "pattern": u["pattern"],
                              "accent": u["accent"], "accent2": u["accent2"]})
            cells.append(img.crop(img.getbbox()))
    cw, ch = max(c.width for c in cells) + 12, max(c.height for c in cells) + 8
    for i, c in enumerate(cells):                                    # same size, feet on one line
        cell = Image.new("RGBA", (cw, ch), (226, 228, 236, 255))
        cell.alpha_composite(c, ((cw - c.width) // 2, ch - 4 - c.height))
        cells[i] = cell
    cols = 15                                                         # five teams per row
    sheet = Image.new("RGBA", (cw * cols, ch * ((len(cells) + cols - 1) // cols)), (255, 255, 255, 255))
    for i, c in enumerate(cells):
        sheet.alpha_composite(c, ((i % cols) * cw, (i // cols) * ch))
    sheet.save(os.path.join(g.PREVIEW_DIR, "uniform_sprites.png"))


def main():
    data = uniforms()
    shutil.rmtree(os.path.join(OUT, "png"), ignore_errors=True)       # keeps uniforms.test.ts
    os.makedirs(os.path.join(OUT, "png"))
    teams = {t[0]: t for t in lg.TEAMS}
    cards = []
    for n, (tid, kinds) in enumerate(data.items()):
        for k in KINDS:
            img = card(teams[tid], kinds[k], (n * 7 + 3) % 50 + 1)
            img.save(os.path.join(OUT, "png", "%s_%s.png" % (tid, k)), optimize=True)
            cards.append((tid, k, kinds[k]["name"], img))
    with open(os.path.join(OUT, "uniforms.json"), "w") as f:
        json.dump(data, f, indent=2)
    write_ts(data)
    # preview: one row per team, home / away / city
    cw, ch = 256, 160
    sheet = Image.new("RGB", (cw * 3 + 70, ch * len(data)), (236, 236, 242))
    d = ImageDraw.Draw(sheet)
    for i, (tid, k, name, img) in enumerate(cards):
        r, c = i // 3, i % 3
        sheet.paste(img.resize((cw, ch), Image.NEAREST), (70 + c * cw, r * ch), img.resize((cw, ch), Image.NEAREST))
        d.text((70 + c * cw + 4, r * ch + 2), "%s %s" % (k, "" if k != "city" else "- " + name), fill=(40, 40, 50))
        if c == 0:
            d.text((6, r * ch + ch // 2 - 6), tid, fill=(40, 40, 50))
    sheet.save(os.path.join(g.PREVIEW_DIR, "uniforms.png"))
    write_sprite_preview(data)
    print("wrote", OUT, len(cards), "cards")


if __name__ == "__main__":
    main()
