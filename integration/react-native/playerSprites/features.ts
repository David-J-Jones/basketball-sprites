/**
 * Every look option, in index order. A FaceSpec stores indices into these
 * lists, and the in-game sprite look is derived from the same FaceSpec, so
 * the headshot and the sprite always match.
 */
export const SKIN_TONES = ['light', 'medium', 'tan', 'brown', 'deep'] as const;
export const HEAD_SHAPES = ['oval', 'round', 'square', 'long'] as const;
export const EYE_SHAPES = ['almond', 'round', 'hooded', 'deepSet', 'narrow'] as const;
export const NOSES = ['narrow', 'medium', 'broad', 'wide', 'aquiline'] as const;
export const MOUTHS = ['thin', 'medium', 'full', 'smile'] as const;
export const HAIR_STYLES = ['bald', 'buzz', 'fade', 'crew', 'cornrows', 'afro', 'locs'] as const;
export const HAIR_COLORS = ['black', 'darkBrown', 'brown', 'auburn', 'blond', 'bleached'] as const;
export const FACIAL_HAIR = ['none', 'stubble', 'mustache', 'goatee', 'beard'] as const;
export const EYE_COLORS = ['darkBrown', 'brown', 'hazel', 'green', 'blue'] as const;

export type SkinToneId = (typeof SKIN_TONES)[number];
export type HairStyleId = (typeof HAIR_STYLES)[number];
export type HairColorId = (typeof HAIR_COLORS)[number];
export type FacialHairId = (typeof FACIAL_HAIR)[number];
export type EyeColorId = (typeof EYE_COLORS)[number];

/** Body types for the in-game sprites: 5 height classes x 3 weight classes. */
export const HEIGHT_CLASSES = [1, 2, 3, 4, 5] as const;
export const WEIGHT_CLASSES = ['slim', 'average', 'heavy'] as const;
export type HeightClass = (typeof HEIGHT_CLASSES)[number];
export type WeightClass = (typeof WEIGHT_CLASSES)[number];
export type BodyKey = `h${HeightClass}-${WeightClass}`;
export const BODY_KEYS: BodyKey[] = HEIGHT_CLASSES.flatMap((h) =>
  WEIGHT_CLASSES.map((w) => `h${h}-${w}` as BodyKey),
);
