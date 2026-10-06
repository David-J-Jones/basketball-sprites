#!/usr/bin/env python3
"""Google Play feature graphic (1024 x 500), matching the app icon.

The icon's dunker (afro, headband, red and gold) throws it down while a
defender in blue leaps in a step too late, over the same purple sunburst,
with a hardwood floor. Drawn on a 128 x 63 art-pixel canvas and upscaled 8x
with nearest-neighbour, then trimmed to 500 px tall.

Writes integration/react-native/appIcon/feature-graphic.png and
previews/feature_graphic.png (with Play's safe-area guides).
"""
import math
import os
import sys

from PIL import Image, ImageDraw

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import generate_app_icon as icon  # noqa: E402
import generate_sprites as g  # noqa: E402

W, H, PX = 128, 63, 8           # canvas in art pixels, screen px per art pixel
OUT_W, OUT_H = 1024, 500
FLOOR_Y = 55                    # first floor row

DUNKER = dict(icon.COLORS)      # same look as the icon
DEFENDER = dict(DUNKER, skin=(96, 60, 40), jersey=(44, 95, 214), trim=(242, 242, 246), shorts=(28, 40, 92),
                shoe=(242, 242, 246), sole=(28, 30, 40), headwear=(242, 242, 246))
WOOD, WOOD_DARK, WOOD_LIGHT, COURT_LINE = (196, 132, 74), (160, 102, 54), (222, 162, 100), (246, 240, 228)


def colorize(grid, palette):
    out = {}
    for p, tag in grid.items():
        base = g.split_tag(tag)[0]
        if base in g.FIXED:
            out[p] = g.FIXED[base][:3]
            continue
        slot, shade, _ = g.TINTED[base]
        c = palette[slot]
        if shade:
            k = shade[3] / 255
            c = tuple(int(c[i] * (1 - k) + shade[i] * k) for i in range(3))
        out[p] = c
    return out


def player(pose, palette, hair, facial, headwear, body):
    g.use_body(body)
    _, stand = g.render(g.STAND_POSE, "crew")
    grid, info = g.render(pose, hair, stand["hip"][1], facial)
    grid = info["restyle"](hair, facial, headwear)
    return colorize(grid, palette), info


def background(img, cx, cy):
    """The icon's sunburst, stretched across the wide canvas."""
    d = img.load()
    for y in range(H):
        for x in range(W):
            dx, dy = x + 0.5 - cx, y + 0.5 - cy
            ang = math.atan2(dy, dx) + math.pi
            ray = int(ang / (2 * math.pi) * 22) % 2 == 0
            far = math.hypot(dx, dy) > 70
            d[x, y] = (icon.BG_MID if ray else icon.BG_DARK) if far else (icon.RAY if ray else icon.BG_MID)


def glow(img, cx, cy):
    """The icon's warm burst behind the ball, on the wide canvas."""
    rings = [(4.5, (255, 226, 140)), (7.5, (255, 176, 76)), (10.5, (232, 104, 70)), (13, (150, 60, 120))]
    for y in range(H):
        for x in range(W):
            r = math.hypot(x + 0.5 - cx, y + 0.5 - cy)
            for rr, col in rings:
                if r < rr:
                    img.putpixel((x, y), col + (255,))
                    break


def floor(img):
    d = ImageDraw.Draw(img)
    d.rectangle((0, FLOOR_Y, W, H), fill=WOOD)
    d.line((0, FLOOR_Y, W, FLOOR_Y), fill=WOOD_LIGHT)
    for y in range(FLOOR_Y + 2, H, 3):                       # plank rows, staggered seams
        d.line((0, y, W, y), fill=WOOD_DARK)
        for x in range((y * 7) % 13, W, 13):
            img.putpixel((x, y - 1), WOOD_DARK)
    d.line((0, FLOOR_Y + 4, W, FLOOR_Y + 4), fill=COURT_LINE)  # baseline paint


