import React, { memo } from 'react';
import { View } from 'react-native';

import type { SwishSegment } from './moveFx';

export type BallSwishTrailProps = {
  /** what BallSwish.update() returned this frame */
  segments: readonly SwishSegment[];
  /** one color for the whole streak, overriding the palette set on BallSwish */
  color?: string;
};

/**
 * The ball's swish: short rotated bars along its path, thinning and fading
 * toward the tail. Draw it just before the ball, after the player.
 */
export const BallSwishTrail = memo(function BallSwishTrail({ segments, color }: BallSwishTrailProps) {
  return (
    <>
      {segments.map((s, i) => {
        const dx = s.x2 - s.x1;
        const dy = s.y2 - s.y1;
        const len = Math.hypot(dx, dy) + s.width * 0.5;
        return (
          <View
            key={i}
            pointerEvents="none"
            style={{
              position: 'absolute',
              left: (s.x1 + s.x2) / 2 - len / 2,
              top: (s.y1 + s.y2) / 2 - s.width / 2,
              width: len,
              height: s.width,
              borderRadius: s.width / 2,
              backgroundColor: color ?? s.color,
              opacity: s.opacity,
              transform: [{ rotate: `${Math.atan2(dy, dx)}rad` }],
            }}
          />
        );
      })}
    </>
  );
});
