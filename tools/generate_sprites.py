#!/usr/bin/env python3
"""
Procedural pixel-art sprite generator for the basketball player + ball.

Everything is drawn at 1x resolution with hard pixels (no anti-aliasing),
then each body part gets a dark 1px outline, which gives the chunky
16-bit sports-game look.

Run:  python3 tools/generate_sprites.py
Outputs go to  sprites/  and  previews/.
"""
import json
import math
import os

from PIL import Image, ImageDraw

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT_DIR = os.path.join(ROOT, "sprites")
PREVIEW_DIR = os.path.join(ROOT, "previews")

FRAME_W, FRAME_H = 48, 64
GROUND = 61          # last row of shoe-sole pixels (outline sits on row 62)
HIP_X = 22           # player faces right, so sit a little left of centre

# ---------------------------------------------------------------- palette
OUTLINE = (28, 22, 32, 255)
PAL = {
    "skin":        (232, 178, 128, 255),
    "skin_shade":  (190, 128, 86, 255),
    "skin_dark":   (150, 96, 62, 255),
    "hair":        (104, 64, 34, 255),
    "hair_shade":  (68, 40, 22, 255),
    "eye":         (28, 22, 32, 255),
    "mouth":       (160, 92, 70, 255),
    "white":       (250, 250, 250, 255),
    "white_shade": (200, 204, 218, 255),
    "white_dark":  (156, 162, 182, 255),
    "trim":        (170, 176, 196, 255),
    "sole":        (72, 70, 82, 255),
    "ball":        (234, 116, 38, 255),
    "ball_light":  (252, 166, 92, 255),
    "ball_shade":  (178, 72, 24, 255),
    "ball_seam":   (58, 26, 14, 255),
}

SMEAR = (255, 255, 255, 150)   # swipe motion streak

LIGHT = (-0.6, -0.8)  # light from the upper-left

# ---------------------------------------------------------------- lengths
THIGH, SHIN = 8.0, 8.0
UPPER_ARM, FOREARM = 6.0, 6.0
SHOULDER_UP = 10.0    # hip -> shoulder along the torso
NECK_UP = 12.0        # hip -> base of head along the torso
BALL_R = 4.8
BALL_CELL = 11


def vec(deg, length=1.0):
    """Limb direction. 0 = straight down, 90 = forward (right), 180 = up."""
    r = math.radians(deg)
    return (math.sin(r) * length, math.cos(r) * length)


def add(a, b):
    return (a[0] + b[0], a[1] + b[1])


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
                d = math.hypot(ox, oy)
                if d <= r:
                    c = color_fn(t, ox / r, oy / r)
                    if c is not None:
                        self.px[(x, y)] = c

    def blit(self, template, origin, colors):
        ox, oy = origin
        for j, row in enumerate(template):
            for i, ch in enumerate(row):
                if ch != ".":
                    self.px[(ox + i, oy + j)] = colors[ch]

    def outline(self):
        out = {}
        for (x, y) in self.px:
            for nx, ny in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)):
                if (nx, ny) not in self.px:
                    out[(nx, ny)] = OUTLINE
        return out


def shaded(base, shade, thr=0.3, light=LIGHT):
    def fn(t, ox, oy):
        return shade if (ox * light[0] + oy * light[1]) < -thr else base
    return fn


# ---------------------------------------------------------------- head
HEAD = [
    "...hhhhh...",
    ".hhHHHHHhh.",
    "hhHHHHHHHHh",
    "hHHHHHHHHHH",
    "hhHHHHSSSSh",
    "hhhHSSSeeS.",
    "hhsSSSSESSS",
    "hhSsSSSESSS",
    ".hsSSSSSSS.",
    "..sSSSSSMS.",
    "..ssSSSSS..",
    "....sss....",
]
HEAD_ANCHOR = (5, 11)   # pixel of the template that sits on the neck point


def head_colors():
    return {
        "H": PAL["hair"], "h": PAL["hair_shade"], "S": PAL["skin"],
        "s": PAL["skin_shade"], "E": PAL["eye"], "e": PAL["hair_shade"],
        "M": PAL["mouth"],
    }


