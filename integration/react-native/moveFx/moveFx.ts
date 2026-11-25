/**
 * Movement effects around a player (dust, skids, bursts, landings, speed
 * lines) and the logic that fires them from what the player's animation is
 * doing. Kept free of image requires and React so it works in tests and
 * plain sim code; <MoveFx> and <PlayerGhosts> draw the results.
 *
 *   const fx = new MoveFxEmitter();
 *   // every rendered frame, after animator.update():
 *   const effects = fx.update(dt, { x, y, anim: out.anim, frame: out.frame, flip: out.flip, speed, scale });
 *   <MoveFx effects={effects} />
 */
import meta from './moveFx.json';
import raw from '../playerSprites/spriteData.json';
import type { AnimName, SpriteData } from '../playerSprites/types';

export type MoveFxId = 'dust_step' | 'dust_skid' | 'cut_burst' | 'land_puff' | 'speed_lines';
export type MoveFxInfo = {
  label: string;
  /** frame size in art px (= sprite frame px) */
  width: number;
  height: number;
  frames: number;
  fps: number;
  loop: boolean;
  /** the strip pixel that sits on the player's foot (speed lines: his back at hip height) */
  anchor: [number, number];
};

export const MOVE_FX_META = meta as unknown as { scale: number; effects: Record<MoveFxId, MoveFxInfo> };
export const MOVE_FX = MOVE_FX_META.effects;
export const MOVE_FX_IDS = Object.keys(MOVE_FX) as MoveFxId[];

const ANIMS = (raw as unknown as SpriteData).anims;

/** One live effect, ready to draw with <MoveFx>. */
export type FxInstance = {
  key: number;
  fx: MoveFxId;
  /** screen position of the effect's anchor */
  x: number;
  y: number;
  /** true: mirrored, for a player facing left */
  flip: boolean;
  /** screen px per art px (use the sprite's scale) */
  scale: number;
  frame: number;
  /** 0..1, for fading speed lines in and out */
  opacity: number;
  /** seconds since it started */
  t: number;
};

export type MoveFxInput = {
  /** screen position of the player's feet (same as <PlayerSprite x y>) */
  x: number;
  y: number;
  anim: AnimName;
  frame: number;
  flip: boolean;
  /** the player's speed, in the same unit as the animator (ft/s by default) */
  speed: number;
  /** the sprite's scale (screen px per frame px) */
  scale: number;
};

export type MoveFxOptions = {
  /** no step dust below this speed (walking is quiet) */
  stepDustSpeed: number;
  /** speed lines fade in above this speed... */
  speedLinesOn: number;
  /** ...and out below this one */
  speedLinesOff: number;
  /** turn each kind on or off */
  enabled: Record<MoveFxId, boolean>;
  /** at most this many effects per player at once (oldest go first) */
  maxEffects: number;
};

export const DEFAULT_MOVE_FX_OPTIONS: MoveFxOptions = {
  stepDustSpeed: 9,
  speedLinesOn: 17,
  speedLinesOff: 14,
  enabled: { dust_step: true, dust_skid: true, cut_burst: true, land_puff: true, speed_lines: true },
  maxEffects: 8,
};

/** Frames where a foot pushes off in every 12-frame run / dribble-run cycle (keys 3 and 7). */
export const STRIDE_PUSH_FRAMES = [4, 10];

const STRIDE = /^(run(_(upright|power|bounce|glide|loose))?|dribble_run(_(low|high|rhythm|protect))?(_far)?)$/;
const SKIDS = new Set<string>(['run_stop', 'turn_run', 'turn_dribble']);

/** Is this a 12-frame stride-clock cycle (run styles, dribble runs)? */
export function isStride(anim: AnimName): boolean {
  return STRIDE.test(anim);
}

/** The frame an animation explodes out of a move on, if it has one (cutStart / burst). */
export function burstFrame(anim: AnimName): number | null {
  const ev = ANIMS[anim]?.events ?? {};
  return ev.cutStart ?? ev.burst ?? null;
}

