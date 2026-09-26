import {
  bodyFor,
  jerseysForGame,
  lookFromFace,
  playerLook,
  teamById,
  TEAMS,
  WHITE_JERSEY,
} from './appearance';
import { faceFromSeed } from './faceArt';
import { BODY_KEYS, FACIAL_HAIR, HAIR_COLORS, HAIR_STYLES, SKIN_TONES } from './features';
import raw from './spriteData.json';
import type { AnimName, SpriteData } from './types';

const SPRITES = raw as unknown as SpriteData;

describe('sprite look', () => {
  it('matches the headshot face for the same player id', () => {
    for (let id = 1; id <= 300; id++) {
      const face = faceFromSeed(id);
      const look = playerLook(id, 78, 215);
      expect(look.skinTone).toBe(SKIN_TONES[face.skin]);
      expect(look.hairColor).toBe(HAIR_COLORS[face.hairColor]);
      expect(look.hairStyle ?? 'bald').toBe(HAIR_STYLES[face.hair]);
      expect(look.facialHair ?? 'none').toBe(FACIAL_HAIR[face.facialHair]);
      expect(look).toEqual(lookFromFace(face, 78, 215));
    }
  });

  it('picks 5 height classes and 3 weight classes', () => {
    expect(bodyFor(72, 185)).toBe('h1-average');
    expect(bodyFor(74, 150)).toBe('h1-slim');
    expect(bodyFor(76, 205)).toBe('h2-average');
    expect(bodyFor(79, 190)).toBe('h3-slim');
    expect(bodyFor(79, 260)).toBe('h3-heavy');
    expect(bodyFor(82, 240)).toBe('h4-average');
    expect(bodyFor(86, 300)).toBe('h5-heavy');
  });
});

describe('sprite data', () => {
  const anims = Object.keys(SPRITES.anims) as AnimName[];

  it('has every body, animation, hair style and facial hair', () => {
    expect(Object.keys(SPRITES.frames).sort()).toEqual([...BODY_KEYS].sort());
    expect(anims).toEqual(expect.arrayContaining(['dunk_basic', 'dunk_athletic', 'dunk_hang', 'layup', 'pass']));
    for (const body of BODY_KEYS) {
      for (const anim of anims) {
        const frames = SPRITES.frames[body][anim];
        expect(frames).toHaveLength(SPRITES.anims[anim].frameCount);
        for (const f of frames) {
          expect(f.skin).not.toBeNull();
          expect(f.detail).not.toBeNull();
          for (const style of HAIR_STYLES.filter((s) => s !== 'bald')) {
            expect(f.hair[style as keyof typeof f.hair]).toBeDefined();
          }
          for (const kind of FACIAL_HAIR.filter((k) => k !== 'none')) {
            expect(f.facial[kind as keyof typeof f.facial]).toBeDefined();
          }
        }
      }
    }
  });

  it('only references pieces and pages that exist', () => {
    const n = SPRITES.pieces.length;
    for (const [page] of SPRITES.pieces) expect(page).toBeLessThan(SPRITES.pages.length);
    for (const body of BODY_KEYS) {
      for (const anim of anims) {
        for (const f of SPRITES.frames[body][anim]) {
          const refs = [f.skin, f.jersey, f.trim, f.detail, ...Object.values(f.hair).flat(), ...Object.values(f.facial).flat()];
          for (const r of refs) if (r) expect(r[0]).toBeLessThan(n);
        }
      }
    }
  });

  it('marks the dunk moments', () => {
    expect(SPRITES.anims.dunk_basic.events.dunk).toBeDefined();
    expect(SPRITES.anims.dunk_athletic.events.dunk).toBeDefined();
    expect(SPRITES.anims.dunk_hang.events.hangStart).toBeLessThan(SPRITES.anims.dunk_hang.events.hangEnd);
  });
});

describe('jerseys', () => {
  it('has 32 teams plus white', () => {
    expect(TEAMS).toHaveLength(32);
    expect(new Set(TEAMS.map((t) => t.id)).size).toBe(32);
    expect(WHITE_JERSEY.jersey).toBeDefined();
  });

  it('puts the away team in white on a color clash', () => {
    const { away } = jerseysForGame(teamById('CHI'), teamById('HOU'));
    expect(away.jersey).toBe(WHITE_JERSEY.jersey);
    const other = jerseysForGame(teamById('LAL'), teamById('BOS'));
    expect(other.away.jersey).toBe(teamById('BOS').jersey);
  });
});
