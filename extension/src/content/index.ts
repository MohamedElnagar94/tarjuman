/**
 * Content script: the overlay in the page.
 *  1) youtube  → captions from the local server, synced to the video; the dub engine speaks each sentence on time.
 *  2) captions → the site player's own text tracks (Coursera, Udemy…), translated and synced the same way.
 *  3) live     → shows the live subtitles that the offscreen document produces from the tab's audio.
 *
 * All server traffic goes through the background (page CORS / private network rules).
 */
import { DubEngine, type DubMedia } from "@tarjuman/dub-engine";
import { t, useTable } from "@/shared/i18n";
import { FONT_STACK } from "@/shared/fonts";
import { mergeSettings, langDir, SIZE_MIN, SIZE_MAX, type Settings } from "@/shared/settings";
import { cueIndexAt, ytVideoId, isYouTube, normalizeTrackCues, stepLine, type Cue, type TrackInfo } from "@/shared/cues";
import { b64ToObjectUrl } from "@/shared/audio";
import type { Reply } from "@/shared/messages";
import { replyError } from "@/shared/errors";
import { shortcutFor, isTypingTarget, type ShortcutAction } from "@/shared/shortcuts";
import { captionTime, formatOffset, nudgeOffset, offsetKey, videoTimeFor } from "@/shared/timing";
import { lineProgress, tokenize, highlight } from "@/shared/cueText";
import { channelFromHref, isAutoStartPage, type Channel } from "@/shared/autostart";
import { injectFonts, overlayHtml, ICONS } from "./overlay";
import { createTranscript, type Transcript } from "./transcript";

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
    /** The activation (gen) whose translation loop is running, 0 when none. A newer activation starts its own
     *  loop instead of waiting on an older one that is still asleep, and the older one then exits. */
    translatingGen: 0,
    /** The server's Whisper job for this page, so it can be cancelled when the user stops or moves on. */
    whisperJob: "",
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
    /** Subtitle timing shift in seconds (shared/timing.ts), and the video it belongs to. */
    offset: 0,
    offsetKey: "",
    /** The video's title from the server, kept with saved words. */
    title: "",
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
    // Closed: the page's own scripts can't reach into the overlay and read the translation.
    const shadow = host.attachShadow({ mode: __SHADOW_MODE__ });
    shadow.innerHTML = overlayHtml();
    overlayParent().appendChild(host);

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
    UI.tpop = shadow.querySelector(".tpop");
    UI.tpopOut = shadow.querySelector(".tpop output");
    UI.tpopNote = shadow.querySelector(".tpop .note");
    UI.tpopReset = shadow.querySelector(".tpop .reset");
    UI.lk = shadow.querySelector(".lk");
    UI.lkWord = shadow.querySelector(".lk-word");
    UI.lkMean = shadow.querySelector(".lk-mean");
    UI.lkSent = shadow.querySelector(".lk-sent");
    UI.lkSave = shadow.querySelector(".lk .save");
    UI.lkState = shadow.querySelector(".lk-state");
    UI.whisperBtn.addEventListener("click", startWhisper);
    UI.tools.addEventListener("click", onToolClick);
    UI.tools.addEventListener("mouseenter", () => showTools(true));
    UI.tools.addEventListener("focusin", () => showTools(true));
    UI.src.addEventListener("click", onWordClick);
    UI.lk.querySelector(".x").addEventListener("click", () => closeLookup(true));
    UI.lkSave.addEventListener("click", saveLookup);
    // Keys pressed on our buttons (Space, Enter, Escape) must not reach the page's player shortcuts.
    for (const el of [UI.tools, UI.lk]) {
      el.addEventListener("keydown", (e: KeyboardEvent) => {
        if (e.key === "Escape") {
          if (!UI.tpop.hidden) toggleTimingPop(false, true);
          if (!UI.lk.hidden) closeLookup(true);
        }
        e.stopPropagation();
      });
      el.addEventListener("keyup", (e: Event) => e.stopPropagation());
    }
    applySettings();
    renderOffset();
    updatePosition();
  }

  /** Where the overlay must live to be painted. In fullscreen only the fullscreen element is drawn, so
   *  inside it; but nothing can be drawn over a fullscreen <video> (the subtitles then go into a text
   *  track on it, see mirrorToVideo) nor over a fullscreen <iframe> from outside it. */
  function overlayParent(): Element {
    const fe = document.fullscreenElement;
    return fe && fe.tagName !== "VIDEO" && fe.tagName !== "IFRAME" ? fe : document.documentElement;
  }

  /* A <video> shown full screen by itself (its own fullscreen button, or a site player that makes the
     video element fullscreen) paints nothing of the page over it, so the overlay can't be seen. The
     browser still draws the video's text tracks there: the current line goes into a track of ours. */
  const fsTracks = new WeakMap<HTMLVideoElement, TextTrack>();
  let fsCue: VTTCue | null = null;
  let fsShown = "";
  let fsVideo: HTMLVideoElement | null = null;

  function mirrorToVideo() {
    const fe = document.fullscreenElement;
    const v = S.active && !S.hidden && fe instanceof HTMLVideoElement ? fe : null;
    const text = v ? [UI.tr?.textContent || "", UI.src?.dataset.text || ""].filter(Boolean).join("\n") : "";
    if (fsVideo && (fsVideo !== v || !text)) {
      const old = fsTracks.get(fsVideo);
      if (old) {
        if (fsCue) old.removeCue(fsCue);
        old.mode = "disabled";
      }
      fsCue = null;
      fsShown = "";
      fsVideo = null;
    }
    if (!v || !text || text === fsShown) return;
    let track = fsTracks.get(v);
    if (!track) {
      // A track added by script can't be removed again: one per video, switched off when not needed.
      track = v.addTextTrack("subtitles", "Tarjuman", S.settings.lang);
      fsTracks.set(v, track);
    }
    track.mode = "showing";
    if (fsCue) track.removeCue(fsCue);
    fsCue = new VTTCue(0, 1e7, text);
    fsCue.line = S.settings.position === "top" ? 1 : -2;
    track.addCue(fsCue);
    fsShown = text;
    fsVideo = v;
  }

  function removeOverlay() {
    lookupFor = null;
    UI.host?.remove();
    for (const k of Object.keys(UI)) delete UI[k];
  }

  const bigEnough = (v: HTMLVideoElement) => v.offsetWidth > 120 && v.offsetHeight > 70;

  function findVideo(): HTMLVideoElement | null {
    // YouTube keeps several <video>s around (Shorts, previews, the hidden watch player): the one playing is
    // the active Shorts player or the main player, whichever is on screen.
    for (const sel of ["ytd-reel-video-renderer[is-active] video.html5-main-video", "#shorts-player video.html5-main-video", "#movie_player video.html5-main-video"]) {
      const v = document.querySelector<HTMLVideoElement>(sel);
      if (v && bigEnough(v)) return v;
    }
    const vids = [...document.querySelectorAll("video")].filter(bigEnough);
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
    UI.tools.style.left = Math.max(4, Math.round(box.left + box.width - UI.tools.offsetWidth - 10)) + "px";
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
    UI.wrap.style.setProperty("--sub-font", FONT_STACK[S.settings.font]);
    UI.trLine.dir = langDir(S.settings.lang);
    UI.subs.classList.toggle("off", S.hidden);
    mirrorToVideo();
    const btn = (a: string) => UI.tools.querySelector(`[data-act="${a}"]`);
    const set = (a: string, on: boolean) => {
      btn(a).classList.toggle("on", on);
      btn(a).setAttribute("aria-pressed", String(on));
    };
    set("subs", !S.hidden);
    set("bi", S.settings.bilingual);
    set("dub", S.settings.dub);
    set("list", S.settings.transcript);
    // Line-based tools need lines: not in live mode. "Open in the app" only for a YouTube video.
    const synced = isSynced();
    btn("time").hidden = !synced;
    btn("list").hidden = !synced;
    btn("dub").hidden = S.mode === "live";
    btn("app").hidden = !(S.mode === "youtube" && S.videoId);
    if (!synced && !UI.tpop.hidden) toggleTimingPop(false);
    syncTranscript();
    updatePosition();
  }

  function showTools(stay?: boolean) {
    if (!UI.tools) return;
    UI.tools.classList.add("show");
    clearTimeout(toolsTimer);
    toolsTimer = setTimeout(() => {
      if (!UI.tools?.matches(":hover") && !UI.tools?.matches(":focus-within") && UI.tpop?.hidden) UI.tools?.classList.remove("show");
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
    const button = (e.target as HTMLElement).closest("button");
    const nudge = button?.dataset.nudge;
    if (nudge) {
      if (nudge === "reset") setOffset(0);
      else setOffset(nudgeOffset(S.offset, Number(nudge)));
      return;
    }
    const act = button?.dataset.act;
    if (!act) return;
    switch (act) {
      case "subs":
        S.hidden = !S.hidden;
        applySettings();
        break;
      case "time":
        toggleTimingPop(UI.tpop.hidden);
        break;
      case "list":
        saveSettings({ transcript: !S.settings.transcript });
        break;
      case "app":
        openInApp();
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
    const shown = src && S.settings.bilingual ? src : "";
    if (UI.src.dataset.text === shown) return void mirrorToVideo();
    UI.src.dataset.text = shown;
    mirrorToVideo();
    UI.src.textContent = "";
    // In synced modes each word of the original can be clicked for its meaning.
    if (!shown || !isSynced()) return void (UI.src.textContent = shown);
    for (const tk of tokenize(shown)) {
      if (!tk.word) {
        UI.src.append(tk.text);
        continue;
      }
      const w = document.createElement("span");
      w.className = "w";
      w.dataset.w = tk.lookup;
      w.textContent = tk.text;
      if (lookupFor && lookupFor.word === tk.lookup && lookupFor.sentence === shown) w.classList.add("sel");
      UI.src.append(w);
    }
  }

  /** A failure in the user's interface language (the app's own messages are in Arabic). */
  const errorText = (res: Reply | null | undefined) => replyError(res);

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
    transcript?.setCues(S.cues, S.tr, S.srcLang, S.settings.lang);
  }

  async function activateYouTube(url: string) {
    const vid = ytVideoId(url);
    if (S.active && S.mode === "youtube" && vid && vid === S.videoId && (S.loading || S.cues.length)) return;

    const gen = ++S.gen;
    cancelWhisper();
    S.active = true;
    S.mode = "youtube";
    S.videoId = vid;
    // The server knows watch pages; a player embedded in another site runs at /embed/ID?….
    if (vid) url = watchUrl(vid);
    // Another video (or a Short) may play in another <video> element: look for it again.
    S.video = null;
    S.whisperUrl = url;
    S.cues = [];
    S.idx = -1;
    S.loading = true;
    S.title = "";
    stopDub();
    closeLookup(false);
    ensureOverlay();
    UI.whisper.classList.remove("show");
    renderText("", "");
    hideNativeCC(true);
    transcript?.setCues([], S.tr, "auto", S.settings.lang);
    loadOffset(gen);
    applySettings();
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

    S.srcLang = res.srcLang || "auto";
    S.title = String(res.title || "");
    fillCues(res.cues);
    setPill(res.alreadyTranslated ? t("pillNativeReady") : t("pillRunning"), { hideAfter: 2200 });
    startSync();
    applyDubSetting();
    if (!res.alreadyTranslated) translateLoop(res.srcLang || "auto", gen);
  }

  const watchUrl = (vid: string) => "https://www.youtube.com/watch?v=" + vid;

  /** YouTube's miniplayer: the video keeps playing in a corner while the user browses the home page. */
  function miniplayerShowing() {
    if (document.querySelector("ytd-app[miniplayer-is-active], ytd-miniplayer[active]")) return true;
    const v = document.querySelector<HTMLVideoElement>("ytd-miniplayer video");
    return !!v && v.offsetWidth > 0;
  }

  const adShowing = () => !!document.querySelector(".html5-video-player.ad-showing");

  function startSync() {
    stopSync();
    let ticks = 0;
    S.timer = setInterval(() => {
      if (!S.active || !isSynced()) return;
      // About once a second: the site's captions may have grown or changed lesson, and a YouTube video
      // in the miniplayer may have been closed.
      if (++ticks % 8 === 0) {
        if (S.mode === "captions") checkCaptions();
        else if (S.videoId && !ytVideoId(location.href) && window.top === window && !miniplayerShowing()) return void activateYouTube(location.href);
      }
      const v = currentVideo();
      if (!v) return;
      const now = captionTime(v.currentTime, S.offset);
      const i = adShowing() ? -1 : cueIndexAt(S.cues, now);
      if (i !== S.idx) {
        S.idx = i;
        renderCurrent();
      }
      if (transcript) {
        const c = S.cues[i];
        transcript.setCurrent(i, c ? lineProgress(c.start, c.end, now) : 0);
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
    renderText(tr || (S.translatingGen === S.gen ? "…" : c.src), c.src, !tr);
  }

  async function translateLoop(sl: string, gen: number) {
    // Only one loop per activation; a loop left from an earlier one stops at its next check of S.gen.
    if (S.translatingGen === gen) return;
    S.translatingGen = gen;
    transcript?.setTranslating(true);
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
        const cuesSent = S.cues;
        const r = await bg("translate", { texts: batch.map((i) => S.cues[i].src), sl, tl: S.settings.lang });
        if (gen !== S.gen) return;
        // The app hasn't allowed this copy of the extension yet (a store copy and a copy loaded by hand
        // have different ids): retrying can't help, and "…" forever told the user nothing. Say what to
        // do and show the original lines meanwhile.
        if (r && r.code === "EXTENSION_NOT_ALLOWED") {
          setPill(t("pillNotAllowed"), { err: true });
          break;
        }
        // Nothing at all came back: the translators are pausing after a rate limit; back off and retry.
        if (!r || !r.ok || !r.map || !Object.keys(r.map).length) {
          if (++failStreak === 5) setPill(t("pillTranslateDown"), { err: true, hideAfter: 5000 });
          await sleep(Math.min(30000, 800 * 2 ** failStreak));
          continue;
        }
        failStreak = 0;
        if (S.cues !== cuesSent) {
          // The site's captions were read again meanwhile (more lines loaded): match by text.
          const got: number[] = [];
          S.cues.forEach((c, i) => {
            const tr = r.map![c.src];
            if (tr && !S.tr.has(i)) {
              S.tr.set(i, tr);
              got.push(i);
            }
          });
          transcript?.updateTr(got, S.tr);
          renderCurrent();
          continue;
        }
        for (const i of batch) {
          const tr = r.map && r.map[S.cues[i].src];
          if (tr) S.tr.set(i, tr);
          else S.tries.set(i, (S.tries.get(i) || 0) + 1);
        }
        transcript?.updateTr(batch, S.tr);
        if (batch.includes(S.idx)) renderCurrent();
      }
    } finally {
      // An older loop ending must not mark a newer one as finished.
      if (S.translatingGen === gen) {
        S.translatingGen = 0;
        transcript?.setTranslating(false);
        renderCurrent();
      }
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
    // Stopped or moved on while the job was being created: nobody will see it.
    if (!S.active || gen !== S.gen) return void bg("whisper-cancel", { id: r.id });
    S.whisperJob = r.id;
    for (;;) {
      if (!S.active || gen !== S.gen) return;
      const j = await bg("whisper-poll", { id: r.id });
      if (!S.active || gen !== S.gen || !UI.meter) return;
      if (!j || !j.ok) {
        // Lost track of the job (server restarted, timed out): say so and let the user try again,
        // rather than leaving the button greyed out for good.
        cancelWhisper();
        setPill(errorText(j), { err: true });
        UI.whisperBtn.disabled = false;
        UI.whisperBtn.textContent = t("btnRetry");
        return;
      }
      UI.meter.style.width = (j.progress || 0) + "%";
      if (j.status === "done") {
        S.whisperJob = "";
        UI.whisper.classList.remove("show");
        S.srcLang = j.srcLang || "auto";
        fillCues(j.cues || []);
        setPill(t("pillWhisperDone"), { hideAfter: 2200 });
        startSync();
        applyDubSetting();
        translateLoop(j.srcLang || "auto", gen);
        return;
      }
      if (j.status === "error" || j.status === "cancelled") {
        S.whisperJob = "";
        setPill("Whisper: " + replyError(j), { err: true });
        UI.whisperBtn.disabled = false;
        UI.whisperBtn.textContent = t("btnRetry");
        return;
      }
      setPill((j.phase || t("pillWorking")) + " — " + (j.progress || 0) + "%", { busy: true });
      await sleep(1500);
    }
  }

  /** Stops the server's Whisper job for this page, if one is running. */
  function cancelWhisper() {
    if (!S.whisperJob) return;
    bg("whisper-cancel", { id: S.whisperJob });
    S.whisperJob = "";
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
    closeLookup(false);
    ensureOverlay();
    applySettings();
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
    // The caption clock: with the subtitles shifted, the voice moves with them.
    time: () => captionTime(currentVideo()?.currentTime ?? 0, S.offset),
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
      if (!v) return;
      v.volume = Math.max(0, Math.min(1, x));
      ourVolume = v.volume;
    },
  };

  /* While dubbing, the original voice is turned down. If the user (or the player, which re-applies its
     own volume now and then) changes the volume, that becomes the level to give back on stop, and the
     original voice is turned down again from it, instead of coming back loud over the dub. */
  let ourVolume = -1;
  function onVolumeChange(e: Event) {
    const v = e.target;
    if (!dub || !(v instanceof HTMLVideoElement) || v !== currentVideo()) return;
    if (Math.abs(v.volume - ourVolume) < 0.002) return; // our own change
    dub.userVolume(v.volume);
  }

  const dubOptions = () => ({ wait: S.settings.dubWait, duck: S.settings.duck });

  function startDub() {
    if (dub) return;
    const url = S.mode === "youtube" && S.videoId ? watchUrl(S.videoId) : location.href;
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
  /*  Subtitle timing: shift the lines (and the dub) earlier or later,   */
  /*  remembered per video for the browser session.                      */
  /* ------------------------------------------------------------------ */

  /** The page that the timing belongs to: the YouTube video, or this player's page. */
  const pageKey = () => (S.mode === "youtube" && S.videoId ? "yt:" + S.videoId : offsetKey(location.href));

  async function loadOffset(gen: number) {
    const key = pageKey();
    S.offsetKey = key;
    S.offset = 0;
    renderOffset();
    const r = await bg("offset-get", { key });
    if (gen !== S.gen || key !== S.offsetKey || !r || !r.ok) return;
    S.offset = Number(r.offset) || 0;
    renderOffset();
    if (S.offset) setPill(t("pillOffset", formatOffset(S.offset)), { hideAfter: 2400 });
  }

  function setOffset(value: number, announce = true) {
    if (!isSynced()) return;
    const next = nudgeOffset(value, 0);
    if (next === S.offset) return void renderOffset(true);
    S.offset = next;
    bg("offset-set", { key: S.offsetKey || pageKey(), offset: next });
    renderOffset(true);
    // Show the new line right away rather than at the next tick.
    S.idx = -2;
    if (announce) setPill(next ? t("pillOffset", formatOffset(next)) : t("pillOffsetReset"), { hideAfter: 1800 });
  }

  function renderOffset(pulse = false) {
    if (!UI.tpopOut) return;
    UI.tpopOut.textContent = t("offsetSeconds", formatOffset(S.offset));
    UI.tpopReset.disabled = !S.offset;
    UI.tpopNote.textContent = S.settings.dub ? t("timingDubFollows") : "";
    UI.tpopNote.hidden = !S.settings.dub;
    const tb = UI.tools.querySelector('[data-act="time"]');
    tb.classList.toggle("on", !!S.offset);
    if (pulse && !matchMedia("(prefers-reduced-motion: reduce)").matches) {
      UI.tpopOut.classList.remove("pulse");
      void UI.tpopOut.offsetWidth;
      UI.tpopOut.classList.add("pulse");
    }
  }

  function toggleTimingPop(open: boolean, refocus = false) {
    if (!UI.tpop) return;
    UI.tpop.hidden = !open;
    const tb = UI.tools.querySelector('[data-act="time"]');
    tb.setAttribute("aria-expanded", String(open));
    if (open) {
      renderOffset();
      showTools(true);
      UI.tpop.querySelector("button")?.focus({ preventScroll: true });
    } else {
      if (refocus) tb.focus({ preventScroll: true });
      showTools();
    }
  }

  /* ------------------------------------------------------------------ */
  /*  Lines: previous, next, repeat (keyboard and transcript)            */
  /* ------------------------------------------------------------------ */

  function seekToCue(i: number) {
    const v = currentVideo();
    const c = S.cues[i];
    if (!v || !c) return;
    v.currentTime = videoTimeFor(c.start, S.offset) + 0.01;
    S.idx = -2; // render it at the next tick even if it was the line shown
  }

  function stepTo(delta: -1 | 0 | 1) {
    const v = currentVideo();
    if (!v || !S.cues.length) return;
    const i = stepLine(S.cues, captionTime(v.currentTime, S.offset), delta);
    if (i < 0) return;
    seekToCue(i);
    if (v.paused && !lookupFor) v.play().catch(() => {});
  }

  /* ------------------------------------------------------------------ */
  /*  Keyboard shortcuts on the page                                      */
  /* ------------------------------------------------------------------ */

  function runShortcut(a: ShortcutAction) {
    switch (a) {
      case "prev":
        return stepTo(-1);
      case "next":
        return stepTo(1);
      case "repeat":
        return stepTo(0);
      case "subs":
        S.hidden = !S.hidden;
        applySettings();
        setPill(S.hidden ? t("pillSubsHidden") : t("pillSubsShown"), { hideAfter: 1400 });
        return;
      case "dub":
        saveSettings({ dub: !S.settings.dub });
        applyDubSetting();
        renderOffset();
        setPill(S.settings.dub ? t("pillDubOn") : t("pillDubOff"), { hideAfter: 1400 });
        return;
      case "transcript":
        saveSettings({ transcript: !S.settings.transcript });
        if (S.settings.transcript) setTimeout(() => transcript?.focus(), 50);
        return;
      case "earlier":
        return setOffset(nudgeOffset(S.offset, -0.25));
      case "later":
        return setOffset(nudgeOffset(S.offset, 0.25));
      case "resetTiming":
        return setOffset(0);
    }
  }

  function onKeyDown(e: KeyboardEvent) {
    if (!S.active) return;
    if (e.key === "Escape" && (lookupFor || (UI.tpop && !UI.tpop.hidden))) {
      e.stopImmediatePropagation();
      if (lookupFor) closeLookup(true);
      else toggleTimingPop(false);
      return;
    }
    if (!S.settings.keys || e.defaultPrevented) return;
    const action = shortcutFor(e);
    if (!action) return;
    // Not while typing: YouTube's search and comment boxes, or our own transcript search.
    const target = (e.composedPath()[0] || e.target) as HTMLElement;
    if (isTypingTarget(target)) return;
    const lineAction = action !== "subs" && action !== "dub";
    if (lineAction && !isSynced()) return;
    if (action === "dub" && S.mode === "live") return;
    // Ours, not the page's: Alt+← would otherwise go back in the browser history.
    e.preventDefault();
    e.stopImmediatePropagation();
    if (e.repeat && (action === "subs" || action === "dub" || action === "transcript")) return;
    runShortcut(action);
    showTools();
  }

  /* ------------------------------------------------------------------ */
  /*  Word lookup: click a word of the original (bilingual mode)          */
  /* ------------------------------------------------------------------ */

  let lookupFor: { word: string; sentence: string; sentenceTr: string; t: number; meaning: string; seq: number; paused: boolean } | null = null;
  let lookupSeq = 0;

  function onWordClick(e: MouseEvent) {
    const w = (e.target as HTMLElement).closest<HTMLElement>(".w");
    if (!w || !isSynced()) return;
    e.preventDefault();
    e.stopPropagation();
    openLookup(w);
  }

  async function openLookup(w: HTMLElement) {
    const word = w.dataset.w || w.textContent || "";
    if (!word) return;
    const i = S.idx;
    const c = S.cues[i];
    const v = currentVideo();
    const wasPlaying = !!v && !v.paused;
    // Keep the pause we made, if the user clicks another word while the card is open.
    const paused = lookupFor ? lookupFor.paused : wasPlaying;
    if (wasPlaying) v!.pause();
    const seq = ++lookupSeq;
    lookupFor = { word, sentence: c?.src || UI.src.dataset.text || "", sentenceTr: S.tr.get(i) || "", t: c ? c.start : v?.currentTime || 0, meaning: "", seq, paused };
    UI.src.querySelectorAll(".w.sel").forEach((x: Element) => x.classList.remove("sel"));
    w.classList.add("sel");

    UI.lkWord.textContent = word;
    UI.lkWord.lang = S.srcLang === "auto" ? "" : S.srcLang;
    UI.lkMean.textContent = "";
    UI.lkMean.className = "lk-mean";
    UI.lkMean.dir = langDir(S.settings.lang);
    UI.lkMean.innerHTML = '<span class="shimmer" aria-hidden="true"></span>';
    UI.lkMean.setAttribute("aria-busy", "true");
    UI.lkSent.textContent = "";
    for (const part of highlight(lookupFor.sentence, word)) {
      if (part.hit) {
        const m = document.createElement("mark");
        m.textContent = part.text;
        UI.lkSent.append(m);
      } else UI.lkSent.append(part.text);
    }
    UI.lkSent.hidden = !lookupFor.sentence;
    setSaveState("idle");
    const opening = UI.lk.hidden;
    UI.lk.hidden = false;
    placeLookup(w);
    if (opening) {
      lookupReturn = document.activeElement as HTMLElement | null;
      document.addEventListener("pointerdown", onOutside, true);
    }
    UI.lkSave.focus({ preventScroll: true });

    const sl = S.srcLang && S.srcLang !== "auto" ? S.srcLang : "auto";
    const r = await bg("translate", { texts: [word], sl, tl: S.settings.lang });
    if (!lookupFor || lookupFor.seq !== seq) return;
    UI.lkMean.removeAttribute("aria-busy");
    const meaning = (r && r.ok && r.map && r.map[word]) || "";
    lookupFor.meaning = meaning;
    UI.lkMean.textContent = meaning || (r && r.ok ? t("lookupNone") : errorText(r));
    UI.lkMean.classList.toggle("dim", !meaning);
    placeLookup(w);
  }

  let lookupReturn: HTMLElement | null = null;

  function placeLookup(w: HTMLElement) {
    if (!UI.lk || UI.lk.hidden) return;
    const r = w.isConnected ? w.getBoundingClientRect() : UI.src.getBoundingClientRect();
    const box = UI.lk.getBoundingClientRect();
    const gap = 10;
    // Above the word (the subtitles sit low on the video), or below when there is no room.
    let top = r.top - box.height - gap;
    if (top < 8) top = Math.min(innerHeight - box.height - 8, r.bottom + gap);
    const left = Math.max(8, Math.min(innerWidth - box.width - 8, r.left + r.width / 2 - box.width / 2));
    UI.lk.style.top = Math.max(8, Math.round(top)) + "px";
    UI.lk.style.left = Math.round(left) + "px";
  }

  function onOutside(e: Event) {
    if (!lookupFor || !UI.lk) return;
    const path = e.composedPath();
    if (path.includes(UI.lk)) return;
    // Another word: openLookup takes it from here.
    if (path.some((x) => x instanceof HTMLElement && x.classList?.contains("w") && UI.src.contains(x))) return;
    closeLookup(true);
  }

  /** Closes the card; `resume` plays the video again if the card paused it. */
  function closeLookup(resume: boolean) {
    document.removeEventListener("pointerdown", onOutside, true);
    const was = lookupFor;
    lookupFor = null;
    lookupSeq++;
    if (UI.lk) UI.lk.hidden = true;
    UI.src?.querySelectorAll(".w.sel").forEach((x: Element) => x.classList.remove("sel"));
    if (!was) return;
    if (resume && was.paused) {
      const v = currentVideo();
      if (v && v.paused) v.play().catch(() => {});
    }
    // Back where the user was, unless that was inside the card.
    if (lookupReturn && lookupReturn.isConnected && lookupReturn !== UI.host) lookupReturn.focus?.({ preventScroll: true });
    lookupReturn = null;
  }

  function setSaveState(st: "idle" | "saving" | "saved" | "duplicate" | "error") {
    if (!UI.lkSave) return;
    const label = UI.lkSave.querySelector("span");
    UI.lkSave.disabled = st === "saving" || st === "saved" || st === "duplicate";
    UI.lkSave.classList.toggle("done", st === "saved" || st === "duplicate");
    UI.lkSave.querySelector("svg").outerHTML = st === "saved" || st === "duplicate" ? ICONS.saved : ICONS.save;
    label.textContent = { idle: t("lookupSave"), saving: t("lookupSaving"), saved: t("lookupSaved"), duplicate: t("lookupDuplicate"), error: t("lookupSave") }[st];
    UI.lkState.textContent = st === "error" ? t("lookupSaveFailed") : "";
    UI.lkState.classList.toggle("err", st === "error");
  }

  async function saveLookup() {
    const it = lookupFor;
    if (!it) return;
    setSaveState("saving");
    const r = await bg("vocab-add", {
      item: { word: it.word, tr: it.meaning, sentence: it.sentence, sentenceTr: it.sentenceTr, videoId: S.mode === "youtube" ? S.videoId : "", title: S.title, t: it.t },
    });
    if (lookupFor !== it) return;
    setSaveState(r && r.ok ? (r.duplicate ? "duplicate" : "saved") : "error");
  }

  /* ------------------------------------------------------------------ */
  /*  The transcript beside the video                                     */
  /* ------------------------------------------------------------------ */

  let transcript: Transcript | null = null;

  function syncTranscript() {
    const want = S.active && isSynced() && S.settings.transcript;
    if (!want) {
      transcript?.destroy();
      transcript = null;
      return;
    }
    if (transcript) return;
    injectFonts();
    transcript = createTranscript({
      onSeek: (i) => {
        seekToCue(i);
        const v = currentVideo();
        if (v && v.paused && !lookupFor) v.play().catch(() => {});
      },
      onClose: () => saveSettings({ transcript: false }),
      player: () => document.querySelector("#movie_player") || currentVideo(),
    });
    transcript.place();
    transcript.setCues(S.cues, S.tr, S.srcLang, S.settings.lang);
    transcript.setTranslating(S.translatingGen === S.gen && S.translatingGen !== 0);
  }

  /* ------------------------------------------------------------------ */
  /*  Open the desktop app at this moment (YouTube videos)                */
  /* ------------------------------------------------------------------ */

  async function openInApp() {
    // The app opens YouTube links only; another site's video would need downloading first.
    const vid = S.active && S.mode === "youtube" ? S.videoId : window.top === window && isYouTube(location.href) ? ytVideoId(location.href) : "";
    if (!vid) return;
    const v = S.active ? currentVideo() : findVideo();
    const at = Math.floor(v?.currentTime || 0);
    // The app picks up from here; two players speaking at once would be confusing.
    v?.pause();
    const r = await bg("open-app-at", { videoId: vid, t: at });
    if (!r || !r.ok) setPill(errorText(r), { err: true, hideAfter: 4000 });
  }

  /* ------------------------------------------------------------------ */
  /*  The channel of the YouTube video (for auto-start)                   */
  /* ------------------------------------------------------------------ */

  function currentChannel(): Channel | null {
    if (!isYouTube(location.href)) return null;
    const vid = ytVideoId(location.href);
    const flexy = document.querySelector("ytd-watch-flexy");
    // YouTube swaps the page in place: until the watch page says it shows this video, its channel
    // link may still be the previous video's.
    if (!vid || !flexy || flexy.getAttribute("video-id") !== vid) return null;
    const a = flexy.querySelector<HTMLAnchorElement>("#owner ytd-channel-name a, ytd-video-owner-renderer ytd-channel-name a, #upload-info ytd-channel-name a");
    const id = channelFromHref(a?.getAttribute("href"));
    if (!id) return null;
    return { id, name: (a?.textContent || "").trim() || id };
  }

  async function waitForChannel(vid: string): Promise<Channel | null> {
    for (let k = 0; k < 30; k++) {
      if (ytVideoId(location.href) !== vid) return null;
      const c = currentChannel();
      if (c) return c;
      await sleep(300);
    }
    return null;
  }

  /* ------------------------------------------------------------------ */
  /*  Auto-start on YouTube (off unless chosen in the options)            */
  /* ------------------------------------------------------------------ */

  // The last video the translation was stopped on: it doesn't start again by itself.
  const STOPPED_KEY = "__tarjuman_stopped";
  const stoppedVideo = () => {
    try {
      return sessionStorage.getItem(STOPPED_KEY) || "";
    } catch {
      return "";
    }
  };
  const rememberStopped = (vid: string) => {
    try {
      if (vid) sessionStorage.setItem(STOPPED_KEY, vid);
    } catch {}
  };

  let autoChecking = "";

  async function maybeAutoStart() {
    if (window.top !== window || S.active || !isAutoStartPage(location.href)) return;
    const vid = ytVideoId(location.href);
    if (!vid || vid === stoppedVideo() || autoChecking === vid) return;
    autoChecking = vid;
    try {
      // A tab opened in the background waits until it is looked at.
      while (document.visibilityState !== "visible") {
        await new Promise((r) => document.addEventListener("visibilitychange", r, { once: true }));
        if (ytVideoId(location.href) !== vid) return;
      }
      const channel = await waitForChannel(vid);
      if (S.active || ytVideoId(location.href) !== vid) return;
      await bg("auto-start", { url: location.href, channel });
    } finally {
      if (autoChecking === vid) autoChecking = "";
    }
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

  /* Sites like Udemy and Coursera load their captions bit by bit as the video plays, and change lesson
     in the same player without a new page. The track is looked at again about once a second. */
  let capTrack: TextTrack | null = null;
  let capSrc = "";
  let capCount = 0;

  function checkCaptions() {
    const v = currentVideo();
    if (!v || !capTrack || S.loading) return;
    const src = v.currentSrc || "";
    if ((src && capSrc && src !== capSrc) || ![...v.textTracks].includes(capTrack)) {
      // Another lesson: the same language again if the new video has it.
      const lang = capTrack.language;
      const next = textTracks().find((x) => x.tr.language === lang) || textTracks()[0];
      capTrack = null;
      void activateCaptions(next ? next.i : undefined);
      return;
    }
    // The player switched the track off (or back on screen) when the lesson changed: hidden again.
    if (capTrack.mode !== "hidden") capTrack.mode = "hidden";
    const n = capTrack.cues ? capTrack.cues.length : 0;
    if (n === capCount) return;
    capCount = n;
    mergeCues(normalizeTrackCues((capTrack.cues || []) as unknown as ArrayLike<VTTCue>));
  }

  /** New cues for the same video: keeps the translations already made. */
  function mergeCues(cues: Cue[]) {
    if (!cues.length) return;
    const known = new Map<string, string>();
    S.cues.forEach((c, i) => {
      const tr = S.tr.get(i);
      if (tr) known.set(c.src, tr);
    });
    S.cues = cues;
    S.tr = new Map();
    S.tries = new Map();
    cues.forEach((c, i) => {
      const tr = known.get(c.src);
      if (tr) S.tr.set(i, tr);
    });
    S.idx = -2;
    transcript?.setCues(S.cues, S.tr, S.srcLang, S.settings.lang);
    if (S.translatingGen !== S.gen) translateLoop(S.srcLang, S.gen);
  }

  async function activateCaptions(index?: number) {
    const gen = ++S.gen;
    const all = textTracks();
    const entry = all.find((x) => x.i === index) || all[0];
    capTrack = null;
    capCount = 0;
    S.active = true;
    S.mode = "captions";
    S.trackIndex = entry ? entry.i : -1;
    S.cues = [];
    S.idx = -1;
    S.videoId = "";
    S.title = document.title || "";
    stopDub();
    closeLookup(false);
    ensureOverlay();
    UI.whisper.classList.remove("show");
    renderText("", "");
    loadOffset(gen);
    applySettings();
    if (!rafId) rafId = requestAnimationFrame(positionLoop);
    if (!entry) return setPill(t("pillNoSiteCaptions"), { err: true });
    setPill(t("pillReadingSiteCaptions"), { busy: true });
    S.loading = true;
    const cues = await loadTrackCues(entry.tr);
    if (gen !== S.gen || !S.active) return;
    S.loading = false;
    capTrack = entry.tr;
    capSrc = currentVideo()?.currentSrc || "";
    capCount = entry.tr.cues ? entry.tr.cues.length : 0;
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
      case "page-info": {
        // Answered by the frame that translates, or by the YouTube page itself (for auto-start).
        const yt = window.top === window && isYouTube(location.href);
        if (!S.active && !yt) return;
        const v = S.active ? currentVideo() : findVideo();
        return {
          ok: true,
          active: S.active,
          mode: S.mode,
          youtube: yt,
          videoId: yt ? ytVideoId(location.href) : "",
          time: v ? v.currentTime : 0,
          offset: S.offset,
          synced: S.active && isSynced(),
          channel: yt ? currentChannel() : null,
        };
      }
      case "page-cmd": {
        if (msg.cmd === "open-app") {
          if (window.top !== window || !ytVideoId(location.href) || !isYouTube(location.href)) return;
          void openInApp();
          return { ok: true };
        }
        if (!S.active || !isSynced()) return;
        if (msg.cmd === "nudge") setOffset(nudgeOffset(S.offset, Number(msg.delta) || 0));
        else if (msg.cmd === "reset-offset") setOffset(0);
        else if (msg.cmd === "focus-transcript") transcript?.focus();
        return { ok: true, offset: S.offset };
      }
      case "activate-youtube":
        if (msg.settings) S.settings = mergeSettings(S.settings, msg.settings);
        whenI18n(() => activateYouTube(msg.url || location.href));
        return { ok: true };
      case "probe-captions":
        return { ok: true, tracks: probeCaptions() };
      case "activate-captions":
        if (msg.settings) S.settings = mergeSettings(S.settings, msg.settings);
        whenI18n(() => activateCaptions(msg.index));
        return { ok: true };
      case "activate-live":
        if (msg.settings) S.settings = mergeSettings(S.settings, msg.settings);
        whenI18n(activateLive);
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
        renderOffset();
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
        else if (msg.status === "error") setPill(msg.message || msg.code ? replyError(msg, "pillLiveError") : t("pillLiveError"), { err: true, hideAfter: 4000 });
        return;
      default:
        return;
    }
  }

  // The interface language chosen in the options (the browser's otherwise). The overlay's texts are written
  // as it is built, so activations wait for this; otherwise they would come out in the browser's language.
  let i18nLoaded = false;
  const i18nReady = bg("i18n").then((r) => {
    if (r && r.ok && r.table) useTable(r.lang, r.table);
    i18nLoaded = true;
  });

  /** Runs an activation once the interface language is known; dropped if a stop or another activation came first. */
  function whenI18n(run: () => void) {
    if (i18nLoaded) return run();
    const gen = S.gen;
    i18nReady.then(() => gen === S.gen && run());
  }

  chrome.runtime.onMessage.addListener((msg, sender, respond) => {
    if (!msg || !msg.type || msg.target === "offscreen" || sender.id !== chrome.runtime.id) return;
    const res = handle(msg);
    if (res) respond(res);
  });

  function deactivate() {
    // Stopped on this video: it does not start again by itself (auto-start) until another one opens.
    if (S.mode === "youtube" && S.videoId) rememberStopped(S.videoId);
    closeLookup(false);
    restoreTracks();
    cancelWhisper();
    capTrack = null;
    S.gen++;
    S.active = false;
    S.loading = false;
    mirrorToVideo();
    S.video = null;
    S.mode = null;
    S.videoId = "";
    S.cues = [];
    S.offset = 0;
    S.offsetKey = "";
    stopSync();
    stopDub();
    transcript?.destroy();
    transcript = null;
    clearTimeout(S.liveTimer);
    if (rafId) cancelAnimationFrame(rafId);
    rafId = null;
    hideNativeCC(false);
    removeOverlay();
  }

  // YouTube is a single-page app: reload when the video changes.
  document.addEventListener("yt-navigate-finish", () => {
    S.video = null; // the new page may play in another <video> (Shorts, for one)
    // Off to the home page or a search with the video still playing in the miniplayer: carry on.
    if (S.active && S.mode === "youtube" && S.videoId && !ytVideoId(location.href) && miniplayerShowing()) return void transcript?.place();
    if (S.active && S.mode === "youtube") activateYouTube(location.href);
    else if (!S.active) void maybeAutoStart();
    transcript?.place();
  });

  document.addEventListener("fullscreenchange", () => {
    if (!UI.host) return;
    const target = overlayParent();
    if (UI.host.parentNode !== target) target.appendChild(UI.host);
    mirrorToVideo();
  });
  // Media events don't bubble, but a capturing listener on the document still hears them.
  document.addEventListener("volumechange", onVolumeChange, true);

  document.addEventListener("mousemove", onMouseMove, { passive: true });
  // Capture, on window: before the player sees the key (Alt+← would also go back in history).
  window.addEventListener("keydown", onKeyDown, true);
  window.addEventListener("resize", () => lookupFor && closeLookup(false));

  // After a reload or a new page in a tab that was translating, pick up where it left off.
  // Asked once the interface language is in, so the overlay is built in it.
  i18nReady
    .then(() => bg("content-ready", { url: location.href }))
    .then((r) => {
      if (r && r.ok && r.activate) handle(r.activate);
      else void maybeAutoStart();
    });
})();
