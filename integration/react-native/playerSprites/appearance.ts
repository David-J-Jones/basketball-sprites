import palettes from './palettes.json';
import type { BuildName, HairStyle, JerseyColors, PlayerLook } from './types';

export type Team = { id: string; name: string; jersey: string; trim: string };

export const TEAMS: Team[] = palettes.teams;
export const WHITE_JERSEY: Team = palettes.white;
export const SKIN_TONES = palettes.skinTones;
export const HAIR_STYLES = palettes.hairStyles as { id: HairStyle; weight: number }[];
export const HAIR_COLORS = palettes.hairColors;

export function teamById(id: string): Team {
  const team = TEAMS.find((t) => t.id === id);
  if (!team) throw new Error(`Unknown team ${id}`);
  return team;
}

export function buildForHeight(inches: number): BuildName {
  if (inches <= palettes.builds.guardMaxInches) return 'guard';
  if (inches <= palettes.builds.wingMaxInches) return 'wing';
  return 'big';
}

/** Small seeded RNG (mulberry32) so a player's look never changes between sessions. */
function rng(seed: number) {
  let a = seed >>> 0;
  return () => {
    a = (a + 0x6d2b79f5) >>> 0;
    let t = a;
    t = Math.imul(t ^ (t >>> 15), t | 1);
    t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

function pickWeighted<T extends { weight: number }>(items: T[], r: number): T {
  const total = items.reduce((sum, it) => sum + it.weight, 0);
  let x = r * total;
  for (const it of items) {
    x -= it.weight;
    if (x <= 0) return it;
  }
  return items[items.length - 1];
}

/**
 * Generate a player's look when the player is created. Pass a stable seed
 * (e.g. hash of the player id) and store the result on the player record.
 */
export function generateLook(seed: number, heightInches: number): PlayerLook {
  const next = rng(seed);
  return {
    build: buildForHeight(heightInches),
    skinTone: SKIN_TONES[Math.floor(next() * SKIN_TONES.length)].id,
    hairStyle: pickWeighted(HAIR_STYLES, next()).id,
    hairColor: pickWeighted(HAIR_COLORS, next()).id,
  };
}

export function skinColor(look: PlayerLook): string {
  return (SKIN_TONES.find((s) => s.id === look.skinTone) ?? SKIN_TONES[0]).color;
}

export function hairColor(look: PlayerLook): string {
  return (HAIR_COLORS.find((h) => h.id === look.hairColor) ?? HAIR_COLORS[0]).color;
}

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
