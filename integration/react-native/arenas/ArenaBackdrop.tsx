import React, { memo } from 'react';
import { Image, View } from 'react-native';

import { ARENA_IMAGES } from './arenaImages';
import { ARENA_META, BACKDROP_H, BACKDROP_W, backdropLeft, crowdFrame, type ArenaId } from './arenas';

export type ArenaBackdropProps = {
  arena: ArenaId;
  /** screen width in px */
  width: number;
  /** screen px per art px; use arenaScale(screenHeight) so it matches the court */
  scale: number;
  /** camera pan, 0 (left end of the court) .. 1 (right end) */
  pan?: number;
  /** seconds of game time, for the crowd */
  time?: number;
  /** 0..1: how loud the building is (see crowdFrame) */
  excitement?: number;
  /** home team color: banners, ribbon boards, seat stripes, half the crowd's shirts */
  homeColor: string;
  /** away team color: their fans' shirts */
  awayColor: string;
};

const img = { position: 'absolute' as const, top: 0 };

/**
 * Everything behind the far sideline: the arena's backdrop, its team-colored
 * parts, and the crowd (home and away fans in their teams' colors). Draw it
 * at the top of the screen, under the game's court, banner and ribbon.
 */
export const ArenaBackdrop = memo(function ArenaBackdrop({
  arena, width, scale, pan = 0.5, time = 0, excitement = 0, homeColor, awayColor,
}: ArenaBackdropProps) {
  const src = ARENA_IMAGES[arena];
  const w = BACKDROP_W * scale;
  const h = BACKDROP_H * scale;
  const left = backdropLeft(pan, width, scale);
  const f = crowdFrame(time, excitement);
  const strip = { ...img, left: -f * w, width: w * ARENA_META.crowdFrames, height: h };
  return (
    <View pointerEvents="none" style={{ position: 'absolute', left: 0, top: 0, width, height: h, overflow: 'hidden' }}>
      <View style={{ position: 'absolute', left, top: 0, width: w, height: h }}>
        <Image source={src.backdrop()} fadeDuration={0} style={{ ...img, left: 0, width: w, height: h }} />
        <Image source={src.team()} fadeDuration={0} style={{ ...img, left: 0, width: w, height: h, tintColor: homeColor }} />
        <View style={{ position: 'absolute', left: 0, top: 0, width: w, height: h, overflow: 'hidden' }}>
          <Image source={src.crowd()} fadeDuration={0} style={strip} />
          <Image source={src.crowd_home()} fadeDuration={0} style={{ ...strip, tintColor: homeColor }} />
          <Image source={src.crowd_away()} fadeDuration={0} style={{ ...strip, tintColor: awayColor }} />
        </View>
      </View>
    </View>
  );
});

export type ArenaOverlayProps = { arena: ArenaId; width: number; height: number; opacity?: number };

/** The arena's lighting (spotlights, sunbeams, neon haze...), drawn over everything but the HUD. */
export const ArenaOverlay = memo(function ArenaOverlay({ arena, width, height, opacity = 1 }: ArenaOverlayProps) {
  return (
    <Image
      source={ARENA_IMAGES[arena].overlay()}
      fadeDuration={0}
      pointerEvents="none"
      style={{ position: 'absolute', left: 0, top: 0, width, height, opacity }}
    />
  );
});
