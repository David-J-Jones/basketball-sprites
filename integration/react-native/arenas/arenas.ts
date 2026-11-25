/**
 * Arena themes the player can pick: everything around the court (backdrop,
 * crowd, floor texture, lighting). Kept free of image requires and React so
 * it works in tests and plain game logic; <ArenaBackdrop> and <ArenaOverlay>
 * draw them, and arenaFloor() hands the floor to the game's court renderer.
 */
import meta from './arenas.json';

export type ArenaId = 'pro_arena' | 'retro_gym' | 'street' | 'neon' | 'beach' | 'rooftop';
/** The image layers of an arena (see tools/generate_arenas.py). */
export type ArenaLayer = 'backdrop' | 'team' | 'crowd' | 'crowd_home' | 'crowd_away' | 'floor' | 'overlay';

export type ArenaInfo = {
  id: ArenaId;
  /** for a selection screen */
  label: string;
  description: string;
  /** the floor texture's kind: maple, honey, concrete, glossy, boards, painted */
  floor: string;
  /** the lighting overlay's kind */
  lighting: string;
  /** court colors that suit the arena: lines, the out-of-bounds apron, a default paint */
  line: string;
  apron: string;
  paint: string;
};

export const ARENA_META = meta as unknown as {
  scale: number;
  /** backdrop size in art px [w, h] */
  backdrop: [number, number];
  floorTile: number;
  /** overlay size in art px (16:9) */
  overlay: [number, number];
  crowdFrames: number;
  crowdLoop: number[];
  crowdFps: number;
  arenas: ArenaInfo[];
};
export const ARENAS: ArenaInfo[] = ARENA_META.arenas;
export const ARENA_IDS = ARENAS.map((a) => a.id);
export const DEFAULT_ARENA: ArenaId = 'pro_arena';

/** The art px a 16:9 screen is laid out in; the backdrop is the top BACKDROP_H of them. */
export const SCREEN_ART_H = ARENA_META.overlay[1];
export const BACKDROP_W = ARENA_META.backdrop[0];
export const BACKDROP_H = ARENA_META.backdrop[1];

export function arenaById(id: string): ArenaInfo | undefined {
  return ARENAS.find((a) => a.id === id);
}

/**
 * Screen px per art px, so the backdrop's pixels match the court's: the
 * screen is SCREEN_ART_H (152) art px tall. At 608 px tall that's 4.
 */
export function arenaScale(screenHeight: number): number {
  return screenHeight / SCREEN_ART_H;
}

/**
 * Crowd frame after `seconds`. excitement 0..1 speeds the crowd up and,
 * past 0.7 (a run, a dunk, a buzzer beater), has everyone on their feet.
 */
export function crowdFrame(seconds: number, excitement = 0): number {
  const loop = excitement > 0.7 ? [2, 1, 2, 0] : ARENA_META.crowdLoop;
  const fps = ARENA_META.crowdFps * (1 + 2 * Math.max(0, Math.min(1, excitement)));
  return loop[Math.floor(Math.max(0, seconds) * fps) % loop.length];
}

/**
 * Left edge of the backdrop on screen, for a camera pan of 0 (left end of the
 * court) .. 1 (right end). The backdrop is wider than the screen, so it
 * scrolls a little slower than the court (parallax).
 */
export function backdropLeft(pan: number, screenWidth: number, scale: number): number {
  const extra = BACKDROP_W * scale - screenWidth;
  return -Math.max(0, extra) * Math.max(0, Math.min(1, pan));
}
