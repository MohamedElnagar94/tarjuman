/**
 * Content script: the overlay in the page.
 *  1) youtube  → captions from the local server, synced to the video; the dub engine speaks each sentence on time.
 *  2) captions → the site player's own text tracks (Coursera, Udemy…), translated and synced the same way.
 *  3) live     → shows the live subtitles that the offscreen document produces from the tab's audio.
 *
 * All server traffic goes through the background (page CORS / private network rules).
 */
import { DubEngine, type DubMedia } from "@tarjuman/dub-engine";
import { t } from "@/shared/i18n";
import { mergeSettings, langDir, SIZE_MIN, SIZE_MAX, type Settings } from "@/shared/settings";
import { cueIndexAt, ytVideoId, normalizeTrackCues, type Cue, type TrackInfo } from "@/shared/cues";
import { b64ToObjectUrl } from "@/shared/audio";
import type { Reply } from "@/shared/messages";
import { injectFonts, overlayHtml } from "./overlay";

declare global {
  interface Window {
    __tarjuman_v3?: boolean;
  }
}

(() => {
  if (window.__tarjuman_v3) return;
  window.__tarjuman_v3 = true;
  // An older copy (before the extension was reloaded) may have left its overlay behind.
  document.getElementById("__tarjuman_host")?.remove();

  type Mode = "youtube" | "captions" | "live" | null;

  const S = {
    active: false,
    mode: null as Mode,
    videoId: "",
    loading: false,
    cues: [] as Cue[],
    tr: new Map<number, string>(),
    tries: new Map<number, number>(),
    idx: -1,
    translating: false,
    hidden: false,
    settings: mergeSettings(null) as Settings,
    video: null as HTMLVideoElement | null,
    timer: 0 as ReturnType<typeof setInterval> | 0,
    liveTimer: 0 as ReturnType<typeof setTimeout> | 0,
    whisperUrl: "",
    srcLang: "auto",
    trackIndex: -1,
    /** Bumped on every activation so late replies from an earlier one are ignored. */
    gen: 0,
  };

  const UI: Record<string, any> = {};
  let rafId: number | null = null;
  let toolsTimer: ReturnType<typeof setTimeout> | undefined;
  let pillTimer: ReturnType<typeof setTimeout> | undefined;

  const sleep = (ms: number) => new Promise((r) => setTimeout(r, ms));

  function bg(type: string, payload: Record<string, unknown> = {}): Promise<Reply> {
    return new Promise((resolve) => {
      try {
        chrome.runtime.sendMessage({ type, ...payload }, (res) => {
          if (chrome.runtime.lastError) resolve({ ok: false, message: chrome.runtime.lastError.message });
          else resolve(res || { ok: false });
        });
      } catch (e) {
        // The extension was reloaded or removed and this script is orphaned.
        if (/context invalidated/i.test(String(e))) deactivate();
        resolve({ ok: false, message: String(e) });
      }
    });
  }

  /* ------------------------------------------------------------------ */
  /*  Overlay                                                            */
  /* ------------------------------------------------------------------ */

  function ensureOverlay() {
    if (UI.host && UI.host.isConnected) return;
    injectFonts();
    const host = document.createElement("div");
    host.id = "__tarjuman_host";
    host.style.cssText = "position:fixed;inset:0;pointer-events:none;z-index:2147483647;";
    const shadow = host.attachShadow({ mode: "open" });
    shadow.innerHTML = overlayHtml();
    // In fullscreen only the fullscreen element is painted, so the overlay must live inside it.
    (document.fullscreenElement && document.fullscreenElement.tagName !== "VIDEO" ? document.fullscreenElement : document.documentElement).appendChild(host);

    UI.host = host;
    UI.wrap = shadow.querySelector(".wrap");
    UI.pill = shadow.querySelector(".pill");
    UI.pillTxt = shadow.querySelector(".pill .txt");
    UI.subs = shadow.querySelector(".subs");
    UI.src = shadow.querySelector(".src span");
    UI.trLine = shadow.querySelector(".tr");
    UI.tr = shadow.querySelector(".tr span");
    UI.whisper = shadow.querySelector(".whisper");
    UI.whisperBtn = shadow.querySelector(".whisper .go");
    UI.meter = shadow.querySelector(".meter > i");
    UI.tools = shadow.querySelector(".tools");
    UI.whisperBtn.addEventListener("click", startWhisper);
    UI.tools.addEventListener("click", onToolClick);
    UI.tools.addEventListener("mouseenter", () => showTools(true));
    UI.tools.addEventListener("focusin", () => showTools(true));
    applySettings();
    updatePosition();
  }

  function removeOverlay() {
    UI.host?.remove();
    for (const k of Object.keys(UI)) delete UI[k];
  }

  function findVideo(): HTMLVideoElement | null {
    const vids = [...document.querySelectorAll("video")].filter((v) => v.offsetWidth > 120 && v.offsetHeight > 70);
    vids.sort((a, b) => b.offsetWidth * b.offsetHeight - a.offsetWidth * a.offsetHeight);
    return vids[0] || null;
  }

  function currentVideo() {
    if (!S.video || !S.video.isConnected) S.video = findVideo();
    return S.video;
  }

  function updatePosition() {
    if (!UI.wrap) return;
    const v = currentVideo();
    const vw = window.innerWidth;
    const vh = window.innerHeight;
    const r = v ? v.getBoundingClientRect() : null;
    const valid = r && r.width > 160 && r.height > 90 && r.bottom > 40 && r.top < vh - 40;
    const box = valid
      ? { left: r!.left, top: Math.max(0, r!.top), width: r!.width, height: Math.min(r!.bottom, vh) - Math.max(0, r!.top) }
      : { left: vw * 0.03, top: vh * 0.1, width: vw * 0.94, height: vh * 0.8 };
    const st = UI.wrap.style;
    st.left = Math.round(box.left) + "px";
    st.top = Math.round(box.top) + "px";
    st.width = Math.round(box.width) + "px";
    st.height = Math.round(box.height) + "px";
    // Keep clear of the player's own controls at the bottom.
    const pad = Math.round(box.height * (S.settings.position === "top" ? 0.06 : 0.13));
    st.paddingTop = st.paddingBottom = pad + "px";
    UI.tools.style.top = Math.round(box.top + 10) + "px";
    UI.tools.style.left = Math.round(box.left + box.width - UI.tools.offsetWidth - 10) + "px";
    // The size setting is for a 900px-wide player; the text scales with the player.
    const scale = Math.max(0.6, Math.min(1.8, box.width / 900));
    st.fontSize = Math.round(S.settings.size * scale) + "px";
  }

  function positionLoop() {
    if (!S.active) return void (rafId = null);
    updatePosition();
    rafId = requestAnimationFrame(positionLoop);
  }

  function applySettings() {
    if (!UI.wrap) return;
    UI.wrap.classList.toggle("top", S.settings.position === "top");
    UI.wrap.classList.toggle("bottom", S.settings.position !== "top");
    UI.wrap.style.setProperty("--bgo", String(S.settings.bgOpacity));
    UI.trLine.dir = langDir(S.settings.lang);
    UI.subs.classList.toggle("off", S.hidden);
    const btn = (a: string) => UI.tools.querySelector(`[data-act="${a}"]`);
    const set = (a: string, on: boolean) => {
      btn(a).classList.toggle("on", on);
      btn(a).setAttribute("aria-pressed", String(on));
    };
    set("subs", !S.hidden);
    set("bi", S.settings.bilingual);
    set("dub", S.settings.dub);
    updatePosition();
  }

  function showTools(stay?: boolean) {
    if (!UI.tools) return;
    UI.tools.classList.add("show");
    clearTimeout(toolsTimer);
    toolsTimer = setTimeout(() => {
      if (!UI.tools?.matches(":hover") && !UI.tools?.matches(":focus-within")) UI.tools?.classList.remove("show");
    }, stay ? 4000 : 2200);
  }

  function onMouseMove(e: MouseEvent) {
    if (!S.active || !S.video) return;
    const r = S.video.getBoundingClientRect();
    if (e.clientX >= r.left && e.clientX <= r.right && e.clientY >= r.top && e.clientY <= r.bottom) showTools();
  }

  function saveSettings(patch: Partial<Settings>) {
    S.settings = mergeSettings(S.settings, patch);
    bg("set-settings", { settings: patch });
    applySettings();
  }

  function onToolClick(e: Event) {
    const act = (e.target as HTMLElement).closest("button")?.dataset.act;
    if (!act) return;
    switch (act) {
      case "subs":
        S.hidden = !S.hidden;
        applySettings();
        break;
      case "bi":
        saveSettings({ bilingual: !S.settings.bilingual });
        renderCurrent();
        break;
      case "minus":
        saveSettings({ size: Math.max(SIZE_MIN, S.settings.size - 2) });
        break;
      case "plus":
        saveSettings({ size: Math.min(SIZE_MAX, S.settings.size + 2) });
        break;
      case "pos":
        saveSettings({ position: S.settings.position === "top" ? "bottom" : "top" });
        break;
      case "dub":
        saveSettings({ dub: !S.settings.dub });
        applyDubSetting();
        break;
      case "stop":
        bg("stop-from-page");
        deactivate();
        return;
    }
    showTools(true);
  }

  // Hide YouTube's own captions so ours stand alone.
  function hideNativeCC(on: boolean) {
    const id = "__tarjuman_cc_hide";
    const existing = document.getElementById(id);
    if (on && !existing) {
      const st = document.createElement("style");
      st.id = id;
      st.textContent = ".ytp-caption-window-container{display:none!important}";
      document.documentElement.appendChild(st);
    } else if (!on && existing) existing.remove();
  }

  function setPill(text: string, { busy = false, err = false, hideAfter = 0 } = {}) {
    if (!UI.pill) return;
    UI.pill.classList.remove("hide");
    UI.pill.classList.toggle("busy", busy);
    UI.pill.classList.toggle("err", err);
    UI.pillTxt.textContent = text;
    clearTimeout(pillTimer);
    if (hideAfter) pillTimer = setTimeout(hidePill, hideAfter);
  }

  function hidePill() {
    UI.pill?.classList.add("hide");
  }

  function renderText(tr: string, src: string, pending = false) {
    if (!UI.tr) return;
    UI.tr.textContent = tr || "";
    UI.trLine.classList.toggle("pending", pending);
    UI.src.textContent = src && S.settings.bilingual ? src : "";
  }

  function errorText(res: Reply | null | undefined) {
    const code = res && res.code;
    if (code === "NO_SERVER") return t("errNoServerShort");
    if (code === "UNPLAYABLE") return t("errUnplayable");
    if (code === "WHISPER_NOT_INSTALLED") return t("errWhisper");
    if (code === "TIMEOUT") return t("errTimeout");
    return (res && (res.message || code)) || t("errGeneric");
  }

  /* ------------------------------------------------------------------ */
  /*  YouTube mode                                                       */
  /* ------------------------------------------------------------------ */

  function fillCues(cues: Cue[]) {
    S.cues = cues || [];
    S.tr = new Map();
    S.tries = new Map();
    S.cues.forEach((c, i) => c.ar && S.tr.set(i, c.ar));
    S.idx = -1;
    stopDub();
  }

  async function activateYouTube(url: string) {
    const vid = ytVideoId(url);
    if (S.active && S.mode === "youtube" && vid && vid === S.videoId && (S.loading || S.cues.length)) return;

    const gen = ++S.gen;
    S.active = true;
    S.mode = "youtube";
    S.videoId = vid;
    S.whisperUrl = url;
    S.cues = [];
    S.idx = -1;
    S.loading = true;
    stopDub();
    ensureOverlay();
    UI.whisper.classList.remove("show");
    renderText("", "");
    hideNativeCC(true);
    if (!rafId) rafId = requestAnimationFrame(positionLoop);

    if (!vid) {
      // A YouTube page that isn't a video (the home page): wait for one to open.
      S.loading = false;
      setPill(t("pillOpenVideo"), { hideAfter: 3000 });
      return;
    }
    setPill(t("pillPreparing"), { busy: true });

    const res = await bg("fetch-cues", { url, tl: S.settings.lang });
    if (gen !== S.gen || !S.active) return;
    S.loading = false;

    if (!res || !res.ok) {
      if (res && res.code === "NO_CAPTIONS") return offerWhisper(url);
      return setPill(errorText(res), { err: true });
    }

    fillCues(res.cues);
    setPill(res.alreadyTranslated ? t("pillNativeReady") : t("pillRunning"), { hideAfter: 2200 });
    startSync();
    applyDubSetting();
    if (!res.alreadyTranslated) translateLoop(res.srcLang || "auto", gen);
  }

  const adShowing = () => !!document.querySelector(".html5-video-player.ad-showing");

  function startSync() {
    stopSync();
    S.timer = setInterval(() => {
      if (!S.active || !isSynced()) return;
      const v = currentVideo();
      if (!v) return;
      const i = adShowing() ? -1 : cueIndexAt(S.cues, v.currentTime);
      if (i !== S.idx) {
        S.idx = i;
        renderCurrent();
      }
    }, 120);
  }

  function stopSync() {
    clearInterval(S.timer);
    S.timer = 0;
  }

  function renderCurrent() {
    if (!isSynced()) return;
    const i = S.idx;
    if (i < 0 || !S.cues[i]) return renderText("", "");
    const c = S.cues[i];
    const tr = S.tr.get(i) || "";
    renderText(tr || (S.translating ? "…" : c.src), c.src, !tr);
  }

  async function translateLoop(sl: string, gen: number) {
    if (S.translating) return;
    S.translating = true;
    let failStreak = 0;
    try {
      while (S.active && isSynced() && gen === S.gen) {
        const now = S.video ? S.video.currentTime : 0;
        const pending = (i: number) => !S.tr.has(i) && !!S.cues[i].src && (S.tries.get(i) || 0) < 3;
        const todo: number[] = [];
        for (let i = 0; i < S.cues.length; i++) {
          // Only a window around the playhead: translating a whole long video at once exhausts the free
          // translators' limits, and then the dub (which needs them too) goes silent.
          if (pending(i) && S.cues[i].start <= now + 300 && S.cues[i].end >= now - 30) todo.push(i);
        }
        if (!todo.length) {
          if (!S.cues.some((_, i) => pending(i))) break;
          await sleep(4000);
          continue;
        }
        // What is about to be shown first.
        todo.sort((a, b) => Math.abs(S.cues[a].start - now) - Math.abs(S.cues[b].start - now));
        const batch = todo.slice(0, 40);
        const r = await bg("translate", { texts: batch.map((i) => S.cues[i].src), sl, tl: S.settings.lang });
        if (gen !== S.gen) return;
        // Nothing at all came back: the translators are pausing after a rate limit; back off and retry.
        if (!r || !r.ok || !r.map || !Object.keys(r.map).length) {
          if (++failStreak === 5) setPill(t("pillTranslateDown"), { err: true, hideAfter: 5000 });
          await sleep(Math.min(30000, 800 * 2 ** failStreak));
          continue;
        }
        failStreak = 0;
        for (const i of batch) {
          const tr = r.map && r.map[S.cues[i].src];
          if (tr) S.tr.set(i, tr);
          else S.tries.set(i, (S.tries.get(i) || 0) + 1);
        }
        if (batch.includes(S.idx)) renderCurrent();
      }
    } finally {
      S.translating = false;
      renderCurrent();
    }
  }

  /* ------------------------------------------------------------------ */
  /*  Whisper, for videos without captions                               */
  /* ------------------------------------------------------------------ */

  function offerWhisper(url: string) {
    S.whisperUrl = url;
    setPill(t("pillNoCaptions"));
    UI.whisper.classList.add("show");
    UI.whisperBtn.disabled = false;
    UI.whisperBtn.textContent = t("btnWhisper");
    UI.meter.style.width = "0%";
  }

  async function startWhisper() {
    UI.whisperBtn.disabled = true;
    UI.whisperBtn.textContent = t("btnWhisperStarting");
    const gen = S.gen;
    const r = await bg("whisper-start", { url: S.whisperUrl, tl: S.settings.lang });
    if (!r || !r.ok) {
      setPill(errorText(r), { err: true });
      UI.whisperBtn.disabled = false;
      UI.whisperBtn.textContent = t("btnRetry");
      return;
    }
    for (;;) {
      if (!S.active || gen !== S.gen) return;
      const j = await bg("whisper-poll", { id: r.id });
      if (!j || !j.ok) return;
      if (!UI.meter) return;
      UI.meter.style.width = (j.progress || 0) + "%";
      if (j.status === "done") {
        UI.whisper.classList.remove("show");
        fillCues(j.cues || []);
        setPill(t("pillWhisperDone"), { hideAfter: 2200 });
        startSync();
        applyDubSetting();
        translateLoop(j.srcLang || "auto", gen);
        return;
      }
      if (j.status === "error" || j.status === "cancelled") {
        setPill("Whisper: " + (j.message || t("errGeneric")), { err: true });
        UI.whisperBtn.disabled = false;
        UI.whisperBtn.textContent = t("btnRetry");
        return;
      }
      setPill((j.phase || t("pillWorking")) + " — " + (j.progress || 0) + "%", { busy: true });
      await sleep(1500);
    }
  }

  /* ------------------------------------------------------------------ */
  /*  Live mode                                                          */
  /* ------------------------------------------------------------------ */

  function activateLive() {
    S.gen++;
    S.active = true;
    S.mode = "live";
    stopSync();
    stopDub();
    ensureOverlay();
    UI.whisper.classList.remove("show");
    if (!rafId) rafId = requestAnimationFrame(positionLoop);
    setPill(t("pillListening"), { busy: true, hideAfter: 3500 });
  }

  /* ------------------------------------------------------------------ */
  /*  Dubbing (youtube and captions modes): the shared sentence engine.  */
  /*  A sentence is never cut: a late one plays faster, or the video     */
  /*  waits a moment (see specs §7).                                     */
  /* ------------------------------------------------------------------ */

  let dub: DubEngine | null = null;

  const videoMedia: DubMedia = {
    time: () => currentVideo()?.currentTime ?? 0,
    // An ad counts as paused: no dubbing over ads.
    paused: () => {
      const v = currentVideo();
      return !v || v.paused || adShowing();
    },
    rate: () => currentVideo()?.playbackRate || 1,
    // The engine slows the video slightly while the dub catches up, instead of pausing it.
    setRate: (r) => {
      const v = currentVideo();
      if (v) v.playbackRate = r;
    },
    play: () => void currentVideo()?.play().catch(() => {}),
    pause: () => currentVideo()?.pause(),
    // The real volume even while muted; otherwise stopping the dub would restore 0.
    getVolume: () => currentVideo()?.volume ?? 1,
    setVolume: (x) => {
      const v = currentVideo();
      if (v) v.volume = Math.max(0, Math.min(1, x));
    },
  };

  const dubOptions = () => ({ wait: S.settings.dubWait, duck: S.settings.duck });

  function startDub() {
    if (dub) return;
    const url = location.href;
    const lang = S.settings.lang;
    const voice = S.settings.voice || "";
    dub = new DubEngine({
      media: videoMedia,
      loadPlan: async (from, to, { urgent, speed }) => {
        const r =
          S.mode === "captions"
            ? await bg("dub-plan-cues", { cues: S.cues.map((c) => ({ start: c.start, end: c.end, src: c.src })), sl: S.srcLang, tl: lang, voice, from, to, urgent, speed })
            : await bg("dub-plan", { url, tl: lang, voice, from, to, urgent, speed });
        if (!r || !r.ok) throw new Error((r && r.code) || "PLAN");
        return r as any;
      },
      synth: async (b, rate) => {
        const r = await bg("tts-fetch", { text: b.text, lang, voice, rate });
        if (!r || !r.ok) throw new Error("TTS");
        return { url: b64ToObjectUrl(r.audio_b64, r.mime), duration: r.duration || 0 };
      },
      onState: (st) => {
        if (st === "waiting") setPill(t("pillDubWaiting"), { busy: true });
        else if (st === "buffering") setPill(t("pillDubBuffering"), { busy: true });
        else if (st === "error") setPill(t("pillDubError"), { err: true, hideAfter: 4000 });
        else hidePill();
      },
      options: dubOptions(),
    });
    dub.start();
  }

  function stopDub() {
    if (dub) dub.stop();
    dub = null;
  }

  function applyDubSetting(restart?: boolean) {
    // In live mode the offscreen document does the dubbing.
    const want = S.settings.dub && isSynced() && S.cues.length > 0;
    if (!want || restart) stopDub();
    if (!want) return;
    if (dub) dub.setOptions(dubOptions());
    else startDub();
  }

  /* ------------------------------------------------------------------ */
  /*  The site's own captions (Coursera, Udemy, any player with text      */
  /*  tracks). Far better than transcribing audio: the exact words, timed.*/
  /* ------------------------------------------------------------------ */

  const isSynced = () => S.mode === "youtube" || S.mode === "captions";

  function textTracks() {
    const v = findVideo();
    if (!v || !v.textTracks) return [];
    return [...v.textTracks].map((tr, i) => ({ tr, i })).filter(({ tr }) => tr.kind === "subtitles" || tr.kind === "captions");
  }

  function probeCaptions(): TrackInfo[] {
    return textTracks().map(({ tr, i }) => ({ index: i, lang: (tr.language || "").toLowerCase(), label: tr.label || "" }));
  }

  /** Turns the track on (hidden) and waits for its cues to load. */
  // Tracks we switched off screen, with the mode to give back when translation stops.
  const hiddenTracks = new Map<TextTrack, TextTrackMode>();

  async function loadTrackCues(track: TextTrack) {
    // "hidden" still loads the cues but stops the player drawing them under our translation.
    if (!hiddenTracks.has(track)) hiddenTracks.set(track, track.mode);
    track.mode = "hidden";
    for (let k = 0; k < 25 && !(track.cues && track.cues.length); k++) await sleep(200);
    return normalizeTrackCues((track.cues || []) as unknown as ArrayLike<VTTCue>);
  }

  function restoreTracks() {
    for (const [track, mode] of hiddenTracks) {
      try {
        track.mode = mode;
      } catch {}
    }
    hiddenTracks.clear();
  }

  async function activateCaptions(index?: number) {
    const gen = ++S.gen;
    const all = textTracks();
    const entry = all.find((x) => x.i === index) || all[0];
    S.active = true;
    S.mode = "captions";
    S.trackIndex = entry ? entry.i : -1;
    S.cues = [];
    S.idx = -1;
    stopDub();
    ensureOverlay();
    UI.whisper.classList.remove("show");
    renderText("", "");
    if (!rafId) rafId = requestAnimationFrame(positionLoop);
    if (!entry) return setPill(t("pillNoSiteCaptions"), { err: true });
    setPill(t("pillReadingSiteCaptions"), { busy: true });
    const cues = await loadTrackCues(entry.tr);
    if (gen !== S.gen || !S.active) return;
    if (!cues.length) return setPill(t("pillSiteCaptionsEmpty"), { err: true });
    S.srcLang = (entry.tr.language || "auto").toLowerCase().split("-")[0] || "auto";
    fillCues(cues);
    setPill(t("pillSiteCaptionsRunning"), { hideAfter: 2500 });
    startSync();
    applyDubSetting();
    translateLoop(S.srcLang, gen);
  }

  /* ------------------------------------------------------------------ */
  /*  Messages                                                           */
  /* ------------------------------------------------------------------ */

  function handle(msg: any): Reply | undefined {
    switch (msg.type) {
      case "ping":
        return { ok: true, active: S.active, mode: S.mode };
      case "activate-youtube":
        if (msg.settings) S.settings = mergeSettings(S.settings, msg.settings);
        activateYouTube(msg.url || location.href);
        return { ok: true };
      case "probe-captions":
        return { ok: true, tracks: probeCaptions() };
      case "activate-captions":
        if (msg.settings) S.settings = mergeSettings(S.settings, msg.settings);
        activateCaptions(msg.index);
        return { ok: true };
      case "activate-live":
        if (msg.settings) S.settings = mergeSettings(S.settings, msg.settings);
        activateLive();
        return { ok: true };
      case "deactivate":
        deactivate();
        return { ok: true };
      case "settings": {
        const next = mergeSettings(S.settings, msg.settings);
        const langChanged = next.lang !== S.settings.lang;
        const voiceChanged = next.voice !== S.settings.voice;
        S.settings = next;
        applySettings();
        if (S.active && S.mode === "youtube" && langChanged) {
          S.videoId = "";
          activateYouTube(location.href);
        } else if (S.active && S.mode === "captions" && langChanged) {
          activateCaptions(S.trackIndex);
        } else {
          applyDubSetting(voiceChanged);
          renderCurrent();
        }
        return { ok: true };
      }
      case "live-sub":
        if (!S.active || S.mode !== "live" || (!msg.ar && !msg.text)) return;
        renderText(msg.ar || msg.text, msg.text, !msg.ar);
        hidePill();
        clearTimeout(S.liveTimer);
        S.liveTimer = setTimeout(() => S.mode === "live" && renderText("", ""), 9000);
        return;
      case "live-status":
        if (!S.active || S.mode !== "live") return;
        if (msg.status === "server-down") setPill(t("pillServerDown"), { err: true });
        else if (msg.status === "error") setPill(msg.message || t("pillLiveError"), { err: true, hideAfter: 4000 });
        return;
      default:
        return;
    }
  }

  chrome.runtime.onMessage.addListener((msg, _sender, respond) => {
    if (!msg || !msg.type || msg.target === "offscreen") return;
    const res = handle(msg);
    if (res) respond(res);
  });

  function deactivate() {
    restoreTracks();
    S.gen++;
    S.active = false;
    S.mode = null;
    S.videoId = "";
    S.cues = [];
    stopSync();
    stopDub();
    clearTimeout(S.liveTimer);
    if (rafId) cancelAnimationFrame(rafId);
    rafId = null;
    hideNativeCC(false);
    removeOverlay();
  }

  // YouTube is a single-page app: reload when the video changes.
  document.addEventListener("yt-navigate-finish", () => {
    if (S.active && S.mode === "youtube") activateYouTube(location.href);
  });

  document.addEventListener("fullscreenchange", () => {
    if (!UI.host) return;
    const fe = document.fullscreenElement;
    const target = fe && fe.tagName !== "VIDEO" ? fe : document.documentElement;
    if (UI.host.parentNode !== target) target.appendChild(UI.host);
  });

  document.addEventListener("mousemove", onMouseMove, { passive: true });

  // After a reload or a new page in a tab that was translating, pick up where it left off.
  bg("content-ready", { url: location.href }).then((r) => {
    if (r && r.ok && r.activate) handle(r.activate);
  });
})();
