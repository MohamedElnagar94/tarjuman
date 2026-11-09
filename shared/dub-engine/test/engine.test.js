// Simulates the live dub engine with a fake clock and fake audio elements.
import { test } from "node:test";
import assert from "node:assert/strict";
import { DubEngine } from "../src/index.js";

let clock = 0;

class FakeAudio {
  static all = [];
  static durations = {};
  constructor(url) {
    this.url = url;
    this.duration = FakeAudio.durations[url];
    this.currentTime = 0;
    this.paused = true;
    this.ended = false;
    this.playbackRate = 1;
    this.on = {};
    FakeAudio.all.push(this);
  }
  addEventListener(e, f) {
    (this.on[e] ||= []).push(f);
  }
  play() {
    if (!this.ended) this.paused = false;
    return Promise.resolve();
  }
  pause() {
    this.paused = true;
  }
  advance(dt) {
    if (this.paused || this.ended) return;
    this.currentTime += dt * this.playbackRate;
    if (this.currentTime >= this.duration) {
      this.ended = this.paused = true;
      (this.on.ended || []).forEach((f) => f());
    }
  }
}

const fakes = { AudioCtor: FakeAudio, now: () => clock, revokeUrl: () => {} };

function fakeMedia({ t = 0, lagMs = 0 } = {}) {
  return {
    t,
    isPaused: false,
    pausedSteps: 0,
    time() { return this.t; },
    paused() { return this.isPaused; },
    rate() { return 1; },
    // lagMs: like the YouTube player, the state changes after a delay
    play() { this.later(false); },
    pause() { this.later(true); },
    later(p) {
      if (!lagMs) return void (this.isPaused = p);
      this.pendingState = { p, at: clock + lagMs };
    },
    applyPending() {
      if (this.pendingState && clock >= this.pendingState.at) {
        this.isPaused = this.pendingState.p;
        this.pendingState = null;
      }
    },
    getVolume() { return 1; },
    setVolume(v) { this.vol = v; },
  };
}

function simulate({ wait, durations, blocks, seconds = 30, seekAt, lagMs = 0 }) {
  FakeAudio.all = [];
  FakeAudio.durations = durations;
  clock = 0;
  const media = fakeMedia({ lagMs });
  const engine = new DubEngine({
    media,
    loadPlan: async () => ({ blocks, end: blocks[blocks.length - 1].start + 5 }),
    synth: async (b) => ({ url: "u" + b.i, duration: durations["u" + b.i] }),
    options: { wait },
    ...fakes,
  });
  return (async () => {
    engine.start();
    clearInterval(engine.timer);
    let maxSimultaneous = 0;
    for (let step = 0; step < seconds * 10; step++) {
      await new Promise((r) => setImmediate(r)); // let pending promises settle
      if (seekAt && Math.abs(media.t - seekAt.at) < 0.05 && !seekAt.done) {
        seekAt.done = true;
        media.t = seekAt.to;
      }
      engine.tick();
      clock += 100;
      media.applyPending();
      if (!media.isPaused) media.t += 0.1;
      else media.pausedSteps++;
      FakeAudio.all.forEach((a) => a.advance(0.1));
      maxSimultaneous = Math.max(maxSimultaneous, FakeAudio.all.filter((a) => !a.paused && !a.ended).length);
    }
    engine.stop();
    return { media, audios: FakeAudio.all, maxSimultaneous, vol: media.vol };
  })();
}

// Three sentences, each 4 s of audio but only 2 s of slot.
const BLOCKS = [
  { i: 0, start: 0, slot: 2, text: "a", rate: 0 },
  { i: 1, start: 2, slot: 2, text: "b", rate: 0 },
  { i: 2, start: 4, slot: 4, text: "c", rate: 0 },
];
const LONG = { u0: 4, u1: 4, u2: 4 };

test("wait mode: no sentence is ever cut, none overlap, video waits for the dub", async () => {
  const r = await simulate({ wait: true, durations: LONG, blocks: BLOCKS });
  assert.deepEqual(r.audios.map((a) => a.url), ["u0", "u1", "u2"], "every sentence spoken once, in order");
  for (const a of r.audios) assert.ok(a.ended, a.url + " played to the end");
  assert.equal(r.maxSimultaneous, 1, "never two voices at once");
  assert.ok(r.media.pausedSteps > 0, "video paused briefly to let the dub catch up");
  assert.ok(r.media.pausedSteps < 60, "but only briefly (" + r.media.pausedSteps / 10 + "s)");
  assert.equal(r.media.isPaused, false, "video resumed");
});

test("flow mode: never pauses the video, still no cuts, catches up by speeding up", async () => {
  const r = await simulate({ wait: false, durations: LONG, blocks: BLOCKS });
  assert.equal(r.media.pausedSteps, 0);
  for (const a of r.audios) assert.ok(a.ended, a.url + " played to the end");
  assert.equal(r.maxSimultaneous, 1);
  assert.ok(r.audios.some((a) => a.playbackRate > 1), "late sentences speed up");
  assert.ok(r.audios.every((a) => a.playbackRate <= 1.3 + 1e-9), "but never above 1.3x");
});

test("sentences that fit are played at normal speed with no pauses (after warm-up)", async () => {
  const r = await simulate({ wait: true, durations: { u0: 1.5, u1: 1.5, u2: 3 }, blocks: BLOCKS });
  assert.ok(r.media.pausedSteps <= 3, "only the short warm-up hold, got " + r.media.pausedSteps);
  assert.ok(r.audios.every((a) => a.playbackRate === 1));
  assert.equal(r.audios.length, 3);
});

