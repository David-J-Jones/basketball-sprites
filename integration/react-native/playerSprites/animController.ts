/**
 * PlayerAnimator: picks the animation, frame and facing for one player from
 * his velocity, so sprites stay smooth when the sim (especially AI players)
 * changes direction a lot.
 *
 * - Facing only changes through a turn animation, and only after the new
 *   direction has held for `turnDelay`. Jittery velocity never flips the
 *   sprite back and forth.
 * - Starting and stopping play run_start / run_stop.
 * - run, dribble_run and dribble_run_far share one stride clock, so switching
 *   between them never restarts the legs. The stride speeds up and slows down
 *   with the player's actual speed.
 * - Actions (shoot, pass, crossovers, dunks...) play once and then hand back
 *   to movement.
 *
 * Call update(dt, input) once per rendered frame and pass the result to
 * <PlayerSprite anim frame flip />.
 */
import raw from './spriteData.json';
import { handAfter, type BallHand } from './moves';
import type { AnimName, RunStyle, SpriteData } from './types';

const ANIMS = (raw as unknown as SpriteData).anims;

export type Facing = 'right' | 'left';

export type AnimatorInput = {
  /** velocity along the court's x axis (screen right = +), any unit */
  vx: number;
  /** velocity in depth (screen down = +) */
  vy?: number;
  hasBall?: boolean;
  /**
   * Keep facing this way whatever the movement (e.g. a defender facing the
   * ball handler). Moving the other way backpedals instead of turning.
   */
  face?: Facing;
  /** defensive stance: idle -> defense_stance, sideways -> defense_slide, backward -> backpedal */
  defending?: boolean;
  /** tired: idles bent over, hands on knees */
  tired?: boolean;
  /** guarding the ball handler: pressure stance (guard_on_ball) instead of defense_stance */
  onBall?: boolean;
};

export type AnimatorOutput = {
  anim: AnimName;
  frame: number;
  /** pass straight to <PlayerSprite flip> */
  flip: boolean;
  facing: Facing;
  /** which hand is dribbling (changes after crossovers) */
  hand: BallHand;
};

export type AnimatorOptions = {
  /** speed at which a standing player starts running */
  runOn: number;
  /** speed below which a running player stops (lower than runOn) */
  runOff: number;
  /** |vx| needed before a direction change counts at all */
  turnSpeed: number;
  /** seconds the new direction must hold before the player turns */
  turnDelay: number;
  /** minimum seconds between switching standing <-> running */
  minHold: number;
  /** speed at which the run cycle plays at its normal rate */
  refSpeed: number;
  /** walking -> running above this speed */
  sprintOn: number;
  /** running -> walking below this speed (lower than sprintOn) */
  sprintOff: number;
  /** speed at which the walk cycle plays at its normal rate */
  walkRefSpeed: number;
  /** seconds standing before a waiting pose (hands on hips) */
  idleVariantAfter: number;
  /** this player's run cycle (see runStyleFor); all share one stride clock */
  runStyle: RunStyle;
};

/** Defaults assume the sim works in feet per second. */
export const DEFAULT_ANIMATOR_OPTIONS: AnimatorOptions = {
  runOn: 2.5,
  runOff: 1.2,
  turnSpeed: 1.5,
  turnDelay: 0.15,
  minHold: 0.2,
  refSpeed: 14,
  sprintOn: 8,
  sprintOff: 6,
  walkRefSpeed: 4,
  idleVariantAfter: 5,
  runStyle: 'run',
};

type OneShot = {
  anim: AnimName;
  t: number;
  /** facing before and after (differs for turns) */
  from: Facing;
  to: Facing;
};

const LOCOMOTION: AnimName[] = [
  'idle', 'run', 'run_upright', 'run_power', 'run_bounce', 'guard_on_ball', 'walk', 'dribble', 'dribble_run', 'dribble_far', 'dribble_run_far',
  'walk_dribble', 'walk_dribble_far', 'backpedal', 'defense_stance', 'defense_slide',
];

