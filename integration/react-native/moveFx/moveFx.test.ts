import { PlayerAnimator } from '../playerSprites/animController';
import type { AnimName } from '../playerSprites/types';
import {
  burstFrame, fxDuration, fxFrame, GhostTrail, isStride, landFrame, MOVE_FX, MOVE_FX_IDS, MoveFxEmitter,
  type FxInstance, type MoveFxId,
} from './moveFx';

const DT = 1 / 60;

function drive(seconds: number, vx: number, hasBall = false, fx = new MoveFxEmitter(), a = new PlayerAnimator('right')) {
  const seen = new Set<MoveFxId>();
  let last: readonly FxInstance[] = [];
  for (let t = 0; t < seconds; t += DT) {
    const o = a.update(DT, { vx, hasBall });
    last = fx.update(DT, { x: 100, y: 200, anim: o.anim, frame: o.frame, flip: o.flip, speed: Math.abs(vx), scale: 2 });
    for (const e of last) seen.add(e.fx);
  }
  return { seen, last, fx, a };
}

describe('move fx data', () => {
  it('has every effect with a size, frames, fps and an anchor inside the frame', () => {
    expect(MOVE_FX_IDS).toEqual(['dust_step', 'dust_skid', 'cut_burst', 'land_puff', 'speed_lines']);
    for (const id of MOVE_FX_IDS) {
      const m = MOVE_FX[id];
      expect(m.label).toBeTruthy();
      expect(m.frames).toBeGreaterThan(2);
      expect(m.fps).toBeGreaterThan(0);
      expect(m.anchor[0]).toBeLessThan(m.width);
      expect(m.anchor[1]).toBeLessThan(m.height);
    }
  });

  it('holds one-shots on their last frame and loops the speed lines', () => {
    expect(fxFrame('dust_step', 99)).toBe(MOVE_FX.dust_step.frames - 1);
    expect(fxFrame('speed_lines', MOVE_FX.speed_lines.frames / MOVE_FX.speed_lines.fps)).toBe(0);
    expect(fxDuration('speed_lines')).toBe(Infinity);
  });

  it('knows which animations burst, land and share the stride clock', () => {
    expect(burstFrame('crossover_wide_up')).toBe(4);
    expect(burstFrame('hesitation')).toBe(3);
    expect(burstFrame('dribble')).toBeNull();
    expect(landFrame('dunk_basic')).not.toBeNull();
    expect(landFrame('run')).toBeNull();
    for (const a of ['run', 'run_power', 'dribble_run', 'dribble_run_low_far'] as AnimName[]) expect(isStride(a)).toBe(true);
    expect(isStride('walk')).toBe(false);
  });
});

describe('MoveFxEmitter', () => {
  it('kicks up step dust while running, but not while walking', () => {
    expect(drive(2, 12).seen.has('dust_step')).toBe(true);
    expect(drive(2, 4).seen.has('dust_step')).toBe(false);
  });

  it('adds speed lines at a sprint and fades them out when he slows down', () => {
    const fast = drive(2, 20);
    expect(fast.seen.has('speed_lines')).toBe(true);
    const lines = fast.last.find((e) => e.fx === 'speed_lines')!;
    expect(lines.opacity).toBe(1);
    expect(lines.x).toBeLessThan(100);        // behind a player facing right
    const slow = drive(2, 10, false, fast.fx, fast.a);
    expect(slow.last.some((e) => e.fx === 'speed_lines')).toBe(false);
  });

  it('throws up a skid cloud when he stops, and a burst out of a crossover', () => {
    const r = drive(1, 12, true);
    r.a.play('crossover_wide_up');
    const after = drive(1, 12, true, r.fx, r.a);
    expect(after.seen.has('cut_burst')).toBe(true);
    const stop = drive(1, 0, false, after.fx, after.a);
    expect(stop.seen.has('dust_skid')).toBe(true);
  });

  it('mirrors and places dust behind a player facing left', () => {
    const fx = new MoveFxEmitter();
    const a = new PlayerAnimator('left');
    let dust: FxInstance | undefined;
    for (let t = 0; t < 2 && !dust; t += DT) {
      const o = a.update(DT, { vx: -12 });
      dust = fx.update(DT, { x: 100, y: 200, anim: o.anim, frame: o.frame, flip: o.flip, speed: 12, scale: 2 })
        .find((e) => e.fx === 'dust_step');
    }
    expect(dust).toBeDefined();
    expect(dust!.flip).toBe(true);
    expect(dust!.x).toBeGreaterThan(100);
  });

  it('respects the switches and the per-player cap', () => {
    const off = drive(2, 20, false, new MoveFxEmitter({ enabled: { speed_lines: false, dust_step: false } as never }));
    expect(off.seen.has('speed_lines')).toBe(false);
    expect(off.seen.has('dust_step')).toBe(false);
    const fx = new MoveFxEmitter({ maxEffects: 3 });
    for (let i = 0; i < 10; i++) fx.spawn('dust_skid', 0, 0, false, 1);
    expect(fx.effects.length).toBe(3);
    fx.clear();
    expect(fx.effects.length).toBe(0);
  });
});

describe('GhostTrail', () => {
  it('records fading ghosts only at speed', () => {
    const g = new GhostTrail({ minSpeed: 16, count: 3, spacing: 0.05 });
    for (let i = 0; i < 60; i++) g.update(DT, { x: i, y: 0, anim: 'run', frame: i % 12, flip: false, speed: 20 });
    expect(g.ghosts.length).toBe(3);
    expect(g.opacityOf(g.ghosts[0])).toBeGreaterThan(g.opacityOf(g.ghosts[2]));
    for (let i = 0; i < 60; i++) g.update(DT, { x: i, y: 0, anim: 'run', frame: i % 12, flip: false, speed: 5 });
    expect(g.ghosts.length).toBe(0);
  });
});
