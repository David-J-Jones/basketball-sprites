/**
 * Park-mode outfits: which tint goes on each layer. Kept free of React so the
 * game (and tests) can use it directly; PlayerSprite draws the result.
 */
import { SPRITE_DATA } from './frames';
import type {
  HatStyle, HeadwearStyle, JerseyColors, Outfit, PantsStyle, ShirtPrint, SpriteHeadwear, WearRegion,
} from './types';

export type OutfitTints = {
  /** the shirt color to draw (differs from colors.jersey for a color-shifting shirt) */
  shirt: string;
  shorts: string;
  sock: string;
  shoe: string;
  sole: string;
  /** a tint per wear region (FrameData.wear order); null = not worn, the skin shows */
  wear: (string | null)[];
  /** the head overlay to draw (a hat, or a headband) and its tint */
  headwear: { style: SpriteHeadwear; color: string } | null;
  /** hats hide the hair; the goat head hides the facial hair too */
  hideHair: boolean;
  hideFacial: boolean;
  /** index into FrameData.prints, or null for a plain shirt */
  print: number | null;
  /** index into FrameData.legPrints, or null */
  legPrint: number | null;
};

const PRINT_INDEX = new Map(SPRITE_DATA.prints.map((p, i) => [p.id, i]));
const LEG_PRINT_INDEX = new Map(SPRITE_DATA.legPrints.map((p, i) => [p.id, i]));

/** Default tints for hats whose color can be chosen. */
export const HAT_COLORS: Partial<Record<HatStyle, string>> = {
  top_hat: '#1c1c22', cap_forward: '#d62b2b', cap_backward: '#2c5fd6', fedora: '#6b5a48', cat_ears: '#2a2a30',
  goat_head: '#eeeade',
};
/** Color options for the hats that take a color (the halo, fishbowl and propeller hat have their own). */
export const HAT_COLOR_OPTIONS: Partial<Record<HatStyle, { id: string; label: string; value: string }[]>> = {
  top_hat: [
    { id: 'black', label: 'Black', value: '#1c1c22' }, { id: 'white', label: 'White', value: '#f0f0f0' },
    { id: 'purple', label: 'Purple', value: '#7a3ac8' }, { id: 'red', label: 'Red', value: '#c82830' },
    { id: 'green', label: 'Green', value: '#2e8250' }, { id: 'brown', label: 'Brown', value: '#6e5032' },
  ],
  cap_forward: [
    { id: 'red', label: 'Red', value: '#d62828' }, { id: 'black', label: 'Black', value: '#1c1c22' },
    { id: 'royal', label: 'Royal', value: '#2c5fd6' }, { id: 'white', label: 'White', value: '#f0f0f0' },
    { id: 'green', label: 'Green', value: '#2ea050' }, { id: 'gold', label: 'Gold', value: '#ffc828' },
  ],
  cap_backward: [
    { id: 'royal', label: 'Royal', value: '#2c5fd6' }, { id: 'red', label: 'Red', value: '#d62828' },
    { id: 'black', label: 'Black', value: '#1c1c22' }, { id: 'orange', label: 'Orange', value: '#ff7828' },
    { id: 'pink', label: 'Pink', value: '#f064aa' }, { id: 'green', label: 'Green', value: '#2ea050' },
  ],
  fedora: [
    { id: 'brown', label: 'Brown', value: '#6b5a48' }, { id: 'grey', label: 'Grey', value: '#464650' },
    { id: 'black', label: 'Black', value: '#1c1c22' }, { id: 'tan', label: 'Tan', value: '#c4aa78' },
    { id: 'wine', label: 'Wine', value: '#962832' }, { id: 'white', label: 'White', value: '#f0f0f0' },
  ],
  cat_ears: [
    { id: 'black', label: 'Black', value: '#28282e' }, { id: 'white', label: 'White', value: '#f0f0f0' },
    { id: 'pink', label: 'Pink', value: '#f08cb4' }, { id: 'orange', label: 'Ginger', value: '#e68c3c' },
    { id: 'grey', label: 'Grey', value: '#9696a0' }, { id: 'purple', label: 'Purple', value: '#7a3ac8' },
  ],
  goat_head: [
    { id: 'white', label: 'White', value: '#eeeade' }, { id: 'black', label: 'Black', value: '#28282e' },
    { id: 'brown', label: 'Brown', value: '#825a3c' }, { id: 'grey', label: 'Grey', value: '#c8c8cd' },
    { id: 'tan', label: 'Tan', value: '#e6be8c' }, { id: 'cocoa', label: 'Cocoa', value: '#a0785a' },
  ],
};

/** Propeller spin speed, frames per second (4 frames per turn). */
export const PROPELLER_FPS = 14;

/** The league look: tank top, black shorts, white socks, grey shoes. */
export const LEAGUE_OUTFIT: Outfit = {};

function hsl(h: number, s: number, l: number): string {
  const f = (n: number) => {
    const k = (n + h * 12) % 12;
    const a = s * Math.min(l, 1 - l);
    const c = l - a * Math.max(-1, Math.min(k - 3, 9 - k, 1));
    return Math.round(c * 255).toString(16).padStart(2, '0');
  };
  return `#${f(0)}${f(8)}${f(4)}`;
}

