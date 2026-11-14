/**
 * Live dub engine, shared by the web app and the browser extension.
 *
 * It plays the sentences of a dub plan (`/api/dubplan`) in sync with a video.
 * The server has usually synthesized and measured every sentence before the
 * plan arrives, so the engine mostly schedules audio that is already cached.
 *
 * Rules (see docs/specs.md §7):
 *  - A sentence is never cut, and never skipped for being late. A late
 *    sentence plays a little faster until the dub catches up with the speaker.
 *  - The video is held only when the dub is more than HOLD_LAG seconds
 *    behind, or the next sentence's audio is still missing READY_GRACE seconds
 *    after it was due.
 *  - Seeking to a part that is not prepared yet behaves like a fresh start:
 *    hold the video there, fetch a small urgent window, resume on the spot.
 *
 * new DubEngine({
 *   media:    { time(), paused(), rate(), play(), pause(), getVolume(), setVolume(v) },
 *   loadPlan: async (from, to, { urgent }) => ({ blocks: DubBlock[], end }),
 *   synth:    async (block, rate) => ({ url, duration }),
 *   onState:  (state, info) => {},  // speaking | catching-up | waiting | buffering | idle | error
 *   options:  { wait: true, duck: 0.15 },
 *   AudioCtor, now, revokeUrl        // injectable for tests
 * })
 */

/** Seconds a sentence may run into the next one's slot before we speed it up more. */
export const SPILL = 0.7;
/** Maximum extra speed-up applied in the browser to catch up. */
export const MAX_FIT = 1.3;
/** Maximum total speed (synthesis rate × browser rate); beyond this speech is hard to follow. */
export const MAX_EFFECTIVE = 1.65;
/** Hold the video only when the dub is further behind than this. */
export const HOLD_LAG = 1.8;
/** Grace period for a sentence whose audio is still being prepared. */
export const READY_GRACE = 1.5;
/** "No pauses" mode only: a sentence missed by more than this is dropped. */
export const SKIP_LAG = 8;
/** Safety net: never hold the video longer than this. */
export const HOLD_MAX_MS = 15000;
/** Seconds of audio to prefetch ahead of playback. */
export const AHEAD = 40;
/** Seconds of plan to keep ahead of playback. */
export const PLAN_AHEAD = 60;
export const PARALLEL = 3;
/** The server synthesizes and measures a whole window before answering, so small windows return faster. */
export const PLAN_WINDOW = 45;
export const FIRST_WINDOW = 12;
/** When the dub trails the speaker by this much, the video slows down a little (if the player allows). */
export const SOFT_LAG = 0.8;
/** How much it slows: a fast speaker is followed by a slightly slower video instead of a racing voice. */
export const SOFT_RATE = 0.85;
/** After a hold hits HOLD_MAX_MS, don't hold again for this long (no endless hold-release loop). */
export const NO_HOLD_MS = 10000;

export class DubEngine {
  constructor(o) {
    this.media = o.media;
    this.loadPlan = o.loadPlan;
    this.synth = o.synth;
    this.onState = o.onState || (() => {});
    this.opts = { wait: true, duck: 0.15, ...(o.options || {}) };
    this.Audio = o.AudioCtor || globalThis.Audio;
    this.now = o.now || (() => performance.now());
    this.revoke = o.revokeUrl || ((u) => URL.revokeObjectURL(u));
    this.planGen = 0;
    this.reset();
  }

  reset() {
    this.order = [];
    this.byIndex = new Map();
    this.pending = new Map(); // i -> Promise
    this.ready = new Map(); // i -> { url, duration }
    this.failed = new Set();
    this.done = new Set();
    this.cur = null;
    this.els = [];
    this.covered = null; // [from, to]
    this.planEnd = Infinity;
    this.loading = false;
    this.holding = false;
    this.lastT = null;
    this.state = "idle";
    this.stats = { spoken: 0, skipped: 0, holds: 0, slowed: 0 };
    this.noHoldUntil = 0;
    this.ourRate = null; // the rate we set to slow the video; null when the user's own rate is in force
  }

  /* ---------------- start / stop ---------------- */

  start() {
    if (this.running) return;
    this.running = true;
    try {
      this.origVolume = this.media.getVolume();
      this.media.setVolume(this.origVolume * this.opts.duck);
    } catch {}
    // Hold the video until the first sentence is ready; the engine resumes it.
    this.startedAt = this.media.time();
    this.userRate = this.media.rate() || 1;
    if (this.opts.wait) {
      this.hold();
      this.emit("buffering");
    }
    this.timer = setInterval(() => {
      try {
        this.tick();
      } catch (e) {
        this.emit("error", { message: String(e && e.message) });
      }
    }, 100);
    this.tick();
  }

