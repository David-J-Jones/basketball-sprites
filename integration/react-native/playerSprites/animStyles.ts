/**
 * Signature animations a player can pick (or be given): run, dribble and
 * jump-shot styles, plus the layups and dunks in his bag. Every style keeps
 * the frame count and event frames of its classic version, so game logic is
 * the same whichever one a player uses.
 */
import { runStyleFor } from './appearance';
import type { AnimatorOptions } from './animController';
import type { BodyKey } from './features';
import { dribbleAnim, shotFor, type BallHand } from './moves';
import type { AnimName, DribbleStyle, DunkAnim, LayupAnim, RunStyle, ShotAnim, ShotStyle } from './types';

export type AnimStyles = {
  run: RunStyle;
  dribble: DribbleStyle;
  shot: ShotStyle;
  /** layups he can use; the game picks among them */
  layups: LayupAnim[];
  /** dunks he can use; the game picks among them */
  dunks: DunkAnim[];
};

export type StyleOption<T extends string> = { id: T; label: string; description: string };

/** Everything a player can choose from, with names for a selection screen. */
export const STYLE_OPTIONS: {
  run: StyleOption<RunStyle>[];
  dribble: StyleOption<DribbleStyle>[];
  shot: StyleOption<ShotStyle>[];
  layup: StyleOption<LayupAnim>[];
  dunk: StyleOption<DunkAnim>[];
} = {
  run: [
    { id: 'run', label: 'Classic', description: 'Balanced, athletic stride' },
    { id: 'run_upright', label: 'Upright', description: 'Tall, smooth, long strides' },
    { id: 'run_power', label: 'Power', description: 'Hunched and heavy, short choppy steps' },
    { id: 'run_bounce', label: 'Bouncy', description: 'Springy, high knees' },
    { id: 'run_glide', label: 'Glide', description: 'Long, low, gliding strides' },
    { id: 'run_loose', label: 'Loose', description: 'Relaxed lope, arms hanging low' },
  ],
  dribble: [
    { id: 'classic', label: 'Classic', description: 'Standard waist-high dribble' },
    { id: 'low', label: 'Low', description: 'Crouched, quick pounds below the knee' },
    { id: 'high', label: 'High', description: 'Tall and casual, high lazy dribble out wide' },
    { id: 'rhythm', label: 'Rhythm', description: 'Bouncy, rocking with the ball' },
    { id: 'protect', label: 'Protect', description: 'Wide base, ball on the hip, off arm up' },
  ],
  shot: [
    { id: 'classic', label: 'Classic', description: 'Textbook set point above the forehead' },
    { id: 'quick', label: 'Quick', description: 'One-motion, low set point, quick release' },
    { id: 'high', label: 'High release', description: 'Big jump, ball set high, high arc' },
    { id: 'kick', label: 'Leg kick', description: 'Legs kick out on the release' },
    { id: 'push', label: 'Push', description: 'Old-school push from the chin, low arc' },
  ],
  layup: [
    { id: 'layup', label: 'Standard', description: 'One hand off the glass' },
    { id: 'layup_finger_roll', label: 'Finger roll', description: 'Palm up, rolled off the fingers' },
    { id: 'layup_euro', label: 'Euro step', description: 'Step one way, then long across' },
    { id: 'layup_reverse', label: 'Reverse', description: 'Under the rim, flipped back over the head' },
    { id: 'layup_scoop', label: 'Scoop', description: 'Underhand scoop from down low' },
    { id: 'layup_floater', label: 'Floater', description: 'Early, soft teardrop off one foot' },
  ],
  dunk: [
    { id: 'dunk_basic', label: 'One hand', description: 'One-hand dunk in stride' },
    { id: 'dunk_athletic', label: 'Two-hand kick', description: 'Two hands, heels kicked up behind' },
    { id: 'dunk_hang', label: 'Hang', description: 'Power it down and hang on the rim' },
    { id: 'dunk_windmill', label: 'Windmill', description: 'Full arm windmill' },
    { id: 'dunk_tomahawk', label: 'Tomahawk', description: 'Cocked behind the head' },
    { id: 'dunk_reverse', label: 'Reverse', description: 'Back to the rim, hammered behind the head' },
    { id: 'dunk_two_hand', label: 'Power two-hand', description: 'Straight up off two feet' },
    { id: 'dunk_cradle', label: 'Cradle', description: 'Rock the cradle, then slam' },
  ],
};

