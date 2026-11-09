import { describe, expect, it, vi } from "vitest";
import { html5Player, type VideoLike } from "@/player/html5";
import { dubMedia } from "@/player/dubMedia";
import { PlayerState } from "@/player/types";

function fakeVideo(over: Partial<VideoLike> = {}): VideoLike {
  const v = {
    currentTime: 0,
    paused: true,
    ended: false,
    readyState: 4,
    playbackRate: 1,
    volume: 1,
    muted: false,
    duration: 120,
    play: vi.fn(() => {
      v.paused = false;
      return Promise.resolve();
    }),
    pause: vi.fn(() => {
      v.paused = true;
    }),
    ...over,
  };
  return v as VideoLike;
}

describe("html5Player (YouTube IFrame API look-alike)", () => {
  it("maps play state like YouTube", () => {
    const v = fakeVideo();
    const p = html5Player(v);
    expect(p.getPlayerState()).toBe(PlayerState.Paused);
    p.playVideo();
    expect(p.getPlayerState()).toBe(PlayerState.Playing);
    (v as { readyState: number }).readyState = 2;
    expect(p.getPlayerState()).toBe(PlayerState.Buffering);
    (v as { ended: boolean }).ended = true;
    expect(p.getPlayerState()).toBe(PlayerState.Ended);
  });

  it("seeks, clamps and reports time", () => {
    const v = fakeVideo();
    const p = html5Player(v);
    p.seekTo(42.5, true);
    expect(p.getCurrentTime()).toBe(42.5);
    p.seekTo(-3);
    expect(v.currentTime).toBe(0);
  });

  it("uses 0..100 volume like YouTube", () => {
    const v = fakeVideo();
    const p = html5Player(v);
    p.setVolume(15);
    expect(v.volume).toBeCloseTo(0.15);
    expect(p.getVolume()).toBeCloseTo(15);
    p.setVolume(400);
    expect(v.volume).toBe(1);
  });

  it("handles rate, duration and rejected play()", () => {
    const v = fakeVideo({ duration: Number.NaN, play: vi.fn(() => Promise.reject(new Error("blocked"))) });
    const p = html5Player(v);
    p.setPlaybackRate(1.5);
    expect(p.getPlaybackRate()).toBe(1.5);
    expect(p.getDuration()).toBe(0);
    expect(() => p.playVideo()).not.toThrow();
  });
});

describe("dubMedia", () => {
  it("adapts a player for the dub engine", () => {
    const v = fakeVideo();
    const p = html5Player(v);
    const m = dubMedia(() => p);
    expect(m.paused()).toBe(true);
    m.play();
    expect(m.paused()).toBe(false);
    m.setVolume(0.2);
    expect(m.getVolume()).toBeCloseTo(0.2);
    // Muted still reports the real volume, so stopping the dub restores it.
    (v as { muted: boolean }).muted = true;
    expect(m.getVolume()).toBeCloseTo(0.2);
  });
  it("is safe without a player", () => {
    const m = dubMedia(() => null);
    expect(m.time()).toBe(0);
    expect(m.paused()).toBe(true);
    expect(m.rate()).toBe(1);
    expect(() => m.pause()).not.toThrow();
  });
});