  stop() {
    if (!this.running) return;
    this.running = false;
    clearInterval(this.timer);
    this.stopAudio();
    this.soften(false);
    if (this.holding) this.release();
    try {
      if (this.origVolume != null) this.media.setVolume(this.origVolume);
    } catch {}
    for (const a of this.ready.values()) this.revoke(a.url);
    this.reset();
    this.emit("idle");
  }

  setOptions(o) {
    this.opts = { ...this.opts, ...o };
    if (this.running && o.duck != null && this.origVolume != null) {
      try {
        this.media.setVolume(this.origVolume * this.opts.duck);
      } catch {}
    }
    if (o.wait === false && this.holding) this.release();
  }

  /** The user changed the video's volume while the dub runs (the player's slider, a key): that is the
   *  volume to give back on stop, and the original voice is lowered again under the dub. */
  userVolume(v) {
    if (!this.running || !(v >= 0)) return;
    this.origVolume = v;
    try {
      this.media.setVolume(v * this.opts.duck);
    } catch {}
  }

  emit(state, info) {
    if (state === this.state && !info) return;
    this.state = state;
    this.onState(state, info || {});
  }

  /* Players (YouTube especially) report play/pause a little late. For a second
     after we pause or play, trust what we asked for instead of assuming the
     user pressed the button. */
  mediaPlay() {
    this.expectPaused = false;
    this.graceUntil = this.now() + 1000;
    try {
      this.media.play();
    } catch {}
  }

  mediaPause() {
    this.expectPaused = true;
    this.graceUntil = this.now() + 1000;
    try {
      this.media.pause();
    } catch {}
  }

  isPaused() {
    return this.now() < (this.graceUntil || 0) ? this.expectPaused : this.media.paused();
  }

  hold() {
    if (this.holding || this.now() < this.noHoldUntil) return;
    this.holding = true;
    this.holdSince = this.now();
    this.stats.holds++;
    this.mediaPause();
  }

  release() {
    if (!this.holding) return;
    this.holding = false;
    this.mediaPlay();
  }

  /* ---------------- plan ---------------- */

  addBlocks(blocks) {
    for (const b of blocks || []) {
      if (!this.byIndex.has(b.i)) {
        this.byIndex.set(b.i, b);
        this.order.push(b);
      }
    }
    this.order.sort((a, b) => a.start - b.start);
  }

  async ensurePlan(t) {
    // After a seek we don't wait for an older request that is still running (planGen changed).
    if ((this.loading && this.loadingGen === this.planGen) || t > this.planEnd) return;
    const c = this.covered;
    if (c && t >= c[0] - 1 && t + PLAN_AHEAD < c[1]) return;
    // The first window (and the first one after a seek) is small so the dub starts quickly.
    const from = c && t >= c[0] - 1 && t <= c[1] ? c[1] : Math.max(0, t - 2);
    const to = from + (c ? PLAN_WINDOW : FIRST_WINDOW);
    const gen = this.planGen;
    this.loading = true;
    this.loadingGen = gen;
    try {
      // The first window after a start or seek is urgent: the server puts it ahead of background work.
      const res = await this.loadPlan(from, to, { urgent: !c, speed: this.userRate || 1 });
      if (!this.running) return;
      this.addBlocks(res.blocks);
      if (gen !== this.planGen) {
        // The user seeked elsewhere while this loaded: keep the sentences, not the coverage.
        for (const b of this.order) if (b.start < this.startedAt - 0.6) this.done.add(b.i);
        return;
      }
      if (!c) {
        // First plan: sentences before the current position are not spoken.
        for (const b of this.order) if (b.start < this.startedAt - 0.6) this.done.add(b.i);
      }
      if (res.end) this.planEnd = res.end;
      this.covered = c && from === c[1] ? [c[0], to] : [from, to];
      this.edgeGaveUp = false;
    } catch {
      this.emit("error", { message: "plan request failed" });
      await new Promise((r) => setTimeout(r, 3000));
    } finally {
      if (this.loadingGen === gen) this.loading = false;
    }
  }

  /* ---------------- audio ---------------- */

  fetchAudio(b) {
    if (this.pending.has(b.i) || this.ready.has(b.i) || this.failed.has(b.i)) return;
    const p = (async () => {
      const a = await this.synth(b, b.synthRate ?? b.rate ?? 0);
      if (!this.running) return this.revoke(a.url);
      this.ready.set(b.i, a);
    })()
      .catch(() => this.failed.add(b.i))
      .finally(() => this.pending.delete(b.i));
    this.pending.set(b.i, p);
  }

