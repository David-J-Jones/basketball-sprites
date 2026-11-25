#!/usr/bin/env python3
"""Movement showcase: previews/movement_showcase.gif.

Four lanes drawn from the built atlas (run generate_sprites.py and
generate_move_fx.py first), each with a camera following the player:
a run, a sprint (speed lines, ghosts), a dribble drive into a killer
crossover, and a plant / turn / stop. Effects fire on the same frames as
MoveFxEmitter in moveFx/moveFx.ts.

Run:  python3 tools/preview_movement.py
"""
import json, os, sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT + '/tools')
import generate_sprites as G
from PIL import Image, ImageDraw

RN = ROOT + '/integration/react-native'
meta = json.load(open(RN + '/playerSprites/spriteData.json'))
BODY = G.MID_BODY
bodies = {BODY: json.load(open(RN + '/playerSprites/bodies/%s.json' % BODY))}
comp = G.Compositor(meta, bodies, G.DiskPages(RN + '/playerSprites/atlas', len(meta['pages'])))
FX = json.load(open(RN + '/moveFx/moveFx.json'))['effects']
STRIP = {k: Image.open(RN + '/moveFx/%s.png' % k).convert('RGBA') for k in FX}
ANIMS = meta['anims']
U = json.load(open(RN + '/teamUniforms/uniforms.json'))
pal = json.load(open(RN + '/playerSprites/palettes.json'))
skins = [s['color'] for s in pal['skinTones']]
hair = {h['id']: h['color'] for h in pal['hairColors']}

S = 3                                     # atlas px per art px
PX_PER_FT = meta['standingHeight'][BODY] / 6.6
DT = 1 / 30
SECONDS = 3.2
W, LANE = 760, 300
FW, FH = meta['frameWidth'], meta['frameHeight']

def uni(tid, kind):
    u = U[tid][kind]
    return ({'jersey': u['jersey'], 'trim': u['trim'], 'pattern': u['pattern'], 'accent': u['accent'],
             'accent2': u['accent2']}, u['shorts'])

cache = {}
def sprite(anim, i, look, colors, flip):
    key = (anim, i, id(look), flip)
    if key not in cache:
        img = comp.frame(BODY, anim, i, look, colors)
        rec = G.frame_obj(bodies, BODY, anim, i)
        ball = rec['ball']
        if flip:
            img = img.transpose(Image.FLIP_LEFT_RIGHT)
            if ball:
                ball = [FW - ball[0], ball[1]]
        cache[key] = (img, ball, rec['ballDepth'] or 0)
    return cache[key]

def fx_img(fid, f, flip):
    m = FX[fid]; w, h = m['width'] * S, m['height'] * S
    im = STRIP[fid].crop((f * w, 0, (f + 1) * w, h))
    return im.transpose(Image.FLIP_LEFT_RIGHT) if flip else im

def draw_ball(img, x, y):
    r = G.BALL_R * S
    d = ImageDraw.Draw(img)
    d.ellipse([x - r, y - r, x + r, y + r], fill=(222, 112, 36), outline=(40, 20, 10), width=3)
    d.line([(x - r + 3, y), (x + r - 3, y)], fill=(90, 40, 15), width=2)
    d.arc([x - r * 0.6, y - r, x + r * 0.6, y + r], 90, 270, fill=(90, 40, 15), width=2)