# ---------------------------------------------------------------- ball
def ball_layer(center, rot_deg=0.0, squash=0.0):
    """Shaded basketball with seams. rot_deg spins the seams around the ball
    (the pattern repeats every 180 degrees).
    squash > 0 flattens it (ground contact)."""
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
            # spin the seam pattern about the vertical axis, then tip it
            # toward the camera a little so the top seam is visible
            u = nx * math.cos(th) + nz * math.sin(th)
            w = -nx * math.sin(th) + nz * math.cos(th)
            v = ny
            v, w = v * math.cos(tilt_x) - w * math.sin(tilt_x), v * math.sin(tilt_x) + w * math.cos(tilt_x)
            # two great-circle seams + the two curved side seams
            seam = abs(u) < 0.12 or abs(v) < 0.12 or abs(abs(u) - 0.66 - 0.3 * v * v) < 0.07
            if seam and d2 < 0.9:
                c = PAL["ball_seam"]
            elif light > 0.72:
                c = PAL["ball_light"]
            elif light > 0.12:
                c = PAL["ball"]
            else:
                c = PAL["ball_shade"]
            layer.px[(x, y)] = c
    return layer


# ---------------------------------------------------------------- body
def limb_colors(far):
    if far:
        return PAL["skin_shade"], PAL["skin_dark"], PAL["white_shade"], PAL["white_dark"]
    return PAL["skin"], PAL["skin_shade"], PAL["white"], PAL["white_shade"]


def draw_leg(layer, hip, thigh_deg, shin_deg, foot_rot, far):
    skin, skin_s, cloth, cloth_s = limb_colors(far)
    knee = add(hip, vec(thigh_deg, THIGH))
    ankle = add(knee, vec(shin_deg, SHIN))
    # shin + sock
    def shin_fn(t, ox, oy):
        if t > 0.62:
            return cloth_s if (ox * LIGHT[0] + oy * LIGHT[1]) < -0.4 else cloth
        return skin_s if (ox * LIGHT[0] + oy * LIGHT[1]) < -0.3 else skin
    layer.capsule(knee, ankle, 1.6, shin_fn)
    # thigh; top part covered by shorts
    def thigh_fn(t, ox, oy):
        if t < 0.55:
            return cloth_s if (ox * LIGHT[0] + oy * LIGHT[1]) < -0.2 else cloth
        return skin_s if (ox * LIGHT[0] + oy * LIGHT[1]) < -0.3 else skin
    layer.capsule(hip, knee, 2.1, thigh_fn)
    # shorts leg opening is a touch wider than the thigh
    layer.capsule(hip, add(hip, vec(thigh_deg, THIGH * 0.5)), 2.7,
                  shaded(cloth, cloth_s, 0.2))
    # shoe
    fr = math.radians(foot_rot)
    fwd = (math.cos(fr), math.sin(fr))
    down = (-math.sin(fr), math.cos(fr))
    base = add(ankle, (down[0] * 1.2, down[1] * 1.2))
    heel = add(base, (-fwd[0] * 1.5, -fwd[1] * 1.5))
    toe = add(base, (fwd[0] * 3.2, fwd[1] * 3.2))
    upper = PAL["white_shade"] if far else PAL["white"]
    def shoe_fn(t, ox, oy):
        side = ox * down[0] + oy * down[1]
        if side > 0.35:
            return PAL["sole"]
        if side < -0.5 and t < 0.5:
            return PAL["white_dark"] if far else PAL["trim"]
        return upper
    layer.capsule(heel, toe, 1.55, shoe_fn)
    return ankle


def arm_points(shoulder, upper_deg, fore_deg, reach=1.0):
    elbow = add(shoulder, vec(upper_deg, UPPER_ARM * reach))
    return elbow, add(elbow, vec(fore_deg, FOREARM * reach))


def draw_arm(layer, shoulder, upper_deg, fore_deg, far, reach=1.0):
    skin, skin_s, _, _ = limb_colors(far)
    elbow, hand = arm_points(shoulder, upper_deg, fore_deg, reach)
    layer.capsule(shoulder, elbow, 1.5, shaded(skin, skin_s, 0.3))
    layer.capsule(elbow, hand, 1.35, shaded(skin, skin_s, 0.3))
    layer.capsule(hand, hand, 1.7, shaded(skin, skin_s, 0.5))
    return hand