/** The frame a jump lands on: the first frame after the airborne ones (null if it never leaves the floor). */
export function landFrame(anim: AnimName): number | null {
  const a = ANIMS[anim];
  if (!a) return null;
  const ev = a.events;
  if (ev.takeoff === undefined && ev.rise === undefined) return null;
  return a.frameCount - 1;
}

/** Frame of an effect after `t` seconds (loops wrap, one-shots hold the last frame). */
export function fxFrame(fx: MoveFxId, t: number): number {
  const m = MOVE_FX[fx];
  const f = Math.floor(Math.max(0, t) * m.fps);
  return m.loop ? f % m.frames : Math.min(f, m.frames - 1);
}

/** Seconds a one-shot effect lasts (Infinity for loops). */
export function fxDuration(fx: MoveFxId): number {
  const m = MOVE_FX[fx];
  return m.loop ? Infinity : m.frames / m.fps;
}

/** Frames passed going from `a` to `b` in an n-frame animation (exclusive of a, inclusive of b). */
function crossed(a: number, b: number, n: number, loop: boolean): number[] {
  if (a === b) return [];
  const out: number[] = [];
  if (b > a) for (let f = a + 1; f <= b; f++) out.push(f);
  else if (loop) {
    for (let f = a + 1; f < n; f++) out.push(f);
    for (let f = 0; f <= b; f++) out.push(f);
  } else out.push(b);
  return out;
}

/**
 * Fires movement effects for one player from his animation and speed, and
 * keeps them alive until they finish. Effects stay where they were kicked up
 * (dust doesn't follow the player); speed lines ride along with him.
 */
export class MoveFxEmitter {
  private opts: MoveFxOptions;
  private live: FxInstance[] = [];
  private nextKey = 1;
  private lastAnim: AnimName | null = null;
  private lastFrame = 0;
  private lines: FxInstance | null = null;

  constructor(opts: Partial<MoveFxOptions> = {}) {
    this.opts = { ...DEFAULT_MOVE_FX_OPTIONS, ...opts, enabled: { ...DEFAULT_MOVE_FX_OPTIONS.enabled, ...opts.enabled } };
  }

  /** The effects alive right now. */
  get effects(): readonly FxInstance[] {
    return this.live;
  }

  /** Drop everything (e.g. on a dead ball or a camera cut). */
  clear(): void {
    this.live = [];
    this.lines = null;
    this.lastAnim = null;
  }

  /** Start an effect by hand at a screen point (e.g. a dust cloud on a hard foul). */
  spawn(fx: MoveFxId, x: number, y: number, flip: boolean, scale: number): FxInstance | null {
    if (!this.opts.enabled[fx]) return null;
    const inst: FxInstance = { key: this.nextKey++, fx, x, y, flip, scale, frame: 0, opacity: 1, t: 0 };
    this.live.push(inst);
    while (this.live.length > this.opts.maxEffects) {
      const i = this.live.findIndex((e) => e !== this.lines);
      this.live.splice(i, 1);
    }
    return inst;
  }

