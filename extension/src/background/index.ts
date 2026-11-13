/**
 * Background service worker: the hub between
 *  - the popup / options / welcome pages and the Alt+Shift+A shortcut,
 *  - the content script (the overlay in the page),
 *  - the offscreen document (tab audio capture and live dub playback),
 *  - the local Tarjuman server (found on ports 4318–4327).
 *
 * Chrome stops an idle service worker after ~30 s, so the run state lives in
 * chrome.storage.session and settings in chrome.storage.local.
 *
 * Content scripts talk to the server through here: page CORS / private network
 * rules would block them, while the extension has host permission for loopback.
 */
import { mergeSettings, type Settings } from "@/shared/settings";
import { readTable } from "@/shared/i18n";
import { findServer, probe, normalizeServerUrl, DEFAULT_BASE, type Found } from "@/shared/server";
import { isYouTube, isProtectedUrl, originPattern, pickTrack, type TrackInfo } from "@/shared/cues";
import { bytesToB64 } from "@/shared/audio";
import type { RunState, TabInfo, Status, Reply } from "@/shared/messages";

const IDLE: RunState = { active: false, mode: null, tabId: null };

let state: RunState = { ...IDLE };
let settings: Settings = mergeSettings(null);
let serverBase: string | null = null;
let override: string | null = null;
/** Set by the popup right before it asks for a site permission (the prompt may close the popup). */
let pendingStart: { tabId: number; at: number } | null = null;
/** The tab showing the badge, so it can be cleared there when translation stops or moves to another tab. */
let badgeTab: number | null = null;

const ready = (async () => {
  try {
    const s = await chrome.storage.session.get(["state", "pendingStart"]);
    if (s.state) state = { ...IDLE, ...s.state };
    // The worker may have been stopped while a tab showed the badge; remember which, to clear it later.
    if (state.active) badgeTab = state.tabId;
    if (s.pendingStart) pendingStart = s.pendingStart;
  } catch {}
  try {
    const l = await chrome.storage.local.get(["settings", "serverBase", "serverOverride"]);
    settings = mergeSettings(l.settings);
    if (l.serverBase) serverBase = l.serverBase;
    if (l.serverOverride) override = normalizeServerUrl(l.serverOverride);
  } catch {}
})();

function saveState() {
  chrome.storage.session.set({ state }).catch(() => {});
  updateBadge();
}

// The badge is set on the translating tab only: a global badge would say "ON" on every other tab too.
function updateBadge() {
  const on = state.active && state.tabId != null;
  if (badgeTab != null && (!on || badgeTab !== state.tabId)) {
    chrome.action.setBadgeText({ text: "", tabId: badgeTab }).catch(() => {});
    badgeTab = null;
  }
  if (!on) return;
  const tabId = state.tabId!;
  badgeTab = tabId;
  const text = state.mode === "live" ? "LIVE" : state.mode === "captions" ? "CC" : "ON";
  chrome.action.setBadgeText({ text, tabId }).catch(() => {});
  chrome.action.setBadgeBackgroundColor({ color: "#FFD27A", tabId }).catch(() => {});
  chrome.action.setBadgeTextColor?.({ color: "#121A57", tabId })?.catch?.(() => {});
}

/* ------------------------------------------------------------------ */
/*  Local server                                                       */
/* ------------------------------------------------------------------ */

async function fetchTimeout(url: string, opts: RequestInit = {}, ms = 2500) {
  const ctrl = new AbortController();
  const timer = setTimeout(() => ctrl.abort(), ms);
  try {
    return await fetch(url, { ...opts, signal: ctrl.signal });
  } finally {
    clearTimeout(timer);
  }
}

async function locate(): Promise<Found | null> {
  const found = await findServer({ fetch: (u, i) => fetch(u, i), override, last: serverBase });
  if (found && found.base !== serverBase) {
    serverBase = found.base;
    chrome.storage.local.set({ serverBase }).catch(() => {});
  }
  return found;
}

const currentBase = () => override || serverBase;

