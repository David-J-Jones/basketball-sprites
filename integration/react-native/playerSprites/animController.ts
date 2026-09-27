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
import type { AnimName, SpriteData } from './types';

const ANIMS = (raw as unknown as SpriteData).anims;

export type Facing = 'right' | 'left';

export type AnimatorInput = {
  /** velocity along the court's x axis (screen right = +), any unit */
  vx: number;
  /** velocity in depth (screen down = +); only used for overall speed */
  vy?: number;
  hasBall?: boolean;
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
};

/** Defaults assume the sim works in feet per second. */
export const DEFAULT_ANIMATOR_OPTIONS: AnimatorOptions = {
  runOn: 2.5,
  runOff: 1.2,
  turnSpeed: 1.5,
  turnDelay: 0.15,
  minHold: 0.2,
  refSpeed: 14,
};

type OneShot = {
  anim: AnimName;
  t: number;
  /** facing before and after (differs for turns) */
  from: Facing;
  to: Facing;
};

const LOCOMOTION: AnimName[] = ['idle', 'run', 'dribble', 'dribble_run', 'dribble_far', 'dribble_run_far'];

export class PlayerAnimator {
  facing: Facing;
  hand: BallHand = 'near';
  private opts: AnimatorOptions;
  private moving = false;
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
    if (!this.moving && speed > o.runOn && this.sinceSwitch >= o.minHold) {
      this.moving = true;
      this.sinceSwitch = 0;
      if (!hasBall) {
        this.shot = { anim: 'run_start', t: 0, from: this.facing, to: this.facing };
        return this.update(0, input);
      }
      this.stride = 0;
    } else if (this.moving && speed < o.runOff && this.sinceSwitch >= o.minHold) {
      this.moving = false;
      this.sinceSwitch = 0;
      this.idleT = 0;
      if (!hasBall) {
        this.shot = { anim: 'run_stop', t: 0, from: this.facing, to: this.facing };
        return this.update(0, input);
      }
    }

    // ---- facing: only turn once the new direction has held for a moment
    const want: Facing | null = input.vx > o.turnSpeed ? 'right' : input.vx < -o.turnSpeed ? 'left' : null;
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
      const runFps = ANIMS.run.fps * Math.min(1.5, Math.max(0.7, speed / o.refSpeed));
      this.stride = (this.stride + dt * runFps) % ANIMS.run.frameCount;
      const anim: AnimName = !hasBall ? 'run' : this.hand === 'far' ? 'dribble_run_far' : 'dribble_run';
      return this.out(anim, Math.floor(this.stride) % ANIMS[anim].frameCount, this.facing);
    }
    const anim: AnimName = !hasBall ? 'idle' : this.hand === 'far' ? 'dribble_far' : 'dribble';
    const info = ANIMS[anim];
    return this.out(anim, Math.floor(this.idleT * info.fps) % info.frameCount, this.facing);
  }

  private finish(s: OneShot): void {
    this.shot = null;
    this.facing = s.to;
    if (s.anim === 'crossover_up' || s.anim === 'crossover_down') this.hand = handAfter(s.anim);
    // run_start ends just before run frame 0; turn_run ends on it
    if (s.anim === 'run_start') this.stride = 0;
    if (s.anim === 'turn_run') this.stride = 1;
    if (!LOCOMOTION.includes(s.anim)) this.idleT = 0;
  }

  private out(anim: AnimName, frame: number, face: Facing): AnimatorOutput {
    return { anim, frame, flip: face === 'left', facing: face, hand: this.hand };
  }
}