  update(dt: number, s: MoveFxInput): readonly FxInstance[] {
    // age what's there
    for (const e of this.live) {
      e.t += dt;
      e.frame = fxFrame(e.fx, e.t);
    }
    this.live = this.live.filter((e) => e === this.lines || e.t < fxDuration(e.fx));

    const n = ANIMS[s.anim]?.frameCount ?? 1;
    const loop = ANIMS[s.anim]?.loop ?? false;
    const entered = s.anim !== this.lastAnim;
    const frames = entered ? [s.frame] : crossed(this.lastFrame, s.frame, n, loop);
    const dir = s.flip ? -1 : 1;
    const foot = (dx: number) => s.x + dx * dir * s.scale;

    if (entered && SKIDS.has(s.anim)) this.spawn('dust_skid', foot(2), s.y, s.flip, s.scale);
    const burst = burstFrame(s.anim);
    const land = landFrame(s.anim);
    for (const f of frames) {
      if (isStride(s.anim) && s.speed >= this.opts.stepDustSpeed && STRIDE_PUSH_FRAMES.includes(f)) {
        this.spawn('dust_step', foot(-2), s.y, s.flip, s.scale);
      }
      if (burst !== null && f === burst) this.spawn('cut_burst', foot(-1), s.y, s.flip, s.scale);
      if (land !== null && f === land) this.spawn('land_puff', s.x, s.y, s.flip, s.scale);
    }
    this.lastAnim = s.anim;
    this.lastFrame = s.frame;

    this.updateLines(dt, s);
    return this.live;
  }

  private updateLines(dt: number, s: MoveFxInput): void {
    const fast = isStride(s.anim) && (this.lines ? s.speed > this.opts.speedLinesOff : s.speed >= this.opts.speedLinesOn);
    if (fast && !this.lines && this.opts.enabled.speed_lines) {
      this.lines = this.spawn('speed_lines', 0, 0, s.flip, s.scale);
      if (this.lines) this.lines.opacity = 0;
    }
    const l = this.lines;
    if (!l) return;
    // ride along at hip height, just behind the back; fade in and out
    l.x = s.x - (s.flip ? -1 : 1) * 5 * s.scale;
    l.y = s.y - 26 * s.scale;
    l.flip = s.flip;
    l.scale = s.scale;
    l.opacity = Math.max(0, Math.min(1, l.opacity + (fast ? 6 : -4) * dt));
    if (!fast && l.opacity <= 0) {
      this.live = this.live.filter((e) => e !== l);
      this.lines = null;
    }
  }
}

/** A past pose of a player, drawn faded behind him by <PlayerGhosts>. */
export type Ghost = { x: number; y: number; anim: AnimName; frame: number; flip: boolean; age: number };

export type GhostTrailOptions = {
  /** ghosts appear above this speed */
  minSpeed: number;
  /** how many ghosts at most */
  count: number;
  /** seconds between ghosts */
  spacing: number;
  /** opacity of the newest ghost; older ones fade toward 0 */
  opacity: number;
};

export const DEFAULT_GHOST_OPTIONS: GhostTrailOptions = { minSpeed: 16, count: 3, spacing: 0.05, opacity: 0.35 };

/**
 * Afterimages behind a fast player: records a pose every `spacing` seconds
 * while he is above `minSpeed`. Good for fast breaks and park-mode flair;
 * each ghost is a full sprite, so keep `count` small.
 */
export class GhostTrail {
  private opts: GhostTrailOptions;
  private list: Ghost[] = [];
  private since = 0;

  constructor(opts: Partial<GhostTrailOptions> = {}) {
    this.opts = { ...DEFAULT_GHOST_OPTIONS, ...opts };
  }

  get ghosts(): readonly Ghost[] {
    return this.list;
  }

  /** Opacity to draw a ghost at (newest brightest). */
  opacityOf(g: Ghost): number {
    const life = this.opts.count * this.opts.spacing;
    return this.opts.opacity * Math.max(0, 1 - g.age / life);
  }

  update(dt: number, s: { x: number; y: number; anim: AnimName; frame: number; flip: boolean; speed: number }): readonly Ghost[] {
    for (const g of this.list) g.age += dt;
    const life = this.opts.count * this.opts.spacing;
    this.list = this.list.filter((g) => g.age < life);
    this.since += dt;
    if (s.speed >= this.opts.minSpeed && this.since >= this.opts.spacing) {
      this.since = 0;
      this.list.unshift({ x: s.x, y: s.y, anim: s.anim, frame: s.frame, flip: s.flip, age: 0 });
      this.list.length = Math.min(this.list.length, this.opts.count);
    }
    return this.list;
  }
}