function darken(hex: string, k: number): string {
  const n = parseInt(hex.replace('#', ''), 16);
  const c = [(n >> 16) & 255, (n >> 8) & 255, n & 255].map((v) => Math.round(v * k).toString(16).padStart(2, '0'));
  return `#${c.join('')}`;
}

type ColorShift = NonNullable<NonNullable<Outfit['shirt']>['colorShift']>;

/** The color of a color-shifting shirt at `time` seconds. */
export function shiftingColor(time: number, shift: ColorShift = {}): string {
  const period = shift.period ?? 8;
  const hue = (((time / period) % 1) + 1) % 1;
  return hsl(hue, shift.saturation ?? 0.75, shift.lightness ?? 0.55);
}

/**
 * Resolve an outfit to layer tints. `shirtColor` is the jersey color (used
 * for sleeves unless the outfit gives its own). `flip` is the sprite's flip,
 * so a one-arm sleeve stays on the same arm when the player turns around.
 * `time` (seconds) drives a color-shifting shirt and the propeller hat.
 */
export function outfitTints(outfit: Outfit | undefined, shirtColor: string, flip = false, time = 0): OutfitTints {
  const o = outfit ?? {};
  const d = SPRITE_DATA.defaultOutfit;
  const worn: Partial<Record<WearRegion, string>> = {};
  const shirt = o.shirt?.colorShift ? shiftingColor(time, o.shirt.colorShift) : shirtColor;
  const print = o.shirt?.print ? PRINT_INDEX.get(o.shirt.print) ?? null : null;
  // printed shirts are tees: the print covers the short sleeves
  const sleeves = o.shirt?.sleeves === 'long' ? 'long' : print !== null ? 'short' : o.shirt?.sleeves ?? 'none';
  const sleeveColor = o.shirt?.sleeveColor ?? shirt;
  if (sleeves !== 'none') worn.sleeveShort = sleeveColor;
  if (sleeves === 'long') worn.sleeveLong = sleeveColor;
  if (o.armSleeve) {
    // the near (camera-side) arm is the right arm when facing right (not flipped)
    const nearIsRight = !flip;
    worn[(o.armSleeve.arm === 'right') === nearIsRight ? 'armSleeveNear' : 'armSleeveFar'] = o.armSleeve.color;
  }
  if (o.wristbands) worn.wristband = o.wristbands.color;
  const shorts = o.shorts?.color ?? d.shorts;
  // parachute pants are always full length
  const pants = o.shorts?.length === 'pants' || o.shorts?.style === 'parachute';
  if (o.shorts?.length === 'long' || pants) worn.shortsLong = shorts;
  if (pants) worn.pantsLong = shorts;
  let sock = pants ? shorts : o.socks?.color ?? d.sock;
  if (o.socks?.tall && !pants) worn.sockTall = sock;
  const shoe = o.shoes?.color ?? d.shoe;
  if (o.shoes?.style === 'cowboy_boots') {
    // boots go over the socks (and trouser cuffs) up to mid-shin
    sock = shoe;
    worn.bootShaft = shoe;
    worn.bootTop = o.shoes.topColor ?? darken(shoe, 0.62);
  }
  let headwear: OutfitTints['headwear'] = o.headband ?? null;
  if (o.hat) {
    const style = (o.hat.style === 'propeller_hat'
      ? `propeller_hat_${Math.floor(Math.max(0, time) * PROPELLER_FPS) % 4}`
      : o.hat.style) as SpriteHeadwear;
    headwear = { style, color: o.hat.color ?? HAT_COLORS[o.hat.style] ?? '#ffffff' };
  }
  const hides = headwear ? SPRITE_DATA.headwearHides[headwear.style] ?? [] : [];
  return {
    shirt,
    shorts,
    sock,
    shoe,
    sole: o.shoes?.sole ?? d.sole,
    wear: SPRITE_DATA.wearRegions.map((r) => worn[r] ?? null),
    headwear,
    hideHair: hides.includes('hair'),
    hideFacial: hides.includes('facial'),
    print,
    legPrint: o.shorts?.style ? LEG_PRINT_INDEX.get(o.shorts.style) ?? null : null,
  };
}

export type CosmeticOption<T> = { id: string; label: string; value: T };

export type OutfitPreset = {
  id: string;
  label: string;
  outfit: Outfit;
  colors: JerseyColors;
  /** only for the account(s) your game marks as developers; never sold in the store */
  exclusive?: 'developer';
};

/** Bright nylon colors for parachute pants (any tint works). */
export const PARACHUTE_COLORS = { purple: '#8a3cf0', pink: '#ff4fb3', green: '#2ee06a', red: '#ff3b3b' };

