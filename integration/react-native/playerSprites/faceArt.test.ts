import { faceFromSeed, faceSvg, HEADSHOT_VIEWBOX, type FaceSpec } from './faceArt';
import {
  EYE_COLORS,
  EYE_SHAPES,
  FACIAL_HAIR,
  HAIR_COLORS,
  HAIR_STYLES,
  HEAD_SHAPES,
  MOUTHS,
  NOSES,
  SKIN_TONES,
} from './features';
import palettes from './palettes.json';

const DEEP = SKIN_TONES.indexOf('deep');

describe('faceFromSeed', () => {
  it('always gives the same face and SVG for the same seed', () => {
    for (const seed of [0, 1, 42, 1234, 987654]) {
      expect(faceFromSeed(seed)).toEqual(faceFromSeed(seed));
      expect(faceSvg(faceFromSeed(seed), seed)).toBe(faceSvg(faceFromSeed(seed), seed));
    }
  });

  it('gives more than 45 distinct faces for 50 seeds', () => {
    const faces = new Set<string>();
    for (let seed = 1; seed <= 50; seed++) faces.add(JSON.stringify(faceFromSeed(seed)));
    expect(faces.size).toBeGreaterThan(45);
  });

  it('never gives the darkest skin blue or green eyes, or blond or auburn hair', () => {
    let deep = 0;
    for (let seed = 1; seed <= 5000; seed++) {
      const f = faceFromSeed(seed);
      if (f.skin !== DEEP) continue;
      deep++;
      expect(['blue', 'green']).not.toContain(EYE_COLORS[f.eyeColor]);
      expect(['blond', 'auburn']).not.toContain(HAIR_COLORS[f.hairColor]);
    }
    expect(deep).toBeGreaterThan(100);
  });

  it('keeps every field in range', () => {
    for (let seed = 1; seed <= 2000; seed++) {
      const f = faceFromSeed(seed);
      expect(f.head).toBeLessThan(HEAD_SHAPES.length);
      expect(f.skin).toBeLessThan(SKIN_TONES.length);
      expect(f.eyes).toBeLessThan(EYE_SHAPES.length);
      expect(f.nose).toBeLessThan(NOSES.length);
      expect(f.mouth).toBeLessThan(MOUTHS.length);
      expect(f.hair).toBeLessThan(HAIR_STYLES.length);
      expect(f.hairColor).toBeLessThan(HAIR_COLORS.length);
      expect(f.facialHair).toBeLessThan(FACIAL_HAIR.length);
      expect(f.eyeColor).toBeLessThan(EYE_COLORS.length);
      expect(f.browWeight).toBeGreaterThanOrEqual(0.85);
      expect(f.browWeight).toBeLessThanOrEqual(1.25);
    }
  });

  it('uses every hair style and facial hair option', () => {
    const hair = new Set<number>();
    const facial = new Set<number>();
    for (let seed = 1; seed <= 3000; seed++) {
      const f = faceFromSeed(seed);
      hair.add(f.hair);
      facial.add(f.facialHair);
    }
    expect(hair.size).toBe(HAIR_STYLES.length);
    expect(facial.size).toBe(FACIAL_HAIR.length);
  });
});

describe('faceSvg', () => {
  function checkSvg(svg: string, seed: number) {
    expect(svg.startsWith('<svg xmlns="http://www.w3.org/2000/svg"')).toBe(true);
    expect(svg).not.toMatch(/undefined|NaN|null/);
    // self-contained: no external references
    expect(svg.replace('http://www.w3.org/2000/svg', '')).not.toMatch(/https?:|href=|<image/);
    // every id and url(#...) reference is scoped to this face
    for (const m of svg.matchAll(/id="([^"]+)"/g)) expect(m[1].startsWith(`f${seed}`)).toBe(true);
    for (const m of svg.matchAll(/url\(#([^)]+)\)/g)) expect(m[1].startsWith(`f${seed}`)).toBe(true);
  }

  it('is self-contained with scoped ids and no undefined or NaN values', () => {
    for (let seed = 1; seed <= 60; seed++) checkSvg(faceSvg(faceFromSeed(seed), seed, '#552583'), seed);
  });

  it('draws every option of every feature', () => {
    const base: FaceSpec = faceFromSeed(7);
    const lists: [keyof FaceSpec, number][] = [
      ['head', HEAD_SHAPES.length], ['skin', SKIN_TONES.length], ['eyes', EYE_SHAPES.length],
      ['nose', NOSES.length], ['mouth', MOUTHS.length], ['hair', HAIR_STYLES.length],
      ['hairColor', HAIR_COLORS.length], ['facialHair', FACIAL_HAIR.length], ['eyeColor', EYE_COLORS.length],
    ];
    const seen = new Set<string>();
    for (const [field, n] of lists) {
      for (let i = 0; i < n; i++) {
        const svg = faceSvg({ ...base, [field]: i }, 7);
        checkSvg(svg, 7);
        seen.add(svg);
      }
    }
    // each option changes the picture (the base face repeats once per list)
    expect(seen.size).toBeGreaterThanOrEqual(lists.reduce((a, [, n]) => a + n - 1, 1));
  });

  it('crops to the head-and-shoulders viewBox', () => {
    const svg = faceSvg(faceFromSeed(3), 3, undefined, { crop: true, size: 64 });
    expect(svg).toContain(`viewBox="${HEADSHOT_VIEWBOX}"`);
    expect(svg).toContain('width="64" height="64"');
    expect(faceSvg(faceFromSeed(3), 3)).toContain('viewBox="0 0 200 240"');
  });

  it('uses the team color for the jersey and navy when none is given', () => {
    expect(faceSvg(faceFromSeed(5), 5, '#007A33')).toContain('fill="#007a33"');
    expect(faceSvg(faceFromSeed(5), 5)).toContain(`fill="${palettes.neutralJersey.jersey.toLowerCase()}"`);
  });

  it('survives bad input', () => {
    const bad = { ...faceFromSeed(1), head: 99, skin: -3, browWeight: NaN } as FaceSpec;
    checkSvg(faceSvg(bad, 1), 1);
  });
});

describe('palettes', () => {
  it('lists colors in the same order as the feature ids', () => {
    expect(palettes.skinTones.map((s) => s.id)).toEqual([...SKIN_TONES]);
    expect(palettes.hairColors.map((h) => h.id)).toEqual([...HAIR_COLORS]);
    expect(palettes.eyeColors.map((e) => e.id)).toEqual([...EYE_COLORS]);
  });
});
