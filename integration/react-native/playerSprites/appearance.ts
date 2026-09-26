import { faceFromSeed, type FaceSpec } from './faceArt';
import {
  FACIAL_HAIR,
  HAIR_COLORS,
  HAIR_STYLES,
  SKIN_TONES,
  type BodyKey,
  type HeightClass,
  type WeightClass,
} from './features';
import palettes from './palettes.json';
import type { JerseyColors, PlayerLook, SpriteFacialHair, SpriteHairStyle } from './types';

export type Team = { id: string; name: string; jersey: string; trim: string };

export const TEAMS: Team[] = palettes.teams;
export const WHITE_JERSEY: Team = palettes.white;

export function teamById(id: string): Team {
  const team = TEAMS.find((t) => t.id === id);
  if (!team) throw new Error(`Unknown team ${id}`);
  return team;
}

// ------------------------------------------------------------------ bodies

export function heightClass(inches: number): HeightClass {
  for (const c of palettes.heightClasses) {
    if (c.maxInches === null || inches <= c.maxInches) return c.class as HeightClass;
  }
  return 5;
}

/** Weight class from BMI (703 x lbs / inches^2); cutoffs live in palettes.json. */
export function weightClass(inches: number, lbs: number): WeightClass {
  const bmi = (703 * lbs) / (inches * inches);
  if (bmi < palettes.weightClasses.slimBelowBmi) return 'slim';
  if (bmi >= palettes.weightClasses.heavyFromBmi) return 'heavy';
  return 'average';
}

export function bodyFor(heightInches: number, weightLbs: number): BodyKey {
  return `h${heightClass(heightInches)}-${weightClass(heightInches, weightLbs)}`;
}

// ------------------------------------------------------------------ looks

/** The on-court look for a face, so the sprite always matches the headshot. */
export function lookFromFace(face: FaceSpec, heightInches: number, weightLbs: number): PlayerLook {
  const hair = HAIR_STYLES[face.hair];
  const facial = FACIAL_HAIR[face.facialHair];
  return {
    body: bodyFor(heightInches, weightLbs),
    skinTone: SKIN_TONES[face.skin],
    hairStyle: hair === 'bald' ? null : (hair as SpriteHairStyle),
    hairColor: HAIR_COLORS[face.hairColor],
    facialHair: facial === 'none' ? null : (facial as SpriteFacialHair),
  };
}

/** Everything from the player's numeric id (the same seed as the headshot). */
export function playerLook(playerId: number, heightInches: number, weightLbs: number): PlayerLook {
  return lookFromFace(faceFromSeed(playerId), heightInches, weightLbs);
}

export function skinColor(look: PlayerLook): string {
  return (palettes.skinTones.find((s) => s.id === look.skinTone) ?? palettes.skinTones[0]).color;
}

export function hairColor(look: PlayerLook): string {
  return (palettes.hairColors.find((h) => h.id === look.hairColor) ?? palettes.hairColors[0]).color;
}

// ------------------------------------------------------------------ jerseys

export function teamColors(team: Team): JerseyColors {
  return { jersey: team.jersey, trim: team.trim };
}

/** The white jersey, with the team's own color as the trim. */
export function whiteColors(team: Team): JerseyColors {
  return { jersey: WHITE_JERSEY.jersey, trim: team.jersey };
}

function rgb(hex: string): [number, number, number] {
  const n = parseInt(hex.replace('#', ''), 16);
  return [(n >> 16) & 255, (n >> 8) & 255, n & 255];
}

/** Rough perceptual distance between two colors (0 = identical, ~765 max). */
export function colorDistance(a: string, b: string): number {
  const [r1, g1, b1] = rgb(a);
  const [r2, g2, b2] = rgb(b);
  const rMean = (r1 + r2) / 2;
  const dr = r1 - r2;
  const dg = g1 - g2;
  const db = b1 - b2;
  return Math.sqrt((2 + rMean / 256) * dr * dr + 4 * dg * dg + (2 + (255 - rMean) / 256) * db * db);
}

/**
 * Jerseys for a game. The home team wears its color. The away team wears its
 * color too, unless it is hard to tell apart from the home team, then white.
 */
export function jerseysForGame(
  home: Team,
  away: Team,
  minDistance = 150,
): { home: JerseyColors; away: JerseyColors } {
  const clash = colorDistance(home.jersey, away.jersey) < minDistance;
  return { home: teamColors(home), away: clash ? whiteColors(away) : teamColors(away) };
}