export class PlayerAnimator {
  facing: Facing;
  hand: BallHand = 'near';
  private opts: AnimatorOptions;
  private moving = false;
  private running = false;   // running pace (vs walking) while moving
  private loopT = 0;         // clock for backpedal / slides
  private sinceSwitch = 1e9;
  private pendingTurn = 0;
  private stride = 0;   // shared run-cycle clock, in frames
  private idleT = 0;    // shared clock for idle / dribble-in-place
  private shot: OneShot | null = null;
  private holding: AnimName | null = null;

  constructor(facing: Facing = 'right', opts: Partial<AnimatorOptions> = {}) {
    this.facing = facing;
    this.opts = { ...DEFAULT_ANIMATOR_OPTIONS, ...opts };
  }

  /** Is a one-shot (action, turn, start/stop) playing? */
  get busy(): boolean {
    return this.shot !== null;
  }

  /**
   * Play an animation once (shoot, pass, steal, crossover_up, dunk_hang...).
   * `face` turns the player instantly first, e.g. toward the basket.
   * Movement resumes when it finishes.
   */
  play(anim: AnimName, face?: Facing): void {
    if (face) this.facing = face;
    this.pendingTurn = 0;
    this.shot = { anim, t: 0, from: this.facing, to: this.facing };
  }

  /**
   * Hold a looping pose in place of movement until release(), e.g. setting
   * a screen: hold('screen_hold', 'screen_set'). The optional intro plays
   * first. Facing and movement are frozen while holding; play() still works
   * (e.g. 'screen_contact' when a defender runs into the screen).
   */
  hold(anim: AnimName, intro?: AnimName): void {
    this.holding = anim;
    this.moving = false;
    this.pendingTurn = 0;
    this.idleT = 0;
    if (intro) this.play(intro);
  }

  /** Stop holding; movement picks up again on the next update. */
  release(): void {
    this.holding = null;
    this.sinceSwitch = 1e9;
  }

  get isHolding(): boolean {
    return this.holding !== null;
  }

  /** Snap facing without a turn animation (e.g. at an inbound or reset). */
  setFacing(face: Facing): void {
    this.facing = face;
    this.pendingTurn = 0;
  }

