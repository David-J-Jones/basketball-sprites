import { framesOf, SPRITE_DATA as SPRITES } from '../playerSprites/frames';
import { LEAGUE_TEAMS } from '../teamLogos';
import {
  RETRO_KINDS, TEAM_UNIFORMS, UNIFORM_CARDS, UNIFORM_KINDS, UNIFORM_UNLOCKS, availableUniforms, getUniform, uniformSprite,
} from './index';

describe('team uniforms', () => {
  it('gives every league team home, away, city and three throwback uniforms with a card', () => {
    expect(UNIFORM_KINDS).toEqual(['home', 'away', 'city', 'retro70', 'retro80', 'retro90']);
    for (const team of LEAGUE_TEAMS) {
      for (const kind of UNIFORM_KINDS) {
        const u = getUniform(team.id, kind)!;
        expect(u).toBeTruthy();
        for (const c of [u.jersey, u.trim, u.accent, u.accent2, u.shorts]) expect(c).toMatch(/^#[0-9A-F]{6}$/i);
        expect(SPRITES.uniformPatterns.some((p) => p.id === u.pattern)).toBe(true);
        expect(UNIFORM_CARDS[team.id][kind]).toBeTruthy();
      }
      expect(getUniform(team.id, 'city')!.name).not.toBe('Home');
    }
  });

  it("keeps each team's six uniforms distinct, and city editions unique across the league", () => {
    const cities = new Set<string>();
    for (const t of Object.values(TEAM_UNIFORMS)) {
      const looks = UNIFORM_KINDS.map((k) => `${t[k].pattern}|${t[k].jersey}|${t[k].accent}`);
      expect(new Set(looks).size).toBe(UNIFORM_KINDS.length);
      cities.add(`${t.city.pattern}|${t.city.jersey}|${t.city.accent}|${t.city.accent2}`);
    }
    expect(cities.size).toBe(Object.keys(TEAM_UNIFORMS).length);
  });

  it('names the throwbacks by era and keeps them locked until earned', () => {
    for (const t of Object.values(TEAM_UNIFORMS)) {
      expect(t.retro70.name).toBe("'70s Throwback");
      expect(t.retro80.name).toBe("'80s Throwback");
      expect(t.retro90.name).toBe("'90s Throwback");
    }
    for (const k of RETRO_KINDS) {
      expect(UNIFORM_UNLOCKS[k].unlockedByDefault).toBe(false);
      expect(UNIFORM_UNLOCKS[k].hint).toBeTruthy();
    }
    expect(availableUniforms()).toEqual(['home', 'away', 'city']);
    expect(availableUniforms(['retro90'])).toEqual(['home', 'away', 'city', 'retro90']);
  });

  it('dresses each era in its own patterns', () => {
    const eras: Record<string, string[]> = {
      retro70: ['retro', 'chest_band', 'yoke'],
      retro80: ['pinstripes', 'two_tone', 'classic', 'chevron'],
      retro90: ['lightning', 'flames', 'fade', 'chevron', 'waves', 'stars'],
    };
    for (const t of Object.values(TEAM_UNIFORMS)) {
      for (const k of RETRO_KINDS) expect(eras[k]).toContain(t[k].pattern);
    }
  });

  it('maps to PlayerSprite props', () => {
    const u = getUniform('PHX', 'away')!;
    const s = uniformSprite(u);
    expect(s.colors).toMatchObject({ jersey: u.jersey, pattern: u.pattern, accent: u.accent, accent2: u.accent2 });
    expect(s.outfit.shorts?.color).toBe(u.shorts);
    expect(getUniform('NOPE')).toBeNull();
  });

  it('has the pattern masks in every frame', () => {
    const n = SPRITES.uniformPatterns.length;
    const classic = SPRITES.uniformPatterns.findIndex((p) => p.id === 'classic');
    for (const f of framesOf('h4-average', 'run')) {
      expect(f.uniforms).toHaveLength(2 * n);
      expect(f.uniforms![2 * classic]).not.toBeNull();
    }
  });
});