def shadow(img, cx, w):
    for x in range(int(cx - w), int(cx + w) + 1):
        for y in (FLOOR_Y + 1, FLOOR_Y + 2):
            if 0 <= x < W and (abs(x - cx) < w - 1 or y == FLOOR_Y + 1):
                c = img.getpixel((x, y))
                img.putpixel((x, y), tuple(int(v * 0.6) for v in c[:3]) + (255,))


def blit(img, px, ox, oy):
    for (x, y), c in px.items():
        if 0 <= x + ox < W and 0 <= y + oy < FLOOR_Y + 3:
            img.putpixel((x + ox, y + oy), c + (255,))


def compose():
    img = Image.new("RGBA", (W, H), (0, 0, 0, 255))
    dunk_px, dunk = player(icon.POSE, DUNKER, icon.HAIR, "goatee", "headband", "h5-lean")
    ball_px = icon.render_player()[0]                         # icon player incl. ball, same pose/body
    xs = [x for x, _ in ball_px]
    ys = [y for _, y in ball_px]
    ox = 78 - (min(xs) + max(xs)) // 2                        # dunker right of centre
    oy = FLOOR_Y - 3 - max(ys)                                # in the air above the floor
    bx, by = dunk["ball"][0] + ox, dunk["ball"][1] + oy
    background(img, bx, by)
    glow(img, bx, by)
    floor(img)
    rim_y, rim_x0 = int(by + 5), int(bx - 5)
    # hoop: same drawing as the icon, pole down to the floor
    icon.hoop(img, rim_y, rim_x0)
    d = ImageDraw.Draw(img)
    d.rectangle((rim_x0 + 16, FLOOR_Y, rim_x0 + 17, H), fill=icon.POLE)
    # defender: a block attempt from behind, a beat late
    block = g.block_frames()[3]
    def_px, _ = player(block, DEFENDER, "fade", None, None, "h6-average")
    dxs = [x for x, _ in def_px]
    dys = [y for _, y in def_px]
    dox = 46 - (min(dxs) + max(dxs)) // 2
    doy = max(FLOOR_Y - 2 - max(dys), 2 - min(dys))           # keep his hands in frame
    shadow(img, 46, 6)
    shadow(img, 78, 7)
    blit(img, def_px, dox, doy)
    blit(img, ball_px, ox, oy)
    # speed lines and rim sparks, like the icon
    for i, (y, x0, ln) in enumerate([(14, 8, 12), (20, 3, 16), (27, 10, 9), (33, 4, 14), (40, 12, 8)]):
        for x in range(x0, x0 + ln):
            if (x + i) % 6 != 0:
                img.putpixel((x, y), (255, 255, 255, 255))
    for sx, sy in ((rim_x0 - 3, rim_y - 3), (rim_x0 - 4, rim_y + 3), (rim_x0 + 2, rim_y - 6), (rim_x0 + 6, rim_y - 4)):
        for ddx, ddy in ((0, 0), (1, 0), (-1, 0), (0, 1), (0, -1)):
            img.putpixel((sx + ddx, sy + ddy), (255, 236, 150, 255) if (ddx, ddy) == (0, 0) else (255, 206, 64, 255))
    return img


def main():
    art = compose()
    big = art.resize((W * PX, H * PX), Image.NEAREST).convert("RGB")
    out = big.crop((0, 0, OUT_W, OUT_H))                      # trim the bottom floor rows to 500
    os.makedirs(icon.OUT_DIR, exist_ok=True)
    path = os.path.join(icon.OUT_DIR, "feature-graphic.png")
    out.save(path, optimize=True)
    # preview with the area Play may cover/crop marked
    prev = out.copy()
    d = ImageDraw.Draw(prev)
    d.rectangle((OUT_W * 0.15, OUT_H * 0.15, OUT_W * 0.85, OUT_H * 0.85), outline=(255, 255, 255))
    prev.save(os.path.join(g.PREVIEW_DIR, "feature_graphic.png"))
    print("wrote", path, out.size, "%.0f KB" % (os.path.getsize(path) / 1024))


if __name__ == "__main__":
    main()
