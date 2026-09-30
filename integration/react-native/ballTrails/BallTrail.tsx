import React, { memo } from 'react';
import { Image, View } from 'react-native';

import { TRAIL_IMAGES } from './trailImages';
import { TRAIL_META as meta, trailFrame, type TrailId } from './trails';

export type BallTrailProps = {
  trail: TrailId;
  /** screen position of the ball's centre */
  x: number;
  y: number;
  /** the ball's velocity on screen; the trail streams out behind it */
  vx: number;
  vy: number;
  /** on-screen ball diameter in px (match the size you draw the ball at) */
  size: number;
  /** seconds the ball has been in the air (drives the animation); or pass `frame` */
  seconds?: number;
  frame?: number;
};

/**
 * The ball with an animated trail behind it, pointed along its velocity.
 * Draw it in place of the ball while the ball is in the air; the ball is
 * part of the image.
 */
export const BallTrail = memo(function BallTrail({ trail, x, y, vx, vy, size, seconds = 0, frame }: BallTrailProps) {
  const s = size / meta.ballDiameter;                  // screen px per strip px
  const f = frame ?? trailFrame(trail, seconds);
  const w = meta.frameWidth * s;
  const h = meta.frameHeight * s;
  const [cx, cy] = meta.ballCenter;
  const angle = Math.atan2(vy, vx);
  // rotate about the ball centre: shift it to the view centre, rotate, shift back
  const ox = cx * s - w / 2;
  const oy = cy * s - h / 2;
  return (
    <View
      pointerEvents="none"
      style={{
        position: 'absolute',
        left: x - cx * s,
        top: y - cy * s,
        width: w,
        height: h,
        overflow: 'hidden',
        transform: [
          { translateX: ox }, { translateY: oy },
          { rotate: `${angle}rad` },
          { translateX: -ox }, { translateY: -oy },
        ],
      }}
    >
      <Image
        source={TRAIL_IMAGES[trail]()}
        fadeDuration={0}
        style={{ position: 'absolute', left: -f * w, top: 0, width: w * meta.frames, height: h }}
      />
    </View>
  );
});
