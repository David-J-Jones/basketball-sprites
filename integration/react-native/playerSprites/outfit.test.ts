import { framesOf, headOverlay, SPRITE_DATA as SPRITES } from './frames';
import { COSMETICS, OUTFIT_PRESETS, developerNeonColor, outfitTints } from './outfit';
import type { AnimName, Outfit } from './types';

const region = (name: string) => SPRITES.wearRegions.indexOf(name as never);

describe('outfits', () => {
  it('defaults to the league look', () => {
    const t = outfitTints(undefined, '#123456');
    expect(t).toMatchObject(SPRITES.defaultOutfit);
    expect(t.wear.every((w) => w === null)).toBe(true);
    expect(t.headwear).toBeNull();
  });

  it('covers the right skin areas for sleeves, long shorts and tall socks', () => {
    const o: Outfit = {
      shirt: { sleeves: 'long', sleeveColor: '#000000' },
      shorts: { color: '#ff0000', length: 'long' },
      socks: { color: '#00ff00', tall: true },
      wristbands: { color: '#ffffff' },
    };
    const t = outfitTints(o, '#123456');
    expect(t.wear[region('sleeveShort')]).toBe('#000000');
    expect(t.wear[region('sleeveLong')]).toBe('#000000');
    expect(t.wear[region('shortsLong')]).toBe('#ff0000');
    expect(t.wear[region('sockTall')]).toBe('#00ff00');
    expect(t.wear[region('wristband')]).toBe('#ffffff');
    expect(outfitTints({ shirt: { sleeves: 'short' } }, '#123456').wear[region('sleeveShort')]).toBe('#123456');
    expect(outfitTints({ shirt: { sleeves: 'short' } }, '#123456').wear[region('sleeveLong')]).toBeNull();
  });

  it('keeps a shooting sleeve on the same arm when the player turns around', () => {
    const o: Outfit = { armSleeve: { color: '#111111', arm: 'right' } };
    expect(outfitTints(o, '#fff', false).wear[region('armSleeveNear')]).toBe('#111111');
    expect(outfitTints(o, '#fff', true).wear[region('armSleeveFar')]).toBe('#111111');
    expect(outfitTints(o, '#fff', true).wear[region('armSleeveNear')]).toBeNull();
  });

  it('has wear masks and headbands in the sprite data', () => {
    for (const anim of ['idle', 'run', 'shoot', 'dance_robot'] as AnimName[]) {
      for (const f of framesOf('h4-average', anim)) {
        expect(f.wear).not.toBeNull();
        expect(f.wear![region('sleeveShort')]).not.toBeNull();
        expect(f.wear![region('shortsLong')]).not.toBeNull();
        for (const hb of COSMETICS.headbands) expect(headOverlay(f, hb.value)[0]).not.toBeNull();
      }
    }
  });

  it('has 3 dances and 5 victory poses, each victory pose ending on its hold frame', () => {
    const names = Object.keys(SPRITES.anims);
    expect(names.filter((n) => n.startsWith('dance_'))).toHaveLength(3);
    const victory = names.filter((n) => n.startsWith('victory_')) as AnimName[];
    expect(victory).toHaveLength(5);
    for (const v of victory) {
      const a = SPRITES.anims[v];
      expect(a.loop).toBe(false);
      expect(a.events.hold).toBe(a.frameCount - 1);
      expect(a.group).toBe('celebrations');
    }
  });
});

describe('shirt prints', () => {
  it('has at least 10 prints, each with a piece on every frame of a few animations', () => {
    expect(SPRITES.prints.length).toBeGreaterThanOrEqual(10);
    expect(SPRITES.prints.map((p) => p.id)).toEqual(
      expect.arrayContaining(['hawaiian', 'tie_dye', 'wave', 'us_flag']),
    );
    for (const anim of ['idle', 'run', 'shoot', 'dunk_athletic'] as AnimName[]) {
      for (const f of framesOf('h4-average', anim)) {
        expect(f.prints).toHaveLength(SPRITES.prints.length);
        for (const p of f.prints!) {
          expect(p).not.toBeNull();
          expect(SPRITES.pageGroups[p![0]].startsWith('h4-average/print_')).toBe(true);
        }
      }
    }
  });

  it('turns a printed shirt into a tee and picks the right print piece', () => {
    const t = outfitTints({ shirt: { print: 'us_flag' } }, '#ffffff');
    expect(t.print).toBe(SPRITES.prints.findIndex((p) => p.id === 'us_flag'));
    expect(t.wear[region('sleeveShort')]).toBe('#ffffff');
    expect(t.wear[region('sleeveLong')]).toBeNull();
    const long = outfitTints({ shirt: { print: 'plaid', sleeves: 'long', sleeveColor: '#111111' } }, '#ffffff');
    expect(long.wear[region('sleeveLong')]).toBe('#111111');
    expect(outfitTints({}, '#ffffff').print).toBeNull();
    expect(COSMETICS.prints).toHaveLength(SPRITES.prints.length);
  });
});

describe('brown suit', () => {
  it('is a full suit: jacket print with long sleeves, trousers to the shoe, matching socks', () => {
    const suit = OUTFIT_PRESETS.find((p) => p.id === 'brown_suit')!;
    const t = outfitTints(suit.outfit, suit.colors.jersey);
    expect(t.print).toBe(SPRITES.prints.findIndex((p) => p.id === 'suit_brown'));
    expect(t.wear[region('sleeveShort')]).toBe('#7a4a26');
    expect(t.wear[region('sleeveLong')]).toBe('#7a4a26');
    expect(t.wear[region('shortsLong')]).toBe('#6e4222');
    expect(t.wear[region('pantsLong')]).toBe('#6e4222');
    expect(t.sock).toBe('#6e4222');
    expect(t.wear[region('sockTall')]).toBeNull();
  });

  it('has trouser masks on every frame', () => {
    for (const f of framesOf('h4-average', 'walk')) expect(f.wear![region('pantsLong')]).not.toBeNull();
  });
});


describe('developer neon tee', () => {
  it('is developer-only, short sleeved, and cycles through the hue wheel', () => {
    const dev = OUTFIT_PRESETS.find((p) => p.id === 'developer_neon_tee')!;
    expect(dev.developerOnly).toBe(true);
    expect(dev.outfit.shirt).toMatchObject({ sleeves: 'short', effect: 'developer_neon' });
    expect(developerNeonColor(0)).toBe('#ff0000');
    expect(developerNeonColor(2)).toBe('#80ff00');
    expect(developerNeonColor(4)).toBe('#00ffff');
    expect(developerNeonColor(6)).toBe('#8000ff');
    expect(developerNeonColor(8)).toBe('#ff0000');
    const tint = outfitTints(dev.outfit, developerNeonColor(4));
    expect(tint.wear[region('sleeveShort')]).toBe('#00ffff');
    expect(tint.wear[region('sleeveLong')]).toBeNull();
  });
});
