#!/usr/bin/env python3
"""Move showcases drawn from the built atlas, with the movement effects:

  previews/crossover_showcase.gif  every hand-switch / fake move against a
                                   defender who bites the wrong way
  previews/drive_showcase.gif      a full drive: hesitation, killer cross,
                                   a tomahawk at the rim, the landing puff

Effects fire on the same frames as MoveFxEmitter (moveFx/moveFx.ts). Run
generate_sprites.py and generate_move_fx.py first.

Run:  python3 tools/preview_moves.py
"""
import os
import sys

from PIL import Image, ImageDraw

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import preview_movement as pm  # noqa: E402

A, S, PX, DT, FW, FH, FX = pm.ANIMS, pm.S, pm.PX_PER_FT, pm.DT, pm.FW, pm.FH, pm.FX
STRIDE_PUSH = (4, 10)
PALETTES = {                                         # same as SWISH_PALETTES in moveFx.ts
    "electric": ["#ffffff", "#3be8f0", "#7a5cff", "#ff4fb3"],
    "fire": ["#fff3c0", "#ffd23f", "#ff8c2a", "#e8321e"],
    "rainbow": ["#ffffff", "#ffd23f", "#5ce05c", "#3bb8f0", "#8e44e8", "#ff3e7a"],
    "ice": ["#ffffff", "#bde3f5", "#6ec6f0", "#2a6fdb"],
}
SWISH_LIFE, SWISH_W = 0.3, 5


def palette_at(pal, u):
    u = max(0.0, min(1.0, u)) * (len(pal) - 1)
    i = min(len(pal) - 2, int(u))
    t = u - i
    a, b = [tuple(int(c.lstrip("#")[k:k + 2], 16) for k in (0, 2, 4)) for c in (pal[i], pal[i + 1])]
    return tuple(round(x + (y - x) * t) for x, y in zip(a, b))


def is_dribble_move(anim):
    return anim.startswith(("crossover", "behind_back", "between_legs", "inside_out"))


def cross_frames(anim):
    ev = A[anim]["events"]
    return [ev[k] for k in ("cross", "cross2", "cross3", "fake") if k in ev] if is_dribble_move(anim) else []
MOVES_WITH_BURST = ("crossover", "hesitation", "inside_out", "behind_back", "between_legs")


def dur(anim):
    return A[anim]["frameCount"] / A[anim]["fps"]


def cut_frame(anim):
    ev = A[anim]["events"]
    return ev.get("cutStart", ev.get("burst", 0))


