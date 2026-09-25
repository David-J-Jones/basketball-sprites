import React, { memo } from 'react';
import { Image, View } from 'react-native';

import { hairColor, skinColor } from './appearance';
import { PAGES, SPRITES } from './spriteData';
import type { AnimName, BuildName, JerseyColors, PieceRef, PlayerLook } from './types';

export type PlayerSpriteProps = {
  look: PlayerLook;
  colors: JerseyColors;
  anim: AnimName;
  frame: number;
  /** screen position of the player's feet (the sprite's bottom-centre anchor) */
  x: number;
  y: number;
  /** screen px per atlas px; use scaleForHeight() */
  scale: number;
  /** true when the player faces left */
  flip?: boolean;
  /**
   * Jump frames (shoot, layup, block, rebound) have a small hop drawn in.
   * If the sim already raises the player off the floor (z), set this to
   * false so the hop isn't added twice.
   */
  bakedLift?: boolean;
};

type PieceProps = { piece: PieceRef | null; scale: number; tint?: string };

/** One cropped piece of an atlas page, optionally tinted a flat color. */
const Piece = ({ piece, scale, tint }: PieceProps) => {
  if (!piece) return null;
  const [index, dx, dy] = piece;
  const [page, sx, sy, w, h] = SPRITES.pieces[index];
  const [pageW, pageH] = SPRITES.pages[page];
  return (
    <View
      style={{
        position: 'absolute',
        left: dx * scale,
        top: dy * scale,
        width: w * scale,
        height: h * scale,
        overflow: 'hidden',
      }}
    >
      <Image
        source={PAGES[page]}
        fadeDuration={0}
        style={{
          position: 'absolute',
          left: -sx * scale,
          top: -sy * scale,
          width: pageW * scale,
          height: pageH * scale,
          tintColor: tint,
        }}
      />
    </View>
  );
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
}: PlayerSpriteProps) {
  const frames = SPRITES.frames[look.build][anim];
  const f = frames[((frame % frames.length) + frames.length) % frames.length];
  const hair = look.hairStyle ? f.hair[look.hairStyle] : null;
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
      <Piece piece={f.skin} scale={scale} tint={skinColor(look)} />
      <Piece piece={f.jersey} scale={scale} tint={colors.jersey} />
      <Piece piece={f.trim} scale={scale} tint={colors.trim} />
      <Piece piece={f.detail} scale={scale} />
      {hair && <Piece piece={hair[0]} scale={scale} tint={hairColor(look)} />}
      {hair && <Piece piece={hair[1]} scale={scale} />}
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
export function scaleForHeight(build: BuildName, screenHeightPx: number): number {
  return screenHeightPx / SPRITES.standingHeight[build];
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
