/**
 * Park-mode outfits: which tint goes on each layer. Kept free of React so the
 * game (and tests) can use it directly; PlayerSprite draws the result.
 */
import { SPRITE_DATA } from './frames';
import type { HeadwearStyle, Outfit, ShirtPrint, WearRegion } from './types';

export type OutfitTints = {
  shorts: string;
  sock: string;
  shoe: string;
  sole: string;
  /** a tint per wear region (FrameData.wear order); null = not worn, the skin shows */
  wear: (string | null)[];
  headwear: { style: HeadwearStyle; color: string } | null;
  /** index into FrameData.prints, or null for a plain shirt */
  print: number | null;
};

const PRINT_INDEX = new Map(SPRITE_DATA.prints.map((p, i) => [p.id, i]));

/** The league look: tank top, black shorts, white socks, grey shoes. */
export const LEAGUE_OUTFIT: Outfit = {};

/**
 * Resolve an outfit to layer tints. `shirtColor` is the jersey color (used
 * for sleeves unless the outfit gives its own). `flip` is the sprite's flip,
 * so a one-arm sleeve stays on the same arm when the player turns around.
 */
export function outfitTints(outfit: Outfit | undefined, shirtColor: string, flip = false): OutfitTints {
  const o = outfit ?? {};
  const d = SPRITE_DATA.defaultOutfit;
  const worn: Partial<Record<WearRegion, string>> = {};
  const print = o.shirt?.print ? PRINT_INDEX.get(o.shirt.print) ?? null : null;
  // printed shirts are tees: the print covers the short sleeves
  const sleeves = o.shirt?.sleeves === 'long' ? 'long' : print !== null ? 'short' : o.shirt?.sleeves ?? 'none';
  const sleeveColor = o.shirt?.sleeveColor ?? shirtColor;
  if (sleeves !== 'none') worn.sleeveShort = sleeveColor;
  if (sleeves === 'long') worn.sleeveLong = sleeveColor;
  if (o.armSleeve) {
    // the near (camera-side) arm is the right arm when facing right (not flipped)
    const nearIsRight = !flip;
    worn[(o.armSleeve.arm === 'right') === nearIsRight ? 'armSleeveNear' : 'armSleeveFar'] = o.armSleeve.color;
  }
  if (o.wristbands) worn.wristband = o.wristbands.color;
  const shorts = o.shorts?.color ?? d.shorts;
  if (o.shorts?.length === 'long') worn.shortsLong = shorts;
  const sock = o.socks?.color ?? d.sock;
  if (o.socks?.tall) worn.sockTall = sock;
  return {
    shorts,
    sock,
    shoe: o.shoes?.color ?? d.shoe,
    sole: o.shoes?.sole ?? d.sole,
    wear: SPRITE_DATA.wearRegions.map((r) => worn[r] ?? null),
    headwear: o.headband ?? null,
    print,
  };
}

export type CosmeticOption<T> = { id: string; label: string; value: T };

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
  ] as CosmeticOption<'standard' | 'long'>[],
  headbands: [
    { id: 'headband', label: 'Headband', value: 'headband' },
    { id: 'wide_headband', label: 'Sweatband', value: 'wide_headband' },
    { id: 'tied_headband', label: 'Tied headband', value: 'tied_headband' },
  ] as CosmeticOption<HeadwearStyle>[],
  prints: SPRITE_DATA.prints.map((p) => ({ id: p.id, label: p.label, value: p.id })) as CosmeticOption<ShirtPrint>[],
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
