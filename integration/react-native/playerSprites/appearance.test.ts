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
import { crossoverFor, dribbleAnim, handAfter, handSwitch, hesitationFor, shotFor } from './moves';
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

  it('crossovers move the ball across the body', () => {
    for (const body of BODY_KEYS) {
      const up = SPRITES.frames[body].crossover_up.map((f) => f.ballDepth ?? 0);
      const down = SPRITES.frames[body].crossover_down.map((f) => f.ballDepth ?? 0);
      expect(up[0]).toBe(1);
      expect(up[up.length - 1]).toBe(-1);
      expect(down[0]).toBe(-1);
      expect(down[down.length - 1]).toBe(1);
      expect(SPRITES.frames[body].dribble_far.every((f) => (f.ballDepth ?? 0) < 0)).toBe(true);
      expect(SPRITES.frames[body].dribble_run_far.every((f) => (f.ballDepth ?? 0) < 0)).toBe(true);
    }
  });

  it('marks the dunk moments', () => {
    expect(SPRITES.anims.dunk_basic.events.dunk).toBeDefined();
    expect(SPRITES.anims.dunk_athletic.events.dunk).toBeDefined();
    expect(SPRITES.anims.dunk_hang.events.hangStart).toBeLessThan(SPRITES.anims.dunk_hang.events.hangEnd);
  });
});

describe('jerseys', () => {
  it('has the 30 league teams plus white', () => {
    expect(TEAMS).toHaveLength(30);
    expect(new Set(TEAMS.map((t) => t.id)).size).toBe(30);
    expect(WHITE_JERSEY.jersey).toBeDefined();
  });

  it('puts the away team in white on a color clash', () => {
    // LA Cars and Toronto Sorries are both red
    const { away } = jerseysForGame(teamById('LAC'), teamById('TOR'));
    expect(away.jersey).toBe(WHITE_JERSEY.jersey);
    const other = jerseysForGame(teamById('CHA'), teamById('NO'));
    expect(other.away.jersey).toBe(teamById('NO').jersey);
  });
});

describe('direction helpers', () => {
  it('crosses up the screen to the far hand and down to the near hand', () => {
    expect(crossoverFor(-1)).toBe('crossover_up');
    expect(crossoverFor(2)).toBe('crossover_down');
    expect(handAfter('crossover_up')).toBe('far');
    expect(handAfter('crossover_down')).toBe('near');
  });

  it('picks the dribble for the ball hand', () => {
    expect(dribbleAnim('near', false)).toBe('dribble');
    expect(dribbleAnim('near', true)).toBe('dribble_run');
    expect(dribbleAnim('far', false)).toBe('dribble_far');
    expect(dribbleAnim('far', true)).toBe('dribble_run_far');
  });
});

describe('move helpers', () => {
  it('names hand-switch moves by screen direction', () => {
    expect(handSwitch('behind_back', -1)).toBe('behind_back_up');
    expect(handSwitch('between_legs', 1)).toBe('between_legs_down');
    expect(handAfter('behind_back_down')).toBe('near');
    expect(handAfter('between_legs_up')).toBe('far');
    expect(handAfter('shoot')).toBeNull();
  });

  it('picks hesitation, walking dribbles and moving shots', () => {
    expect(hesitationFor('far')).toBe('hesitation_far');
    expect(dribbleAnim('far', true, true)).toBe('walk_dribble_far');
    expect(shotFor(8)).toBe('shoot_pullup');
    expect(shotFor(-8)).toBe('shoot_fade');
    expect(shotFor(1)).toBe('shoot');
  });

  it('has every animation the helpers can return', () => {
    for (const name of ['walk_dribble', 'walk_dribble_far', 'hesitation_far', 'shoot_pullup', 'shoot_fade',
      'behind_back_up', 'behind_back_down', 'between_legs_up', 'between_legs_down']) {
      expect(SPRITES.anims[name as AnimName]).toBeDefined();
    }
  });
});
