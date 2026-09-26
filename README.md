# Basketball Sprites

Pixel-art court sprites and headshots for the sim league. Both come from the same seeded `FaceSpec`, so a player's headshot and his in-game sprite always match.

![headshot and sprite match](previews/headshot_match.png)

![animations](previews/animations.png)

| | |
|---|---|
| ![jerseys](previews/jerseys.png) | ![bodies](previews/bodies.png) |
| ![looks](previews/looks.png) | ![headshots](previews/headshots.png) |

## What's included

**Court sprites** (side view, facing right)
- **15 bodies:** 5 height classes × 3 weight classes.

  | Height class | 1 | 2 | 3 | 4 | 5 |
  |---|---|---|---|---|---|
  | Height | 6'2" and under | 6'3"–6'5" | 6'6"–6'8" | 6'9"–6'11" | 7'0"+ |

  The weight class comes from BMI: slim < 23.5 ≤ average < 26.5 ≤ heavy. The head is the same size on every body, so tall players look lanky and heavy players carry a gut. The game still scales each sprite by the player's real height.
- **32 team jerseys + a white one**, 5 skin tones, 7 hair styles (bald, buzz, fade, crew, cornrows, afro, locs), 6 hair colors, 5 facial-hair options (none, stubble, mustache, goatee, beard).
- **Always the same:** black shorts, grey shoes.
- **13 animations:** `idle`, `run`, `dribble`, `dribble_run`, `shoot`, `layup`, `pass`, `steal`, `block`, `rebound`, `dunk_basic`, `dunk_athletic`, `dunk_hang`.
- **No ball, shadow or rim in the art.** Frames list where the ball and hands are.

**Headshots** (front view)
- `faceFromSeed(playerId)` → `FaceSpec`, then `faceSvg(face, id, jersey)` → one self-contained SVG, on the same 200×240 grid and square crop (`viewBox="12 24 176 176"`) as before.
- Drawn as 50×60 pixel art in the same style as the sprites. Every pixel is a crisp square, grouped into one `<path>` per color with `shape-rendering="crispEdges"`, so it stays sharp at any size.
- **Features:** 4 head shapes, 5 eye shapes, 5 noses, 4 mouths, 5 eye colors, brow weight, plus the same skin, hair and facial-hair options as the sprite. The jersey uses the team color (navy if none) and can show a number.

## Files

Everything the app needs is in **`integration/react-native/playerSprites/`**.

| File | What it is |
|---|---|
| `palettes.json` | **Edit to change colors:** teams, skin tones, hair and eye colors, height/weight cutoffs. No regenerating needed. |
| `features.ts` | The option lists (skin tones, hair styles…) and body keys, shared by headshots and sprites. |
| `faceArt.ts` | `faceFromSeed`, `faceSvg`, `FaceSpec`, `BY_SKIN`. Replaces the app's current `faceArt.ts`. |
| `Headshot.tsx` | `<Headshot playerId size jersey />`, a thin `SvgXml` wrapper. |
| `appearance.ts` | `playerLook(id, heightIn, weightLbs)` / `lookFromFace()` for sprites, `bodyFor()`, teams, `jerseysForGame()`. |
| `PlayerSprite.tsx` | `<PlayerSprite>` plus `frameAt`, `scaleForHeight`, `frameToScreen`. |
| `faceArt.test.ts`, `appearance.test.ts` | Jest tests (see below). |
| `spriteData.*`, `atlas/*.png` | Generated. Don't edit by hand. |

## How a face is generated

Same design as the app's current system:

1. The seed is the league player's numeric id. `rng(seed)` is mulberry32.
2. Skin tone is picked first (5 tones, weighted `[1, 1, 1.2, 1.3, 1.2]`).
3. Everything else is picked to suit that tone via the `BY_SKIN` table, which gives each tone its own odds for hair color, eye color, coily hair (0.15 → 0.95), nose and mouth. The deepest tone never gets blue/green eyes or blond/auburn hair.
4. Hair style has separate weights for coily and straight hair. Head shape and eyes are even odds. Facial hair leans toward none. Brow weight is 0.85–1.25.
5. Nothing is stored. The face is recomputed from the id every time.

This is a fresh implementation, so its random draws won't line up with the old `faceArt.ts`. **Existing players will get new faces**, but each one stays stable from then on.

## Using it

