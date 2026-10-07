import { framesOf, headOverlay, SPRITE_DATA as SPRITES } from './frames';
import { COSMETICS, OUTFIT_PRESETS, outfitTints, presetsFor, shiftingColor } from './outfit';
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
    expect(names).toContain('air_guitar');
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

describe('developer tee', () => {
  it('shifts color over time and loops', () => {
    const dev = OUTFIT_PRESETS.find((p) => p.id === 'developer_tee')!;
    const a = outfitTints(dev.outfit, dev.colors.jersey, false, 0).shirt;
    const b = outfitTints(dev.outfit, dev.colors.jersey, false, 2).shirt;
    const c = outfitTints(dev.outfit, dev.colors.jersey, false, 8).shirt;
    expect(a).toMatch(/^#[0-9a-f]{6}$/);
    expect(b).not.toBe(a);
    expect(c).toBe(a);
    expect(outfitTints(dev.outfit, '#fff', false, 2).wear[region('sleeveShort')]).toBe(b);
    expect(shiftingColor(0)).toBe(shiftingColor(8));
  });

  it('is exclusive to developers', () => {
    expect(presetsFor(false).some((p) => p.id === 'developer_tee')).toBe(false);
    expect(presetsFor(true).some((p) => p.id === 'developer_tee')).toBe(true);
    expect(presetsFor(false).some((p) => p.id === 'brown_suit')).toBe(true);
  });
});

describe('hats, parachute pants, cowboy boots, air guitar', () => {
  it('draws every hat on every frame, and hats hide the hair', () => {
    for (const hat of COSMETICS.hats) {
      const t = outfitTints({ hat: { style: hat.value } }, '#fff');
      for (const f of framesOf('h4-average', 'idle')) expect(headOverlay(f, t.headwear!.style)[0] ?? headOverlay(f, t.headwear!.style)[1]).not.toBeNull();
      const keepsHair = hat.value === 'halo' || hat.value === 'cat_ears';
      expect(t.hideHair).toBe(!keepsHair);
      expect(t.hideFacial).toBe(hat.value === 'goat_head');
    }
  });

  it('spins the propeller', () => {
    const styles = new Set([0, 0.08, 0.16, 0.24, 0.32].map((s) => outfitTints({ hat: { style: 'propeller_hat' } }, '#fff', false, s).headwear!.style));
    expect(styles.size).toBe(4);
  });

  it('makes parachute pants full length with their detail layer', () => {
    const t = outfitTints({ shorts: { color: '#8a3cf0', style: 'parachute' } }, '#fff');
    expect(t.legPrint).toBe(0);
    expect(t.wear[region('pantsLong')]).toBe('#8a3cf0');
    for (const f of framesOf('h4-average', 'run')) expect(f.legPrints?.[0]).toBeTruthy();
  });

  it('pulls cowboy boots up the shin over the socks', () => {
    const t = outfitTints({ shoes: { style: 'cowboy_boots', color: '#7a4520' } }, '#fff');
    expect(t.sock).toBe('#7a4520');
    expect(t.wear[region('bootShaft')]).toBe('#7a4520');
    expect(t.wear[region('bootTop')]).not.toBeNull();
    for (const f of framesOf('h4-average', 'walk')) expect(f.wear![region('bootShaft')]).not.toBeNull();
  });

  it('has an air guitar celebration', () => {
    const a = SPRITES.anims.air_guitar;
    expect(a.loop).toBe(true);
    expect(a.group).toBe('celebrations');
  });
});
