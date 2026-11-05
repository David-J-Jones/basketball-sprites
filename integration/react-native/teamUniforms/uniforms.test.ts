import { framesOf, SPRITE_DATA as SPRITES } from '../playerSprites/frames';
import { LEAGUE_TEAMS } from '../teamLogos';
import { TEAM_UNIFORMS, UNIFORM_CARDS, UNIFORM_KINDS, getUniform, uniformSprite } from './index';

describe('team uniforms', () => {
  it('gives every league team a home, away and city uniform with a card', () => {
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

  it("keeps each team's three uniforms distinct, and city editions unique across the league", () => {
    const cities = new Set<string>();
    for (const t of Object.values(TEAM_UNIFORMS)) {
      const looks = UNIFORM_KINDS.map((k) => `${t[k].pattern}|${t[k].jersey}|${t[k].accent}`);
      expect(new Set(looks).size).toBe(3);
      cities.add(`${t.city.pattern}|${t.city.jersey}|${t.city.accent}|${t.city.accent2}`);
    }
    expect(cities.size).toBe(Object.keys(TEAM_UNIFORMS).length);
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