class Actor:
    """One player. script(t) -> (anim, speed ft/s, vy ft/s, facing, one_shot)."""

    def __init__(self, look, colors, script, x=0.0, y=0.0, facing=1, lines=False, z_fn=None):
        self.look, self.colors, self.script = look, colors, script
        self.z_fn, self.z = z_fn, 0.0         # jump height the sim adds on top of the baked-in hop
        self.palette = PALETTES["electric"]
        self.rim = None                        # world (x, y) of the rim, for the dunk splash
        self.swish = []                        # [world x, world y, age] (BallSwish in moveFx.ts)
        self.ball_hist = []
        self.x, self.y, self.facing = x, y, facing
        self.stride = 0.0
        self.shot = None
        self.last = (None, -1)
        self.lines_on, self.lines, self.lines_t = lines, 0.0, 0.0
        self.out = None

    def step(self, t, fx):
        anim, speed, vy, facing, one_shot = self.script(t)
        self.z = self.z_fn(t) if self.z_fn else 0.0
        a = A[anim]
        n = a["frameCount"]
        if one_shot:
            if not self.shot or self.shot[0] != anim:
                self.shot = (anim, t)
            fi = min(int((t - self.shot[1]) * a["fps"] + 1e-6), n - 1)
        else:
            self.shot = None
            rate = a["fps"] * (max(speed, 0.1) / 14 if n == 12 and anim != "walk" else 1)
            self.stride += DT * rate
            fi = int(self.stride) % n
        self.facing = facing
        self.x += facing * speed * PX * DT
        self.y += vy * PX * DT
        flip = facing < 0
        prev, pf = self.last
        if anim != prev:
            frames = [fi]
        elif fi > pf:
            frames = list(range(pf + 1, fi + 1))
        elif fi < pf and a["loop"]:
            frames = list(range(pf + 1, n)) + list(range(0, fi + 1))
        else:
            frames = []
        stride = n == 12 and anim.startswith(("run", "dribble_run")) and anim not in ("run_start", "run_stop")
        if anim != prev and anim in ("run_stop", "turn_run", "turn_dribble"):
            fx.append(["dust_skid", self.x + facing * 2 * S, self.y, 0.0, flip])
        ev = a["events"]
        for f in frames:
            if stride and speed >= 9 and f in STRIDE_PUSH:
                fx.append(["dust_step", self.x - facing * 2 * S, self.y, 0.0, flip])
            if anim.startswith(MOVES_WITH_BURST) and f == cut_frame(anim):
                fx.append(["cut_burst", self.x - facing * S, self.y, 0.0, flip])
            if ("takeoff" in ev or "rise" in ev) and f == n - 1:
                fx.append(["land_puff", self.x, self.y, 0.0, flip])
        img, ball, depth = pm.sprite(anim, fi, self.look, self.colors, flip)
        bw = None
        if ball:
            bw = (self.x - FW / 2 + ball[0], -FH + ball[1] + depth * 4 * S - self.z)
        for f in frames:
            if anim.startswith("dunk_") and f == ev.get("dunk"):
                sx, sy = self.rim if self.rim else (bw or (self.x, -58 * S))
                fx.append(["dunk_splash", sx, sy, 0.0, flip])            # centred on the rim
            if f in cross_frames(anim) and bw:
                fx.append(["cross_swoosh", bw[0], bw[1] + FX["cross_swoosh"]["anchor"][1] * S - 6, 0.0, flip])
        for p in self.swish:
            p[2] += DT
        self.swish = [p for p in self.swish if p[2] < SWISH_LIFE]
        if is_dribble_move(anim) and bw:
            if not self.ball_hist or abs(bw[0] - self.ball_hist[-1][0]) + abs(bw[1] - self.ball_hist[-1][1]) > 0.5:
                if self.ball_hist:                       # Catmull-Rom in-betweens, as in BallSwish
                    p1 = self.ball_hist[-1]
                    p0 = self.ball_hist[-2] if len(self.ball_hist) > 1 else p1
                    p2 = bw
                    for i in range(1, 4):
                        u = i / 4
                        c = [0.5 * (2 * p1[k] + (-p0[k] + p2[k]) * u + (2 * p0[k] - 5 * p1[k] + 3 * p2[k]) * u * u
                                    + (-p0[k] + 3 * p1[k] - 2 * p2[k]) * u ** 3) for k in (0, 1)]
                        self.swish.append([c[0], c[1], DT * (1 - u)])
                self.swish.append([bw[0], bw[1], 0.0])
                self.ball_hist = (self.ball_hist + [bw])[-2:]
        else:
            self.ball_hist = []
        self.last = (anim, fi)
        fast = self.lines_on and stride and (speed > 14 if self.lines > 0 else speed >= 17)
        self.lines = max(0.0, min(1.0, self.lines + (6 if fast else -4) * DT))
        self.lines_t += DT
        self.out = (anim, fi, img, ball, depth, flip, speed)
        return self.out