export const DEFAULT_ANIM_STYLES: AnimStyles = {
  run: 'run',
  dribble: 'classic',
  shot: 'classic',
  layups: ['layup', 'layup_finger_roll', 'layup_euro'],
  dunks: ['dunk_basic', 'dunk_athletic'],
};

/** A stable number in [0, 1) for a player id and a salt. */
function seeded(playerId: number, salt: number): number {
  let h = Math.imul((playerId | 0) ^ Math.imul(salt, 0x9e3779b9), 2654435761 | 0);
  h ^= h >>> 15;
  h = Math.imul(h, 0x85ebca6b);
  h ^= h >>> 13;
  return (h >>> 0) / 4294967296;
}

function weighted<T>(x: number, options: [T, number][]): T {
  x *= options.reduce((a, [, w]) => a + w, 0);
  for (const [v, w] of options) {
    x -= w;
    if (x < 0) return v;
  }
  return options[options.length - 1][0];
}

/**
 * Starting styles for a player who hasn't chosen any, stable per id and
 * suited to the body: bigs protect the ball and power it down, small guards
 * dribble low and finish with touch.
 */
export function defaultAnimStyles(playerId: number, body: BodyKey): AnimStyles {
  const h = Number(body[1]);
  const heavy = body.endsWith('solid') || body.endsWith('heavy');
  const big = h >= 6 || (h >= 5 && heavy);
  const small = h <= 3;
  const dribble = weighted<DribbleStyle>(seeded(playerId, 1), [
    ['classic', 2], ['low', small ? 3 : 0.8], ['high', big ? 2 : 1], ['rhythm', small ? 2 : 1], ['protect', big ? 3 : 0.8],
  ]);
  const shot = weighted<ShotStyle>(seeded(playerId, 2), [
    ['classic', 3], ['quick', small ? 2 : 1], ['high', big ? 2 : 1], ['kick', 1], ['push', big ? 1 : 0.4],
  ]);
  const layupExtra = weighted<LayupAnim>(seeded(playerId, 3), [
    ['layup_reverse', 1], ['layup_scoop', small ? 2 : 0.6], ['layup_floater', small ? 2.5 : 0.8],
  ]);
  const dunks: DunkAnim[] = big
    ? ['dunk_two_hand', 'dunk_hang', 'dunk_basic']
    : ['dunk_basic', weighted<DunkAnim>(seeded(playerId, 4), [
      ['dunk_athletic', 2], ['dunk_tomahawk', 1.5], ['dunk_windmill', 1], ['dunk_reverse', 1], ['dunk_cradle', 0.6],
    ])];
  return {
    run: runStyleFor(playerId, body),
    dribble,
    shot,
    layups: ['layup', big ? 'layup_finger_roll' : 'layup_euro', layupExtra],
    dunks,
  };
}

/** PlayerAnimator options for a player's styles: new PlayerAnimator(facing, animatorOptions(styles)). */
export function animatorOptions(styles: AnimStyles): Partial<AnimatorOptions> {
  return { runStyle: styles.run, dribbleStyle: styles.dribble };
}

/** The jumper to play in the player's shot style (set, pull-up or fade; see shotFor). */
export function jumperFor(styles: AnimStyles, speedTowardBasket: number, threshold = 3): ShotAnim {
  return shotFor(speedTowardBasket, threshold, styles.shot);
}

/** Dribble animation in the player's dribble style (see dribbleAnim). */
export function dribbleFor(styles: AnimStyles, hand: BallHand, moving: boolean, walking = false): AnimName {
  return dribbleAnim(hand, moving, walking, styles.dribble);
}

/** One layup from his bag. `rand` is 0..1 (defaults to Math.random). */
export function pickLayup(styles: AnimStyles, rand = Math.random()): LayupAnim {
  return styles.layups[Math.floor(rand * styles.layups.length)] ?? 'layup';
}

/** One dunk from his bag. `rand` is 0..1 (defaults to Math.random). */
export function pickDunk(styles: AnimStyles, rand = Math.random()): DunkAnim {
  return styles.dunks[Math.floor(rand * styles.dunks.length)] ?? 'dunk_basic';
}