```tsx
import { Headshot, PlayerSprite, playerLook, teamById, jerseysForGame,
         scaleForHeight, frameAt } from './playerSprites';

// roster screens
<Headshot playerId={player.id} size={64} jersey={{ jersey: team.jersey, trim: team.trim, number: player.number }} />

// game setup: look is cheap to recompute, or cache it per player
const look = playerLook(player.id, player.heightInches, player.weightLbs);
const jerseys = jerseysForGame(teamById(homeId), teamById(awayId));

// every frame
<PlayerSprite
  look={look}
  colors={isHome ? jerseys.home : jerseys.away}
  anim="dunk_athletic"
  frame={frameAt('dunk_athletic', secondsInState)}
  x={feetScreenX} y={feetScreenY}                     // bottom-centre anchor
  scale={scaleForHeight(look.body, onScreenHeightPx)}
  flip={facingLeft}
/>
```

- **The mismatch is fixed.** The sprite look now comes from `faceFromSeed(player.id)`, the same numeric seed as the headshot. The old `generateLook()` (hash of the id string) is gone.
- **Jumps:** shoot, layup, block, rebound and the dunks have a small hop drawn in. Pass `bakedLift={false}` if the sim raises players with `z`.
- **Dunks and the rim:** position the jump so `nearHand`/`farHand` at the `dunk` frame land on the rim. For `dunk_hang`, loop frames `hangStart`–`hangEnd` while he hangs, then play the rest.

| Animation | Frames | FPS | Loop | Events |
|---|---|---|---|---|
| `idle` | 4 | 6 | yes | |
| `run` | 8 | 12 | yes | |
| `dribble` | 6 | 17.14 | yes | `bounce: 3` (0.35 s per bounce) |
| `dribble_run` | 8 | 11.43 | yes | `bounce: 2`, `bounce2: 6` |
| `shoot` | 8 | 12 | no | `gather: 0`, `rise: 2`, `release: 4` |
| `layup` | 8 | 12 | no | `gather: 0`, `takeoff: 2`, `release: 4`. Near hand |
| `pass` | 6 | 14 | no | `release: 3` |
| `steal` | 6 | 14 | no | `activeStart: 2`, `activeEnd: 4` |
| `block` | 6 | 10 | no | `takeoff: 1`, `activeStart: 2`, `activeEnd: 4` |
| `rebound` | 6 | 10 | no | `takeoff: 1`, `catch: 3` |
| `dunk_basic` | 8 | 12 | no | `gather: 0`, `takeoff: 2`, `dunk: 4`. One hand, like the layup |
| `dunk_athletic` | 8 | 11 | no | `gather: 0`, `takeoff: 2`, `dunk: 5`. Heels kicked up, both hands |
| `dunk_hang` | 8 | 10 | no | `gather: 0`, `takeoff: 2`, `dunk: 4`, `hangStart: 5`, `hangEnd: 6` |

## Memory

Each player is drawn from tinted layers: skin, jersey, trim, a crisp detail layer, then facial hair and hair. There are up to 8 small `View`+`Image` pairs per player.

- **Masks** (the tinted parts) are stored at 2× and **detail** at 5×. A mask's soft edge always sits under the crisp outline, so it isn't visible.
- **Per-body pages:** each body's atlas pages are only decoded when a player with that body is on screen. That's about 10–14 MB per body, plus about 14 MB shared for hair and facial hair. A typical game with ~7 distinct bodies uses roughly 90 MB.
- **Knob:** set `SCALE = 4` in the generator to cut body memory by about a third, with slightly softer outlines. `SCALE = 6` is sharper and uses about 45% more.

## Tests

```bash
npx jest playerSprites
```

The tests cover:
- the same seed gives the same face and SVG;
- 50 seeds give more than 45 distinct faces;
- the deepest skin tone never gets blue/green eyes or blond/auburn hair;
- the SVG is self-contained, with scoped `f<id>` ids and no `undefined`/`NaN`;
- every option of every feature draws;
- the sprite look matches the headshot;
- body classes are picked correctly;
- the sprite data covers every body × animation × hair × facial hair;
- jersey clashes switch the away team to white.

## Regenerating the sprite art

```bash
pip install pillow
python3 tools/generate_sprites.py      # ~30 s
```

This rewrites the atlas, `spriteData.*`, and the sprite previews in `previews/`.
- **Poses:** joint-angle tables such as `dunk_hang_frames()`, where 0° points down, 90° forward and 180° up.
- **Bodies:** `BASE_BODY` × `HEIGHT_CLASSES` / `WEIGHT_CLASSES`.
- **Side-view hair and facial hair:** pixel templates in `HAIR_STYLES` / `FACIAL_HAIR`.
- **Headshot art:** lives in `faceArt.ts`. There's nothing to regenerate there.