class Scene:
    def __init__(self, w, h, actors, label, follow=0, hoop=None):
        self.w, self.h, self.actors, self.label, self.follow = w, h, actors, label, follow
        self.fx = []
        self.cam = actors[follow].x
        self.hoop = hoop            # (rim world x, rim screen-y offset above the floor)
        self.loose = None           # ball dropping through the net: [x, y, vy]

    def step(self, t):
        for e in self.fx:
            e[3] += DT
        self.fx = [e for e in self.fx if e[3] < FX[e[0]]["frames"] / FX[e[0]]["fps"]]
        for a in self.actors:
            a.step(t, self.fx)
        target = self.actors[self.follow].x
        if self.hoop:
            target = min(target, self.hoop[0] - self.w * 0.22)
        self.cam += (target - self.cam) * 0.3

    def render(self, caption=""):
        img = Image.new("RGBA", (self.w, self.h), (176, 124, 72, 255))
        d = ImageDraw.Draw(img)
        floor = self.h - 46
        ox = self.w / 2 - self.cam
        for k in range(-2, 40):
            x = (k * 90 + ox) % (self.w + 180) - 90
            d.line([(x, floor - 130), (x - 40, self.h)], fill=(160, 110, 60), width=2)
        x = (ox % 1400) - 300
        d.line([(x, floor - 130), (x - 40, self.h)], fill=(245, 240, 225), width=5)
        d.line([(0, floor - 130), (self.w, floor - 130)], fill=(150, 100, 55), width=2)
        if self.hoop:                                           # backboard and stanchion, behind everyone
            rx, ry = self.hoop[0] + ox, floor - self.hoop[1]
            d.rectangle([rx + 26, ry + 6, rx + 36, floor - 60], fill=(70, 70, 80))
            d.rectangle([rx + 30, floor - 64, rx + 70, floor - 54], fill=(70, 70, 80))
            d.rectangle([rx + 18, ry - 96, rx + 26, ry + 12], fill=(240, 240, 245), outline=(30, 30, 40), width=3)
        for e in self.fx:
            m = FX[e[0]]
            f = min(int(e[3] * m["fps"]), m["frames"] - 1)
            im = pm.fx_img(e[0], f, e[4])
            ax = (m["width"] - m["anchor"][0]) if e[4] else m["anchor"][0]
            img.alpha_composite(im, (int(e[1] + ox - ax * S), int(floor + e[2] - m["anchor"][1] * S)))
        for a in sorted(self.actors, key=lambda a: a.y):        # farther (up the screen) first
            anim, fi, im, ball, depth, flip, speed = a.out
            px, py = a.x + ox, floor + a.y
            if a.lines > 0:
                m = FX["speed_lines"]
                li = pm.fx_img("speed_lines", int(a.lines_t * m["fps"]) % m["frames"], flip)
                li.putalpha(li.getchannel("A").point(lambda v, k=a.lines: int(v * k)))
                ax = (m["width"] - m["anchor"][0]) if flip else m["anchor"][0]
                img.alpha_composite(li, (int(px - (-1 if flip else 1) * 5 * S - ax * S),
                                         int(py - 26 * S - m["anchor"][1] * S)))
            tl = (int(px - FW / 2), int(py - FH - a.z))
            if ball and depth < 0:
                pm.draw_ball(img, tl[0] + ball[0], tl[1] + ball[1] + depth * 4 * S)
            img.alpha_composite(im, tl)
            if ball and depth >= 0:
                pm.draw_ball(img, tl[0] + ball[0], tl[1] + ball[1] + depth * 4 * S)
        for a in self.actors:                                   # swishes over everyone, so the cross reads
            if len(a.swish) > 1:                                 # the swish, over the body, under the ball
                layer = Image.new("RGBA", img.size, (0, 0, 0, 0))
                ld = ImageDraw.Draw(layer)
                for p, q in zip(a.swish, a.swish[1:]):
                    k = 1 - q[2] / SWISH_LIFE
                    if k <= 0:
                        continue
                    col = palette_at(a.palette, 1 - k) + (int(255 * 0.9 * min(1, k * 1.4)),)
                    w = max(2, int(SWISH_W * S * k))
                    ld.line([(p[0] + ox, floor + p[1]), (q[0] + ox, floor + q[1])], fill=col, width=w)
                    ld.ellipse([q[0] + ox - w / 2, floor + q[1] - w / 2, q[0] + ox + w / 2, floor + q[1] + w / 2], fill=col)
                img.alpha_composite(layer)
                anim, fi, im, ball, depth, flip, speed = a.out
                if ball and depth >= 0:                          # the ball rides on the head of its streak
                    pm.draw_ball(img, a.x + ox - FW / 2 + ball[0], floor + a.y - FH - a.z + ball[1] + depth * 4 * S)
        if self.hoop:                                           # rim and net in front of the dunker's hand
            rx, ry = self.hoop[0] + ox, floor - self.hoop[1]
            if self.loose:
                pm.draw_ball(img, self.loose[0] + ox, self.loose[1])
            for k in range(5):
                d.line([(rx - 22 + k * 11, ry), (rx - 14 + k * 7, ry + 34)], fill=(250, 250, 250), width=2)
            d.line([(rx - 16, ry + 17), (rx + 16, ry + 17)], fill=(250, 250, 250), width=2)
            d.ellipse([rx - 26, ry - 6, rx + 26, ry + 6], outline=(232, 92, 30), width=5)
        d.rectangle([0, 0, self.w, 26], fill=(20, 16, 30, 210))
        d.text((10, 7), self.label + ("   " + caption if caption else ""), fill=(255, 255, 255))
        return img