const noServer = () => Object.assign(new Error("NO_SERVER"), { code: "NO_SERVER" });

async function api(path: string, opts: RequestInit = {}, ms = 60000): Promise<any> {
  if (!currentBase() && !(await locate())) throw noServer();
  let res: Response;
  try {
    res = await fetchTimeout(currentBase() + path, opts, ms);
  } catch (e) {
    // A timeout is not retried: the server is there but slow, and asking again would send the
    // request (a translation, a Whisper job) twice and double the wait.
    if ((e as any)?.name === "AbortError") throw e;
    // Nothing answered at all (fetch's TypeError): the server may have restarted on another port.
    if (!(await locate())) throw noServer();
    res = await fetchTimeout(currentBase() + path, opts, ms);
  }
  // The server did answer, so a bad reply is reported as it is rather than sent again.
  return res.json();
}

const postJson = (path: string, body: unknown, ms?: number) =>
  api(path, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) }, ms);

/* ------------------------------------------------------------------ */
/*  Offscreen document                                                 */
/* ------------------------------------------------------------------ */

let offscreenPromise: Promise<void> | null = null;

async function hasOffscreen() {
  try {
    const ctxs = await chrome.runtime.getContexts({ contextTypes: [chrome.runtime.ContextType.OFFSCREEN_DOCUMENT] });
    return ctxs.length > 0;
  } catch {
    return false;
  }
}

async function ensureOffscreen() {
  if (await hasOffscreen()) return;
  if (!offscreenPromise) {
    offscreenPromise = chrome.offscreen
      .createDocument({
        url: "offscreen.html",
        reasons: [chrome.offscreen.Reason.USER_MEDIA, chrome.offscreen.Reason.AUDIO_PLAYBACK],
        justification: "Capture the tab's audio to transcribe and translate it, and play the dubbed voice.",
      })
      .finally(() => (offscreenPromise = null));
  }
  await offscreenPromise;
}

async function closeOffscreen() {
  try {
    if (await hasOffscreen()) await chrome.offscreen.closeDocument();
  } catch {}
}

/* ------------------------------------------------------------------ */
/*  Tabs                                                               */
/* ------------------------------------------------------------------ */

/** Loads the overlay script into the page, and into every frame we may access: on most movie and anime
 *  sites the video plays inside an iframe from another site, and only a script inside it can see it. */
async function inject(tabId: number, allFrames = false) {
  await chrome.scripting.executeScript({ target: { tabId, allFrames }, files: ["content.js"] });
}

/** Sends to the overlay; if there is none yet (a site other than YouTube, or a reloaded page) injects it first. */
async function sendToTab(tabId: number, msg: Record<string, unknown>, frameId = 0): Promise<Reply> {
  try {
    return await chrome.tabs.sendMessage(tabId, msg, { frameId });
  } catch {
    try {
      await inject(tabId, frameId !== 0);
      return await chrome.tabs.sendMessage(tabId, msg, { frameId });
    } catch (e2) {
      return { ok: false, code: "NO_ACCESS", message: String((e2 as Error)?.message || e2) };
    }
  }
}

// Site and path only: player frames often carry a fresh token in the query on every reload.
const frameKey = (url: string) => {
  try {
    const u = new URL(url);
    return u.origin + u.pathname;
  } catch {
    return url;
  }
};

/** The frame that plays the video: the one with the biggest <video>. 0 (the page itself) if none is found. */
async function findPlayerFrame(tabId: number): Promise<{ frameId: number; url: string }> {
  try {
    await inject(tabId, true);
  } catch {}
  let results: chrome.scripting.InjectionResult<{ url: string; area: number }>[] = [];
  try {
    results = await chrome.scripting.executeScript({
      target: { tabId, allFrames: true },
      func: () => {
        let area = 0;
        for (const v of Array.from(document.querySelectorAll("video"))) area = Math.max(area, v.offsetWidth * v.offsetHeight);
        return { url: location.href, area };
      },
    });
  } catch {}
  let best = { frameId: 0, url: "", area: 0 };
  for (const r of results) {
    const res = r.result;
    if (res && res.area > best.area) best = { frameId: r.frameId, url: res.url, area: res.area };
  }
  return { frameId: best.frameId, url: best.frameId ? frameKey(best.url) : "" };
}

