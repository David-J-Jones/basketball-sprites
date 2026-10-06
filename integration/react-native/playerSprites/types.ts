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
  | 'dunk_reverse' | 'dunk_two_hand' | 'dunk_cradle'
  | 'dance_two_step' | 'dance_shimmy' | 'dance_robot'
  | 'victory_flex' | 'victory_arms_up' | 'victory_bow' | 'victory_cool' | 'victory_roar';

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

/** A piece ready to draw: its atlas rect plus where its top-left sits in the frame. */
export type PlacedPiece = [page: number, sx: number, sy: number, w: number, h: number, dx: number, dy: number];

/** Full-color shirt prints for park-mode tees (see Outfit.shirt.print). */
export type ShirtPrint =
  | 'hawaiian' | 'tie_dye' | 'wave' | 'us_flag' | 'camo' | 'flames' | 'checker' | 'galaxy' | 'plaid'
  | 'retro_stripes' | 'polka_dots' | 'lightning' | 'suit_brown';

/** Headbands, drawn over the hair (see Outfit). */
export type HeadwearStyle = 'headband' | 'wide_headband' | 'tied_headband';

/** Skin areas an outfit can cover, in the order of FrameData.wear. */
export type WearRegion =
  | 'sleeveShort' | 'sleeveLong' | 'armSleeveNear' | 'armSleeveFar' | 'wristband' | 'shortsLong' | 'sockTall'
  | 'pantsLong';

export type FrameData = {
  skin: PlacedPiece | null;
  jersey: PlacedPiece | null;
  trim: PlacedPiece | null;
  detail: PlacedPiece | null;
  shorts: PlacedPiece | null;
  sock: PlacedPiece | null;
  shoe: PlacedPiece | null;
  sole: PlacedPiece | null;
  /** one mask per WearRegion (drawn over the skin only when the outfit covers it), or null */
  wear: (PlacedPiece | null)[] | null;
  /** one full-color piece per shirt print (SpriteData.prints order): torso and short sleeves */
  prints: (PlacedPiece | null)[] | null;
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
  shorts: PieceRef | null, sock: PieceRef | null, shoe: PieceRef | null, sole: PieceRef | null,
  wear: (PieceRef | null)[] | null, prints: (PieceRef | null)[] | null,
];

/** One body's own pieces and frames (bodies/<body>.json, loaded on first use). */
export type BodyData = {
  pieces: PieceRect[];
  frames: Record<AnimName, CompactFrame[]>;
};

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
  /** shared pieces (hair, facial hair, headwear); body pieces are in BodyData */
  pieces: PieceRect[];
  /** hair styles, then facial-hair types, then headwear: the column order of each overlay set */
  hairStyles: SpriteHairStyle[];
  facialHair: SpriteFacialHair[];
  headwear: HeadwearStyle[];
  wearRegions: WearRegion[];
  prints: { id: ShirtPrint; label: string }[];
  /** league colors for shorts, socks, shoes and soles */
  defaultOutfit: { shorts: string; sock: string; shoe: string; sole: string };
  /** unique [mask, detail] overlay pieces, positioned relative to the head */
  overlayPairs: [PieceRef | null, PieceRef | null][];
  /** overlay sets: one overlayPairs index per style (-1 = nothing drawn) */
  overlays: number[][];
  frameFields: string[];
  /** idle height, sole to top of the head, per body */
  standingHeight: Record<BodyKey, number>;
  anims: Record<AnimName, AnimInfo>;
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

/**
 * Park-mode cosmetics. Everything is optional; left out, a player wears the
 * league look (tank top, black shorts, white socks, grey shoes). The shirt's
 * colors are the `colors` (jersey / trim) passed to PlayerSprite.
 */
export type Outfit = {
  shirt?: {
    /** 'none' = tank top */
    sleeves?: 'none' | 'short' | 'long';
    /** defaults to the shirt color; a different color reads as a compression shirt under the top */
    sleeveColor?: string;
    /**
     * A printed tee (Hawaiian, tie-dye, US flag...). The print covers the
     * torso and short sleeves in its own colors; the collar and arm trim
     * still use `colors.trim`. Printed shirts always have at least short sleeves.
     */
    print?: ShirtPrint;
    /** Developer-only animated shirt treatment; color is resolved at render time. */
    effect?: 'developer_neon';
  };
  /** 'pants' = full-length trousers (socks take the same color so the leg reads as one piece) */
  shorts?: { color?: string; length?: 'standard' | 'long' | 'pants' };
  socks?: { color?: string; tall?: boolean };
  shoes?: { color?: string; sole?: string };
  headband?: { style: HeadwearStyle; color: string } | null;
  wristbands?: { color: string } | null;
  /** shooting sleeve on one arm (stays on that arm whichever way the player faces) */
  armSleeve?: { color: string; arm: 'right' | 'left' } | null;
};