# ------------------------------------------------------------------ crossover cells
T0 = 0.55          # when the move starts
CELL_W, CELL_H = 400, 300
MOVES = [
    ("CLASSIC CROSSOVER", "crossover_up", True, "electric"),
    ("SNAP", "crossover_quick_up", True, "fire"),
    ("KILLER", "crossover_wide_up", True, "rainbow"),
    ("DOUBLE CROSS", "crossover_double_up", True, "electric"),
    ("HESI CROSS", "crossover_hesi_up", True, "ice"),
    ("INSIDE-OUT", "inside_out", False, "fire"),
    ("BEHIND THE BACK", "behind_back_up", True, "rainbow"),
    ("BETWEEN THE LEGS", "between_legs_up", True, "electric"),
]
LOOKS = [pm.look1, pm.look2, pm.look3, pm.look4]
KITS = [("PHX", "city"), ("MIA", "city"), ("CHI", "retro90"), ("BOS", "away"), ("ORL", "retro80"),
        ("LAC", "home"), ("NY", "retro70"), ("SF", "city")]


def offense_script(move, switches):
    d, cut = dur(move), cut_frame(move) / A[move]["fps"]

    def script(t):
        if t < T0:
            return "dribble_run", 11, 0, 1, False
        if t < T0 + d:
            after = t >= T0 + cut
            return move, 15 if after else 4, (-5 if after and switches else 0), 1, True
        return ("dribble_run_far" if switches else "dribble_run"), 16, (-2 if switches and t < T0 + d + 0.25 else 0), 1, False
    return script


def defender_script(move, switches):
    d = dur(move)
    bite = A[move]["events"].get("cross", A[move]["events"].get("fake", 2)) / A[move]["fps"]

    def script(t):
        if T0 + bite <= t < T0 + bite + 0.3:
            return "defense_slide", 0, (3 if switches else -3), -1, False        # bites the wrong way
        if t > T0 + d + 0.2:
            return "defense_stance", 0, 0, -1, False
        return ("guard_on_ball" if t < T0 + bite else "defense_stance"), 0, 0, -1, False
    return script