  prefetch(t) {
    for (const b of this.order) {
      if (this.pending.size >= PARALLEL) break;
      if (this.done.has(b.i) || b.start + b.slot < t - 1) continue;
      if (b.start > t + AHEAD) break;
      this.fetchAudio(b);
    }
    for (const [i, a] of this.ready) {
      const b = this.byIndex.get(i);
      if (b && b.start + b.slot < t - 90) {
        this.revoke(a.url);
        this.ready.delete(i);
      }
    }
  }

  /* ---------------- playback ---------------- */

  stopAudio() {
    this.silenceAll();
    this.cur = null;
  }

  /** Guarantee: never two dub voices at the same time. */
  silenceAll(except) {
    for (const el of this.els) {
      if (el !== except) {
        try {
          el.pause();
        } catch {}
      }
    }
    this.els = except ? [except] : [];
  }

  onSeek(t) {
    this.stopAudio();
    this.soften(false);
    this.noHoldUntil = 0;
    this.edgeGaveUp = false;
    this.done = new Set();
    // Sentences already past (or that we are in the middle of) are not spoken.
    for (const b of this.order) if (b.start < t - 0.6) this.done.add(b.i);
    const c = this.covered;
    if (!c || t < c[0] - 1 || t > c[1]) {
      // Jumped somewhere not prepared yet: treat it as a fresh start and hold the
      // video until the first sentence there is ready, instead of letting it play
      // on silently until it reaches the part that was prepared.
      this.planGen++;
      this.covered = null;
      this.startedAt = t;
      // "Was it playing before the seek?" — YouTube reports "buffering" for a moment after one.
      if (this.opts.wait && this.wasPlaying) {
        this.holding = false;
        this.hold();
        this.emit("buffering");
      }
      return;
    }
    if (this.holding) this.release();
  }

  nextBlock() {
    for (const b of this.order) if (!this.done.has(b.i)) return b;
    return null;
  }

  /** The audio element's rate, in real time: the server's correction for the speed the plan was paced
   *  at, sped up (up to MAX_FIT) when the sentence would overrun its time, capped by MAX_EFFECTIVE.
   *  Video seconds and real seconds differ when the user changes the video's speed: at 0.75 a sentence
   *  has 1/0.75 times longer to be said, and the voice gets that time instead of racing. */
  playbackRate(b, duration, t) {
    const userRate = this.userRate || 1;
    const base = ((b.playRate || 1) * userRate) / (b.speed || 1);
    const avail = Math.max(0.6, b.start + b.slot + SPILL - t); // video seconds
    const need = duration ? (duration * userRate) / avail : 0;
    const fit = Math.min(base * MAX_FIT, Math.max(base, need));
    const synthFactor = 1 + (b.synthRate ?? b.rate ?? 0) / 100;
    const cap = MAX_EFFECTIVE / synthFactor;
    return Math.max(0.5, Math.min(fit, Math.max(cap, base)));
  }

  /** Slow the video a little while the dub catches up, or give the user's speed back. */
  soften(on) {
    if (!this.media.setRate) return;
    const user = this.userRate || 1;
    const want = on ? Math.max(0.5, user * SOFT_RATE) : null;
    if (want === this.ourRate) return;
    try {
      this.media.setRate(want ?? user);
      if (on) this.stats.slowed++;
      this.ourRate = want;
    } catch {}
  }

  play(b, a, t) {
    const el = new this.Audio(a.url);
    el.preservesPitch = true;
    el.playbackRate = this.playbackRate(b, a.duration, t);
    if (!a.duration) {
      el.addEventListener("loadedmetadata", () => {
        if (isFinite(el.duration)) el.playbackRate = this.playbackRate(b, el.duration, t);
      });
    }
    const cur = { b, el, ended: false };
    el.addEventListener("ended", () => (cur.ended = true));
    el.addEventListener("error", () => (cur.ended = true));
    this.silenceAll(el);
    this.cur = cur;
    this.done.add(b.i);
    this.stats.spoken++;
    this.startEl(cur);
    if (this.holding) this.release();
    this.emit(t - b.start > 0.4 ? "catching-up" : "speaking", { block: b });
  }

  startEl(cur) {
    cur.el.play().catch((e) => {
      // AbortError = paused before it started (normal, we resume it). Anything else (autoplay blocked) = give up on it.
      if (!e || e.name !== "AbortError") cur.ended = true;
    });
  }

