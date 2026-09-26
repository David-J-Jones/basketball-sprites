import React, { memo, useMemo } from 'react';
import { SvgXml } from 'react-native-svg';

import { faceFromSeed, faceSvg, type HeadshotJersey } from './faceArt';

export type HeadshotProps = {
  /** the league player's numeric id: the face seed */
  playerId: number;
  /** rendered width and height */
  size: number;
  /** team jersey color (or { jersey, trim, number }); navy if omitted */
  jersey?: HeadshotJersey;
};

/** Square head-and-shoulders pixel-art portrait for a player. */
export const Headshot = memo(function Headshot({ playerId, size, jersey }: HeadshotProps) {
  const key = typeof jersey === 'string' ? jersey : JSON.stringify(jersey ?? null);
  const xml = useMemo(
    () => faceSvg(faceFromSeed(playerId), playerId, jersey, { crop: true }),
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [playerId, key],
  );
  return <SvgXml xml={xml} width={size} height={size} />;
});