/** Sites of the large iframes on the page (players, not ad pixels), as permission patterns. */
async function frameOriginsOf(tabId: number, pageOrigin: string | null): Promise<string[]> {
  try {
    const [r] = await chrome.scripting.executeScript({
      target: { tabId },
      func: () =>
        Array.from(document.querySelectorAll("iframe"))
          .filter((f) => f.offsetWidth * f.offsetHeight >= 300 * 160)
          .map((f) => f.src)
          .filter((s) => /^https?:/.test(s)),
    });
    const out = new Set<string>();
    for (const src of (r && r.result) || []) {
      const p = originPattern(src);
      if (p && p !== pageOrigin) out.add(p);
    }
    return [...out].slice(0, 5);
  } catch {
    return [];
  }
}

async function tellTab(tabId: number | null, msg: Record<string, unknown>) {
  if (!tabId) return;
  try {
    await chrome.tabs.sendMessage(tabId, msg);
  } catch {}
}

function activation(url?: string) {
  if (state.mode === "youtube" || (url && isYouTube(url))) return { type: "activate-youtube", url, settings };
  if (state.mode === "captions") return { type: "activate-captions", index: state.track, settings };
  return { type: "activate-live", settings };
}

async function activeTab(): Promise<chrome.tabs.Tab | undefined> {
  const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
  return tab;
}

// Without the `tabs` permission, tab.url is only present when the extension has
// access to the page: after the user invoked it there (activeTab) or granted the site.
async function tabInfo(tab: chrome.tabs.Tab | undefined): Promise<TabInfo | null> {
  if (!tab || tab.id == null) return null;
  const url = tab.url || tab.pendingUrl || "";
  const youtube = isYouTube(url);
  const origin = youtube ? null : originPattern(url);
  const frameOrigins = origin && !isProtectedUrl(url) ? await frameOriginsOf(tab.id, origin) : [];
  let siteGranted = youtube;
  if (origin) {
    try {
      siteGranted = await chrome.permissions.contains({ origins: [origin, ...frameOrigins] });
    } catch {}
  }
  return { id: tab.id, url, youtube, protected: isProtectedUrl(url), origin, siteGranted, frameOrigins };
}

/* ------------------------------------------------------------------ */
/*  Start / stop                                                       */
/* ------------------------------------------------------------------ */

async function start(tab: chrome.tabs.Tab | undefined): Promise<Reply> {
  if (!tab || tab.id == null) return { ok: false, code: "NO_TAB" };
  const tabId = tab.id;
  const url = tab.url || "";
  if (isProtectedUrl(url)) return { ok: false, code: "PROTECTED" };
  const srv = await locate();
  if (!srv) return { ok: false, code: "NO_SERVER" };
  if (state.active) await stop();

  if (isYouTube(url)) {
    state = { active: true, mode: "youtube", tabId };
    saveState();
    const res = await sendToTab(tabId, activation(url));
    if (res && res.ok === false) {
      state = { ...IDLE };
      saveState();
      return { ok: false, code: res.code || "START_FAILED", message: res.message };
    }
    return { ok: true, mode: "youtube" };
  }

  // Any other site: the player's own captions are exact and well timed, so prefer them; otherwise capture
  // the tab's audio. Either way the overlay runs in the frame that plays the video, so it sees the player
  // and stays visible when that player goes full screen.
  const player = await findPlayerFrame(tabId);
  const probeRes = await sendToTab(tabId, { type: "probe-captions" }, player.frameId);
  if (probeRes && probeRes.ok === false) return { ok: false, code: "NO_ACCESS", message: probeRes.message };
  const tracks: TrackInfo[] = (probeRes && probeRes.tracks) || [];
  const pick = pickTrack(tracks, settings.lang);
  if (pick) {
    state = { active: true, mode: "captions", tabId, track: pick.index, frameUrl: player.url };
    saveState();
    await sendToTab(tabId, activation(), player.frameId);
    return { ok: true, mode: "captions" };
  }

  if (!srv.health.whisper || !srv.health.whisper.installed) return { ok: false, code: "WHISPER_NOT_INSTALLED" };
  let streamId: string;
  try {
    streamId = await (chrome.tabCapture.getMediaStreamId as unknown as (o: { targetTabId: number }) => Promise<string>)({ targetTabId: tabId });
  } catch (e) {
    return { ok: false, code: "CAPTURE_FAILED", message: String((e as Error)?.message || e) };
  }
  await ensureOffscreen();
  const r: Reply | undefined = await chrome.runtime
    .sendMessage({ type: "start-capture", target: "offscreen", streamId, settings, server: currentBase() })
    .catch((e) => ({ ok: false, message: String(e) }));
  if (!r || !r.ok) {
    await closeOffscreen();
    return { ok: false, code: "CAPTURE_FAILED", message: r && r.message };
  }
  state = { active: true, mode: "live", tabId, frameUrl: player.url };
  saveState();
  await sendToTab(tabId, activation(), player.frameId);
  return { ok: true, mode: "live" };
}