def render(pose, with_ball=True, stand_hip_y=None):
    """Render one pose to a FRAME_W x FRAME_H RGBA image.
    Returns (image, info) where info has the hip / ball / hand positions."""
    lean = pose.get("lean", 8)
    hip = (HIP_X + pose.get("dx", 0), 100.0)
    tdir = vec(180 - lean)  # up the torso; positive lean tips it forward
    # 'shrug' raises the shoulders, e.g. when both arms reach overhead
    shoulder_up = SHOULDER_UP + pose.get("shrug", 0)
    shoulder = add(hip, (tdir[0] * shoulder_up, tdir[1] * shoulder_up))
    neck = add(hip, (tdir[0] * NECK_UP, tdir[1] * NECK_UP))

    far_leg, near_leg, body = Layer(), Layer(), Layer()
    far_arm, near_arm, head = Layer(), Layer(), Layer()

    fl = pose["far_leg"]
    nl = pose["near_leg"]
    draw_leg(far_leg, add(hip, (-0.5, 0)), fl[0], fl[1], fl[2] if len(fl) > 2 else 0, True)
    draw_leg(near_leg, add(hip, (0.5, 0)), nl[0], nl[1], nl[2] if len(nl) > 2 else 0, False)

    # torso: jersey + shorts waist
    chest_lo = add(hip, (tdir[0] * 3.0, tdir[1] * 3.0))
    chest_hi = add(hip, (tdir[0] * 9.0, tdir[1] * 9.0))

    def jersey_fn(t, ox, oy):
        side = ox * LIGHT[0] + oy * LIGHT[1]
        # arm-hole / collar trim near the top of the jersey
        if t > 0.93 and abs(ox) < 0.45:
            return PAL["trim"]
        if side < -0.35:
            return PAL["white_shade"]
        return PAL["white"]
    body.capsule(chest_lo, chest_hi, 3.7, jersey_fn)
    body.capsule(add(hip, (0, -0.5)), add(hip, (tdir[0] * 2.5, tdir[1] * 2.5)), 3.9,
                 lambda t, ox, oy: PAL["trim"] if 0.72 < t <= 1.0 and abs(ox) < 0.95 and oy < -0.1
                 else (PAL["white_shade"] if (ox * LIGHT[0] + oy * LIGHT[1]) < -0.35 else PAL["white"]))
    # shoulder strap bump
    body.capsule(shoulder, add(shoulder, (tdir[0] * 1.2, tdir[1] * 1.2)), 2.0,
                 lambda t, ox, oy: PAL["white"])
    # neck + head
    head.capsule(add(neck, (tdir[0] * -1.5, tdir[1] * -1.5)), neck, 1.6,
                 shaded(PAL["skin"], PAL["skin_shade"], 0.1))
    hx = int(round(neck[0])) - HEAD_ANCHOR[0] + pose.get("head_dx", 0)
    hy = int(round(neck[1])) - HEAD_ANCHOR[1] + pose.get("head_dy", 0)
    head.blit(HEAD, (hx, hy), head_colors())

    fa = pose["far_arm"]
    na = pose["near_arm"]
    reach = pose.get("reach", 1.0)
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
                    smear[(int(x + ox - 0.5), int(y + oy - 0.5))] = SMEAR

    ball = None
    ball_center = None
    if pose.get("ball"):
        b = pose["ball"]
        kind = b[0]
        if kind == "near":
            ball_center = add(near_hand, (b[1], b[2]))
        elif kind == "far":
            ball_center = add(far_hand, (b[1], b[2]))
        elif kind == "hip":
            ball_center = add(hip, (b[1], b[2]))
        elif kind == "ground":   # x relative to hip, sits on the floor
            ball_center = (hip[0] + b[1], None)
        ball = (ball_center, b[3] if len(b) > 3 else 0, b[4] if len(b) > 4 else 0)

    # --- vertical placement
    legs_bottom = max(y for (_, y) in list(far_leg.px) + list(near_leg.px))
    if "lift" in pose and stand_hip_y is not None:
        dy = (stand_hip_y - pose["lift"]) - hip[1]
    else:
        dy = GROUND - legs_bottom
    dy = int(round(dy)) + pose.get("bob", 0)

    if ball is not None:
        (bx, by), rot, squash = ball
        if by is None:
            by = GROUND - dy + 0.5 - BALL_R * (1 - 0.22 * squash)
        bx, by = math.floor(bx) + 0.5, math.floor(by) + 0.5
        ball = ball_layer((bx, by), rot, squash)
        ball_center = (bx, by)

    if pose.get("arms_behind_head"):
        # arms straight up would hide the face, so tuck them behind the head
        order = [far_arm, far_leg, near_leg, body, near_arm, head]
    else:
        order = [far_arm, far_leg, near_leg, body, head]
    if pose.get("arms_behind_head"):
        pass
    elif ball is not None and with_ball:
        if pose.get("ball_behind_arm", True):
            order += [ball, near_arm]
        else:
            order += [near_arm, ball]
    else:
        order += [near_arm]

    img = Image.new("RGBA", (FRAME_W, FRAME_H), (0, 0, 0, 0))
    pix = img.load()
    clipped = False
    for (x, y), c in smear.items():
        if 0 <= x < FRAME_W and 0 <= y + dy < FRAME_H:
            pix[x, y + dy] = c
    for layer in order:
        for src in (layer.outline(), layer.px):
            for (x, y), c in src.items():
                y2 = y + dy
                if 0 <= x < FRAME_W and 0 <= y2 < FRAME_H:
                    pix[x, y2] = c
                else:
                    clipped = True

    info = {
        "hip": [round(hip[0], 1), round(hip[1] + dy, 1)],
        "near_hand": [round(near_hand[0], 1), round(near_hand[1] + dy, 1)],
        "far_hand": [round(far_hand[0], 1), round(far_hand[1] + dy, 1)],
        "clipped": clipped,
    }
    if ball_center is not None:
        info["ball"] = [round(ball_center[0], 1), round(ball_center[1] + dy, 1)]
    return img, info