class Lane:
    def __init__(self, label, script, look, colors, ghosts=True):
        self.label, self.script, self.look, self.colors, self.ghosts_on = label, script, look, colors, ghosts
        self.x, self.y, self.facing = 0.0, 0.0, 1
        self.t = 0.0; self.stride = 0.0
        self.shot = None          # (anim, t0)
        self.live = []            # [fid, wx, wy, t, flip]
        self.lines = 0.0; self.lines_t = 0.0
        self.ghosts = []; self.since_ghost = 0
        self.last = (None, -1)
        self.cam = 0.0

    def state(self):
        """script(t) -> (anim or 'RUN', speed ft/s, vy, facing); one-shots started with ('PLAY', name)."""
        return self.script(self.t, self)

    def step(self):
        anim, speed, vy, facing = self.state()
        flip_before = self.facing
        if anim.startswith('PLAY:'):
            name = anim[5:]
            if not self.shot or self.shot[0] != name:
                self.shot = (name, self.t)
            a = ANIMS[name]
            fi = int((self.t - self.shot[1]) * a['fps'])
            if fi >= a['frameCount']:
                fi = a['frameCount'] - 1
            cur = name
            if name.startswith('turn') and fi >= a['events'].get('flipAt', 99):
                self.facing = facing
        else:
            self.shot = None
            cur = anim
            a = ANIMS[cur]
            if a['frameCount'] == 12 and cur not in ('walk',):
                self.stride += DT * 18 * max(speed, 0.1) / 14
            else:
                self.stride += DT * a['fps']
            fi = int(self.stride) % a['frameCount']
            self.facing = facing
        dirn = self.facing
        self.x += dirn * speed * PX_PER_FT * DT if not cur.startswith('turn') else 0
        self.y += vy * DT * PX_PER_FT
        flip = dirn < 0
        # ---- effects (same rules as MoveFxEmitter)
        prev_anim, prev_f = self.last
        frames = [fi] if cur != prev_anim else ([f for f in range(prev_f + 1, fi + 1)] if fi > prev_f else
                                                 [f for f in range(prev_f + 1, a['frameCount'])] + list(range(0, fi + 1)) if a['loop'] else [])
        stride = a['frameCount'] == 12 and (cur.startswith('run') or cur.startswith('dribble_run')) and cur not in ('run_start', 'run_stop')
        if cur != prev_anim and cur in ('run_stop', 'turn_run', 'turn_dribble'):
            self.live.append(['dust_skid', self.x + dirn * 2 * S, self.y, 0.0, flip])
        ev = a['events']
        for f in frames:
            if stride and speed >= 9 and f in (4, 10):
                self.live.append(['dust_step', self.x - dirn * 2 * S, self.y, 0.0, flip])
            b = ev.get('cutStart', ev.get('burst'))
            if b is not None and f == b and cur.startswith(('crossover', 'hesitation', 'inside_out', 'behind', 'between')):
                self.live.append(['cut_burst', self.x - dirn * 1 * S, self.y, 0.0, flip])
        self.last = (cur, fi)
        fast = stride and (speed > 14 if self.lines > 0 else speed >= 17)
        self.lines = max(0.0, min(1.0, self.lines + (6 if fast else -4) * DT))
        self.lines_t += DT
        for e in self.live:
            e[3] += DT
        self.live = [e for e in self.live if e[3] < FX[e[0]]['frames'] / FX[e[0]]['fps']]
        img, ball, depth = sprite(cur, fi, self.look, self.colors, flip)
        # ghosts
        for g in self.ghosts:
            g[3] += DT
        self.ghosts = [g for g in self.ghosts if g[3] < 0.15]
        self.since_ghost += DT
        if self.ghosts_on and speed >= 16 and stride and self.since_ghost >= 0.05:
            self.since_ghost = 0
            self.ghosts.insert(0, [img, self.x, self.y, 0.0])
            self.ghosts = self.ghosts[:3]
        self.t += DT
        self.cam += (self.x - self.cam) * 0.35          # soft camera follow
        return cur, fi, img, ball, depth, flip, speed

    def render(self, cur, fi, img, ball, depth, flip, speed):
        lane = Image.new('RGBA', (W, LANE), (176, 124, 72, 255))
        d = ImageDraw.Draw(lane)
        floor_y = LANE - 40
        ox = W / 2 - self.cam
        # hardwood planks and court lines scroll with the camera
        for k in range(-2, 30):
            x = (k * 90 + ox) % (W + 180) - 90
            d.line([(x, floor_y - 120), (x - 40, LANE)], fill=(160, 110, 60), width=2)
        x = (ox % 1400) - 300                                # one court line every 1400 px
        d.line([(x, floor_y - 120), (x - 40, LANE)], fill=(245, 240, 225), width=5)
        d.line([(0, floor_y - 120), (W, floor_y - 120)], fill=(150, 100, 55), width=2)
        def world(wx, wy):
            return wx + ox, floor_y + wy
        for e in self.live:
            m = FX[e[0]]; f = min(int(e[3] * m['fps']), m['frames'] - 1)
            im = fx_img(e[0], f, e[4])
            ax = (m['width'] - m['anchor'][0]) if e[4] else m['anchor'][0]
            sx, sy = world(e[1], e[2])
            lane.alpha_composite(im, (int(sx - ax * S), int(sy - m['anchor'][1] * S)))
        px, py = world(self.x, self.y)
        if self.lines > 0:
            m = FX['speed_lines']; f = int(self.lines_t * m['fps']) % m['frames']
            im = fx_img('speed_lines', f, flip)
            a = im.getchannel('A').point(lambda v: int(v * self.lines)); im.putalpha(a)
            lx = px - (-1 if flip else 1) * 5 * S
            ax = (m['width'] - m['anchor'][0]) if flip else m['anchor'][0]
            lane.alpha_composite(im, (int(lx - ax * S), int(py - 26 * S - m['anchor'][1] * S)))
        for g in reversed(self.ghosts):
            gi = g[0].copy(); op = 0.35 * max(0, 1 - g[3] / 0.15)
            gi.putalpha(gi.getchannel('A').point(lambda v: int(v * op)))
            gx, gy = world(g[1], g[2])
            lane.alpha_composite(gi, (int(gx - FW / 2), int(gy - FH)))
        tl = (int(px - FW / 2), int(py - FH))
        if ball and depth < 0:
            draw_ball(lane, tl[0] + ball[0], tl[1] + ball[1] + depth * 4 * S)
        lane.alpha_composite(img, tl)
        if ball and depth >= 0:
            draw_ball(lane, tl[0] + ball[0], tl[1] + ball[1] + depth * 4 * S)
        d.rectangle([0, 0, W, 26], fill=(20, 16, 30, 200))
        d.text((10, 7), '%s   %s  %.0f ft/s' % (self.label, cur, speed), fill=(255, 255, 255))
        return lane

