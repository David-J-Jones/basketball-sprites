/**
 * Readable access to the compact sprite data. spriteData.json stores each
 * frame as a small array (see SpriteData.frameFields); these helpers expand
 * it. Kept free of image requires so it works in tests and plain logic.
 */
import raw from './spriteData.json';
import type { BodyKey } from './features';
import type { AnimName, CompactFrame, FrameData, PieceRef, SpriteData, SpriteFacialHair, SpriteHairStyle } from './types';

export const SPRITE_DATA = raw as unknown as SpriteData;

export function expandFrame(r: CompactFrame): FrameData {
  return {
    skin: r[0], jersey: r[1], trim: r[2], detail: r[3], head: r[4],
    nearHand: r[5], farHand: r[6], ball: r[7], ballDepth: r[8], lift: r[9],
  };
}

/** One frame of an animation for a body (frame index wraps around). */
export function frameData(body: BodyKey, anim: AnimName, frame: number): FrameData {
  const list = SPRITE_DATA.frames[body][anim];
  return expandFrame(list[((frame % list.length) + list.length) % list.length]);
}

/** Every frame of an animation for a body. */
export function framesOf(body: BodyKey, anim: AnimName): FrameData[] {
  return SPRITE_DATA.frames[body][anim].map(expandFrame);
}

const STYLE_INDEX = new Map<string, number>(
  [...SPRITE_DATA.hairStyles, ...SPRITE_DATA.facialHair].map((s, i) => [s, i]),
);

/**
 * The [mask, detail] pieces for a hair style or facial-hair type in a frame,
 * already moved to frame coordinates. Nulls when nothing is drawn.
 */
export function headOverlay(
  f: FrameData,
  style: SpriteHairStyle | SpriteFacialHair,
): [PieceRef | null, PieceRef | null] {
  const [set, hx, hy] = f.head;
  const i = STYLE_INDEX.get(style);
  const pid = i === undefined ? -1 : SPRITE_DATA.overlays[set][i];
  if (pid < 0) return [null, null];
  const place = (r: PieceRef | null): PieceRef | null => (r ? [r[0], r[1] + hx, r[2] + hy] : null);
  const [m, d] = SPRITE_DATA.overlayPairs[pid];
  return [place(m), place(d)];
}
