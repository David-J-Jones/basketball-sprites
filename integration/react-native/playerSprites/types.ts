import type { BodyKey, HairColorId, SkinToneId } from './features';

export type { BodyKey } from './features';

export type AnimName =
  | 'idle'
  | 'run'
  | 'dribble'
  | 'dribble_run'
  | 'shoot'
  | 'layup'
  | 'pass'
  | 'steal'
  | 'block'
  | 'rebound'
  | 'dunk_basic'
  | 'dunk_athletic'
  | 'dunk_hang';

/** Hair styles drawn on the sprite (bald = no hair overlay). */
export type SpriteHairStyle = 'buzz' | 'fade' | 'crew' | 'cornrows' | 'afro' | 'locs';
/** Facial hair drawn on the sprite (none = no overlay). */
export type SpriteFacialHair = 'stubble' | 'mustache' | 'goatee' | 'beard';

/** [pieceIndex, x, y]: which atlas piece, and where its top-left sits in the frame. */
export type PieceRef = [piece: number, dx: number, dy: number];

/** [page, sx, sy, w, h]: where a piece lives on its atlas page (page pixels). */
export type PieceRect = [page: number, sx: number, sy: number, w: number, h: number];

export type FrameData = {
  skin: PieceRef | null;
  jersey: PieceRef | null;
  trim: PieceRef | null;
  detail: PieceRef | null;
  /** per facial-hair type: [mask (tinted hair color), detail (untinted)] */
  facial: Record<SpriteFacialHair, [PieceRef | null, PieceRef | null]>;
  /** per hair style: [mask (tinted hair color), detail (untinted)] */
  hair: Record<SpriteHairStyle, [PieceRef | null, PieceRef | null]>;
  nearHand: [number, number];
  farHand: [number, number];
  /** where a held/dribbled ball should be drawn (ball centre), or null */
  ball: [number, number] | null;
  /** how far the feet are raised off the floor in this frame (baked jump) */
  lift: number;
};

export type AnimInfo = {
  fps: number;
  loop: boolean;
  frameCount: number;
  /** named frame indices, e.g. { release: 4 } */
  events: Record<string, number>;
};

/** Positions and sizes are in frame pixels unless noted. */
export type SpriteData = {
  /** frame pixels per art pixel */
  scale: number;
  frameWidth: number;
  frameHeight: number;
  anchorX: number;
  anchorY: number;
  /** page sizes, in page pixels */
  pages: [w: number, h: number][];
  /** which body each page belongs to ('heads' = hair/facial hair, shared) */
  pageGroups: string[];
  /** frame pixels per page pixel (1 for detail pages, >1 for tint-mask pages) */
  pageScale: number[];
  pieces: PieceRect[];
  /** idle height, sole to top of the head, per body */
  standingHeight: Record<BodyKey, number>;
  anims: Record<AnimName, AnimInfo>;
  frames: Record<BodyKey, Record<AnimName, FrameData[]>>;
};

/** What a player looks like on court. Derive it with lookFromFace() / playerLook(). */
export type PlayerLook = {
  body: BodyKey;
  skinTone: SkinToneId;
  hairStyle: SpriteHairStyle | null;   // null = bald
  hairColor: HairColorId;
  facialHair: SpriteFacialHair | null; // null = clean-shaven
};

export type JerseyColors = { jersey: string; trim: string };