# ---------------------------------------------------------------- animations
def P(near_leg, far_leg, near_arm, far_arm, **kw):
    d = {"near_leg": near_leg, "far_leg": far_leg, "near_arm": near_arm, "far_arm": far_arm}
    d.update(kw)
    return d


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


def run_frames():
    frames = []
    for i in range(8):
        j = (i + 4) % 8
        frames.append(P(RUN_LEG[i], RUN_LEG[j], RUN_ARM[j], RUN_ARM[i],
                        lean=14, bob=RUN_BOB[i]))
    return frames


def idle_frames():
    frames = []
    for i, b in enumerate([0, 0, 1, 1]):
        frames.append(P((8, -4, 0), (-6, -2, 0), (10 - b * 2, 40 - b * 4), (-6, 30),
                        lean=4, bob=b))
    return frames


# ball height above the ground for the dribble bounce, one bounce per cycle
def dribble_frames():
    # near hand pushes the ball down, ball hits floor at frame 3, back at 6
    arm = [(30, 70), (28, 45), (30, 40), (32, 50), (32, 60), (30, 70)]
    ball = [
        ("near", 1.5, 4.5, 0), ("near", 1.5, 5.0, 40), ("ground_hi", 12, 7, 80),
        ("ground", 11, 0, 120, 1), ("ground_hi", 12, 7, 160), ("near", 1.5, 4.8, 200),
    ]
    frames = []
    for i in range(6):
        bob = [0, 1, 1, 1, 0, 0][i]
        b = ball[i]
        if b[0] == "ground_hi":
            b = ("hip", b[1], b[2], b[3])
        frames.append(P((22, -14, 0), (-14, -34, 12), arm[i], (40, 90),
                        lean=16, bob=bob, ball=b))
    return frames


