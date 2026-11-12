import React, { memo } from 'react';
import { Image, View } from 'react-native';

import { COACH_FRAMES, type CoachFrame } from './lines';

const IMAGES = {
  base: require('./base.png'),
  capMask: require('./cap_mask.png'),
  capDetail: require('./cap_detail.png'),
  shirtMask: require('./shirt_mask.png'),
  shirtDetail: require('./shirt_detail.png'),
};

export type CoachPortraitProps = {
  /** on-screen size in px (the art is square, 64 art px) */
  size: number;
  frame?: CoachFrame;
  /** ball cap and polo colors (team colors) */
  capColor?: string;
  shirtColor?: string;
};

const layer = (size: number) => ({ position: 'absolute' as const, left: 0, top: 0, width: size, height: size });

/** The coach's portrait: tinted polo and cap around the face frame. */
export const CoachPortrait = memo(function CoachPortrait({
  size,
  frame = 'closed',
  capColor = '#1D4FB8',
  shirtColor = '#1D4FB8',
}: CoachPortraitProps) {
  const i = Math.max(0, COACH_FRAMES.indexOf(frame));
  return (
    <View style={{ width: size, height: size }} pointerEvents="none">
      <Image source={IMAGES.shirtMask} fadeDuration={0} style={[layer(size), { tintColor: shirtColor }]} />
      <Image source={IMAGES.shirtDetail} fadeDuration={0} style={layer(size)} />
      <View style={[layer(size), { overflow: 'hidden' }]}>
        <Image
          source={IMAGES.base}
          fadeDuration={0}
          style={{ position: 'absolute', left: -i * size, top: 0, width: size * COACH_FRAMES.length, height: size }}
        />
      </View>
      <Image source={IMAGES.capMask} fadeDuration={0} style={[layer(size), { tintColor: capColor }]} />
      <Image source={IMAGES.capDetail} fadeDuration={0} style={layer(size)} />
    </View>
  );
});
