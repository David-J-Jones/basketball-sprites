/**
 * What the coach says, and which portrait frame to show while he says it.
 * Pure functions (no React), so they're easy to test and reuse.
 */

/** Frames in base.png, left to right. */
export const COACH_FRAMES = ['closed', 'small', 'open', 'wide', 'blink'] as const;
export type CoachFrame = (typeof COACH_FRAMES)[number];

export type CoachMessageKind =
  | 'playing_well'
  | 'more_minutes'
  | 'starting_lineup'
  | 'contract_extension'
  | 'all_star'
  | 'slump'
  | 'bench'
  | 'trade_rumors';

/** A few ways to say each thing; {name} is the player's name (or "kid"). */
export const COACH_LINES: Record<CoachMessageKind, string[]> = {
  playing_well: [
    "Congrats, {name}. You've been playing well. Keep it up.",
    "I see you out there, {name}. That's the kind of hoops we need.",
    "Hey {name}, nice work lately. The whole staff has noticed.",
  ],
  more_minutes: [
    "Congrats, {name}. You've been playing well. We're going to get you some more minutes.",
    "You've earned it, {name}. Starting tonight, you're getting more run.",
    "Keep this up and the minutes will keep coming. I'm bumping you up the rotation, {name}.",
  ],
  starting_lineup: [
    "{name}, you're in the starting five tonight. Don't make me regret it.",
    "Big news, {name}. You're starting. Go show them why.",
  ],
  contract_extension: [
    "The front office wants to talk extension, {name}. You've been playing great.",
    "Congrats, {name}. Management's putting a contract extension on the table. You earned it.",
    "You keep hooping like this, {name}, and they'll pay you like it. Extension talks start today.",
  ],
  all_star: [
    "All-Star, {name}! Couldn't be prouder. Go represent us.",
    "They voted you in, {name}. All-Star weekend. Enjoy it, then get back to work.",
  ],
  slump: [
    "Rough stretch, {name}. Keep shooting. They'll fall.",
    "Shake it off, {name}. Everybody slumps. Get in the gym.",
  ],
  bench: [
    "I'm cutting your minutes for now, {name}. Earn them back in practice.",
    "{name}, you're coming off the bench for a bit. Show me something.",
  ],
  trade_rumors: [
    "You've probably heard the rumors, {name}. Tune them out and play your game.",
    "Don't read the headlines, {name}. Focus on tonight.",
  ],
};

/** Pick a line for a moment in the career (seeded, so it's stable for a given event). */
export function coachMessage(kind: CoachMessageKind, opts: { name?: string; seed?: number } = {}): string {
  const lines = COACH_LINES[kind];
  const i = Math.abs(Math.floor(opts.seed ?? 0)) % lines.length;
  return lines[i].replace(/\{name\}/g, opts.name?.trim() || 'kid');
}

/** Mouth shapes cycled while talking: small, open, wide, open, small, closed. */
const TALK_CYCLE: CoachFrame[] = ['small', 'open', 'wide', 'open', 'small', 'closed'];
export const TALK_FPS = 10;
export const BLINK_EVERY = 3.4;   // seconds
export const BLINK_FOR = 0.14;    // seconds

/**
 * The portrait frame at `seconds` since the popup opened. While talking the
 * mouth cycles; `pausing` (on punctuation) closes it. When quiet he blinks
 * every few seconds.
 */
export function coachFrame(seconds: number, talking: boolean, pausing = false): CoachFrame {
  const t = Math.max(0, seconds);
  if (talking && !pausing) return TALK_CYCLE[Math.floor(t * TALK_FPS) % TALK_CYCLE.length];
  return t % BLINK_EVERY > BLINK_EVERY - BLINK_FOR ? 'blink' : 'closed';
}

/** Characters shown after `seconds` of typing, with short pauses after punctuation. */
export function typedLength(text: string, seconds: number, charsPerSecond = 38): number {
  let budget = Math.max(0, seconds) * charsPerSecond;
  for (let i = 0; i < text.length; i++) {
    if (budget < 1) return i;
    budget -= 1;
    // a beat after the punctuation shows (only mid-text)
    if (i < text.length - 1) budget -= /[.!?]/.test(text[i]) ? 7 : text[i] === ',' ? 3 : 0;
  }
  return text.length;
}
