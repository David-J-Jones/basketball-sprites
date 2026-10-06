import React, { memo } from 'react';
import { Image, View } from 'react-native';

import { hairColor, skinColor } from './appearance';
import type { BodyKey } from './features';
import { frameData, headOverlay } from './frames';
import { developerNeonColor, outfitTints } from './outfit';
import { PAGES, SPRITES } from './spriteData';
import type { AnimName, JerseyColors, Outfit, PlacedPiece, PlayerLook } from './types';

export type PlayerSpriteProps = {
  look: PlayerLook;
  colors: JerseyColors;
  anim: AnimName;
  frame: number;
  /** screen position of the player's feet (the sprite's bottom-centre anchor) */
  x: number;
  y: number;
  /** screen px per frame px; use scaleForHeight() */
  scale: number;
  /** true when the player faces left */
  flip?: boolean;
  /**
   * Jump frames (shoot, layup, block, rebound, dunks) have a small hop drawn
   * in. If the sim already raises the player off the floor (z), set this to
   * false so the hop isn't added twice.
   */
  bakedLift?: boolean;
  /** park-mode cosmetics; leave out for the league look */
  outfit?: Outfit;
  /** Seconds on a continuous game clock; drives animated cosmetic effects. */
  effectTime?: number;
};

type PieceProps = { piece: PlacedPiece | null; scale: number; tint?: string; offsetX?: number; offsetY?: number; opacity?: number };

/** One cropped piece of an atlas page, optionally tinted a flat color. */
const Piece = ({ piece, scale, tint, offsetX = 0, offsetY = 0, opacity = 1 }: PieceProps) => {
  if (!piece) return null;
  const [page, sx, sy, w, h, dx, dy] = piece;
  const [pageW, pageH] = SPRITES.pages[page];
  // mask pages are stored at lower resolution; k converts page px to frame px
  const s = SPRITES.pageScale[page] * scale;
  return (
    <View
      style={{
        position: 'absolute',
        left: dx * scale + offsetX,
        top: dy * scale + offsetY,
        width: w * s,
        height: h * s,
        overflow: 'hidden',
      }}
    >
      <Image
        source={PAGES[page]}
        fadeDuration={0}
        style={{
          position: 'absolute',
          left: -sx * s,
          top: -sy * s,
          width: pageW * s,
          height: pageH * s,
          tintColor: tint,
          opacity,
        }}
      />
    </View>
  );
};

/** Tight pixel-art glow: eight translucent copies around the shirt mask. */
const GlowPiece = ({ piece, scale, tint }: PieceProps) => {
  if (!piece) return null;
  const d = Math.max(1, SPRITES.scale * scale * 0.45);
  return <>{[
    [-d, 0], [d, 0], [0, -d], [0, d],
    [-d, -d], [d, -d], [-d, d], [d, d],
  ].map(([offsetX, offsetY], i) => (
    <Piece key={i} piece={piece} scale={scale} tint={tint} offsetX={offsetX} offsetY={offsetY} opacity={0.24} />
  ))}</>;
};

export const PlayerSprite = memo(function PlayerSprite({
  look,
  colors,
  anim,
  frame,
  x,
  y,
  scale,
  flip = false,
  bakedLift = true,
  outfit,
  effectTime = 0,
}: PlayerSpriteProps) {
  const f = frameData(look.body, anim, frame);
  const facial = look.facialHair ? headOverlay(f, look.facialHair) : null;
  const hair = look.hairStyle ? headOverlay(f, look.hairStyle) : null;
  const hairTint = hairColor(look);
  const neon = outfit?.shirt?.effect === 'developer_neon';
  const shirtColor = neon ? developerNeonColor(effectTime) : colors.jersey;
  const shirtTrim = neon ? shirtColor : colors.trim;
  const wear = outfitTints(outfit, shirtColor, flip);
  const sleeveShort = SPRITES.wearRegions.indexOf('sleeveShort');
  const sleeveLong = SPRITES.wearRegions.indexOf('sleeveLong');
  const band = wear.headwear ? headOverlay(f, wear.headwear.style) : null;
  const drop = bakedLift ? 0 : f.lift * scale;
  return (
    <View
      pointerEvents="none"
      style={{
        position: 'absolute',
        left: x - SPRITES.anchorX * scale,
        top: y - SPRITES.anchorY * scale + drop,
        width: SPRITES.frameWidth * scale,
        height: SPRITES.frameHeight * scale,
        transform: flip ? [{ scaleX: -1 }] : undefined,
      }}
    >
      {neon && <GlowPiece piece={f.jersey} scale={scale} tint={shirtColor} />}
      {neon && f.wear && <GlowPiece piece={f.wear[sleeveShort]} scale={scale} tint={shirtColor} />}
      {neon && f.wear && <GlowPiece piece={f.wear[sleeveLong]} scale={scale} tint={shirtColor} />}
      <Piece piece={f.skin} scale={scale} tint={skinColor(look)} />
      {f.wear?.map((piece, i) =>
        wear.wear[i] ? <Piece key={i} piece={piece} scale={scale} tint={wear.wear[i]!} /> : null,
      )}
      <Piece piece={f.jersey} scale={scale} tint={shirtColor} />
      <Piece piece={f.trim} scale={scale} tint={shirtTrim} />
      {wear.print !== null && <Piece piece={f.prints?.[wear.print] ?? null} scale={scale} />}
      <Piece piece={f.shorts} scale={scale} tint={wear.shorts} />
      <Piece piece={f.sock} scale={scale} tint={wear.sock} />
      <Piece piece={f.shoe} scale={scale} tint={wear.shoe} />
      <Piece piece={f.sole} scale={scale} tint={wear.sole} />
      <Piece piece={f.detail} scale={scale} />
      {facial && <Piece piece={facial[0]} scale={scale} tint={hairTint} />}
      {facial && <Piece piece={facial[1]} scale={scale} />}
      {hair && <Piece piece={hair[0]} scale={scale} tint={hairTint} />}
      {hair && <Piece piece={hair[1]} scale={scale} />}
      {band && <Piece piece={band[0]} scale={scale} tint={wear.headwear!.color} />}
      {band && <Piece piece={band[1]} scale={scale} />}
    </View>
  );
});

/** Frame index for an animation that has been playing for `seconds`. */
export function frameAt(anim: AnimName, seconds: number): number {
  const a = SPRITES.anims[anim];
  const i = Math.floor(Math.max(0, seconds) * a.fps);
  return a.loop ? i % a.frameCount : Math.min(i, a.frameCount - 1);
}

/** Length of one play-through of an animation, in seconds. */
export function animDuration(anim: AnimName): number {
  const a = SPRITES.anims[anim];
  return a.frameCount / a.fps;
}

/** Scale so the standing player is `screenHeightPx` tall (sole to top of head). */
export function scaleForHeight(body: BodyKey, screenHeightPx: number): number {
  return screenHeightPx / SPRITES.standingHeight[body];
}

/**
 * Convert a frame-local point (nearHand, farHand, ball from the frame data)
 * to a screen position, using the same x/y/scale/flip as the PlayerSprite.
 */
export function frameToScreen(
  point: [number, number],
  x: number,
  y: number,
  scale: number,
  flip = false,
): { x: number; y: number } {
  const dx = (point[0] - SPRITES.anchorX) * scale;
  return { x: x + (flip ? -dx : dx), y: y + (point[1] - SPRITES.anchorY) * scale };
}
