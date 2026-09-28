import { PlayerAnimator } from './animController';
import { SPRITE_DATA as SPRITES } from './frames';
import type { AnimName } from './types';
const DT = 1 / 60;

function run(a: PlayerAnimator, seconds: number, vx: number | ((t: number) => number), hasBall = false) {
  const out = [];
  for (let t = 0; t < seconds; t += DT) {
    out.push(a.update(DT, { vx: typeof vx === 'number' ? vx : vx(t), hasBall }));
  }
  return out;
}

describe('PlayerAnimator', () => {
  it('does not flip back and forth when the velocity jitters', () => {
    const a = new PlayerAnimator('right');
    run(a, 1, 10);
    // AI wobble: direction changes every other frame
    const out = run(a, 2, (t) => (Math.floor(t / DT) % 2 ? 10 : -10));
    expect(new Set(out.map((o) => o.flip)).size).toBe(1);
    expect(out.some((o) => o.anim.startsWith('turn'))).toBe(false);
  });

  it('turns through a turn animation when the direction really changes', () => {
    const a = new PlayerAnimator('right');
    run(a, 1, 10);
    const out = run(a, 1.5, -10);
    const anims = out.map((o) => o.anim);
    expect(anims).toContain('turn_run');
    // facing only flips at the turn's flipAt frame, never before
    const firstTurn = anims.indexOf('turn_run');
    expect(out[firstTurn].flip).toBe(false);
    const flipAt = SPRITES.anims.turn_run.events.flipAt;
    const flipped = out.findIndex((o) => o.flip);
    expect(out[flipped].anim).toBe('turn_run');
    expect(out[flipped].frame).toBe(flipAt);
    // and ends running the other way
    expect(out[out.length - 1]).toMatchObject({ anim: 'run', facing: 'left', flip: true });
  });

  it('uses the standing and dribbling turns when appropriate', () => {
    const standing = new PlayerAnimator('right');
    run(standing, 0.5, 0);
    expect(run(standing, 0.5, -2).map((o) => o.anim)).toContain('turn');
    const dribbling = new PlayerAnimator('right');
    run(dribbling, 0.5, 10, true);
    expect(run(dribbling, 0.5, -10, true).map((o) => o.anim)).toContain('turn_dribble');
  });

  it('plays run_start and run_stop between standing and running', () => {
    const a = new PlayerAnimator('right');
    run(a, 0.5, 0);
    const start = run(a, 0.6, 10).map((o) => o.anim);
    expect(start[0]).toBe('run_start');
    expect(start[start.length - 1]).toBe('run');
    const stop = run(a, 0.8, 0).map((o) => o.anim);
    expect(stop).toContain('run_stop');
    expect(stop[stop.length - 1]).toBe('idle');
  });

  it('keeps the stride when switching between run and dribble_run', () => {
    const a = new PlayerAnimator('right');
    run(a, 1, 10);
    const before = a.update(DT, { vx: 10 });
    const after = a.update(DT, { vx: 10, hasBall: true });
    expect(before.anim).toBe('run');
    expect(after.anim).toBe('dribble_run');
    expect(Math.abs(after.frame - before.frame)).toBeLessThanOrEqual(1);
  });

  it('never skips more than one frame of the run at 60fps', () => {
    const a = new PlayerAnimator('right');
    run(a, 1, 14);
    const out = run(a, 2, 20).filter((o) => o.anim === 'run');
    const n = SPRITES.anims.run.frameCount;
    for (let i = 1; i < out.length; i++) {
      const step = (out[i].frame - out[i - 1].frame + n) % n;
      expect(step).toBeLessThanOrEqual(1);
    }
  });

  it('plays actions once, then goes back to moving', () => {
    const a = new PlayerAnimator('right');
    run(a, 0.5, 0, true);
    a.play('shoot', 'left');
    const out = run(a, 1.5, 0, true);
    expect(out[0]).toMatchObject({ anim: 'shoot', frame: 0, facing: 'left' });
    expect(out[out.length - 1].anim).toBe('dribble');
  });

  it('switches the dribbling hand after a crossover', () => {
    const a = new PlayerAnimator('right');
    run(a, 0.5, 10, true);
    a.play('crossover_up');
    const out = run(a, 1, 10, true);
    expect(out[out.length - 1]).toMatchObject({ anim: 'dribble_run_far', hand: 'far' });
    a.play('crossover_down');
    expect(run(a, 1, 10, true).pop()).toMatchObject({ anim: 'dribble_run', hand: 'near' });
  });

  it('only returns animations that exist', () => {
    const a = new PlayerAnimator('left');
    const names = new Set(Object.keys(SPRITES.anims));
    const out = run(a, 6, (t) => Math.sin(t * 3) * 15, true);
    for (const o of out) {
      expect(names.has(o.anim as AnimName)).toBe(true);
      expect(o.frame).toBeLessThan(SPRITES.anims[o.anim].frameCount);
    }
  });
});

