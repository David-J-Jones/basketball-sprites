#!/usr/bin/env python3
"""App icon: a player sprite throwing down a dunk, in the same pixel art.

Drawn on a 64 x 64 art-pixel canvas and upscaled with nearest-neighbour so
the pixels stay crisp. Writes integration/react-native/appIcon/:
  icon.png                  1024 x 1024, full-bleed, no transparency (iOS / Expo `icon`)
  adaptive-foreground.png   1024 x 1024, transparent, art inside Android's safe zone
  adaptive-background.png   1024 x 1024, the background alone
  splash-icon.png           1024 x 1024, transparent player + hoop for a splash screen
  favicon.png               48 x 48 (web)
and previews/app_icon.png (the icon at several sizes, square and rounded).
"""
import math
import os
import sys

from PIL import Image, ImageDraw

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import generate_sprites as g  # noqa: E402

OUT_DIR = os.path.join(g.ROOT, "integration", "react-native", "appIcon")
N = 64                     # canvas, art pixels
ICON = 1024

COLORS = {                 # tint for each sprite slot
    "skin": (150, 96, 62), "jersey": (226, 52, 44), "trim": (255, 206, 64), "shorts": (240, 240, 244),
    "sock": (242, 242, 246), "shoe": (255, 206, 64), "sole": (40, 36, 48), "hair": (26, 22, 24),
    "facial": (26, 22, 24), "headwear": (255, 255, 255),
}
BG_DARK, BG_MID, RAY = (24, 20, 58), (48, 30, 104), (78, 44, 140)
RIM, RIM_SHADE, NET, NET_SHADE = (240, 96, 30), (176, 58, 20), (250, 250, 252), (180, 184, 204)
BOARD, BOARD_EDGE, POLE = (236, 240, 250), (40, 36, 60), (70, 72, 92)

# the icon pose: flying at the rim, legs trailing, near arm reaching up and
# over to stuff the ball; far arm swinging back for balance
HAIR = os.environ.get("ICON_HAIR", "afro")      # any sprite hair style
POSE = g.P((58, 10, 10), (-18, -70, 35), (132, 128), (-40, -20), lean=16, lift=14, reach=1.2, shrug=1,
           ball=("near", 2.5, -2.5))


def tag_color(tag):
    tag = g.split_tag(tag)[0]
    if tag in g.FIXED:
        return g.FIXED[tag][:3]
    slot, shade, _ = g.TINTED[tag]
    c = COLORS[slot]
    if shade:
        k = shade[3] / 255
        c = tuple(int(c[i] * (1 - k) + shade[i] * k) for i in range(3))
    return c


def render_player():
    g.use_body("h5-lean")
    _, stand = g.render(g.STAND_POSE, "crew")
    grid, info = g.render(POSE, HAIR, stand["hip"][1], "goatee")
    grid = info["restyle"](HAIR, "goatee", "headband")
    px = {p: tag_color(t) for p, t in grid.items()}
    ball = g.ball_layer((info["ball"][0], info["ball"][1]), 30)
    for src in (ball.outline(), ball.px):
        for p, c in src.items():
            px[p] = g.FIXED[c][:3] if isinstance(c, str) else c[:3]
    return px, info["ball"]


def background(img, cx=N / 2, cy=N / 2):
    """Retro sunburst: alternating rays around (cx, cy), darker toward the edges."""
    d = img.load()
    for y in range(N):
        for x in range(N):
            dx, dy = x + 0.5 - cx, y + 0.5 - cy
            ang = math.atan2(dy, dx) + math.pi
            ray = int(ang / (2 * math.pi) * 14) % 2 == 0
            far = math.hypot(dx, dy) > 46
            d[x, y] = (BG_MID if ray else BG_DARK) if far else (RAY if ray else BG_MID)


def glow(img, cx, cy):
    """Warm burst behind the ball as it goes through the rim."""
    rings = [(4.5, (255, 226, 140)), (7.5, (255, 176, 76)), (10.5, (232, 104, 70)), (13, (150, 60, 120))]
    for y in range(N):
        for x in range(N):
            r = math.hypot(x + 0.5 - cx, y + 0.5 - cy)
            for rr, col in rings:
                if r < rr:
                    img.putpixel((x, y), col + (255,))
                    break


def hoop(img, rim_y, rim_x0):
    """Side view: backboard and pole on the right, rim reaching left, net below."""
    dr = ImageDraw.Draw(img)
    bx = rim_x0 + 13
    dr.rectangle((bx + 3, rim_y + 2, bx + 4, N - 1), fill=POLE)                 # pole
    dr.rectangle((bx + 2, rim_y + 6, bx + 5, rim_y + 7), fill=POLE)             # support arm
    dr.rectangle((bx - 1, rim_y - 14, bx + 2, rim_y + 6), fill=BOARD_EDGE)      # backboard edge-on
    dr.rectangle((bx, rim_y - 13, bx + 1, rim_y + 5), fill=BOARD)
    dr.rectangle((rim_x0, rim_y, bx - 1, rim_y + 1), fill=RIM)                  # rim + bracket
    dr.line((rim_x0, rim_y + 1, bx - 1, rim_y + 1), fill=RIM_SHADE)
    for k in range(0, 7):                                                       # net
        y = rim_y + 2 + k
        inset = k // 2
        for x in range(rim_x0 + inset, bx - 1 - inset):
            if (x + k) % 2 == 0:
                img.putpixel((x, y), NET if k < 5 else NET_SHADE)