def dribble_run_frames():
    frames = []
    # near arm stays out in front to dribble, far arm swings with the run
    dr_arm = [(32, 72), (30, 55), (28, 42), (30, 38), (32, 48), (32, 58), (32, 66), (32, 72)]
    ball = [
        ("near", 1.5, 4.5, 0),
        ("near", 1.5, 5.0, 45),
        ("hip", 13, 4, 90),
        ("hip", 13, 10, 135),
        ("ground", 13, 0, 180, 1),
        ("hip", 13, 10, 225),
        ("hip", 13, 4, 270),
        ("near", 1.5, 4.8, 315),
    ]
    for i in range(8):
        j = (i + 4) % 8
        frames.append(P(RUN_LEG[i], RUN_LEG[j], dr_arm[i], RUN_ARM[i],
                        lean=16, bob=RUN_BOB[i], ball=ball[i]))
    return frames


def jump_frames():
    # near arm reaches forward/up, far arm goes straight up behind the head
    return [
        # 0 crouch / anticipation, arms swung back
        P((62, -20, 0), (56, -24, 0), (-40, 10), (-46, 6), lean=26),
        # 1 take-off: legs extend onto the toes, arms swing up
        P((6, -2, 45), (-4, -8, 50), (100, 125), (95, 120), lean=8),
        # 2 rising
        P((20, -20, 30), (8, -30, 35), (112, 140), (165, 175), lean=4, lift=7, head_dx=-1),
        # 3 peak, knees tucked, reaching high
        P((50, -30, 20), (36, -40, 25), (120, 150), (172, 180), lean=2, lift=9, head_dx=-1),
        # 4 falling, legs reach for the floor
        P((18, -6, 15), (4, -16, 20), (105, 125), (150, 165), lean=4, lift=6),
        # 5 landing crouch
        P((58, -18, 0), (50, -24, 0), (40, 70), (30, 60), lean=22),
    ]


def shoot_frames():
    return [
        # 0 set: ball at the chest, knees bent
        P((40, -12, 0), (30, -18, 0), (20, 140), (30, 120), lean=-12,
          ball=("near", 3.0, -1.5, 0)),
        # 1 dip
        P((56, -18, 0), (48, -22, 0), (10, 130), (22, 115), lean=-18,
          ball=("near", 3.2, -1.5, 0)),
        # 2 rise: legs extend, ball comes up in front of the face
        P((10, -4, 35), (0, -10, 40), (75, 165), (60, 150), lean=-4, head_dx=-2,
          ball=("near", 1.0, -4.5, 22)),
        # 3 airborne, set point above the forehead
        P((20, -12, 25), (8, -20, 30), (88, 180), (80, 170), lean=2, lift=6, head_dx=-2,
          ball=("near", 0.5, -4.5, 45)),
        # 4 release: arm extends up and out, ball rolls off the fingertips
        P((22, -14, 25), (10, -22, 30), (118, 148), (95, 150), lean=0, lift=8, head_dx=-1,
          ball=("near", 2.0, -4.0, 67)),
        # 5 follow-through (ball gone - spawn it as a projectile)
        P((22, -14, 25), (10, -22, 30), (122, 140), (100, 130), lean=0, lift=8, head_dx=-2),
        # 6 hang / descend, wrist still flicked
        P((14, -8, 20), (4, -16, 25), (108, 112), (80, 100), lean=-2, lift=4, head_dx=-1),
        # 7 land
        P((48, -16, 0), (40, -22, 0), (60, 80), (30, 60), lean=-16),
    ]


def steal_frames():
    # low defensive stance, then a lunge with a big sweeping swipe of the near arm
    windup = (228, 205)
    return [
        # 0 ready: low stance, hands out
        P((46, -8, 0), (-14, -40, 12), (45, 75), (35, 70), lean=26),
        # 1 wind-up: near hand cocked up behind the head
        P((50, -6, 0), (-18, -44, 14), windup, (20, 55), lean=22, arms_behind_head=True),
        # 2 lunge forward, swipe comes through at shoulder height
        P((60, 10, -4), (-30, -56, 22), (100, 96), (5, 40), lean=32, dx=2,
          smear=[windup, (150, 150)]),
        # 3 swipe through the ball, arm fully extended
        P((62, 14, -4), (-34, -60, 24), (62, 58), (-5, 30), lean=36, dx=3,
          smear=[(100, 96)]),
        # 4 follow-through low
        P((60, 12, -4), (-32, -58, 22), (28, 30), (0, 35), lean=34, dx=3,
          smear=[(62, 58)]),
        # 5 recover back to the stance
        P((48, -6, 0), (-18, -42, 12), (40, 70), (30, 65), lean=28, dx=1),
    ]


