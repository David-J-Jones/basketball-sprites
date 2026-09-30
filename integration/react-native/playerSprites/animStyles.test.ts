import { PlayerAnimator } from './animController';
import {
  STYLE_OPTIONS, DEFAULT_ANIM_STYLES, animatorOptions, defaultAnimStyles, dribbleFor, jumperFor, pickDunk, pickLayup,
  type AnimStyles,
} from './animStyles';
import { BODY_KEYS } from './features';
import { framesOf, SPRITE_DATA as SPRITES } from './frames';
import { dribbleAnim, shotFor } from './moves';
import type { AnimName } from './types';

const has = (a: string) => a in SPRITES.anims;

describe('animation styles', () => {
  it('offers at least 5 of each: runs, dribbles, shots, layups, dunks', () => {
    for (const list of Object.values(STYLE_OPTIONS)) expect(list.length).toBeGreaterThanOrEqual(5);
  });

  it('every option resolves to animations that exist for every body', () => {
    const names: string[] = [];
    for (const r of STYLE_OPTIONS.run) names.push(r.id);
    for (const d of STYLE_OPTIONS.dribble) {
      for (const hand of ['near', 'far'] as const) {
        names.push(dribbleAnim(hand, false, false, d.id), dribbleAnim(hand, true, false, d.id),
          dribbleAnim(hand, true, true, d.id));
      }
    }
    for (const s of STYLE_OPTIONS.shot) names.push(shotFor(0, 3, s.id), shotFor(9, 3, s.id), shotFor(-9, 3, s.id));
    for (const l of STYLE_OPTIONS.layup) names.push(l.id);
    for (const d of STYLE_OPTIONS.dunk) names.push(d.id);
    for (const n of names) {
      expect(has(n)).toBe(true);
      for (const body of BODY_KEYS) expect(framesOf(body, n as AnimName).length).toBe(SPRITES.anims[n as AnimName].frameCount);
    }
  });

  it('keeps frame counts and events of the classic version, so logic is style-independent', () => {
    for (const s of STYLE_OPTIONS.shot) {
      for (const speed of [0, 9, -9]) {
        const a = SPRITES.anims[shotFor(speed, 3, s.id)];
        const c = SPRITES.anims[shotFor(speed, 3)];
        expect(a.frameCount).toBe(c.frameCount);
        expect(a.events.release).toBe(c.events.release);
      }
    }
    for (const d of STYLE_OPTIONS.dribble) {
      expect(SPRITES.anims[dribbleAnim('near', true, false, d.id)].frameCount).toBe(SPRITES.anims.run.frameCount);
      expect(SPRITES.anims[dribbleAnim('far', false, false, d.id)].events.bounce).toBe(3);
    }
    for (const r of STYLE_OPTIONS.run) expect(SPRITES.anims[r.id].frameCount).toBe(SPRITES.anims.run.frameCount);
  });

  it('gives stable, body-suited defaults', () => {
    expect(defaultAnimStyles(7, 'h3-lean')).toEqual(defaultAnimStyles(7, 'h3-lean'));
    const count = (body: 'h1-slim' | 'h7-heavy', pick: (s: AnimStyles) => boolean) =>
      Array.from({ length: 400 }, (_, i) => defaultAnimStyles(i + 1, body)).filter(pick).length;
    expect(count('h7-heavy', (s) => s.dribble === 'protect')).toBeGreaterThan(count('h1-slim', (s) => s.dribble === 'protect'));
    expect(count('h1-slim', (s) => s.dribble === 'low')).toBeGreaterThan(count('h7-heavy', (s) => s.dribble === 'low'));
    expect(defaultAnimStyles(3, 'h7-heavy').dunks).toContain('dunk_two_hand');
    const styles = new Set(Array.from({ length: 200 }, (_, i) => defaultAnimStyles(i, 'h4-average').shot));
    expect(styles.size).toBe(5);
  });

  it('plays the chosen styles', () => {
    const s: AnimStyles = { ...DEFAULT_ANIM_STYLES, run: 'run_glide', dribble: 'low', shot: 'kick' };
    expect(jumperFor(s, 9)).toBe('shoot_kick_pullup');
    expect(dribbleFor(s, 'far', true)).toBe('dribble_run_low_far');
    expect(pickLayup(s, 0.99)).toBe('layup_euro');
    expect(pickDunk(s, 0)).toBe('dunk_basic');
    const a = new PlayerAnimator('right', animatorOptions(s));
    expect(a.update(1 / 60, { vx: 0, hasBall: true }).anim).toBe('dribble_low');
    let o = a.update(1 / 60, { vx: 12, hasBall: true });
    for (let i = 0; i < 60; i++) o = a.update(1 / 60, { vx: 12, hasBall: true });
    expect(o.anim).toBe('dribble_run_low');
    for (let i = 0; i < 60; i++) o = a.update(1 / 60, { vx: 12 });
    expect(o.anim).toBe('run_glide');
  });
});