def ramp(t, t0, t1, a, b):
    if t <= t0: return a
    if t >= t1: return b
    return a + (b - a) * (t - t0) / (t1 - t0)

look1 = {'skin': skins[3], 'hair': 'locs', 'facial': 'goatee', 'hairColor': hair['black']}
look2 = {'skin': skins[1], 'hair': 'fade', 'facial': None, 'hairColor': hair['black']}
look3 = {'skin': skins[4], 'hair': 'high_top', 'facial': None, 'hairColor': hair['black']}
look4 = {'skin': skins[2], 'hair': 'afro', 'facial': 'beard', 'hairColor': hair['darkBrown']}

def with_shorts(look, shorts):
    l = dict(look); l['outfit'] = {'shorts': shorts}; return l

c1, s1 = uni('PHX', 'home'); c2, s2 = uni('MIA', 'city'); c3, s3 = uni('CHI', 'retro90'); c4, s4 = uni('BOS', 'away')

def run_script(t, L):     return ('run', 12, 0, 1)
def sprint_script(t, L):  return ('run', ramp(t, 0, 0.8, 12, 21), 0, 1)
def drive_script(t, L):
    if t < 1.1: return ('dribble_run', 15, 0, 1)
    if t < 1.1 + 7 / 14: return ('PLAY:crossover_wide_up', 6 if t < 1.1 + 4 / 14 else 14, -3 if t > 1.1 + 4 / 14 else 0, 1)
    return ('dribble_run_far', ramp(t, 1.6, 2.2, 15, 19), 0, 1)
def stop_script(t, L):
    if t < 1.0: return ('run', 15, 0, 1)
    if t < 1.0 + 6 / 16: return ('PLAY:turn_run', 0, 0, -1)
    if t < 2.3: return ('run', ramp(t, 1.4, 1.8, 6, 15), 0, -1)
    if t < 2.3 + 5 / 14: return ('PLAY:run_stop', ramp(t, 2.3, 2.6, 8, 0), 0, -1)
    return ('idle', 0, 0, -1)

lanes = [Lane('1  RUN', run_script, with_shorts(look1, s1), c1, ghosts=False),
         Lane('2  SPRINT', sprint_script, with_shorts(look2, s2), c2),
         Lane('3  DRIBBLE DRIVE + KILLER CROSS', drive_script, with_shorts(look3, s3), c3),
         Lane('4  PLANT, TURN, STOP', stop_script, with_shorts(look4, s4), c4)]
frames = []
for k in range(int(SECONDS / DT)):
    sheet = Image.new('RGB', (W, LANE * len(lanes)), (0, 0, 0))
    for i, L in enumerate(lanes):
        sheet.paste(L.render(*L.step()), (0, i * LANE))
    frames.append(sheet)
out = sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT, 'previews', 'movement_showcase.gif')
frames[0].save(out, save_all=True, append_images=frames[1:], duration=int(DT * 1000), loop=0, optimize=True)
print(len(frames), os.path.getsize(out) // 1024, 'KB')