def block_frames():
    # big vertical leap with both arms straight up in a V over the head
    up = dict(arms_behind_head=True, reach=1.3, shrug=3)
    return [
        # 0 load: deep crouch, arms down and back
        P((64, -18, 0), (58, -22, 0), (-30, 10), (-36, 6), lean=26),
        # 1 explode off the floor, arms swinging up in front
        P((6, -2, 45), (-4, -8, 50), (95, 120), (88, 112), lean=6),
        # 2 rising, arms going up
        P((14, -10, 35), (2, -18, 40), (158, 162), (196, 194), lean=2, lift=8, **up),
        # 3 peak: fully stretched, hands high
        P((22, -8, 30), (8, -16, 35), (160, 164), (198, 196), lean=0, lift=11, **up),
        # 4 coming down, arms still up
        P((16, -6, 20), (4, -14, 25), (155, 160), (194, 192), lean=2, lift=6, **up),
        # 5 land
        P((58, -18, 0), (50, -24, 0), (60, 90), (40, 70), lean=22),
    ]


ANIMS = [
    # name, frames-fn, fps, loop
    ("idle", idle_frames, 6, True),
    ("run", run_frames, 12, True),
    ("dribble", dribble_frames, 10, True),
    ("dribble_run", dribble_run_frames, 12, True),
    ("jump", jump_frames, 10, False),
    ("shoot", shoot_frames, 12, False),
    ("steal", steal_frames, 14, False),
    ("block", block_frames, 10, False),
]


# ---------------------------------------------------------------- output
def build_ball_sheet():
    size = BALL_CELL
    frames = []
    for i in range(8):
        img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
        _blit_layer(img, ball_layer((5.5, 5.5), i * 22.5))
        frames.append(("spin_%d" % i, img))
    # squashed (floor contact)
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    _blit_layer(img, ball_layer((5.5, 6.5), 0, 1))
    frames.append(("squash", img))
    # drop shadow for when the ball is in the air
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.ellipse((1, 7, 9, 10), fill=(0, 0, 0, 90))
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


