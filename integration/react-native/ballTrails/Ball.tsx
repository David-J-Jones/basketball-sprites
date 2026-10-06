import React, { memo } from 'react';
import { Image, View } from 'react-native';

import { BALL_IMAGE } from './trailImages';
import { ballFrame, TRAIL_META as meta } from './trails';

export type BallProps = {
  /** screen position of the ball's centre */
  x: number;
  y: number;
  /** on-screen size of the ball sprite in px (the sprite cell, outline included) */
  size: number;
  /** seconds of spin; drives the backspin animation. Or pass `frame`. */
  seconds?: number;
  frame?: number;
  /** spin speed in frames per second (default 20; 0 = still) */
  fps?: number;
  /**
   * Mirror it. The spin is backspin for a ball moving right; flip it when
   * the ball moves left so it still reads as backspin.
   */
  flip?: boolean;
  /** the flattened frame, for the instant a dribble hits the floor */
  squash?: boolean;
  /** draw the ground shadow instead of the ball (place it under the ball, on the floor) */
  shadow?: boolean;
};

/** The basketball: shaded, with seams, spinning. Pixel art at the same scale as the players. */
export const Ball = memo(function Ball({
  x, y, size, seconds = 0, frame, fps, flip = false, squash = false, shadow = false,
}: BallProps) {
  const b = meta.ball;
  const cell = shadow ? b.shadow : squash ? b.squash : frame ?? (fps === 0 ? 0 : ballFrame(seconds, fps));
  const cells = b.spinFrames + 2;
  return (
    <View
      pointerEvents="none"
      style={{
        position: 'absolute',
        left: x - size / 2,
        top: y - size / 2,
        width: size,
        height: size,
        overflow: 'hidden',
        transform: flip ? [{ scaleX: -1 }] : undefined,
      }}
    >
      <Image
        source={BALL_IMAGE}
        fadeDuration={0}
        style={{ position: 'absolute', left: -cell * size, top: 0, width: size * cells, height: size }}
      />
    </View>
  );
});