  update(dt: number, input: AnimatorInput): AnimatorOutput {
    const o = this.opts;
    const hasBall = !!input.hasBall;
    const speed = Math.hypot(input.vx, input.vy ?? 0);
    this.sinceSwitch += dt;
    this.idleT += dt;

    // ---- one-shot playing: advance it, and hand back when it ends
    // start/stop can be cut short if the player changes his mind
    if (this.shot?.anim === 'run_stop' && speed > o.runOn) {
      this.shot = null;
      this.moving = true;
      this.sinceSwitch = 0;
      this.stride = 0;
    } else if (this.shot?.anim === 'run_start' && speed < o.runOff) {
      this.shot = null;
      this.moving = false;
      this.sinceSwitch = 0;
    }
    if (this.shot) {
      const s = this.shot;
      const info = ANIMS[s.anim];
      s.t += dt;
      const frame = Math.floor(s.t * info.fps);
      if (frame < info.frameCount) {
        const flipAt = info.events.flipAt;
        const face = flipAt !== undefined && frame >= flipAt ? s.to : s.from;
        return this.out(s.anim, frame, face);
      }
      this.finish(s);
    }

    // ---- holding a pose (screens): ignore movement and turning
    if (this.holding) {
      const info = ANIMS[this.holding];
      const i = Math.floor(this.idleT * info.fps);
      return this.out(this.holding, info.loop ? i % info.frameCount : Math.min(i, info.frameCount - 1), this.facing);
    }

    // ---- start / stop moving (with hysteresis and a minimum hold)
    const plain = !hasBall && !input.defending;
    if (!this.moving && speed > o.runOn && this.sinceSwitch >= o.minHold) {
      this.moving = true;
      this.running = speed > o.sprintOn;
      this.sinceSwitch = 0;
      this.stride = 0;
      this.loopT = 0;
      if (plain && this.running) {
        this.shot = { anim: 'run_start', t: 0, from: this.facing, to: this.facing };
        return this.update(0, input);
      }
    } else if (this.moving && speed < o.runOff && this.sinceSwitch >= o.minHold) {
      this.moving = false;
      this.sinceSwitch = 0;
      this.idleT = 0;
      if (plain && this.running) {
        this.shot = { anim: 'run_stop', t: 0, from: this.facing, to: this.facing };
        return this.update(0, input);
      }
    }
    // walk <-> run: both cycles are 12 frames on one stride clock, so no pop
    if (this.moving && !this.running && speed > o.sprintOn) this.running = true;
    if (this.moving && this.running && speed < o.sprintOff) this.running = false;

    // ---- facing: only turn once the new direction has held for a moment
    const want: Facing | null =
      input.face ?? (input.vx > o.turnSpeed ? 'right' : input.vx < -o.turnSpeed ? 'left' : null);
    if (want && want !== this.facing) {
      this.pendingTurn += dt;
      if (this.pendingTurn >= o.turnDelay) {
        this.pendingTurn = 0;
        const anim: AnimName = hasBall ? 'turn_dribble' : this.moving ? 'turn_run' : 'turn';
        this.shot = { anim, t: 0, from: this.facing, to: want };
        return this.update(0, input);
      }
    } else {
      this.pendingTurn = 0;
    }

    // ---- locomotion
    if (this.moving) {
      const vy = input.vy ?? 0;
      const along = this.facing === 'right' ? input.vx : -input.vx;   // + = toward where he faces
      const sideways = Math.abs(vy) > Math.abs(input.vx) * 1.2;
      const backward = along < -o.turnSpeed && (input.face !== undefined || input.defending);
      let loop: AnimName | null = null;
      if (input.defending && sideways) loop = 'defense_slide';
      else if (backward) loop = 'backpedal';
      if (loop) {
        this.loopT += dt;
        const info = ANIMS[loop];
        return this.out(loop, Math.floor(this.loopT * info.fps) % info.frameCount, this.facing);
      }
      const ref = this.running ? o.refSpeed : o.walkRefSpeed;
      const base = this.running ? ANIMS.run.fps : ANIMS.walk.fps;
      this.stride = (this.stride + dt * base * Math.min(1.5, Math.max(0.7, speed / ref))) % ANIMS.run.frameCount;
      const far = this.hand === 'far' ? '_far' : '';
      const anim = (!hasBall ? (this.running ? o.runStyle : 'walk')
        : `${this.running ? 'dribble_run' : 'walk_dribble'}${far}`) as AnimName;
      return this.out(anim, Math.floor(this.stride) % ANIMS[anim].frameCount, this.facing);
    }
    let anim: AnimName;
    if (hasBall) anim = this.hand === 'far' ? 'dribble_far' : 'dribble';
    else if (input.defending) anim = input.onBall ? 'guard_on_ball' : 'defense_stance';
    else if (input.tired) anim = 'idle_knees';
    else anim = this.idleT > o.idleVariantAfter ? 'idle_hips' : 'idle';
    const info = ANIMS[anim];
    return this.out(anim, Math.floor(this.idleT * info.fps) % info.frameCount, this.facing);
  }

  private finish(s: OneShot): void {
    this.shot = null;
    this.facing = s.to;
    this.hand = handAfter(s.anim) ?? this.hand;
    // run_start ends just before run frame 0; turn_run ends on it
    if (s.anim === 'run_start') this.stride = 0;
    if (s.anim === 'turn_run') this.stride = 1;
    if (!LOCOMOTION.includes(s.anim)) this.idleT = 0;
  }

  private out(anim: AnimName, frame: number, face: Facing): AnimatorOutput {
    return { anim, frame, flip: face === 'left', facing: face, hand: this.hand };
  }
}
