import type { BodyKey, HairColorId, SkinToneId } from './features';

export type { BodyKey } from './features';

export type AnimName =
  | 'idle' | 'idle_hips' | 'idle_knees'
  | 'walk' | 'walk_dribble' | 'walk_dribble_far' | 'backpedal'
  | 'run' | 'run_upright' | 'run_power' | 'run_bounce' | 'run_start' | 'run_stop'
  | 'turn' | 'turn_run' | 'turn_dribble'
  | 'dribble' | 'dribble_run' | 'dribble_far' | 'dribble_run_far'
  | 'crossover_up' | 'crossover_down' | 'behind_back_up' | 'behind_back_down'
  | 'between_legs_up' | 'between_legs_down' | 'hesitation' | 'hesitation_far'
  | 'shoot' | 'shoot_pullup' | 'shoot_fade'
  | 'layup' | 'layup_finger_roll' | 'layup_euro'
  | 'dunk_basic' | 'dunk_athletic' | 'dunk_hang' | 'dunk_windmill' | 'dunk_tomahawk'
  | 'pass' | 'steal' | 'block' | 'rebound'
  | 'screen_set' | 'screen_hold' | 'screen_contact'
  | 'defense_stance' | 'defense_slide' | 'defense_hands_up' | 'guard_on_ball'
  | 'celebrate' | 'point_up' | 'frustrated'
  | 'post_up' | 'post_hook' | 'post_fadeaway' | 'post_fade_one_leg' | 'spin_move'
  | 'run_glide' | 'run_loose'
  | `dribble_${StyledDribble}` | `dribble_${StyledDribble}_far`
  | `dribble_run_${StyledDribble}` | `dribble_run_${StyledDribble}_far`
  | `shoot_${StyledShot}` | `shoot_${StyledShot}_pullup` | `shoot_${StyledShot}_fade`
  | 'layup_reverse' | 'layup_scoop' | 'layup_floater'
  | 'dunk_reverse' | 'dunk_two_hand' | 'dunk_cradle';

/** The six run cycles; they all share one stride clock (see runStyleFor). */
export type RunStyle = 'run' | 'run_upright' | 'run_power' | 'run_bounce' | 'run_glide' | 'run_loose';

/** Dribble styles. 'classic' is dribble / dribble_run; the rest are dribble_<style>, dribble_run_<style>. */
export type DribbleStyle = 'classic' | 'low' | 'high' | 'rhythm' | 'protect';
type StyledDribble = Exclude<DribbleStyle, 'classic'>;

/** Jump-shot styles. 'classic' is shoot / shoot_pullup / shoot_fade; the rest are shoot_<style>[_pullup|_fade]. */
export type ShotStyle = 'classic' | 'quick' | 'high' | 'kick' | 'push';
type StyledShot = Exclude<ShotStyle, 'classic'>;

export type ShotAnim = 'shoot' | 'shoot_pullup' | 'shoot_fade'
  | `shoot_${StyledShot}` | `shoot_${StyledShot}_pullup` | `shoot_${StyledShot}_fade`;
export type LayupAnim = 'layup' | 'layup_finger_roll' | 'layup_euro' | 'layup_reverse' | 'layup_scoop' | 'layup_floater';
export type DunkAnim = 'dunk_basic' | 'dunk_athletic' | 'dunk_hang' | 'dunk_windmill' | 'dunk_tomahawk'
  | 'dunk_reverse' | 'dunk_two_hand' | 'dunk_cradle';

/** Hair styles drawn on the sprite (bald = no hair overlay). */
export type SpriteHairStyle =
  | 'buzz' | 'fade' | 'crew' | 'cornrows' | 'afro' | 'locs' | 'mohawk' | 'high_top' | 'twists' | 'curly' | 'flow';
/** Facial hair drawn on the sprite (none = no overlay). */
export type SpriteFacialHair = 'stubble' | 'mustache' | 'goatee' | 'beard' | 'chinstrap' | 'long_beard';

/** [pieceIndex, x, y]: which atlas piece, and where its top-left sits in the frame. */
export type PieceRef = [piece: number, dx: number, dy: number];

/** [page, sx, sy, w, h]: where a piece lives on its atlas page (page pixels). */
export type PieceRect = [page: number, sx: number, sy: number, w: number, h: number];

export type FrameData = {
  skin: PieceRef | null;
  jersey: PieceRef | null;
  trim: PieceRef | null;
  detail: PieceRef | null;
  /** [overlay set, headX, headY]: hair / facial hair are placed at the head (see headOverlay) */
  head: [overlaySet: number, hx: number, hy: number];
  nearHand: [number, number];
  farHand: [number, number];
  /** where a held/dribbled ball should be drawn (ball centre), or null */
  ball: [number, number] | null;
  /**
   * Which side of the body the ball is on: +1 = near side (toward the
   * camera, lower on screen), 0 = centred in front, -1 = far side (away from
   * the camera, higher on screen). Draw the ball behind the player when < 0.
   */
  ballDepth: number | null;
  /** how far the feet are raised off the floor in this frame (baked jump) */
  lift: number;
};

/** How a frame is stored in spriteData.json; expand with frameData(). */
export type CompactFrame = [
  skin: PieceRef | null, jersey: PieceRef | null, trim: PieceRef | null, detail: PieceRef | null,
  head: [number, number, number], nearHand: [number, number], farHand: [number, number],
  ball: [number, number] | null, ballDepth: number | null, lift: number,
];

export type AnimInfo = {
  fps: number;
  loop: boolean;
  frameCount: number;
  /** atlas page group: core, moves, finish, extras, or a run style */
  group: string;
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
  /** hair styles, then facial-hair types: the column order of each overlay set */
  hairStyles: SpriteHairStyle[];
  facialHair: SpriteFacialHair[];
  /** unique [mask, detail] overlay pieces, positioned relative to the head */
  overlayPairs: [PieceRef | null, PieceRef | null][];
  /** overlay sets: one overlayPairs index per style (-1 = nothing drawn) */
  overlays: number[][];
  frameFields: string[];
  /** idle height, sole to top of the head, per body */
  standingHeight: Record<BodyKey, number>;
  anims: Record<AnimName, AnimInfo>;
  frames: Record<BodyKey, Record<AnimName, CompactFrame[]>>;
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
