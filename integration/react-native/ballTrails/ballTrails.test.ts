import meta from './trails.json';
import { ballFrame, trailFrame, TRAILS, TRAIL_IDS } from './trails';

describe('ball trails', () => {
  it('has a label and fps for every trail, including at least 10 effects', () => {
    expect(TRAIL_IDS).toEqual([
      'none', 'fire', 'laser', 'bubbles', 'money', 'lightning', 'rainbow', 'ice', 'smoke', 'stars', 'confetti',
      'afterimage',
    ]);
    for (const id of TRAIL_IDS) {
      expect(TRAILS[id].label).toBeTruthy();
      expect(TRAILS[id].fps).toBeGreaterThan(0);
    }
  });

  it('loops through its frames at the trail fps', () => {
    expect(trailFrame('fire', 0)).toBe(0);
    expect(trailFrame('fire', 1.01 / TRAILS.fire.fps)).toBe(1);
    expect(trailFrame('fire', (meta.frames + 0.01) / TRAILS.fire.fps)).toBe(0);
  });

  it('puts the ball centre inside the frame, toward the front', () => {
    const [cx, cy] = meta.ballCenter;
    expect(cx).toBeGreaterThan(meta.frameWidth * 0.8);
    expect(cx).toBeLessThan(meta.frameWidth);
    expect(Math.abs(cy - meta.frameHeight / 2)).toBeLessThanOrEqual(meta.scale);
  });

  it('spins the plain ball through a full loop of frames', () => {
    expect(meta.ball.spinFrames).toBe(16);
    expect(ballFrame(0)).toBe(0);
    expect(ballFrame(1.01 / meta.ball.fps)).toBe(1);
    expect(ballFrame((meta.ball.spinFrames + 0.01) / meta.ball.fps)).toBe(0);
    expect(meta.ball.squash).toBe(meta.ball.spinFrames);
    expect(meta.ball.shadow).toBe(meta.ball.spinFrames + 1);
  });
});
