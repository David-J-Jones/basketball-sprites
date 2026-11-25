import type { ImageSourcePropType } from 'react-native';

import { ARENA_IMAGES } from './arenaImages';
import { ARENA_META, arenaById, type ArenaId, type ArenaInfo } from './arenas';

/**
 * The arena's floor for the game's court renderer: a tileable texture
 * (`tile` art px square, so tile * scale screen px), plus line, apron and
 * paint colors that suit it.
 */
export function arenaFloor(arena: ArenaId): { source: ImageSourcePropType; tile: number; colors: ArenaInfo } {
  return { source: ARENA_IMAGES[arena].floor(), tile: ARENA_META.floorTile, colors: arenaById(arena)! };
}
