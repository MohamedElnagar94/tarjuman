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
    this.stats = { spoken: 0, skipped: 0, holds: 0 };
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
    if (this.holding) return;
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
      const res = await this.loadPlan(from, to, { urgent: !c });
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

  /** Server correction × catch-up speed-up, capped by the maximum effective speed. */
  playbackRate(b, duration, t) {
    const base = b.playRate || 1;
    const avail = Math.max(0.6, b.start + b.slot + SPILL - t);
    const fit = duration ? Math.min(MAX_FIT, Math.max(1, duration / base / avail)) : 1;
    const synthFactor = 1 + (b.synthRate ?? b.rate ?? 0) / 100;
    const cap = MAX_EFFECTIVE / synthFactor;
    return Math.max(0.85, Math.min(base * fit, Math.max(cap, base)));
  }

  play(b, a, t) {
    const el = new this.Audio(a.url);
    el.preservesPitch = true;
    const mediaRate = this.media.rate() || 1;
    el.playbackRate = this.playbackRate(b, a.duration, t) * mediaRate;
    if (!a.duration) {
      el.addEventListener("loadedmetadata", () => {
        if (isFinite(el.duration)) el.playbackRate = this.playbackRate(b, el.duration, t) * mediaRate;
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

    this.ensurePlan(t);
    this.prefetch(t);

    // The user pressed play while we were holding: carry on.
    if (this.holding && !paused) this.holding = false;

    // The user paused the video.
    if (paused && !this.holding) {
      if (this.cur && !this.cur.el.paused) this.cur.el.pause();
      return;
    }

    // Safety: e.g. the network dropped — never hold the video forever.
    if (this.holding && now - this.holdSince > HOLD_MAX_MS) {
      if (this.cur) {
        try {
          this.cur.el.pause();
        } catch {}
        this.cur.ended = true;
      }
      this.release();
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
        // The dub fell behind the speaker: the next sentence should have started a while ago.
        if (this.opts.wait && !paused && next && t - next.start > HOLD_LAG) {
          this.hold();
          this.emit("waiting", { block: this.cur.b });
        }
        return;
      }
    }

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
