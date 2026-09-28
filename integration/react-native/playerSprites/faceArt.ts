/**
 * Player headshots, in the same chunky pixel-art style as the court sprites.
 *
 * faceFromSeed(playerId) picks a FaceSpec (plain indices, never stored), and
 * faceSvg() draws it as one self-contained SVG on a 200 x 240 grid: a
 * 50 x 60 pixel-art portrait with every art pixel a 4 x 4 square. Each color
 * becomes a single <path>, and shape-rendering="crispEdges" keeps the pixels
 * sharp at any size.
 */
import palettes from './palettes.json';
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

export type FaceSpec = {
  head: number;       // HEAD_SHAPES
  skin: number;       // SKIN_TONES
  eyes: number;       // EYE_SHAPES
  nose: number;       // NOSES
  mouth: number;      // MOUTHS
  hair: number;       // HAIR_STYLES
  hairColor: number;  // HAIR_COLORS
  facialHair: number; // FACIAL_HAIR
  eyeColor: number;   // EYE_COLORS
  browWeight: number; // 0.85 - 1.25
};

// ------------------------------------------------------------------ generation

/** Small seeded RNG (mulberry32). */
export function rng(seed: number): () => number {
  let a = seed >>> 0;
  return () => {
    a = (a + 0x6d2b79f5) >>> 0;
    let t = a;
    t = Math.imul(t ^ (t >>> 15), t | 1);
    t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

function pick(weights: readonly number[], r: number): number {
  const total = weights.reduce((a, b) => a + b, 0);
  let x = r * total;
  for (let i = 0; i < weights.length; i++) {
    x -= weights[i];
    if (x < 0) return i;
  }
  // r was ~1: fall back to the last option that can actually be picked
  for (let i = weights.length - 1; i >= 0; i--) if (weights[i] > 0) return i;
  return 0;
}

const SKIN_WEIGHTS = [1, 1, 1.2, 1.3, 1.2];

type SkinTable = {
  hairColor: number[]; // black, darkBrown, brown, auburn, blond, bleached
  eyeColor: number[];  // darkBrown, brown, hazel, green, blue
  coily: number;       // chance the hair texture is coily
  nose: number[];      // narrow, medium, broad, wide, aquiline
  mouth: number[];     // thin, medium, full, smile
};

/** Per-skin-tone odds, so each face reads as one person. */
export const BY_SKIN: SkinTable[] = [
  // light
  { hairColor: [2, 3, 3, 1.2, 2, 0.4], eyeColor: [1, 2, 2, 1.5, 2], coily: 0.15,
    nose: [3, 3, 1, 0.5, 2], mouth: [3, 3, 1, 2] },
  // medium
  { hairColor: [4, 3, 2, 0.6, 0.8, 0.4], eyeColor: [3, 3, 2, 1, 0.8], coily: 0.35,
    nose: [2, 3, 2, 1, 1.5], mouth: [2, 3, 2, 2] },
  // tan
  { hairColor: [6, 3, 1.2, 0.3, 0.3, 0.4], eyeColor: [5, 3, 1.5, 0.5, 0.3], coily: 0.6,
    nose: [1.5, 3, 2.5, 1.5, 1], mouth: [1.5, 3, 2.5, 2] },
  // brown
  { hairColor: [8, 2.5, 0.6, 0.1, 0.1, 0.5], eyeColor: [6, 3, 1, 0.1, 0], coily: 0.85,
    nose: [0.8, 2.5, 3, 2.5, 0.6], mouth: [1, 2.5, 3, 2] },
  // deep: no blue or green eyes, no blond or auburn hair
  { hairColor: [9, 2, 0.3, 0, 0, 0.5], eyeColor: [7, 3, 0.5, 0, 0], coily: 0.95,
    nose: [0.5, 2, 3, 3, 0.5], mouth: [0.8, 2, 3.5, 2] },
];

// bald, buzz, fade, crew, cornrows, afro, locs
// bald, buzz, fade, crew, cornrows, afro, locs, mohawk, high_top, twists, curly, flow
const HAIR_WEIGHTS_COILY = [1.2, 2, 2.5, 1, 1.2, 1, 1.3, 0.4, 0.6, 1.2, 0.8, 0.05];
const HAIR_WEIGHTS_STRAIGHT = [0.8, 2, 2, 3, 0.1, 0, 0.15, 0.4, 0.1, 0.1, 0.8, 1.5];
// none, stubble, mustache, goatee, beard
const FACIAL_WEIGHTS = [6, 2, 0.8, 1.3, 1.6, 0.6, 0.4];

/** The same seed (the league player's numeric id) always gives the same face. */
export function faceFromSeed(seed: number): FaceSpec {
  const r = rng(seed);
  const skin = pick(SKIN_WEIGHTS, r());
  const table = BY_SKIN[skin];
  const coily = r() < table.coily;
  return {
    skin,
    hair: pick(coily ? HAIR_WEIGHTS_COILY : HAIR_WEIGHTS_STRAIGHT, r()),
    hairColor: pick(table.hairColor, r()),
    eyeColor: pick(table.eyeColor, r()),
    nose: pick(table.nose, r()),
    mouth: pick(table.mouth, r()),
    head: Math.floor(r() * HEAD_SHAPES.length),
    eyes: Math.floor(r() * EYE_SHAPES.length),
    facialHair: pick(FACIAL_WEIGHTS, r()),
    browWeight: Math.round((0.85 + r() * 0.4) * 100) / 100,
  };
}

// ------------------------------------------------------------------ colors

function rgbOf(hex: string): [number, number, number] {
  const n = parseInt(hex.slice(1), 16);
  return [(n >> 16) & 255, (n >> 8) & 255, n & 255];
}

function hexOf(r: number, g: number, b: number): string {
  const c = (v: number) => Math.max(0, Math.min(255, Math.round(v))).toString(16).padStart(2, '0');
  return `#${c(r)}${c(g)}${c(b)}`;
}

/** Blend a toward b by t (0..1). */
function mix(a: string, b: string, t: number): string {
  const [r1, g1, b1] = rgbOf(a);
  const [r2, g2, b2] = rgbOf(b);
  return hexOf(r1 + (r2 - r1) * t, g1 + (g2 - g1) * t, b1 + (b2 - b1) * t);
}

/** Lower-case #rrggbb, or the fallback if the input isn't a 6-digit hex color. */
function norm(hex: string | undefined, fallback: string): string {
  return typeof hex === 'string' && /^#[0-9a-fA-F]{6}$/.test(hex) ? hex.toLowerCase() : fallback;
}

function luma(hex: string): number {
  const [r, g, b] = rgbOf(hex);
  return (0.299 * r + 0.587 * g + 0.114 * b) / 255;
}

const OUTLINE = '#1c1620';
const WARM_DARK = '#481a0c';
const EYE_WHITE = '#f1ebe2';
const EYE_WHITE_SHADE = '#c9c0b4';
const TEETH = '#eee8dc';

type SkinRamp = { hi: string; base: string; s1: string; s2: string; s3: string;
  lip: string; lipHi: string; nostril: string };
type HairRamp = { hi: string; base: string; s1: string; s2: string; brow: string };

function skinRamp(base: string): SkinRamp {
  return {
    hi: mix(base, '#ffffff', 0.16),
    base,
    s1: mix(base, WARM_DARK, 0.24),
    s2: mix(base, WARM_DARK, 0.42),
    s3: mix(base, '#2a0c06', 0.62),
    lip: mix(mix(base, WARM_DARK, 0.3), '#b0464a', 0.22),
    lipHi: mix(mix(base, WARM_DARK, 0.12), '#c0605c', 0.18),
    nostril: mix(base, '#1c0804', 0.66),
  };
}

function hairRamp(base: string): HairRamp {
  const light = luma(base) > 0.45;
  return {
    hi: mix(base, '#ffffff', light ? 0.3 : 0.2),
    base,
    s1: mix(base, '#000000', light ? 0.22 : 0.3),
    s2: mix(base, '#000000', light ? 0.42 : 0.55),
    brow: light ? mix(base, '#3a2a1a', 0.45) : mix(base, '#000000', 0.15),
  };
}

// ------------------------------------------------------------------ pixel grid

const GW = 50;          // art pixels
const GH = 60;
const PX = 4;           // SVG units per art pixel -> 200 x 240
const CX = 25;          // vertical centre line (between columns 24 and 25)

/** viewBox that crops the 200 x 240 face to a square head-and-shoulders view. */
export const HEADSHOT_VIEWBOX = '12 24 176 176';

class Grid {
  c: (string | null)[] = new Array(GW * GH).fill(null);
  in(x: number, y: number) {
    return Number.isInteger(x) && Number.isInteger(y) && x >= 0 && y >= 0 && x < GW && y < GH;
  }
  get(x: number, y: number) {
    return this.in(x, y) ? this.c[y * GW + x] : null;
  }
  set(x: number, y: number, col: string) {
    x = Math.round(x);
    y = Math.round(y);
    if (this.in(x, y)) this.c[y * GW + x] = col;
  }
}

type Mask = Set<number>;
const key = (x: number, y: number) => y * GW + x;
const kx = (k: number) => k % GW;
const ky = (k: number) => Math.floor(k / GW);

function each(mask: Mask, fn: (x: number, y: number) => void) {
  mask.forEach((k) => fn(kx(k), ky(k)));
}

/** Pixels of `mask` with a 4-neighbour outside it (or inside `other`). */
function edge(mask: Mask, x: number, y: number, dir?: [number, number]): boolean {
  const ns: [number, number][] = dir ? [dir] : [[1, 0], [-1, 0], [0, 1], [0, -1]];
  return ns.some(([dx, dy]) => !mask.has(key(x + dx, y + dy)));
}

/** Deterministic per-pixel noise in [0, 1). */
function noise(x: number, y: number, seed: number): number {
  return rng((x * 73856093) ^ (y * 19349663) ^ (seed * 83492791))();
}

// ------------------------------------------------------------------ head geometry

type HeadShape = { top: number; chin: number; pts: [number, number][]; neck: number };

// half-width of the head at points from the top of the skull (t = 0) to the chin (t = 1)
const HEADS: HeadShape[] = [
  { top: 13, chin: 39, neck: 6, pts: [[0, 4], [0.08, 7], [0.2, 9.4], [0.35, 10.4], [0.6, 10.4], [0.74, 9.6],
    [0.87, 7.6], [0.96, 5], [1, 3.4]] },                                                   // oval
  { top: 13, chin: 38, neck: 6.5, pts: [[0, 5], [0.08, 8], [0.2, 10.4], [0.35, 11], [0.62, 11], [0.78, 10.2],
    [0.9, 8.2], [0.97, 6], [1, 4.4]] },                                                    // round
  { top: 13, chin: 39, neck: 7, pts: [[0, 5], [0.07, 8.4], [0.18, 10], [0.35, 10.5], [0.7, 10.5], [0.85, 10],
    [0.93, 8.6], [0.98, 7.2], [1, 6]] },                                                   // square
  { top: 12, chin: 40, neck: 5.5, pts: [[0, 4], [0.08, 7], [0.2, 9], [0.35, 9.5], [0.62, 9.5], [0.78, 8.8],
    [0.9, 7], [0.97, 5], [1, 3.4]] },                                                      // long
];

function halfWidth(shape: HeadShape, y: number): number {
  const t = (y + 0.5 - shape.top) / (shape.chin + 1 - shape.top);
  const p = shape.pts;
  if (t <= p[0][0]) return p[0][1];
  for (let i = 1; i < p.length; i++) {
    if (t <= p[i][0]) {
      const u = (t - p[i - 1][0]) / (p[i][0] - p[i - 1][0]);
      return p[i - 1][1] + (p[i][1] - p[i - 1][1]) * u;
    }
  }
  return p[p.length - 1][1];
}

/** Columns [x0, x1] covered by a row whose half-width is hw. */
function span(hw: number): [number, number] {
  const n = Math.max(1, Math.round(hw));
  return [CX - n, CX - 1 + n];
}

// ------------------------------------------------------------------ feature templates

// Eyes: 5 wide, drawn for the left eye and mirrored for the right.
// L lash line, W white, w shaded white, I iris, D pupil, s/d skin shade.
// `at` is the template row that sits on the eye line.
const EYES: { rows: string[]; at: number }[] = [
  { rows: ['.LLLL', 'WIDIW', '.sss.'], at: 1 },               // almond
  { rows: ['.LLL.', 'WIDIW', 'wIIIw', '.sss.'], at: 1 },      // round
  { rows: ['sssss', 'LLLLL', 'WIDIW', '..ss.'], at: 2 },      // hooded
  { rows: ['ddddd', '.LLL.', 'WIDIW', '.sss.'], at: 2 },      // deepSet
  { rows: ['.LLL.', 'LIDIL', '.sss.'], at: 1 },               // narrow
];

// Noses: h highlight, s shade, d deep shade, n nostril. The row `at` sits on
// the nose base line. Centred on the face.
const NOSE_ART: { rows: string[]; at: number }[] = [
  { rows: ['...s..', '..hs..', '..hs..', '..hs..', '..nn..', '..ss..'], at: 4 },          // narrow
  { rows: ['...s..', '..hs..', '..hs..', '.hhss.', '.nhsn.', '..ss..'], at: 4 },          // medium
  { rows: ['...s..', '..hs..', '..hs..', '.hhss.', 'snhssn', '.ssss.'], at: 4 },          // broad
  { rows: ['....s...', '...hs...', '...hs...', '..hhss..', 'snnhssnn', '.ssssss.'], at: 4 }, // wide
  { rows: ['..hs..', '..hhs.', '..hhs.', '..hs..', '.nhsn.', '...s..'], at: 4 },          // aquiline
];

// Mouths: u upper lip, m lip line, l lower lip, g lip highlight, t teeth,
// c corner, s shade under the lip. Row `at` sits on the mouth line.
const MOUTH_ART: { rows: string[]; at: number }[] = [
  { rows: ['.cmmmmc.', '..ssss..'], at: 0 },                         // thin
  { rows: ['..uuuu..', '.cmmmmc.', '..llll..', '...ss...'], at: 1 },   // medium
  { rows: ['.uuuuuu.', 'cmmmmmmc', '.llggll.', '.llllll.', '..ssss..'], at: 1 }, // full
  { rows: ['c......c', '.mttttm.', '..llll..', '...ss...'], at: 1 },   // smile
];

// 3 x 5 digits for an optional jersey number
const DIGITS = ['111101101101111', '010110010010111', '111001111100111', '111001111001111',
  '101101111001001', '111100111001111', '111100111101111', '111001001001001', '111101111101111',
  '111101111001111'];

// ------------------------------------------------------------------ drawing

export type HeadshotJersey = string | { jersey: string; trim?: string; number?: number | string };

export type FaceSvgOptions = {
  /** crop to the square head-and-shoulders view (viewBox HEADSHOT_VIEWBOX) */
  crop?: boolean;
  /** rendered width/height attributes; defaults to the viewBox size */
  size?: number;
};

function clampIndex(i: number, n: number): number {
  return Number.isFinite(i) ? Math.max(0, Math.min(n - 1, Math.floor(i))) : 0;
}

export function faceSvg(face: FaceSpec, id: number, jersey?: HeadshotJersey, opts: FaceSvgOptions = {}): string {
  const f = {
    head: clampIndex(face.head, HEAD_SHAPES.length),
    skin: clampIndex(face.skin, SKIN_TONES.length),
    eyes: clampIndex(face.eyes, EYE_SHAPES.length),
    nose: clampIndex(face.nose, NOSES.length),
    mouth: clampIndex(face.mouth, MOUTHS.length),
    hair: clampIndex(face.hair, HAIR_STYLES.length),
    hairColor: clampIndex(face.hairColor, HAIR_COLORS.length),
    facialHair: clampIndex(face.facialHair, FACIAL_HAIR.length),
    eyeColor: clampIndex(face.eyeColor, EYE_COLORS.length),
    brow: Number.isFinite(face.browWeight) ? face.browWeight : 1,
  };
  const seed = Math.floor(Math.abs(Number.isFinite(id) ? id : 0));
  const g = new Grid();
  const sk = skinRamp(palettes.skinTones[f.skin].color);
  const hr = hairRamp(palettes.hairColors[f.hairColor].color);
  const iris = palettes.eyeColors[f.eyeColor].color;
  const j = typeof jersey === 'string' ? { jersey } : jersey ?? palettes.neutralJersey;
  const jBase = norm(j.jersey, norm(palettes.neutralJersey.jersey, '#1f2a44'));
  const jTrim = norm(j.trim, luma(jBase) < 0.5 ? mix(jBase, '#ffffff', 0.6) : mix(jBase, '#000000', 0.45));
  const number = 'number' in j && j.number !== undefined ? String(j.number).replace(/\D/g, '').slice(0, 2) : '';

  const shape = HEADS[f.head];
  const { top, chin } = shape;
  const eyeY = Math.floor((top + chin) / 2);
  const noseY = eyeY + Math.round((chin - eyeY) / 3);
  const mouthY = noseY + Math.round((chin - noseY) / 3);
  const hwAt = (y: number) => halfWidth(shape, y);
  const maxHw = Math.max(...shape.pts.map((p) => p[1]));

  // head mask
  const head: Mask = new Set();
  for (let y = top; y <= chin; y++) {
    const [x0, x1] = span(hwAt(y));
    for (let x = x0; x <= x1; x++) head.add(key(x, y));
  }
  const nxOf = (x: number, y: number) => (x + 0.5 - CX) / Math.max(1, Math.round(hwAt(y)));

  const hairStyle = HAIR_STYLES[f.hair];
  // hairline: high in the middle, down to the temples at the sides
  const hairline = (x: number, y: number) => {
    const nx = Math.abs(nxOf(x, y));
    return top + 5 + Math.round(nx * nx * (eyeY - 2 - (top + 5)));
  };

  // ---- 1. back hair
  const backHair: Mask = new Set();
  if (hairStyle === 'afro') {
    const cy = top + 6;
    const rx = maxHw + 5;
    const ry = 12;
    for (let y = cy - ry; y <= cy + ry; y++) {
      for (let x = Math.floor(CX - rx - 1); x <= Math.ceil(CX + rx); x++) {
        const dx = (x + 0.5 - CX) / rx;
        const dy = (y + 0.5 - cy) / ry;
        if (dx * dx + dy * dy <= 1 && y <= eyeY + 4) backHair.add(key(x, y));
      }
    }
    // bumpy silhouette: decide on the original edge first, then trim
    const trim = [...backHair].filter((k) => edge(backHair, kx(k), ky(k)) && noise(kx(k), ky(k), seed) < 0.4);
    trim.forEach((k) => backHair.delete(k));
  } else if (hairStyle === 'flow') {
    const w = Math.round(maxHw) + 2;
    for (let x = CX - w; x < CX + w; x++) {
      const bottom = chin + 3 + Math.floor(noise(x, 1, seed) * 2);
      for (let y = top - 1; y <= bottom; y++) {
        const hw = y < top + 4 ? Math.round(hwAt(y + 1)) + 1 : w;
        if (Math.abs(x + 0.5 - CX) <= hw) backHair.add(key(x, y));
      }
    }
  } else if (hairStyle === 'locs') {
    const w = Math.round(maxHw) + 3;
    for (let x = CX - w; x < CX + w; x++) {
      const bottom = 44 + Math.floor(noise(x, 0, seed) * 5);
      for (let y = top - 1; y <= bottom; y++) {
        const hw = y < top + 4 ? Math.round(hwAt(y + 1)) + 1 : w;
        if (Math.abs(x + 0.5 - CX) <= hw) backHair.add(key(x, y));
      }
    }
  }
  each(backHair, (x, y) => {
    const n = noise(x, y, seed);
    const nx = (x + 0.5 - CX) / (maxHw + 5);
    let c = hr.base;
    if (hairStyle === 'locs') {
      c = x % 3 === 2 ? hr.s2 : (y + 2 * x) % 4 === 0 ? hr.hi : x % 2 ? hr.s1 : hr.base;
    } else if (hairStyle === 'flow') {
      c = x % 4 === 0 ? hr.hi : x % 4 === 2 || nx > 0.45 ? hr.s1 : hr.base;   // long strands
    } else {
      if (n < 0.2 || nx > 0.45) c = hr.s1;
      if (n > 0.86 && nx < 0.2) c = hr.hi;
    }
    if (y > eyeY) c = hairStyle === 'locs' && x % 3 !== 2 ? hr.s1 : hr.s2; // behind the head: in shadow
    g.set(x, y, c);
  });

  // ---- 2. shoulders + jersey
  const body: Mask = new Set();
  const jerseyMask: Mask = new Set();
  const armhole = [9, 9, 9, 9.5, 10, 10.5, 11.5, 13, 14.5, 16, 17, 17.5];
  const neckline = [6, 6, 6, 5.5, 4.5, 3, 1.5];
  for (let y = 42; y < GH; y++) {
    const u = Math.min(1, (y - 42) / 7);
    const hw = 23 - 15 * (1 - u) * (1 - u);
    for (let x = 0; x < GW; x++) {
      const dx = Math.abs(x + 0.5 - CX);
      if (dx > hw) continue;
      body.add(key(x, y));
      const i = y - 41;
      const ah = armhole[Math.min(i, armhole.length - 1)];
      const nl = i < neckline.length ? neckline[i] : 0;
      if (dx <= ah && dx >= nl) jerseyMask.add(key(x, y));
    }
  }
  each(body, (x, y) => {
    const nx = (x + 0.5 - CX) / 23;
    g.set(x, y, nx > 0.55 ? sk.s1 : nx < -0.75 && y < 50 ? sk.hi : sk.base);
  });
  each(jerseyMask, (x, y) => {
    const dx = x + 0.5 - CX;
    let c = jBase;
    if (dx > 6) c = mix(jBase, '#10122c', 0.22);
    if (dx > 12) c = mix(jBase, '#10122c', 0.36);
    if (dx < -8 && dx > -13) c = mix(jBase, '#ffffff', 0.1);
    if (y >= 47 && y <= 48 && Math.abs(dx) < 3) c = mix(jBase, '#10122c', 0.22); // fold under the collar
    if ([[1, 0], [-1, 0], [0, -1]].some(([ox, oy]) => body.has(key(x + ox, y + oy)) && !jerseyMask.has(key(x + ox, y + oy)))) {
      c = jTrim;
    }
    g.set(x, y, c);
  });
  if (number) {
    const w = number.length * 4 - 1;
    let x0 = CX - Math.ceil(w / 2);
    for (const ch of number) {
      const bits = DIGITS[Number(ch)];
      for (let i = 0; i < 15; i++) if (bits[i] === '1') g.set(x0 + (i % 3), 51 + Math.floor(i / 3), jTrim);
      x0 += 4;
    }
  }

  // ---- 3. neck
  const nw = shape.neck;
  for (let y = chin - 4; y <= 47; y++) {
    for (let x = Math.round(CX - nw); x < Math.round(CX + nw); x++) {
      if (y >= 42 && !body.has(key(x, y))) continue;
      if (jerseyMask.has(key(x, y))) continue;
      const dx = x + 0.5 - CX;
      let c = dx > nw - 2.5 ? sk.s1 : sk.base;
      if (y <= chin + 2) c = sk.s2;          // shadow under the jaw
      if (y === chin + 3 && dx > 0) c = sk.s2;
      g.set(x, y, c);
    }
  }

  // ---- 4. ears
  for (let y = eyeY - 1; y <= noseY; y++) {
    const [x0, x1] = span(hwAt(y));
    const edgeRow = y === eyeY - 1 || y === noseY;
    g.set(x0 - 1, y, edgeRow ? sk.s1 : sk.s2);
    g.set(x1 + 1, y, sk.s2);
    if (!edgeRow) {
      g.set(x0 - 2, y, sk.base);
      g.set(x1 + 2, y, sk.s1);
    }
  }

  // ---- 5. head + shading
  each(head, (x, y) => {
    const nx = nxOf(x, y);
    let c = sk.base;
    if (nx > 0.6) c = sk.s1;
    if (nx > 0.85) c = sk.s2;
    if (y <= top + 7 && y >= top + 3 && nx > -0.5 && nx < -0.2 && (x + y) % 2 === 0) c = sk.hi; // forehead sheen
    if (y === noseY - 1 && nx > -0.72 && nx < -0.45) c = sk.hi;                         // left cheekbone
    if (y >= noseY - 1 && y <= mouthY + 1 && nx > 0.38 && nx <= 0.6) c = sk.s1;         // right cheek
    if (y >= eyeY - 3 && y <= eyeY && Math.abs(nx) > 0.8) c = sk.s1;                    // temples
    if (y >= chin - 1) c = nx > 0.3 ? sk.s2 : sk.s1;                                    // under the jaw
    if (y >= mouthY + 2 && nx > 0.5) c = sk.s2;
    if (y === eyeY - 2 && Math.abs(nx) > 0.2 && Math.abs(nx) < 0.75) c = mix(c, sk.s1, 0.6); // brow ridge
    g.set(x, y, c);
  });

  // sockets under the brow, shadow down the side of the nose bridge, jawline
  for (const x0 of [18, 27]) {
    for (let x = x0; x < x0 + 5; x++) g.set(x, eyeY - 1, mix(g.get(x, eyeY - 1) ?? sk.base, sk.s1, 0.45));
  }
  for (let y = eyeY; y <= noseY - 3; y++) g.set(CX, y, mix(g.get(CX, y) ?? sk.base, sk.s1, 0.5));
  each(head, (x, y) => {
    if (y >= mouthY && nxOf(x, y) < -0.8) g.set(x, y, sk.s1);
  });

  // ---- 6. beard, goatee, stubble (mustache comes after the mouth)
  const facial = FACIAL_HAIR[f.facialHair];
  const hairTexture = (x: number, y: number, dark: boolean) => {
    const n = noise(x, y, seed + 7);
    if (dark || n < 0.22) return hr.s1;
    if (n > 0.88) return hr.hi;
    return hr.base;
  };
  if (facial === 'stubble') {
    each(head, (x, y) => {
      const nx = nxOf(x, y);
      if (y >= noseY + 1 || (y >= noseY - 1 && Math.abs(nx) > 0.6)) {
        const cur = g.get(x, y) ?? sk.base;
        const n = noise(x, y, seed + 3);
        g.set(x, y, mix(cur, hr.s1, n < 0.45 ? 0.34 : n < 0.8 ? 0.22 : 0.12));
      }
    });
  } else if (facial === 'chinstrap') {
    // a thin line of beard along the jaw, ear to ear
    each(head, (x, y) => {
      if (y < eyeY + 1) return;
      const onEdge = Math.abs(nxOf(x, y)) > 0.8 || y >= chin - 1;
      if (onEdge) g.set(x, y, hairTexture(x, y, nxOf(x, y) > 0.3));
    });
  } else if (facial === 'beard' || facial === 'goatee' || facial === 'long_beard') {
    const beard: Mask = new Set();
    if (facial === 'beard' || facial === 'long_beard') {
      each(head, (x, y) => {
        const nx = Math.abs(nxOf(x, y));
        const line = noseY + 1 - Math.min(1, nx / 0.9) * (noseY + 1 - (eyeY + 2));
        if (y >= line) beard.add(key(x, y));
      });
      const cw = Math.round(hwAt(chin));
      for (let x = CX - cw - 1; x < CX + cw + 1; x++) beard.add(key(x, chin + 1));
      for (let x = CX - cw + 1; x < CX + cw - 1; x++) beard.add(key(x, chin + 2));
      if (facial === 'long_beard') {
        for (let i = 3; i <= 7; i++) {                       // hangs well below the chin
          const w = Math.max(1, cw - Math.floor(i / 2));
          for (let x = CX - w; x < CX + w; x++) beard.add(key(x, chin + i));
        }
      }
    } else {
      for (let y = mouthY - 1; y <= chin + 1; y++) {
        for (let x = CX - 5; x < CX + 5; x++) {
          const dx = Math.abs(x + 0.5 - CX);
          const inChin = y > mouthY && dx <= (y > chin ? 2 : 3.5);
          const ring = y <= mouthY + 1 && dx >= 3.5 && dx <= 5;
          if ((inChin && (head.has(key(x, y)) || y === chin + 1)) || ring) beard.add(key(x, y));
        }
      }
    }
    each(beard, (x, y) => {
      const nx = nxOf(x, y);
      let c = hairTexture(x, y, nx > 0.45);
      if (!beard.has(key(x, y + 1))) c = hr.s2;                                   // lower edge
      if (!beard.has(key(x, y - 1)) && head.has(key(x, y - 1)) && (x + y) % 2) {
        c = mix(g.get(x, y) ?? sk.base, hr.base, 0.55);                            // soft upper edge
      }
      g.set(x, y, c);
    });
  }

  // ---- 7. eyes + brows
  const eye = EYES[f.eyes];
  const eyeColors: Record<string, string> = {
    L: OUTLINE, W: EYE_WHITE, w: EYE_WHITE_SHADE, I: iris, D: mix(iris, '#000000', 0.6),
    s: sk.s1, d: sk.s2,
  };
  for (const [x0, mirror] of [[18, false], [27, true]] as [number, boolean][]) {
    eye.rows.forEach((row, r) => {
      const chars = mirror ? [...row].reverse() : [...row];
      chars.forEach((ch, i) => {
        if (ch !== '.') g.set(x0 + i, eyeY - eye.at + r, eyeColors[ch]);
      });
    });
  }
  const browY = eyeY - 3;
  const browRows: [number, number, number][] = [[browY, 17, 22]];         // [y, from, to] for the left brow
  if (f.brow < 0.95) browRows[0] = [browY, 18, 22];
  if (f.brow >= 0.95) browRows.push([browY + 1, 21, 22]);
  if (f.brow >= 1.1) browRows[1] = [browY + 1, 18, 22];
  if (f.brow >= 1.2) browRows.push([browY - 1, 19, 21]);
  for (const [y, a, b] of browRows) {
    for (let x = a; x <= b; x++) {
      g.set(x, y, hr.brow);
      g.set(GW - 1 - x, y, hr.brow);
    }
  }
  g.set(17, browY + 1, hr.brow);   // outer tail dips down
  g.set(GW - 18, browY + 1, hr.brow);

  // ---- 8. nose
  const nose = NOSE_ART[f.nose];
  const noseColors: Record<string, string> = { h: sk.hi, s: sk.s1, d: sk.s2, n: sk.nostril };
  const nx0 = CX - nose.rows[0].length / 2;
  nose.rows.forEach((row, r) => {
    [...row].forEach((ch, i) => {
      if (ch !== '.') g.set(nx0 + i, noseY - nose.at + r, noseColors[ch]);
    });
  });

  // ---- 9. mouth
  const mouth = MOUTH_ART[f.mouth];
  const mouthColors: Record<string, string> = {
    u: sk.lip, m: sk.s3, l: sk.lip, g: sk.lipHi, t: TEETH, c: sk.s2, s: sk.s1,
  };
  const mx0 = CX - mouth.rows[0].length / 2;
  mouth.rows.forEach((row, r) => {
    [...row].forEach((ch, i) => {
      if (ch !== '.') g.set(mx0 + i, mouthY - mouth.at + r, mouthColors[ch]);
    });
  });

  // ---- 10. mustache
  if (facial === 'mustache' || facial === 'beard' || facial === 'goatee' || facial === 'long_beard') {
    // sits on the upper lip, never over the nostrils
    const my = Math.max(noseY + 1, mouthY - mouth.at - 1);
    for (let x = CX - 4; x < CX + 4; x++) g.set(x, my, hairTexture(x, my, x >= CX + 2));
    for (const x of [CX - 5, CX - 4, CX + 3, CX + 4]) g.set(x, my + 1, hr.s1);
    if (my - 1 > noseY) {
      g.set(CX - 3, my - 1, hr.base);
      g.set(CX + 2, my - 1, hr.base);
      for (let x = CX - 2; x < CX + 2; x++) g.set(x, my - 1, hr.hi);
    }
  }

  // ---- 11. front hair
  const front: Mask = new Set();
  const scalp = (x: number, y: number) => head.has(key(x, y)) && y < hairline(x, y);
  if (hairStyle !== 'bald') {
    const volumes: Partial<Record<string, number>> = { crew: 2, fade: 2, locs: 2, twists: 2, curly: 3, flow: 2 };
    const volume = volumes[hairStyle] ?? 0;
    for (let y = top - volume; y < eyeY + 2; y++) {
      for (let x = 0; x < GW; x++) {
        let inside = scalp(x, y);
        if (!inside && volume && y < top + 6) {
          const [x0, x1] = span(hwAt(Math.min(y + volume, chin)));
          inside = x >= x0 - (y < top + 3 ? 0 : 1) && x <= x1 + (y < top + 3 ? 0 : 1) && y >= top - volume;
          if (hairStyle === 'fade' && Math.abs(nxOf(x, Math.max(y, top))) > 0.75) inside = false;
        }
        // sideburns down to the top of the ear
        if (!inside && head.has(key(x, y)) && Math.abs(nxOf(x, y)) > 0.84 && y <= eyeY - 1 &&
            hairStyle !== 'cornrows') inside = true;
        if (inside) front.add(key(x, y));
      }
    }
    if (hairStyle === 'afro') {
      each(backHair, (x, y) => {
        if (y < hairline(x, y) && !(head.has(key(x, y)) && y >= hairline(x, y))) {
          if (head.has(key(x, y)) || y < top) front.add(key(x, y));
        }
      });
    }
    if (hairStyle === 'high_top') {
      // tall flat box on top of the head
      const [x0, x1] = span(hwAt(top + 4));
      for (let y = top - 7; y <= top + 1; y++) for (let x = x0 + 1; x <= x1 - 1; x++) front.add(key(x, y));
    }
    if (hairStyle === 'mohawk') {
      // the fin: a narrow strip standing up along the middle
      for (let y = top - 4; y < top; y++) {
        const w = y === top - 4 ? 1.5 : 2.5;
        for (let x = 0; x < GW; x++) if (Math.abs(x + 0.5 - CX) <= w) front.add(key(x, y));
      }
    }
    if (hairStyle === 'curly') {
      const trim = [...front].filter((k) => ky(k) < top && edge(front, kx(k), ky(k)) && noise(kx(k), ky(k), seed) < 0.35);
      trim.forEach((k) => front.delete(k));
    }
    if (hairStyle === 'flow') {
      // side-swept fringe, lower on the left
      for (let x = CX - 8; x <= CX + 3; x++) {
        const bottom = top + 8 - Math.floor((x - (CX - 8)) / 3);
        for (let y = top; y <= bottom; y++) if (head.has(key(x, y))) front.add(key(x, y));
      }
    }
    if (hairStyle === 'locs') {
      // locs falling in front of the ears on both sides
      for (let y = eyeY - 3; y <= mouthY + 3; y++) {
        const [x0, x1] = span(hwAt(Math.min(y, chin)));
        for (const x of [x0 - 2, x0 - 1, x0, x1, x1 + 1, x1 + 2]) front.add(key(x, y));
      }
    }
    // jagged fringe
    if (hairStyle === 'crew' || hairStyle === 'locs') {
      each(new Set(front), (x, y) => {
        if (!front.has(key(x, y + 1)) && head.has(key(x, y + 1)) && x % 3 === 0) front.add(key(x, y + 1));
      });
    }
  }
  each(front, (x, y) => {
    const nx = nxOf(x, Math.max(y, top));
    const bottom = !front.has(key(x, y + 1)) && head.has(key(x, y + 1));
    const cur = g.get(x, y) ?? sk.base;
    let c = hr.base;
    switch (hairStyle) {
      case 'buzz':
        c = mix(cur, hr.s1, (x + y) % 2 ? 0.8 : 0.62);
        if (bottom) c = mix(cur, hr.s1, 0.5);
        break;
      case 'fade': {
        const fadeTop = top + 5;
        if (Math.abs(nx) > 0.72 && y > fadeTop) {
          const level = (y - fadeTop) / Math.max(1, eyeY - fadeTop);
          const bayer = [0, 0.5, 0.75, 0.25][(x % 2) + 2 * (y % 2)];
          c = level > bayer + 0.25 ? mix(cur, hr.s1, 0.35) : hr.s1;
        } else {
          c = nx > 0.4 ? hr.s1 : (x + y) % 3 === 0 && nx < 0 && y < top + 3 ? hr.hi : hr.base;
        }
        break;
      }
      case 'cornrows': {
        const stripe = Math.floor((x - CX + 30) / 3);
        const gap = (x - CX + 30) % 3 === 2;
        c = gap ? mix(sk.s1, hr.s2, 0.3) : (y + stripe) % 2 ? hr.base : hr.hi;
        if (nx > 0.5 && !gap) c = hr.s1;
        break;
      }
      case 'locs':
        c = x % 3 === 2 ? hr.s2 : (y + 2 * x) % 4 === 0 ? hr.hi : nx > 0.4 ? hr.s1 : hr.base;
        break;
      case 'afro': {
        const n = noise(x, y, seed);
        c = n < 0.2 || nx > 0.45 ? hr.s1 : n > 0.86 && nx < 0.2 ? hr.hi : hr.base;
        break;
      }
      case 'mohawk':
        if (Math.abs(x + 0.5 - CX) > 3 && y >= top) c = mix(cur, hr.s1, (x + y) % 2 ? 0.55 : 0.4);   // shaved sides
        else c = nx > 0.3 ? hr.s1 : (x + y) % 3 === 0 && nx < 0 ? hr.hi : hr.base;
        break;
      case 'high_top':
        c = nx > 0.45 || y === top - 7 ? hr.s1 : (x * 3 + y) % 5 === 0 ? hr.hi : hr.base;
        break;
      case 'twists':
        c = x % 2 ? hr.s1 : y % 3 === 0 ? hr.hi : hr.base;
        break;
      case 'curly': {
        const n = noise(x, y, seed + 11);
        c = n < 0.25 || nx > 0.5 ? hr.s1 : n > 0.8 ? hr.hi : hr.base;
        break;
      }
      case 'flow':
        c = (x - Math.floor(y / 2)) % 4 === 0 ? hr.hi : nx > 0.45 ? hr.s1 : hr.base;   // swept strands
        break;
      default: // crew
        c = nx > 0.5 ? hr.s1 : (x + y) % 3 === 0 && nx < 0 && y < top + 3 ? hr.hi : hr.base;
    }
    const shaved = hairStyle === 'mohawk' && Math.abs(x + 0.5 - CX) > 3 && y >= top;
    if (bottom && hairStyle !== 'buzz' && !shaved) c = hr.s2;
    g.set(x, y, c);
  });
  if (hairStyle === 'bald') {
    g.set(CX - 5, top + 2, sk.hi);
    g.set(CX - 4, top + 2, mix(sk.hi, '#ffffff', 0.3));
    g.set(CX - 5, top + 3, sk.hi);
  }

  // ---- 12. outline around everything
  const filled: Mask = new Set();
  g.c.forEach((c, k) => {
    if (c) filled.add(k);
  });
  filled.forEach((k) => {
    const x = kx(k);
    const y = ky(k);
    for (const [dx, dy] of [[1, 0], [-1, 0], [0, 1], [0, -1]]) {
      if (g.in(x + dx, y + dy) && !filled.has(key(x + dx, y + dy))) g.set(x + dx, y + dy, OUTLINE);
    }
  });

  return toSvg(g, seed, opts);
}

function toSvg(g: Grid, seed: number, opts: FaceSvgOptions): string {
  const paths = new Map<string, string[]>();
  for (let y = 0; y < GH; y++) {
    let x = 0;
    while (x < GW) {
      const c = g.get(x, y);
      if (!c) {
        x++;
        continue;
      }
      let len = 1;
      while (x + len < GW && g.get(x + len, y) === c) len++;
      if (!paths.has(c)) paths.set(c, []);
      paths.get(c)!.push(`M${x * PX} ${y * PX}h${len * PX}v${PX}h-${len * PX}z`);
      x += len;
    }
  }
  const viewBox = opts.crop ? HEADSHOT_VIEWBOX : `0 0 ${GW * PX} ${GH * PX}`;
  const [, , vw, vh] = viewBox.split(' ').map(Number);
  const w = opts.size ?? vw;
  const h = opts.size ?? vh;
  let body = '';
  paths.forEach((d, c) => {
    body += `<path fill="${c}" d="${d.join('')}"/>`;
  });
  return (
    `<svg xmlns="http://www.w3.org/2000/svg" viewBox="${viewBox}" width="${w}" height="${h}" ` +
    `shape-rendering="crispEdges"><g id="f${seed}">${body}</g></svg>`
  );
}