async function stop(): Promise<Reply> {
  const { tabId, mode } = state;
  state = { ...IDLE };
  saveState();
  if (mode === "live") {
    try {
      await chrome.runtime.sendMessage({ type: "stop-capture", target: "offscreen" });
    } catch {}
    await closeOffscreen();
  }
  await tellTab(tabId, { type: "deactivate" });
  return { ok: true };
}

async function setPendingStart(p: typeof pendingStart) {
  pendingStart = p;
  await chrome.storage.session.set({ pendingStart: p }).catch(() => {});
}

/* ------------------------------------------------------------------ */
/*  Messages                                                           */
/* ------------------------------------------------------------------ */

type Handler = (msg: any, sender: chrome.runtime.MessageSender) => Promise<unknown> | unknown;

const handlers: Record<string, Handler> = {
  // Content scripts can't read extension files: the chosen interface language's messages, for them.
  i18n: async () => ({ ok: true, ...(await readTable()) }),

  start: async (msg) => {
    await setPendingStart(null);
    const tab = msg.tabId != null ? await chrome.tabs.get(msg.tabId).catch(() => undefined) : await activeTab();
    return start(tab);
  },
  stop: () => stop(),

  status: async (): Promise<Status> => {
    const [srv, tab] = await Promise.all([locate(), activeTab()]);
    const info = await tabInfo(tab);
    return {
      ok: true,
      state,
      settings,
      server: srv ? srv.base : null,
      health: srv ? srv.health : null,
      override,
      tab: info,
      activeHere: !!(info && state.active && state.tabId === info.id),
      version: chrome.runtime.getManifest().version,
    };
  },

  "pending-start": (msg) => setPendingStart(msg.tabId != null ? { tabId: msg.tabId, at: Date.now() } : null),

  "test-connection": async (msg) => {
    if (msg.url != null && msg.url !== "") {
      const base = normalizeServerUrl(msg.url);
      if (!base) return { ok: false, code: "BAD_ADDRESS" };
      const health = await probe(base, (u, i) => fetch(u, i), 2500);
      return health ? { ok: true, base, health } : { ok: false, code: "NO_SERVER", base };
    }
    const f = await locate();
    return f ? { ok: true, base: f.base, health: f.health } : { ok: false, code: "NO_SERVER" };
  },

  "set-override": async (msg) => {
    const raw = String(msg.url || "").trim();
    const base = raw ? normalizeServerUrl(raw) : null;
    if (raw && !base) return { ok: false, code: "BAD_ADDRESS" };
    override = base;
    await chrome.storage.local.set({ serverOverride: base || "" });
    const f = await locate();
    return { ok: true, override, server: f ? f.base : null, health: f ? f.health : null };
  },

  "fetch-cues": (msg) => api(`/api/cues?url=${encodeURIComponent(msg.url)}&tl=${encodeURIComponent(msg.tl || settings.lang)}`),

  "whisper-start": (msg) => postJson("/api/whisper/job", { url: msg.url, tl: msg.tl || settings.lang }),
  "whisper-poll": (msg) => api(`/api/whisper/job?id=${encodeURIComponent(msg.id)}`),
  // The user stopped or moved to another video: free the server from a transcription nobody will see.
  "whisper-cancel": (msg) => postJson("/api/job/cancel", { id: msg.id }, 5000),

  translate: (msg) => postJson("/api/translate", { texts: msg.texts || [], tl: msg.tl || settings.lang, sl: msg.sl || "auto" }),

  // Audio goes back as base64: runtime messages carry JSON only.
  "tts-fetch": async (msg) => {
    if (!currentBase() && !(await locate())) return { ok: false, code: "NO_SERVER" };
    const q = new URLSearchParams({
      text: msg.text || "",
      lang: msg.lang || settings.lang,
      voice: msg.voice ?? settings.voice ?? "",
      rate: String(msg.rate || 0),
    });
    const r = await fetchTimeout(`${currentBase()}/api/tts?${q}`, { cache: "force-cache" }, 60000);
    const ct = (r.headers.get("content-type") || "").split(";")[0].trim();
    if (!ct.startsWith("audio")) return { ok: false, code: "TTS_ERROR" };
    const duration = Number(r.headers.get("X-Audio-Duration")) || 0;
    return { ok: true, audio_b64: bytesToB64(new Uint8Array(await r.arrayBuffer())), mime: ct, duration };
  },

  "dub-plan": (msg) => {
    const q = new URLSearchParams({
      url: msg.url,
      tl: msg.tl || settings.lang,
      voice: msg.voice ?? settings.voice ?? "",
      from: String(msg.from || 0),
      to: String(msg.to || 120),
      urgent: msg.urgent ? "1" : "0",
      speed: String(msg.speed || 1),
    });
    return api(`/api/dubplan?${q}`, {}, 90000);
  },

  "dub-plan-cues": (msg) =>
    postJson(
      "/api/dubplan/cues",
      {
        cues: msg.cues || [],
        sl: msg.sl || "auto",
        tl: msg.tl || settings.lang,
        voice: msg.voice ?? settings.voice ?? "",
        from: msg.from || 0,
        to: msg.to || 120,
        speed: msg.speed || 1,
        urgent: !!msg.urgent,
      },
      90000,
    ),

  voices: (msg) => api(`/api/voices?lang=${encodeURIComponent(msg.lang || settings.lang)}`),

  "get-settings": () => ({ ok: true, settings }),

  "set-settings": async (msg) => {
    settings = mergeSettings(settings, msg.settings);
    await chrome.storage.local.set({ settings });
    if (state.active) await tellTab(state.tabId, { type: "settings", settings });
    if (state.mode === "live") {
      try {
        await chrome.runtime.sendMessage({ type: "update-settings", target: "offscreen", settings });
      } catch {}
    }
    return { ok: true, settings };
  },

  "open-app": async () => {
    const srv = await locate();
    const tab = await activeTab();
    let url = srv ? srv.base : currentBase() || DEFAULT_BASE;
    if (srv && tab && isYouTube(tab.url || "")) url += "/?url=" + encodeURIComponent(tab.url!);
    await chrome.tabs.create({ url });
    return { ok: true };
  },
  "open-welcome": async () => {
    await chrome.tabs.create({ url: chrome.runtime.getURL("welcome.html") });
    return { ok: true };
  },
  "open-options": async () => {
    await chrome.runtime.openOptionsPage();
    return { ok: true };
  },
  "open-shortcuts": async () => {
    await chrome.tabs.create({ url: "chrome://extensions/shortcuts" });
    return { ok: true };
  },

  // From a content script that just loaded: carry on if this tab was translating.
  "content-ready": async (msg, sender) => {
    const tabId = sender.tab?.id;
    if (!state.active || tabId == null || tabId !== state.tabId) return { ok: true, activate: null };
    const url = String(msg.url || sender.url || "");
    // Only the frame that plays the video carries the overlay (the page itself when there is no player iframe).
    const wanted = state.mode === "youtube" ? "" : state.frameUrl || "";
    if (wanted ? frameKey(url) !== wanted : (sender.frameId || 0) !== 0) return { ok: true, activate: null };
    if (isYouTube(url) && state.mode !== "youtube" && state.mode !== "live") {
      state = { active: true, mode: "youtube", tabId };
      saveState();
    } else if (state.mode === "youtube" && !isYouTube(url)) {
      await stop();
      return { ok: true, activate: null };
    }
    return { ok: true, activate: activation(url) };
  },

  // From the offscreen document.
  "live-result": async (msg) => {
    await tellTab(state.tabId, { type: "live-sub", text: msg.text || "", ar: msg.ar || "" });
    return { ok: true };
  },
  "live-status": async (msg) => {
    await tellTab(state.tabId, { type: "live-status", status: msg.status, message: msg.message });
    return { ok: true };
  },

  // From the overlay's stop button.
  "stop-from-page": () => stop(),
};

