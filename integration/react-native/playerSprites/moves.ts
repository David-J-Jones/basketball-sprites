import type { AnimName } from './types';

/** Which hand has the ball, in screen terms (see README "Directions"). */
export type BallHand = 'near' | 'far';

/**
 * The crossover to play when a ball handler changes direction on screen.
 * dy < 0: cutting up the screen (away from the camera) -> ball goes near hand
 * to far hand. dy > 0: cutting down toward the camera -> far hand to near.
 * Holds whether or not the sprite is flipped.
 */
export function crossoverFor(dy: number): 'crossover_up' | 'crossover_down' {
  return dy < 0 ? 'crossover_up' : 'crossover_down';
}

/** The hand holding the ball after a crossover. */
export function handAfter(anim: 'crossover_up' | 'crossover_down'): BallHand {
  return anim === 'crossover_up' ? 'far' : 'near';
}

/** Dribble animation for the ball hand, standing or on the move. */
export function dribbleAnim(hand: BallHand, moving: boolean): AnimName {
  if (hand === 'far') return moving ? 'dribble_run_far' : 'dribble_far';
  return moving ? 'dribble_run' : 'dribble';
}
