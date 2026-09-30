import { framesOf, headOverlay, SPRITE_DATA as SPRITES } from './frames';
import { COSMETICS, outfitTints } from './outfit';
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