chrome.runtime.onMessage.addListener((msg, sender, respond) => {
  if (!msg || msg.target === "offscreen") return; // not for us
  const h = handlers[msg.type];
  if (!h) return;
  (async () => {
    await ready;
    try {
      respond(await h(msg, sender));
    } catch (e: any) {
      respond({ ok: false, code: e?.code || (e?.name === "AbortError" ? "TIMEOUT" : "BG_ERROR"), message: String(e?.message || e) });
    }
  })();
  return true;
});

chrome.commands.onCommand.addListener(async (cmd, cmdTab) => {
  if (cmd !== "toggle-translation") return;
  await ready;
  const tab = cmdTab && cmdTab.id != null ? cmdTab : await activeTab();
  if (state.active && tab && state.tabId === tab.id) await stop();
  else await start(tab);
});

// After a reload or navigation in the translating tab, bring the overlay back.
// On YouTube the declared content script announces itself ("content-ready").
// Elsewhere it has to be injected again, which works when the user granted the site.
chrome.tabs.onUpdated.addListener(async (tabId, info) => {
  await ready;
  if (!state.active || tabId !== state.tabId || info.status !== "complete") return;
  await new Promise((r) => setTimeout(r, 1500));
  if (!state.active || tabId !== state.tabId) return;
  try {
    const pong = await chrome.tabs.sendMessage(tabId, { type: "ping" });
    if (pong && pong.ok) return;
  } catch {}
  if (state.mode === "youtube") return void stop(); // left YouTube
  try {
    await inject(tabId, !!state.frameUrl); // the new copy sends "content-ready" and is activated from there
  } catch {
    await stop(); // no access to this page any more
  }
});

chrome.tabs.onRemoved.addListener(async (tabId) => {
  await ready;
  if (state.active && state.tabId === tabId) stop();
});

// The permission prompt can close the popup before it gets the answer; finish the start here.
chrome.permissions.onAdded.addListener(async () => {
  await ready;
  const p = pendingStart;
  if (!p || Date.now() - p.at > 60000) return;
  await new Promise((r) => setTimeout(r, 1200));
  if (!pendingStart || pendingStart.at !== p.at) return; // the popup handled it
  await setPendingStart(null);
  const tab = await chrome.tabs.get(p.tabId).catch(() => undefined);
  if (tab) await start(tab);
});

chrome.runtime.onStartup.addListener(async () => {
  await ready;
  // A fresh browser session: nothing is running.
  state = { ...IDLE };
  saveState();
});

chrome.runtime.onInstalled.addListener((details) => {
  if (details.reason === chrome.runtime.OnInstalledReason.INSTALL) {
    chrome.tabs.create({ url: chrome.runtime.getURL("welcome.html") }).catch(() => {});
  }
});

ready.then(updateBadge);
