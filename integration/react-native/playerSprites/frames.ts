/**
 * Readable access to the compact sprite data. spriteData.json holds what
 * every body shares; each body's frames live in bodies/<body>.json and are
 * loaded (and expanded) the first time a player with that body is drawn.
 * Kept free of image requires so it works in tests and plain logic.
 */
import raw from './spriteData.json';
import { BODY_LOADERS } from './bodyData';
import type { BodyKey } from './features';
import type {
  AnimName, BodyData, CompactFrame, FrameData, HeadwearStyle, PieceRect, PieceRef, PlacedPiece, SpriteData,
  SpriteFacialHair, SpriteHairStyle,
} from './types';

export const SPRITE_DATA = raw as unknown as SpriteData;

function place(table: PieceRect[], r: PieceRef | null, ox = 0, oy = 0): PlacedPiece | null {
  if (!r) return null;
  const [page, sx, sy, w, h] = table[r[0]];
  return [page, sx, sy, w, h, r[1] + ox, r[2] + oy];
}

export function expandFrame(body: BodyData, r: CompactFrame): FrameData {
  const p = (x: PieceRef | null) => place(body.pieces, x);
  return {
    skin: p(r[0]), jersey: p(r[1]), trim: p(r[2]), detail: p(r[3]), head: r[4],
    nearHand: r[5], farHand: r[6], ball: r[7], ballDepth: r[8], lift: r[9],
    shorts: p(r[10]), sock: p(r[11]), shoe: p(r[12]), sole: p(r[13]),
    wear: r[14] ? r[14].map(p) : null,
    prints: r[15] ? r[15].map(p) : null,
  };
}

const loaded = new Map<BodyKey, { data: BodyData; anims: Map<AnimName, FrameData[]> }>();

/** A body's raw data (parsed on first use, then cached). */
export function loadBody(body: BodyKey): BodyData {
  let b = loaded.get(body);
  if (!b) {
    b = { data: BODY_LOADERS[body](), anims: new Map() };
    loaded.set(body, b);
  }
  return b.data;
}

/** Every frame of an animation for a body. */
export function framesOf(body: BodyKey, anim: AnimName): FrameData[] {
  loadBody(body);
  const b = loaded.get(body)!;
  let list = b.anims.get(anim);
  if (!list) {
    list = b.data.frames[anim].map((r) => expandFrame(b.data, r));
    b.anims.set(anim, list);
  }
  return list;
}

/** One frame of an animation for a body (frame index wraps around). */
export function frameData(body: BodyKey, anim: AnimName, frame: number): FrameData {
  const list = framesOf(body, anim);
  return list[((frame % list.length) + list.length) % list.length];
}

const STYLE_INDEX = new Map<string, number>(
  [...SPRITE_DATA.hairStyles, ...SPRITE_DATA.facialHair, ...SPRITE_DATA.headwear].map((s, i) => [s, i]),
);

/**
 * The [mask, detail] pieces for a hair style, facial-hair type or headband
 * in a frame, already moved to frame coordinates. Nulls when nothing is drawn.
 */
export function headOverlay(
  f: FrameData,
  style: SpriteHairStyle | SpriteFacialHair | HeadwearStyle,
): [PlacedPiece | null, PlacedPiece | null] {
  const [set, hx, hy] = f.head;
  const i = STYLE_INDEX.get(style);
  const pid = i === undefined ? -1 : SPRITE_DATA.overlays[set][i];
  if (pid < 0) return [null, null];
  const [m, d] = SPRITE_DATA.overlayPairs[pid];
  return [place(SPRITE_DATA.pieces, m, hx, hy), place(SPRITE_DATA.pieces, d, hx, hy)];
}
