import { ARENA_IMAGES } from './arenaImages';
import {
  ARENAS, ARENA_IDS, ARENA_META, BACKDROP_W, arenaById, arenaScale, backdropLeft, crowdFrame,
} from './arenas';
import { arenaFloor } from './arenaFloor';

describe('arenas', () => {
  it('offers six themes with names, descriptions and court colors', () => {
    expect(ARENA_IDS).toEqual(['pro_arena', 'retro_gym', 'street', 'neon', 'beach', 'rooftop']);
    for (const a of ARENAS) {
      expect(a.label).toBeTruthy();
      expect(a.description.length).toBeGreaterThan(10);
      for (const c of [a.line, a.apron, a.paint]) expect(c).toMatch(/^#[0-9a-f]{6}$/i);
    }
    expect(new Set(ARENAS.map((a) => a.floor)).size).toBe(6);        // every arena has its own floor
    expect(arenaById('neon')!.label).toBe('Neon Nights');
    expect(arenaById('nope')).toBeUndefined();
  });

  it('has every layer for every arena', () => {
    for (const id of ARENA_IDS) {
      for (const layer of ['backdrop', 'team', 'crowd', 'crowd_home', 'crowd_away', 'floor', 'overlay'] as const) {
        expect(ARENA_IMAGES[id][layer]()).toBeTruthy();
      }
      expect(arenaFloor(id).tile).toBe(ARENA_META.floorTile);
    }
  });

  it('matches the court pixel size and pans with parallax', () => {
    expect(arenaScale(608)).toBe(4);
    const s = arenaScale(608);
    expect(backdropLeft(0, 1080, s)).toBeCloseTo(0);
    expect(backdropLeft(1, 1080, s)).toBeCloseTo(1080 - BACKDROP_W * s);  // the right end lines up with the screen
    expect(backdropLeft(0.5, 1080, s)).toBeLessThan(0);
  });

  it('animates the crowd, faster and on their feet when it gets loud', () => {
    const calm = new Set(Array.from({ length: 40 }, (_, i) => crowdFrame(i / 10)));
    expect([...calm].sort()).toEqual([0, 1, 2]);
    const loud = Array.from({ length: 40 }, (_, i) => crowdFrame(i / 30, 1));
    expect(loud.filter((f) => f === 2).length).toBeGreaterThan(loud.filter((f) => f === 0).length);
  });
});