def crossover_showcase(out):
    length = max(T0 + dur(m) for _, m, _, _ in MOVES) + 1.0
    scenes = []
    for i, (label, move, sw, pal) in enumerate(MOVES):
        cols, shorts = pm.uni(*KITS[i])
        off = Actor(pm.with_shorts(LOOKS[i % 4], shorts), cols, offense_script(move, sw), x=0, y=10, lines=True)
        off.palette = PALETTES[pal]
        dcols, dshorts = pm.uni("DET", "home")
        dx = 11 * T0 * PX + 6.5 * PX
        dfn = Actor(pm.with_shorts(LOOKS[(i + 2) % 4], dshorts), dcols, defender_script(move, sw), x=dx, y=16,
                    facing=-1)
        scenes.append(Scene(CELL_W, CELL_H, [off, dfn], "%s   (%s swish)" % (label, pal)))
    frames = []
    for k in range(int(length / DT)):
        t = k * DT
        sheet = Image.new("RGB", (CELL_W * 2, CELL_H * 4), (0, 0, 0))
        for i, sc in enumerate(scenes):
            sc.step(t)
            sheet.paste(sc.render(), ((i % 2) * CELL_W, (i // 2) * CELL_H))
        frames.append(sheet)
    frames += [frames[-1]] * 8
    frames[0].save(out, save_all=True, append_images=frames[1:], duration=int(DT * 1000), loop=0, optimize=True)
    print(out, len(frames), os.path.getsize(out) // 1024, "KB")


# ------------------------------------------------------------------ the drive
def drive_plan():
    """(start, end, anim, speed, vy, one_shot) segments for the ball handler."""
    plan, t = [], 0.0

    def add(anim, length, speed, vy=0.0, one_shot=False):
        nonlocal t
        plan.append((t, t + length, anim, speed, vy, one_shot))
        t += length
    add("dribble_run", 0.7, 13)
    h = dur("hesitation")
    add("hesitation", cut_frame("hesitation") / A["hesitation"]["fps"], 5, one_shot=True)
    add("hesitation", h - cut_frame("hesitation") / A["hesitation"]["fps"], 16, one_shot=True)
    add("dribble_run", 0.3, 16)
    c = dur("crossover_wide_up")
    k = cut_frame("crossover_wide_up") / A["crossover_wide_up"]["fps"]
    add("crossover_wide_up", k, 6, one_shot=True)
    add("crossover_wide_up", c - k, 16, -5, one_shot=True)
    add("dribble_run_far", 0.55, 19)
    add("dunk_tomahawk", dur("dunk_tomahawk"), 7, one_shot=True)
    add("celebrate", dur("celebrate"), 0, one_shot=True)
    add("idle", 0.4, 0)
    return plan, t


def drive_showcase(out):
    plan, length = drive_plan()
    shots = {}

    def handler(t):
        for (a, b, anim, speed, vy, one) in plan:
            if a <= t < b:
                return anim, speed, vy, 1, one
        return "idle", 0, 0, 1, False

    dunk_at = next(a for (a, b, anim, *_r) in plan if anim == "dunk_tomahawk")
    up = A["dunk_tomahawk"]["events"]["takeoff"] / A["dunk_tomahawk"]["fps"]
    air = dur("dunk_tomahawk") - up

    def jump(t):                                   # a real jump arc from takeoff to landing
        u = (t - dunk_at - up) / air
        return 0.0 if not 0 < u < 1 else 2.6 * PX * 4 * u * (1 - u)

    cols, shorts = pm.uni("MIA", "city")
    # first pass: where is his hand on the dunk frame? the rim goes there
    probe = Actor(pm.with_shorts(pm.look3, shorts), cols, handler, y=10, z_fn=jump)
    t, rim = 0.0, None
    dunk_f = A["dunk_tomahawk"]["events"]["dunk"]
    while t < length and rim is None:
        probe.step(t, [])
        anim, fi = probe.out[0], probe.out[1]
        if anim == "dunk_tomahawk" and fi == dunk_f:
            rec = pm.G.frame_obj(pm.bodies, pm.BODY, anim, fi)
            hx, hy = rec["nearHand"]
            rim = (probe.x - FW / 2 + hx + 6, FH - hy - 4 - probe.y + probe.z)
        t += DT
    shots["rim"] = rim
    cross_at = next(a for (a, b, anim, *_r) in plan if anim == "crossover_wide_up")
    hesi_at = next(a for (a, b, anim, *_r) in plan if anim == "hesitation")
    off = Actor(pm.with_shorts(pm.look3, shorts), cols, handler, y=10, lines=True, z_fn=jump)
    off.rim = (rim[0], -rim[1])

    def on_ball(t):
        if hesi_at + 0.1 <= t < hesi_at + 0.35:
            return "defense_stance", 0, 0, -1, False                         # froze on the hesi
        if cross_at + 0.1 <= t < cross_at + 0.45:
            return "defense_slide", 0, 3, -1, False                          # bit on the jab
        return "guard_on_ball", 0, 0, -1, False

    def rim_protector(t):
        if dunk_at - 0.05 <= t < dunk_at - 0.05 + dur("block"):
            return "block", 0, 0, -1, True                                   # a step late
        if t >= dunk_at - 0.05 + dur("block"):
            return "frustrated", 0, 0, -1, True
        return "defense_stance", 0, 0, -1, False

    dc, ds = pm.uni("DET", "home")
    x_cross = sum((min(b, cross_at) - a) * sp * PX for (a, b, an, sp, vy, one) in plan if a < cross_at)
    d1 = Actor(pm.with_shorts(pm.look1, ds), dc, on_ball, x=x_cross + 3.5 * PX, y=16, facing=-1)
    d2 = Actor(pm.with_shorts(pm.look4, ds), dc, rim_protector, x=rim[0] + 0.4 * PX, y=-34, facing=-1,
               z_fn=lambda t: 0.0 if not 0 < t - dunk_at < dur("block") else 1.6 * PX * 4 * ((t - dunk_at) / dur("block"))
               * (1 - (t - dunk_at) / dur("block")))
    scene = Scene(980, 380, [off, d1, d2], "THE DRIVE: hesi, killer cross, tomahawk", hoop=rim)
    frames = []
    t = 0.0
    while t < length:
        scene.step(t)
        anim, fi = off.out[0], off.out[1]
        if anim == "dunk_tomahawk" and fi >= dunk_f and scene.loose is None:
            scene.loose = [rim[0], (scene.h - 46) - rim[1] + 10, 0.0]
        if scene.loose:
            floor_y = scene.h - 46 - pm.G.BALL_R * S
            scene.loose[2] += 2400 * DT
            scene.loose[1] += scene.loose[2] * DT
            if scene.loose[1] > floor_y:
                scene.loose[1], scene.loose[2] = floor_y, -scene.loose[2] * 0.55
        frames.append(scene.render(anim).convert("RGB"))
        t += DT
    frames += [frames[-1]] * 6
    frames[0].save(out, save_all=True, append_images=frames[1:], duration=int(DT * 1000), loop=0, optimize=True)
    print(out, len(frames), os.path.getsize(out) // 1024, "KB")


if __name__ == "__main__":
    crossover_showcase(os.path.join(pm.ROOT, "previews", "crossover_showcase.gif"))
    drive_showcase(os.path.join(pm.ROOT, "previews", "drive_showcase.gif"))