def _blit_layer(img, layer):
    pix = img.load()
    for src in (layer.outline(), layer.px):
        for (x, y), c in src.items():
            if 0 <= x < img.width and 0 <= y < img.height:
                pix[x, y] = c


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    os.makedirs(PREVIEW_DIR, exist_ok=True)

    # standing hip height, used to place airborne frames
    _, stand = render(P((0, 0, 0), (0, 0, 0), (0, 0), (0, 0), lean=0))

    cols = max(len(fn()) for _, fn, _, _ in ANIMS)
    rows = len(ANIMS)
    sheet = Image.new("RGBA", (cols * FRAME_W, rows * FRAME_H), (0, 0, 0, 0))
    sheet_nb = sheet.copy()

    meta = {"frames": {}, "animations": {}, "meta": {
        "image": "player_white.png",
        "image_no_ball": "player_white_noball.png",
        "frame_size": {"w": FRAME_W, "h": FRAME_H},
        "size": {"w": sheet.width, "h": sheet.height},
        "anchor": {"x": HIP_X, "y": GROUND + 1, "note": "feet touch the floor at this pixel when grounded"},
        "facing": "right",
    }}
    previews = {}
    for row, (name, fn, fps, loop) in enumerate(ANIMS):
        poses = fn()
        frames_meta = []
        imgs = []
        for col, pose in enumerate(poses):
            img, info = render_placed(pose, True, stand)
            img_nb, _ = render_placed(pose, False, stand)
            if info["clipped"]:
                print("WARNING: %s frame %d clipped" % (name, col))
            sheet.paste(img, (col * FRAME_W, row * FRAME_H))
            sheet_nb.paste(img_nb, (col * FRAME_W, row * FRAME_H))
            key = "%s_%d" % (name, col)
            meta["frames"][key] = {
                "frame": {"x": col * FRAME_W, "y": row * FRAME_H, "w": FRAME_W, "h": FRAME_H},
                "ball": info.get("ball"),
                "near_hand": info["near_hand"],
                "far_hand": info["far_hand"],
            }
            frames_meta.append(key)
            imgs.append(img)
        anim = {"frames": frames_meta, "fps": fps, "loop": loop, "row": row}
        if name == "shoot":
            anim["release_frame"] = 5
            anim["release_ball_pos"] = meta["frames"]["shoot_4"]["ball"]
        # frames where the move can actually knock the ball away; use each
        # frame's near_hand / far_hand position for the hitbox
        if name == "steal":
            anim["active_frames"] = [2, 3, 4]
        if name == "block":
            anim["active_frames"] = [2, 3, 4]
        meta["animations"][name] = anim
        previews[name] = (imgs, fps)

    sheet.save(os.path.join(OUT_DIR, "player_white.png"))
    sheet_nb.save(os.path.join(OUT_DIR, "player_white_noball.png"))
    with open(os.path.join(OUT_DIR, "player_white.json"), "w") as f:
        json.dump(meta, f, indent=2)

    ball_sheet, ball_meta = build_ball_sheet()
    ball_sheet.save(os.path.join(OUT_DIR, "ball.png"))
    with open(os.path.join(OUT_DIR, "ball.json"), "w") as f:
        json.dump(ball_meta, f, indent=2)

    write_previews(sheet, previews, ball_sheet)


def render_placed(pose, with_ball, stand):
    """Render; airborne poses ('lift') are placed relative to the standing hip."""
    if "lift" in pose:
        return render(pose, with_ball, stand_hip_y=stand["hip"][1])
    return render(pose, with_ball)


def write_previews(sheet, previews, ball_sheet, scale=4):
    bg = (40, 70, 170, 255)
    floor = (30, 50, 140, 255)
    # scaled sheet on a court-ish background with grid lines
    big = Image.new("RGBA", sheet.size, bg)
    big.alpha_composite(sheet)
    big = big.resize((sheet.width * scale, sheet.height * scale), Image.NEAREST)
    d = ImageDraw.Draw(big)
    for x in range(0, big.width + 1, FRAME_W * scale):
        d.line([(x, 0), (x, big.height)], fill=(255, 255, 255, 60))
    for y in range(0, big.height + 1, FRAME_H * scale):
        d.line([(0, y), (big.width, y)], fill=(255, 255, 255, 60))
    for row, name in enumerate(previews):
        d.text((6, row * FRAME_H * scale + 4), name, fill=(255, 255, 255, 255))
    big.save(os.path.join(PREVIEW_DIR, "sheet_preview.png"))

    # animated GIFs
    for name, (imgs, fps) in previews.items():
        out = []
        for im in imgs:
            f = Image.new("RGBA", im.size, bg)
            ImageDraw.Draw(f).rectangle((0, GROUND + 1, FRAME_W, FRAME_H), fill=floor)
            f.alpha_composite(im)
            out.append(f.resize((FRAME_W * scale, FRAME_H * scale), Image.NEAREST).convert("RGB"))
        out[0].save(os.path.join(PREVIEW_DIR, name + ".gif"), save_all=True,
                    append_images=out[1:], duration=int(1000 / fps), loop=0)

    # ball spin
    size = BALL_CELL
    out = []
    for i in range(8):
        f = Image.new("RGBA", (size, size), bg)
        f.alpha_composite(ball_sheet.crop((i * size, 0, (i + 1) * size, size)))
        out.append(f.resize((size * 8, size * 8), Image.NEAREST).convert("RGB"))
    out[0].save(os.path.join(PREVIEW_DIR, "ball_spin.gif"), save_all=True,
                append_images=out[1:], duration=60, loop=0)


if __name__ == "__main__":
    main()
