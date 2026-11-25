import React, { memo } from 'react';
import { View } from 'react-native';

import { PlayerSprite, type PlayerSpriteProps } from '../playerSprites/PlayerSprite';
import type { Ghost, GhostTrail } from './moveFx';

export type PlayerGhostsProps = Omit<PlayerSpriteProps, 'anim' | 'frame' | 'x' | 'y' | 'flip'> & {
  trail: GhostTrail;
  /** what trail.update() returned this frame */
  ghosts: readonly Ghost[];
};

/**
 * Faded afterimages of a fast player, oldest first. Draw it just before his
 * <PlayerSprite>. Each ghost is a full sprite, so use it for the ball handler
 * on a break or as a park-mode cosmetic rather than for all ten players.
 */
export const PlayerGhosts = memo(function PlayerGhosts({ trail, ghosts, ...sprite }: PlayerGhostsProps) {
  return (
    <>
      {[...ghosts].reverse().map((g, i) => (
        <View
          key={i}
          pointerEvents="none"
          style={{ position: 'absolute', left: 0, top: 0, right: 0, bottom: 0, opacity: trail.opacityOf(g) }}
        >
          <PlayerSprite {...sprite} anim={g.anim} frame={g.frame} x={g.x} y={g.y} flip={g.flip} />
        </View>
      ))}
    </>
  );
});
