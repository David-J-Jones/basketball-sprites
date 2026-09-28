import type { AnimName, DribbleStyle, ShotAnim, ShotStyle } from './types';

/** Which hand has the ball, in screen terms (see README "Directions"). */
export type BallHand = 'near' | 'far';

/** Dribble moves that switch hands. `_up` goes near -> far, `_down` far -> near. */
export type HandSwitchMove = 'crossover' | 'behind_back' | 'between_legs';

/**
 * The hand-switch move to play when a ball handler changes direction on
 * screen. dy < 0: cutting up the screen (away from the camera). dy > 0:
 * cutting down toward the camera. Holds whether or not the sprite is flipped.
 */
export function handSwitch(move: HandSwitchMove, dy: number): AnimName {
  return `${move}_${dy < 0 ? 'up' : 'down'}` as AnimName;
}

/** Shorthand for handSwitch('crossover', dy). */
export function crossoverFor(dy: number): 'crossover_up' | 'crossover_down' {
  return dy < 0 ? 'crossover_up' : 'crossover_down';
}

/** The hand holding the ball after a hand-switch move (null for any other animation). */
export function handAfter(anim: AnimName): BallHand | null {
  if (!/^(crossover|behind_back|between_legs)_(up|down)$/.test(anim)) return null;
  return anim.endsWith('_up') ? 'far' : 'near';
}

/** Hesitation move for the current ball hand (keeps the same hand). */
export function hesitationFor(hand: BallHand): 'hesitation' | 'hesitation_far' {
  return hand === 'far' ? 'hesitation_far' : 'hesitation';
}

/**
 * Dribble animation for the ball hand: standing, walking, or running, in the
 * player's dribble style (walking uses the one walk_dribble for every style).
 */
export function dribbleAnim(hand: BallHand, moving: boolean, walking = false, style: DribbleStyle = 'classic'): AnimName {
  const far = hand === 'far' ? '_far' : '';
  const st = style === 'classic' ? '' : `_${style}`;
  if (!moving) return `dribble${st}${far}` as AnimName;
  if (walking) return `walk_dribble${far}` as AnimName;
  return `dribble_run${st}${far}` as AnimName;
}

/**
 * Jump shot for how the shooter is moving along the way he faces (toward the
 * basket). Faster than `threshold` toward the basket: pull-up; away from it:
 * fadeaway; otherwise the set shot.
 */
export function shotFor(speedTowardBasket: number, threshold = 3, style: ShotStyle = 'classic'): ShotAnim {
  const base = style === 'classic' ? 'shoot' : `shoot_${style}`;
  if (speedTowardBasket > threshold) return `${base}_pullup` as ShotAnim;
  if (speedTowardBasket < -threshold) return `${base}_fade` as ShotAnim;
  return base as ShotAnim;
}
