import { LEAGUE_TEAMS, LOGO_STYLES, LOGO_STYLE_LABELS, TEAM_LOGO_STYLES, TEAM_LOGOS, teamLogo } from './index';

describe('team logos', () => {
  it('has a classic badge and three alternate logos for every team', () => {
    expect(LOGO_STYLES).toEqual(['classic', 'retro', 'simple', 'current']);
    for (const style of LOGO_STYLES) expect(LOGO_STYLE_LABELS[style]).toBeTruthy();
    for (const team of LEAGUE_TEAMS) {
      expect(TEAM_LOGOS[team.id]).toBeTruthy();
      for (const style of LOGO_STYLES) expect(teamLogo(team.id, style)).toBeTruthy();
    }
    expect(Object.keys(TEAM_LOGO_STYLES)).toHaveLength(30);
    expect(teamLogo('PHX')).toBe(TEAM_LOGOS.PHX);
    expect(teamLogo('NOPE', 'retro')).toBeUndefined();
  });
});
