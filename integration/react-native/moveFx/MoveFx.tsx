import React, { memo } from 'react';
import { Image, View } from 'react-native';

import { FX_IMAGES } from './fxImages';
import { MOVE_FX, type FxInstance } from './moveFx';

export type MoveFxProps = {
  /** what MoveFxEmitter.update() returned this frame */
  effects: readonly FxInstance[];
};

/** One effect: a cropped frame of its strip, anchored on its foot point and mirrored for a player facing left. */
const Effect = ({ e }: { e: FxInstance }) => {
  const m = MOVE_FX[e.fx];
  const w = m.width * e.scale;
  const h = m.height * e.scale;
  const [ax, ay] = m.anchor;
  // mirroring about the anchor: the anchor stays put, the strip flips around it
  const left = e.flip ? e.x - (m.width - ax) * e.scale : e.x - ax * e.scale;
  return (
    <View
      pointerEvents="none"
      style={{
        position: 'absolute',
        left,
        top: e.y - ay * e.scale,
        width: w,
        height: h,
        overflow: 'hidden',
        opacity: e.opacity,
        transform: e.flip ? [{ scaleX: -1 }] : undefined,
      }}
    >
      <Image
        source={FX_IMAGES[e.fx]()}
        fadeDuration={0}
        style={{ position: 'absolute', left: -e.frame * w, top: 0, width: w * m.frames, height: h }}
      />
    </View>
  );
};

/**
 * Draws a player's movement effects. Put it before the player's
 * <PlayerSprite> so dust sits under his feet; speed lines are behind him anyway.
 */
export const MoveFx = memo(function MoveFx({ effects }: MoveFxProps) {
  return (
    <>
      {effects.map((e) => (
        <Effect key={e.key} e={e} />
      ))}
    </>
  );
});