def compose(with_bg=True, fg_scale=1.0):
    img = Image.new("RGBA", (N, N), (0, 0, 0, 0))
    px, ball = render_player()
    xs = [x for x, _ in px]
    ys = [y for _, y in px]
    # place the player so the ball lands on the rim, centred in the canvas
    ox = 30 - (min(xs) + max(xs)) // 2 - 3
    oy = 58 - max(ys)
    bx, by = ball[0] + ox, ball[1] + oy
    if with_bg:
        background(img, bx, by)
    glow(img, bx, by)
    rim_y = int(by + 5)
    rim_x0 = int(bx - 5)
    hoop(img, rim_y, rim_x0)
    for (x, y), c in px.items():
        if 0 <= x + ox < N and 0 <= y + oy < N:
            img.putpixel((x + ox, y + oy), c + (255,))
    # speed lines behind the player
    for i, (y, x0, ln) in enumerate([(18, 6, 7), (24, 3, 9), (30, 5, 6), (36, 2, 8)]):
        for x in range(x0, x0 + ln):
            if (x + i) % 5 != 0:
                img.putpixel((x, y), (255, 255, 255, 200 if with_bg else 230))
    # net rattle sparks
    for sx, sy in ((rim_x0 - 3, rim_y - 3), (rim_x0 - 4, rim_y + 3), (rim_x0 + 2, rim_y - 6)):
        for dx, dy in ((0, 0), (1, 0), (-1, 0), (0, 1), (0, -1)):
            img.putpixel((sx + dx, sy + dy), (255, 236, 150, 255) if (dx, dy) == (0, 0) else (255, 206, 64, 220))
    return img


def up(img, size):
    return img.resize((size, size), Image.NEAREST)


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    full = compose()
    icon = up(full, ICON).convert("RGB")
    icon.save(os.path.join(OUT_DIR, "icon.png"))
    # Android adaptive icon: foreground art inside the central ~66% safe zone
    fg = compose(with_bg=False)
    safe = int(ICON * 0.62) // N * N                     # whole multiple of the canvas
    fg_big = up(fg, safe)
    fg_img = Image.new("RGBA", (ICON, ICON), (0, 0, 0, 0))
    fg_img.alpha_composite(fg_big, ((ICON - safe) // 2, (ICON - safe) // 2))
    fg_img.save(os.path.join(OUT_DIR, "adaptive-foreground.png"))
    bg = Image.new("RGBA", (N, N), (0, 0, 0, 0))
    background(bg)
    up(bg, ICON).convert("RGB").save(os.path.join(OUT_DIR, "adaptive-background.png"))
    up(fg, ICON).save(os.path.join(OUT_DIR, "splash-icon.png"))
    up(full, 64).resize((48, 48), Image.LANCZOS).convert("RGB").save(os.path.join(OUT_DIR, "favicon.png"))

    # preview: big square, rounded (iOS-style mask), adaptive circle, small sizes
    sheet = Image.new("RGB", (1320, 560), (236, 236, 242))
    big = up(full, 512).convert("RGB")
    sheet.paste(big, (20, 24))
    mask = Image.new("L", (256, 256), 0)
    ImageDraw.Draw(mask).rounded_rectangle((0, 0, 255, 255), radius=58, fill=255)
    sheet.paste(up(full, 256).convert("RGB"), (560, 24), mask)
    circ = Image.new("L", (256, 256), 0)
    ImageDraw.Draw(circ).ellipse((0, 0, 255, 255), fill=255)
    adaptive = Image.alpha_composite(up(bg, 256), up(fg_img, 256))
    # Android shows the middle 72/108 of the adaptive layers
    crop = int(256 * 18 / 108)
    adaptive = adaptive.crop((crop, crop, 256 - crop, 256 - crop)).resize((256, 256), Image.NEAREST)
    sheet.paste(adaptive.convert("RGB"), (840, 24), circ)
    x = 560
    for s in (120, 76, 60, 40, 29):
        m = Image.new("L", (s, s), 0)
        ImageDraw.Draw(m).rounded_rectangle((0, 0, s - 1, s - 1), radius=int(s * 0.225), fill=255)
        sheet.paste(icon.resize((s, s), Image.LANCZOS), (x, 330 + (120 - s)), m)
        x += s + 24
    d = ImageDraw.Draw(sheet)
    d.text((20, 6), "icon.png (1024, shown at 512)", fill=(40, 40, 50))
    d.text((560, 6), "iOS rounded", fill=(40, 40, 50))
    d.text((840, 6), "Android adaptive (circle mask)", fill=(40, 40, 50))
    d.text((560, 310), "home screen sizes", fill=(40, 40, 50))
    sheet.save(os.path.join(g.PREVIEW_DIR, "app_icon.png"))
    print("wrote", OUT_DIR)


if __name__ == "__main__":
    main()
