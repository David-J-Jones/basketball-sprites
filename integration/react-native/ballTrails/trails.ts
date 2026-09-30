/** Trail metadata and timing, kept free of image requires so it works in tests and plain logic. */
import meta from './trails.json';

export const TRAIL_META = meta;
export const TRAIL_IDS = Object.keys(meta.trails) as TrailId[];
export type TrailId =
  | 'none' | 'fire' | 'laser' | 'bubbles' | 'money' | 'lightning' | 'rainbow' | 'ice' | 'smoke' | 'stars'
  | 'confetti' | 'afterimage';
export type TrailInfo = { label: string; fps: number };
export const TRAILS = meta.trails as Record<TrailId, TrailInfo>;

/** Frame of a trail's loop after `seconds`. */
export function trailFrame(trail: TrailId, seconds: number): number {
  return Math.floor(Math.max(0, seconds) * TRAILS[trail].fps) % meta.frames;
}
