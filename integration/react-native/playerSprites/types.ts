export type BuildName = 'guard' | 'wing' | 'big';

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
  | 'rebound';

export type HairStyle = 'short' | 'buzz' | 'afro' | 'long_headband';

/** [pieceIndex, x, y]: which atlas piece, and where its top-left sits in the frame. */
export type PieceRef = [piece: number, dx: number, dy: number];

/** [page, sx, sy, w, h]: where a piece lives in the atlas pages. */
export type PieceRect = [page: number, sx: number, sy: number, w: number, h: number];

export type FrameData = {
  skin: PieceRef | null;
  jersey: PieceRef | null;
  trim: PieceRef | null;
  detail: PieceRef | null;
  /** per hair style: [mask (tinted hair color), detail (untinted)] */
  hair: Record<HairStyle, [PieceRef | null, PieceRef | null]>;
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

/** All positions and sizes are in atlas pixels. */
export type SpriteData = {
  scale: number;
  frameWidth: number;
  frameHeight: number;
  anchorX: number;
  anchorY: number;
  pages: [w: number, h: number][];
  pieces: PieceRect[];
  /** idle height, sole to top of the head, per build */
  standingHeight: Record<BuildName, number>;
  anims: Record<AnimName, AnimInfo>;
  frames: Record<BuildName, Record<AnimName, FrameData[]>>;
};

/** What a generated player looks like. Store this on the player record. */
export type PlayerLook = {
  build: BuildName;
  skinTone: string;          // id from palettes.json skinTones
  hairStyle: HairStyle | null; // null = bald
  hairColor: string;         // id from palettes.json hairColors
};

export type JerseyColors = { jersey: string; trim: string };
