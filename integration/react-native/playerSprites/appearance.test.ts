import {
  bodyFor,
  runStyleFor,
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
import { BODY_LOADERS } from './bodyData';
import { framesOf, headOverlay, SPRITE_DATA as SPRITES } from './frames';
import type { AnimName } from './types';

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

  it('picks 7 height classes and 5 weight classes', () => {
    expect(bodyFor(72, 185)).toBe('h1-average');
    expect(bodyFor(74, 150)).toBe('h2-slim');
    expect(bodyFor(76, 205)).toBe('h3-average');
    expect(bodyFor(78, 205)).toBe('h4-lean');
    expect(bodyFor(79, 260)).toBe('h4-heavy');
    expect(bodyFor(80, 245)).toBe('h5-solid');
    expect(bodyFor(82, 240)).toBe('h6-average');
    expect(bodyFor(86, 300)).toBe('h7-heavy');
  });

  it('gives each player a stable run style that suits his body', () => {
    expect(runStyleFor(42, 'h4-average')).toBe(runStyleFor(42, 'h4-average'));
    const count = (body: Parameters<typeof runStyleFor>[1], style: string) =>
      Array.from({ length: 400 }, (_, i) => runStyleFor(i + 1, body)).filter((s) => s === style).length;
    expect(count('h7-heavy', 'run_power')).toBeGreaterThan(count('h1-slim', 'run_power'));
    expect(count('h1-slim', 'run_bounce')).toBeGreaterThan(count('h7-heavy', 'run_bounce'));
  });
});

describe('sprite data', () => {
  const anims = Object.keys(SPRITES.anims) as AnimName[];

  it('has every body, animation, hair style and facial hair', () => {
    expect(Object.keys(BODY_LOADERS).sort()).toEqual([...BODY_KEYS].sort());
    expect(SPRITES.headwear).toEqual(['headband', 'wide_headband', 'tied_headband']);
    expect(SPRITES.hairStyles).toEqual(HAIR_STYLES.filter((h) => h !== 'bald'));
    expect(SPRITES.facialHair).toEqual(FACIAL_HAIR.filter((h) => h !== 'none'));
    expect(anims).toEqual(expect.arrayContaining(['dunk_basic', 'run_power', 'guard_on_ball', 'celebrate']));
    const styles = SPRITES.hairStyles.length + SPRITES.facialHair.length + SPRITES.headwear.length;
    for (const body of BODY_KEYS) {
      for (const anim of anims) {
        const frames = framesOf(body, anim);
        expect(frames).toHaveLength(SPRITES.anims[anim].frameCount);
        for (const f of frames) {
          expect(f.skin).not.toBeNull();
          expect(f.detail).not.toBeNull();
          expect(f.shorts).not.toBeNull();
          if (f.wear) expect(f.wear).toHaveLength(SPRITES.wearRegions.length);
          expect(SPRITES.overlays[f.head[0]]).toHaveLength(styles);
        }
      }
    }
  });

  it('draws hair on every frame for full styles', () => {
    for (const anim of anims) {
      for (const f of framesOf('h4-average', anim)) {
        expect(headOverlay(f, 'afro')[0]).not.toBeNull();
        expect(headOverlay(f, 'crew')[1]).not.toBeNull();
        expect(headOverlay(f, 'headband')[0]).not.toBeNull();
      }
    }
  });

  it('only references pieces and pages that exist', () => {
    const n = SPRITES.pieces.length;
    for (const [page] of SPRITES.pieces) expect(page).toBeLessThan(SPRITES.pages.length);
    for (const pair of SPRITES.overlayPairs) for (const r of pair) if (r) expect(r[0]).toBeLessThan(n);
    for (const set of SPRITES.overlays) for (const i of set) expect(i).toBeLessThan(SPRITES.overlayPairs.length);
    for (const body of BODY_KEYS) {
      for (const anim of anims) {
        for (const f of framesOf(body, anim)) {
          for (const r of [f.skin, f.jersey, f.trim, f.detail, f.shorts, f.sock, f.shoe, f.sole, ...(f.wear ?? [])]) {
            if (!r) continue;
            const [page, , , w, h] = r;
            expect(page).toBeLessThan(SPRITES.pages.length);
            expect(SPRITES.pageGroups[page].startsWith(body + '/')).toBe(true);
            expect(w * h).toBeGreaterThan(0);
          }
        }
      }
    }
  });

  it('keeps each animation group on its own pages', () => {
    const groups = new Set(SPRITES.pageGroups);
    expect(groups.has('h4-average/core')).toBe(true);
    expect(groups.has('h4-average/run_power')).toBe(true);
    expect(groups.has('hair/afro')).toBe(true);
    expect(SPRITES.anims.dunk_windmill.group).toBe('dunks');
    expect(SPRITES.anims.shoot_kick_fade.group).toBe('shot_kick');
    expect(SPRITES.anims.walk.group).toBe('core');
  });

  it('crossovers move the ball across the body', () => {
    for (const body of BODY_KEYS) {
      const up = framesOf(body, 'crossover_up').map((f) => f.ballDepth ?? 0);
      const down = framesOf(body, 'crossover_down').map((f) => f.ballDepth ?? 0);
      expect(up[0]).toBe(1);
      expect(up[up.length - 1]).toBe(-1);
      expect(down[0]).toBe(-1);
      expect(down[down.length - 1]).toBe(1);
      expect(framesOf(body, 'dribble_far').every((f) => (f.ballDepth ?? 0) < 0)).toBe(true);
      expect(framesOf(body, 'dribble_run_far').every((f) => (f.ballDepth ?? 0) < 0)).toBe(true);
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
