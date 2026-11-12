import { BLINK_EVERY, COACH_FRAMES, COACH_LINES, coachFrame, coachMessage, typedLength } from './lines';

describe('coach', () => {
  it('has lines for every moment, with the player name filled in', () => {
    for (const [kind, lines] of Object.entries(COACH_LINES)) {
      expect(lines.length).toBeGreaterThan(1);
      const m = coachMessage(kind as keyof typeof COACH_LINES, { name: 'Jones', seed: 1 });
      expect(m).not.toContain('{name}');
      expect(m).toContain('Jones');
    }
    expect(coachMessage('more_minutes')).toMatch(/more minutes/);
    expect(coachMessage('contract_extension', { seed: 1 })).toMatch(/extension/);
    expect(coachMessage('playing_well', { seed: 0 })).toContain('kid');
  });

  it('is stable for a given seed', () => {
    expect(coachMessage('slump', { seed: 7 })).toBe(coachMessage('slump', { seed: 7 }));
  });

  it('moves his mouth while talking, closes it on pauses, and blinks when quiet', () => {
    const talking = new Set(Array.from({ length: 30 }, (_, i) => coachFrame(i / 30, true)));
    expect(talking.has('open')).toBe(true);
    expect(talking.has('wide')).toBe(true);
    expect(talking.has('blink')).toBe(false);
    expect(coachFrame(0.5, true, true)).toBe('closed');
    expect(coachFrame(1, false)).toBe('closed');
    expect(coachFrame(BLINK_EVERY - 0.05, false)).toBe('blink');
    for (let i = 0; i < 100; i++) expect(COACH_FRAMES).toContain(coachFrame(i * 0.37, i % 2 === 0));
  });

  it('types the line out, pausing after punctuation', () => {
    const text = 'Hey. You.';
    expect(typedLength(text, 0)).toBe(0);
    expect(typedLength(text, 100)).toBe(text.length);
    const a = typedLength('aaaaaaaaaa', 0.1, 50);
    const b = typedLength('a.aaaaaaaa', 0.1, 50);
    expect(b).toBeLessThan(a);
    for (let s = 0; s < 2; s += 0.05) expect(typedLength(text, s)).toBeLessThanOrEqual(typedLength(text, s + 0.05));
  });
});