/** Complete looks: pass `outfit` and `colors` to PlayerSprite. */
export const OUTFIT_PRESETS: OutfitPreset[] = [
  {
    id: 'brown_suit',
    label: 'Brown suit',
    // brown jacket with a white tie and pocket square, matching trousers, brown dress shoes
    outfit: {
      shirt: { print: 'suit_brown', sleeves: 'long', sleeveColor: '#7a4a26' },
      shorts: { color: '#6e4222', length: 'pants' },
      shoes: { color: '#3b2416', sole: '#1c120c' },
    },
    colors: { jersey: '#7a4a26', trim: '#4e2c14' },
  },
  {
    id: 'developer_tee',
    label: 'Developer tee',
    // a plain tee that keeps shifting through the rainbow; developer only
    outfit: {
      shirt: { sleeves: 'short', colorShift: { period: 8 } },
      shorts: { color: '#26262c' },
      shoes: { color: '#f2f2f4', sole: '#26262c' },
    },
    colors: { jersey: '#ffffff', trim: '#f2f2f4' },
    exclusive: 'developer',
  },
  ...(['purple', 'pink', 'green', 'red'] as const).map((c): OutfitPreset => ({
    id: `parachute_${c}`,
    label: `Parachute pants (${c})`,
    outfit: { shorts: { color: PARACHUTE_COLORS[c], style: 'parachute' } },
    colors: { jersey: '#f2f2f4', trim: '#26262c' },
  })),
  {
    id: 'cowboy',
    label: 'Cowboy boots',
    outfit: { shoes: { style: 'cowboy_boots', color: '#7a4520', sole: '#3a2010' } },
    colors: { jersey: '#f2f2f4', trim: '#26262c' },
  },
];

/**
 * Presets a player may use: exclusive ones only for developer accounts.
 * The game decides who is a developer (e.g. by account id on your server).
 */
export function presetsFor(isDeveloper: boolean): OutfitPreset[] {
  return OUTFIT_PRESETS.filter((p) => !p.exclusive || isDeveloper);
}

/** Ready-made pieces for a park-mode locker (colors are suggestions; any hex works). */
export const COSMETICS = {
  sleeves: [
    { id: 'tank', label: 'Tank top', value: 'none' },
    { id: 'tee', label: 'T-shirt', value: 'short' },
    { id: 'long', label: 'Long sleeve', value: 'long' },
  ] as CosmeticOption<'none' | 'short' | 'long'>[],
  shortsLength: [
    { id: 'standard', label: 'Standard', value: 'standard' },
    { id: 'long', label: 'Long / baggy', value: 'long' },
    { id: 'pants', label: 'Trousers', value: 'pants' },
  ] as CosmeticOption<'standard' | 'long' | 'pants'>[],
  headbands: [
    { id: 'headband', label: 'Headband', value: 'headband' },
    { id: 'wide_headband', label: 'Sweatband', value: 'wide_headband' },
    { id: 'tied_headband', label: 'Tied headband', value: 'tied_headband' },
  ] as CosmeticOption<HeadwearStyle>[],
  prints: SPRITE_DATA.prints.map((p) => ({ id: p.id, label: p.label, value: p.id })) as CosmeticOption<ShirtPrint>[],
  hats: [
    { id: 'top_hat', label: 'Top hat', value: 'top_hat' },
    { id: 'cap_forward', label: 'Ball cap', value: 'cap_forward' },
    { id: 'cap_backward', label: 'Ball cap (backwards)', value: 'cap_backward' },
    { id: 'halo', label: 'Halo', value: 'halo' },
    { id: 'cat_ears', label: 'Cat ears', value: 'cat_ears' },
    { id: 'fedora', label: 'Fedora', value: 'fedora' },
    { id: 'goat_head', label: 'Goat head', value: 'goat_head' },
    { id: 'fishbowl', label: 'Fishbowl', value: 'fishbowl' },
    { id: 'propeller_hat', label: 'Propeller hat', value: 'propeller_hat' },
  ] as CosmeticOption<HatStyle>[],
  pants: SPRITE_DATA.legPrints.map((p) => ({ id: p.id, label: p.label, value: p.id })) as CosmeticOption<PantsStyle>[],
  shoes: [
    { id: 'sneakers', label: 'Sneakers', value: 'sneakers' },
    { id: 'cowboy_boots', label: 'Cowboy boots', value: 'cowboy_boots' },
  ] as CosmeticOption<'sneakers' | 'cowboy_boots'>[],
  colors: [
    { id: 'black', label: 'Black', value: '#26262c' },
    { id: 'white', label: 'White', value: '#f2f2f4' },
    { id: 'grey', label: 'Grey', value: '#9a9ca6' },
    { id: 'red', label: 'Red', value: '#d62b2b' },
    { id: 'orange', label: 'Orange', value: '#f07a1a' },
    { id: 'gold', label: 'Gold', value: '#f2c230' },
    { id: 'green', label: 'Green', value: '#2f9e4f' },
    { id: 'teal', label: 'Teal', value: '#1fa6a0' },
    { id: 'royal', label: 'Royal', value: '#2c5fd6' },
    { id: 'navy', label: 'Navy', value: '#1d2a5c' },
    { id: 'purple', label: 'Purple', value: '#7a3fc4' },
    { id: 'pink', label: 'Pink', value: '#f06aa8' },
  ] as CosmeticOption<string>[],
};