test("seeking skips past sentences and continues cleanly", async () => {
  const blocks = Array.from({ length: 10 }, (_, i) => ({ i, start: i * 3, slot: 3, text: "x", rate: 0 }));
  const durations = Object.fromEntries(blocks.map((b) => ["u" + b.i, 2]));
  const r = await simulate({ wait: true, durations, blocks, seekAt: { at: 4, to: 20 } });
  const urls = r.audios.map((a) => a.url);
  assert.ok(!urls.includes("u3") && !urls.includes("u5"), "skipped sentences are not spoken");
  assert.ok(urls.includes("u7") && urls.includes("u9"), "continues after the seek");
  assert.equal(r.maxSimultaneous, 1);
});

test("ducks the original volume while running and restores it on stop", async () => {
  const r = await simulate({ wait: true, durations: LONG, blocks: BLOCKS, seconds: 2 });
  assert.equal(r.vol, 1, "restored after stop");
});

test("YouTube-style state lag never produces two voices or a stuck video", async () => {
  const blocks = Array.from({ length: 8 }, (_, i) => ({ i, start: i * 2.5, slot: 2.5, text: "x", rate: 0 }));
  const durations = Object.fromEntries(blocks.map((b) => ["u" + b.i, 3.6]));
  const r = await simulate({ wait: true, durations, blocks, lagMs: 300, seconds: 40 });
  assert.equal(r.maxSimultaneous, 1, "never two voices at once");
  assert.equal(r.audios.length, 8, "every sentence spoken");
  for (const a of r.audios) assert.ok(a.ended, a.url + " played to the end");
  assert.equal(r.media.isPaused, false, "video not left paused");
});

test("fast speaker, short segments: nothing is skipped and the video rarely pauses", async () => {
  // 20 short sentences (1.2 s) whose audio is 1.8 s each — a fast talker.
  const blocks = Array.from({ length: 20 }, (_, i) => ({ i, start: i * 1.2, slot: 1.2, text: "x", rate: 0 }));
  const durations = Object.fromEntries(blocks.map((b) => ["u" + b.i, 1.8]));
  for (const wait of [true, false]) {
    const r = await simulate({ wait, durations, blocks, seconds: 40 });
    assert.equal(r.audios.length, 20, `wait=${wait}: every sentence spoken (got ${r.audios.length})`);
    for (const a of r.audios) assert.ok(a.ended, a.url + " played to the end");
    assert.equal(r.maxSimultaneous, 1);
    assert.ok(r.media.pausedSteps <= (wait ? 40 : 0), `wait=${wait}: paused ${r.media.pausedSteps / 10}s`);
  }
});

test("server-side playRate correction is applied without re-synthesizing", async () => {
  const blocks = [{ i: 0, start: 0, slot: 5, text: "x", synthRate: 20, playRate: 1.1 }];
  const r = await simulate({ wait: true, durations: { u0: 3 }, blocks, seconds: 6 });
  assert.ok(Math.abs(r.audios[0].playbackRate - 1.1) < 1e-9, "played at 1.1x, got " + r.audios[0].playbackRate);
});

test("seeking back before where dubbing started: video waits briefly, never plays on without the dub", async () => {
  // Plans arrive after a delay, like the server: a big window ~3 s, a small one ~1 s. Dubbing started at 60 s.
  FakeAudio.all = [];
  const all = Array.from({ length: 40 }, (_, i) => ({ i, start: i * 3, slot: 3, text: "x", rate: 0 }));
  FakeAudio.durations = Object.fromEntries(all.map((b) => ["u" + b.i, 2]));
  clock = 0;
  const pending = [];
  const media = fakeMedia({ t: 60 });
  const engine = new DubEngine({
    media,
    loadPlan: (from, to) =>
      new Promise((resolve) =>
        pending.push({
          at: clock + (to - from > 20 ? 3000 : 1000),
          resolve: () => resolve({ blocks: all.filter((b) => b.start + b.slot >= from && b.start <= to), end: 120 }),
        })
      ),
    synth: async (b) => ({ url: "u" + b.i, duration: 2 }),
    options: { wait: true },
    ...fakes,
  });
  engine.start();
  clearInterval(engine.timer);
  let silentPlay = 0; // seconds the video played after the seek with no dub yet
  let afterSeek = false;
  let spokenAfterSeek = false;
  const step = async () => {
    for (const p of pending.splice(0)) clock >= p.at ? p.resolve() : pending.push(p);
    await new Promise((r) => setImmediate(r));
    engine.tick();
    clock += 100;
    if (!media.isPaused) {
      media.t += 0.1;
      if (afterSeek && !spokenAfterSeek) silentPlay += 0.1;
    }
    FakeAudio.all.forEach((a) => a.advance(0.1));
    if (afterSeek && FakeAudio.all.some((a) => Number(a.url.slice(1)) < 15 && !a.paused)) spokenAfterSeek = true;
  };
  for (let k = 0; k < 150; k++) await step(); // ~15 s of dub from 60 s
  media.t = 21; // the user seeks back, before where dubbing started
  afterSeek = true;
  for (let k = 0; k < 80; k++) await step();
  engine.stop();
  assert.ok(spokenAfterSeek, "dub resumed near the new position");
  assert.ok(silentPlay < 0.5, "video played " + silentPlay.toFixed(1) + "s with no dub after seeking back");
});