describe('PlayerAnimator screens', () => {
  it('sets a screen, holds it through movement noise, absorbs contact, then releases', () => {
    const a = new PlayerAnimator('right');
    run(a, 0.5, 10);
    a.hold('screen_hold', 'screen_set');
    const setting = run(a, 1, (t) => (Math.floor(t / DT) % 2 ? 8 : -8));
    expect(setting[0].anim).toBe('screen_set');
    expect(setting[setting.length - 1].anim).toBe('screen_hold');
    expect(new Set(setting.map((o) => o.flip)).size).toBe(1);
    a.play('screen_contact');
    const hit = run(a, 1, 0);
    expect(hit[0].anim).toBe('screen_contact');
    expect(hit[hit.length - 1].anim).toBe('screen_hold');
    a.release();
    const after = run(a, 0.6, 10).map((o) => o.anim);
    expect(after).toContain('run_start');
    expect(after[after.length - 1]).toBe('run');
  });
});

describe('PlayerAnimator walking, defense and idles', () => {
  it('walks at low speed and runs at high speed without restarting the stride', () => {
    const a = new PlayerAnimator('right');
    const walk = run(a, 1, 4);
    expect(walk[walk.length - 1].anim).toBe('walk');
    const before = walk[walk.length - 1].frame;
    const after = a.update(DT, { vx: 12 });
    expect(after.anim).toBe('run');
    const n = SPRITES.anims.run.frameCount;   // the cycle wraps, so measure around it
    expect((after.frame - before + n) % n).toBeLessThanOrEqual(1);
    expect(run(a, 1, 4).pop()?.anim).toBe('walk');
  });

  it('walks the ball up the court', () => {
    const a = new PlayerAnimator('right');
    expect(run(a, 1, 4, true).pop()?.anim).toBe('walk_dribble');
  });

  it('backpedals when told to keep facing one way while moving the other', () => {
    const a = new PlayerAnimator('right');
    const out = [];
    for (let i = 0; i < 60; i++) out.push(a.update(DT, { vx: -4, face: 'right' }));
    expect(out[out.length - 1]).toMatchObject({ anim: 'backpedal', facing: 'right' });
    expect(out.some((o) => o.anim.startsWith('turn'))).toBe(false);
  });

  it('slides sideways and holds the stance on defense', () => {
    const a = new PlayerAnimator('left');
    let o = a.update(DT, { vx: 0, defending: true });
    expect(o.anim).toBe('defense_stance');
    for (let i = 0; i < 40; i++) o = a.update(DT, { vx: 0, vy: 5, defending: true, face: 'left' });
    expect(o).toMatchObject({ anim: 'defense_slide', facing: 'left' });
  });

  it('gets hands on hips after waiting, and on knees when tired', () => {
    const a = new PlayerAnimator('right');
    expect(run(a, 6, 0).pop()?.anim).toBe('idle_hips');
    const b = new PlayerAnimator('right');
    expect(b.update(DT, { vx: 0, tired: true }).anim).toBe('idle_knees');
  });

  it('switches hands after behind-the-back and between-the-legs moves', () => {
    const a = new PlayerAnimator('right');
    run(a, 0.3, 0, true);
    a.play('behind_back_up');
    expect(run(a, 1, 0, true).pop()).toMatchObject({ anim: 'dribble_far', hand: 'far' });
    a.play('between_legs_down');
    expect(run(a, 1, 0, true).pop()).toMatchObject({ anim: 'dribble', hand: 'near' });
  });
});

describe('PlayerAnimator run styles and guarding', () => {
  it('runs in the player\'s own style, on the same stride clock', () => {
    const a = new PlayerAnimator('right', { runStyle: 'run_power' });
    const out = run(a, 1.5, 12);
    expect(out[out.length - 1].anim).toBe('run_power');
    expect(a.update(DT, { vx: 12, hasBall: true }).anim).toBe('dribble_run');
  });

  it('pressures the ball handler when guarding on the ball', () => {
    const a = new PlayerAnimator('left');
    expect(a.update(DT, { vx: 0, defending: true, onBall: true }).anim).toBe('guard_on_ball');
    expect(a.update(DT, { vx: 0, defending: true }).anim).toBe('defense_stance');
  });
});