  tick() {
    if (!this.running) return;
    const m = this.media;
    const t = m.time();
    const now = this.now();
    const paused = this.isPaused();
    const wasPlaying = this.wasPlaying;
    this.wasPlaying = !paused || this.holding;

    // Seek?
    if (this.lastT != null) {
      const expected = this.lastT + (paused ? 0 : ((now - this.lastNow) / 1000) * (m.rate() || 1));
      if (Math.abs(t - expected) > 1.5) {
        this.wasPlaying = wasPlaying;
        this.onSeek(t);
        this.wasPlaying = wasPlaying;
        this.lastT = t;
        this.lastNow = now;
        // The play/pause state read above is stale after a seek; continue next tick.
        return;
      }
    }
    this.lastT = t;
    this.lastNow = now;

    // The user changed the video's speed (any rate we didn't set ourselves is theirs).
    const r = m.rate() || 1;
    if (this.ourRate == null ? Math.abs(r - (this.userRate || 1)) > 0.01 : Math.abs(r - this.ourRate) > 0.01) {
      this.userRate = r;
      this.ourRate = null;
    }

    this.ensurePlan(t);
    this.prefetch(t);

    // The user pressed play while we were holding: carry on.
    if (this.holding && !paused) this.holding = false;

    // The user paused the video.
    if (paused && !this.holding) {
      if (this.cur && !this.cur.el.paused) this.cur.el.pause();
      this.soften(false);
      return;
    }

    // Safety: e.g. the network dropped — never hold the video forever. Let it play for a while without
    // holding again, and drop a sentence whose audio still hasn't come, so the dub picks up from where
    // the video is instead of freezing.
    if (this.holding && now - this.holdSince > HOLD_MAX_MS) {
      if (this.cur) {
        try {
          this.cur.el.pause();
        } catch {}
        this.cur.ended = true;
      }
      const stuck = this.nextBlock();
      if (stuck && !this.ready.has(stuck.i) && stuck.start < t) {
        this.done.add(stuck.i);
        this.stats.skipped++;
      }
      this.release();
      this.noHoldUntil = now + NO_HOLD_MS;
      // If it was the end of the plan we waited at, don't wait there again until that part arrives.
      if (this.covered && t > this.covered[1]) this.edgeGaveUp = true;
      this.emit("idle");
      return;
    }

    // Still waiting for the plan of this spot (start or after a seek): sentences elsewhere are not ours yet.
    if (!this.covered && !this.cur) return;

    const next = this.nextBlock();

    if (this.cur) {
      const { el } = this.cur;
      if (this.cur.ended || el.ended) {
        this.cur = null;
        if (this.holding && !(next && t - next.start > READY_GRACE && !this.ready.has(next.i))) this.release();
        this.emit("idle");
      } else {
        if (el.paused) this.startEl(this.cur);
        // A little behind: slow the video slightly so the voice doesn't have to race (if the player can).
        // Back to the user's speed as soon as the dub has caught up.
        const behind = next ? t - next.start : t - (this.cur.b.start + this.cur.b.slot);
        if (this.opts.flex !== false && !paused) {
          if (behind > SOFT_LAG) this.soften(true);
          else if (behind < 0.2) this.soften(false);
        }
        // The dub fell behind the speaker: the next sentence should have started a while ago.
        if (this.opts.wait && !paused && next && t - next.start > HOLD_LAG) {
          this.hold();
          this.emit("waiting", { block: this.cur.b });
        }
        return;
      }
    }

    // Playback reached the end of the prepared part while the next part is still on its way: wait for
    // it instead of letting the video run on with no dub.
    const c = this.covered;
    if (this.opts.wait && !this.edgeGaveUp && c && t > c[1] && t < this.planEnd && this.loading && !(next && next.start <= t + 0.05)) {
      if (!this.holding && !paused) {
        this.hold();
        this.emit("buffering");
      }
      return;
    }

    if (!next || next.start > t + 0.05) this.soften(false); // in sync (or nothing to say): the user's speed
    if (!next) return this.covered ? this.release() : undefined;
    if (next.start > t + 0.05) return this.release();

    const late = t - next.start;
    if (!this.opts.wait && late > SKIP_LAG) {
      this.done.add(next.i); // "no pauses" mode and far behind: drop it
      this.stats.skipped++;
      return;
    }
    const a = this.ready.get(next.i);
    if (a) return this.play(next, a, t);
    if (this.failed.has(next.i)) {
      this.done.add(next.i);
      this.stats.skipped++;
      return this.release();
    }
    this.fetchAudio(next);
    if (this.opts.wait && !paused && !this.holding && late > READY_GRACE) {
      this.hold();
      this.emit("buffering", { block: next });
    }
  }
}

export default DubEngine;
