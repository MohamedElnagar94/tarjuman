/**
 * The transcript beside the video: every line in the translation and the original, the line being
 * said filled as it is spoken and kept in view, speaker turns and sound tags as marks, a search box,
 * and a way back to the current line after scrolling away. Clicking a line (or Enter on it) seeks there.
 *
 * Where it goes:
 *  - YouTube, two columns (normal and theater mode): at the top of the right column (#secondary).
 *  - YouTube, one column (a narrow window): right under the player, as a drawer that folds away.
 *  - Anywhere else (other sites, Shorts): a floating panel that can be dragged and folded.
 *
 * Plain DOM in its own shadow root, so neither the page's styles nor its keyboard shortcuts reach it.
 * destroy() removes everything it added (element, timers, window listeners).
 */
import { t, uiDir } from "@/shared/i18n";
import { langDir } from "@/shared/settings";
import type { Cue } from "@/shared/cues";
import { clock, highlight, pieces, speakers, startsTurn, type Piece, type SoundKind } from "@/shared/cueText";
import { icon } from "./overlay";

export interface TranscriptOptions {
  onSeek(i: number): void;
  onClose(): void;
  /** The player, to size the panel to it beside the video. */
  player(): Element | null;
}

export interface Transcript {
  setCues(cues: readonly Cue[], tr: ReadonlyMap<number, string>, srcLang: string, tl: string): void;
  updateTr(indices: readonly number[], tr: ReadonlyMap<number, string>): void;
  setTranslating(on: boolean): void;
  setCurrent(i: number, frac: number): void;
  place(): void;
  focus(): void;
  destroy(): void;
  readonly element: HTMLElement;
}

type Mode = "side" | "below" | "float";

const SOUND_ICON: Record<SoundKind, string> = {
  music: icon('<path d="M9 18V5l12-2v13"/><circle cx="6" cy="18" r="3"/><circle cx="18" cy="16" r="3"/>', 13),
  applause: icon('<path d="M7 11 4.5 8.5a1.6 1.6 0 0 1 2.3-2.3L11 10.5"/><path d="m9 8-1.5-1.5a1.6 1.6 0 0 1 2.3-2.3L15 9.5c2.5 2.5 2.5 6 0 8.5s-6 2.5-8.5 0L3.5 15a1.6 1.6 0 0 1 2.3-2.3L8 15"/><path d="M17 3.5 18 2M20 6.5l1.5-1M19.5 3.5l1-1"/>', 13),
  laughter: icon('<circle cx="12" cy="12" r="9"/><path d="M8 14s1.5 2.5 4 2.5 4-2.5 4-2.5"/><path d="M9 9.5h.01M15 9.5h.01"/>', 13),
  other: icon('<path d="M21 12a8 8 0 0 1-11.6 7.1L4 20.5l1.4-4.9A8 8 0 1 1 21 12Z"/><path d="M8.5 12h.01M12 12h.01M15.5 12h.01"/>', 13),
};
const I = {
  list: icon('<path d="M8 6h13M8 12h13M8 18h9"/><path d="M3.5 6h.01M3.5 12h.01M3.5 18h.01"/>', 16),
  search: icon('<circle cx="11" cy="11" r="7"/><path d="m20 20-3.5-3.5"/>', 15),
  close: icon('<path d="M18 6 6 18"/><path d="m6 6 12 12"/>', 16),
  fold: icon('<path d="m6 9 6 6 6-6"/>', 16),
  down: icon('<path d="M12 5v14"/><path d="m19 12-7 7-7-7"/>', 14),
  grip: icon('<path d="M9 6h.01M15 6h.01M9 12h.01M15 12h.01M9 18h.01M15 18h.01"/>', 14),
};

const CSS = `
  :host { all: initial; }
  * { box-sizing: border-box; }
  .shell { height: 100%; }
  .panel {
    position: relative; display: flex; flex-direction: column; height: 100%; min-height: 0; overflow: hidden;
    border-radius: 14px; color: #F5F2EA;
    background: linear-gradient(180deg, rgba(23,33,112,.97), rgba(13,19,66,.98));
    border: 1px solid rgba(255,255,255,.1);
    box-shadow: 0 10px 30px rgba(0,0,0,.28);
    font: 400 14px/1.5 "Tarjuman Sans", "IBM Plex Sans Arabic", "Segoe UI", Tahoma, sans-serif;
    -webkit-font-smoothing: antialiased;
    animation: enter .22s cubic-bezier(.2,.7,.2,1);
  }
  .float .panel { box-shadow: 0 18px 50px rgba(0,0,0,.5); }
  @keyframes enter { from { opacity: 0; transform: translateY(6px); } }
  .head { display: flex; align-items: center; gap: 8px; padding: 10px 10px 8px 14px; }
  .float .head { cursor: grab; touch-action: none; }
  .float.dragging .head { cursor: grabbing; }
  .title { display: flex; align-items: center; gap: 8px; flex: 1; min-width: 0; margin: 0; font-size: 14.5px; font-weight: 700; }
  .title svg { color: #FFD27A; flex: none; }
  .title .sub { color: #AEB6DE; font-weight: 500; font-size: 12px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
  .grip { color: #7F89C0; display: none; }
  .float .grip { display: inline-grid; }
  button.ic {
    display: grid; place-items: center; width: 32px; height: 32px; padding: 0; flex: none; border: 0; border-radius: 9px; cursor: pointer;
    background: transparent; color: #AEB6DE; transition: background .15s, color .15s, transform .2s;
  }
  button.ic:hover { background: rgba(255,255,255,.1); color: #fff; }
  .fold svg { transition: transform .2s cubic-bezier(.2,.7,.2,1); }
  .collapsed .fold svg { transform: rotate(-90deg); }
  [dir="rtl"] .collapsed .fold svg, .collapsed[dir="rtl"] .fold svg { transform: rotate(90deg); }
  .search {
    display: flex; align-items: center; gap: 6px; margin: 0 10px 8px; padding-inline: 10px 8px; min-height: 36px;
    border-radius: 10px; background: rgba(0,0,0,.22); border: 1px solid rgba(255,255,255,.09); color: #7F89C0;
    transition: border-color .15s;
  }
  .search:focus-within { border-color: rgba(255,210,122,.55); }
  .search input {
    flex: 1; min-width: 0; min-height: 34px; border: 0; outline: none; background: transparent; color: #F5F2EA;
    font: inherit; font-size: 13px;
  }
  .search input::placeholder { color: #7F89C0; }
  .search input::-webkit-search-cancel-button { filter: invert(1) opacity(.6); }
  .count { font-size: 11.5px; color: #AEB6DE; white-space: nowrap; font-variant-numeric: tabular-nums; }
  .collapsed .search, .collapsed .lines, .collapsed .now { display: none; }
  .lines {
    position: relative; flex: 1; min-height: 0; overflow-y: auto; padding: 2px 8px 10px; overscroll-behavior: contain;
    scrollbar-width: thin; scrollbar-color: rgba(255,255,255,.2) transparent; outline: none;
  }
  .empty { padding: 28px 16px; text-align: center; color: #AEB6DE; font-size: 13px; margin: 0; }
  .row {
    position: relative; display: grid; grid-template-columns: 46px minmax(0, 1fr); gap: 6px; align-items: start;
    padding: 7px 8px 9px 4px; border-radius: 10px; cursor: pointer; outline: none;
    border-inline-start: 3px solid transparent;
    transition: background-color .2s;
    content-visibility: auto; contain-intrinsic-size: auto 64px;
  }
  .row:hover { background: rgba(255,255,255,.06); }
  .row:focus-visible { box-shadow: 0 0 0 2px #FFD27A inset; }
  .row.on { background: rgba(255,210,122,.11); }
  .row.turn { margin-top: 8px; }
  .row.sp0 { border-inline-start-color: rgba(154,171,245,.5); }
  .row.sp1 { border-inline-start-color: rgba(255,210,122,.6); }
  /* The line being said: the saffron diamond of the mark, and a fill as it is spoken. */
  .row.on::before {
    content: ""; position: absolute; inset-inline-start: -7px; top: 14px; width: 7px; height: 7px; border-radius: 1px;
    transform: rotate(45deg); background: #FFD27A; animation: dia .25s cubic-bezier(.2,.7,.2,1);
  }
  @keyframes dia { from { transform: rotate(45deg) scale(0); } }
  .bar {
    position: absolute; inset-inline-start: 8px; bottom: 3px; height: 2px; border-radius: 2px;
    width: calc((100% - 16px) * var(--p, 0));
    background: linear-gradient(90deg, #F0922B, #FFD27A); transition: width .25s linear;
  }
  [dir="rtl"] .bar { background: linear-gradient(270deg, #F0922B, #FFD27A); }
  .tm {
    direction: ltr; unicode-bidi: isolate; justify-self: start; margin-top: 2px; padding: 1px 5px; border-radius: 6px;
    color: #7F89C0; font-size: 11.5px; font-variant-numeric: tabular-nums;
  }
  .row.on .tm { color: #FFD27A; }
  .tx { display: grid; gap: 2px; min-width: 0; }
  .tx p { margin: 0; overflow-wrap: anywhere; }
  .tr { font-size: 14.5px; line-height: 1.7; font-weight: 500; color: #F5F2EA; }
  .tr[dir="ltr"], .src[dir="ltr"] { text-align: left; }
  .tr[dir="rtl"], .src[dir="rtl"] { text-align: right; }
  .row:not(.on) .tr { color: #E4E2F0; }
  .tr.pending { color: #7F89C0; }
  .src { font-size: 12.5px; line-height: 1.55; color: #AEB6DE; }
  .row.on .src { color: #D6DDFB; }
  .snd {
    display: inline-grid; place-items: center; width: 22px; height: 18px; margin-inline: 2px; vertical-align: -3px;
    border-radius: 99px; background: rgba(255,255,255,.1); color: #AEB6DE;
  }
  .snd.music { color: #FFD27A; background: rgba(255,210,122,.14); }
  .row.on .snd.music svg { animation: bob 1.2s ease-in-out infinite; }
  @keyframes bob { 50% { transform: translateY(-2px); } }
  .dots { display: inline-flex; gap: 3px; vertical-align: middle; }
  .dots i { width: 5px; height: 5px; border-radius: 50%; background: #7F89C0; animation: blink 1.2s ease-in-out infinite; }
  .dots i:nth-child(2) { animation-delay: .2s; }
  .dots i:nth-child(3) { animation-delay: .4s; }
  @keyframes blink { 50% { opacity: .25; } }
  mark { background: rgba(255,210,122,.32); color: #fff; border-radius: 3px; padding: 0 1px; }
  .now {
    position: absolute; bottom: 12px; left: 50%; transform: translateX(-50%); z-index: 2;
    display: inline-flex; align-items: center; gap: 6px; min-height: 34px; padding: 0 14px; border: 0; border-radius: 99px; cursor: pointer;
    font-family: inherit; font-size: 12.5px; font-weight: 700; line-height: 1; color: #121A57; background: linear-gradient(180deg, #FFDC94, #FFC35C);
    box-shadow: 0 8px 22px rgba(0,0,0,.4); animation: rise .2s cubic-bezier(.2,.7,.2,1);
  }
  .now[hidden] { display: none; }
  @keyframes rise { from { opacity: 0; transform: translate(-50%, 10px); } }
  button:focus-visible { outline: 2px solid #FFD27A; outline-offset: 2px; }
  @media (prefers-reduced-motion: reduce) {
    .panel, .row.on::before, .now, .row.on .snd.music svg, .dots i { animation: none; }
    .bar, .row, .fold svg, button.ic { transition: none; }
  }
`;

const reduceMotion = () => matchMedia("(prefers-reduced-motion: reduce)").matches;

export function createTranscript(opts: TranscriptOptions): Transcript {
  const host = document.createElement("div");
  host.id = "__tarjuman_transcript";
  const shadow = host.attachShadow({ mode: "open" });
  const dir = uiDir();
  shadow.innerHTML = `<style>${CSS}</style>
    <div class="shell" dir="${dir}">
      <section class="panel" aria-labelledby="tj-title">
        <header class="head">
          <span class="grip" aria-hidden="true">${I.grip}</span>
          <h2 class="title" id="tj-title">${I.list}<span class="name"></span><span class="sub"></span></h2>
          <button type="button" class="ic fold" aria-expanded="true"></button>
          <button type="button" class="ic close"></button>
        </header>
        <label class="search">${I.search}<input type="search" autocomplete="off" spellcheck="false" /><output class="count"></output></label>
        <div class="lines" role="list"></div>
        <button type="button" class="now" hidden>${I.down}<span></span></button>
      </section>
    </div>`;
  const $ = <T extends Element>(sel: string) => shadow.querySelector(sel) as T;
  const shell = $<HTMLElement>(".shell");
  const lines = $<HTMLElement>(".lines");
  const input = $<HTMLInputElement>(".search input");
  const count = $<HTMLOutputElement>(".count");
  const nowBtn = $<HTMLButtonElement>(".now");
  const foldBtn = $<HTMLButtonElement>(".fold");
  const closeBtn = $<HTMLButtonElement>(".close");
  const sub = $<HTMLElement>(".title .sub");
  $<HTMLElement>(".title .name").textContent = t("trTitle");
  input.placeholder = t("trSearch");
  input.setAttribute("aria-label", t("trSearch"));
  nowBtn.querySelector("span")!.textContent = t("trBackToNow");
  closeBtn.innerHTML = I.close;
  closeBtn.title = t("trClose");
  closeBtn.setAttribute("aria-label", t("trClose"));
  foldBtn.innerHTML = I.fold;
  foldBtn.title = t("trFold");
  foldBtn.setAttribute("aria-label", t("trFold"));
  lines.setAttribute("aria-label", t("trTitle"));

  let cues: readonly Cue[] = [];
  let trMap: ReadonlyMap<number, string> = new Map();
  let srcLang = "auto";
  let tl = "ar";
  let rows: HTMLElement[] = [];
  let low: { src: string; tr: string }[] = [];
  let cur = -1;
  let needle = "";
  let marked = new Set<number>();
  let away = false;
  let ours = false;
  let oursTimer: ReturnType<typeof setTimeout> | undefined;
  let searchTimer: ReturnType<typeof setTimeout> | undefined;
  let mode: Mode | null = null;
  let collapsed = false;
  let focusRow = -1;
  let translating = false;
  const bar = document.createElement("i");
  bar.className = "bar";
  bar.setAttribute("aria-hidden", "true");

  /* ---------- rows ---------- */

  function appendPieces(el: HTMLElement, list: Piece[]) {
    for (const p of list) {
      if (p.kind === "text") el.append(p.text);
      else {
        const s = document.createElement("span");
        s.className = "snd " + p.sound;
        s.title = p.label;
        s.setAttribute("role", "img");
        s.setAttribute("aria-label", p.label);
        s.innerHTML = SOUND_ICON[p.sound];
        el.append(s);
      }
    }
  }

  function appendMarked(el: HTMLElement, text: string) {
    for (const part of highlight(text, needle)) {
      if (part.hit) {
        const m = document.createElement("mark");
        m.textContent = part.text;
        el.append(m);
      } else el.append(part.text);
    }
  }

  function fillTr(i: number) {
    const p = rows[i]?.querySelector<HTMLElement>(".tr");
    if (!p) return;
    const text = trMap.get(i) || "";
    p.textContent = "";
    p.classList.toggle("pending", !text);
    if (!text) {
      if (translating) p.innerHTML = '<span class="dots" aria-hidden="true"><i></i><i></i><i></i></span>';
      return;
    }
    if (needle && marked.has(i)) appendMarked(p, text);
    else appendPieces(p, pieces(text));
  }

  function fillSrc(i: number) {
    const p = rows[i]?.querySelector<HTMLElement>(".src");
    if (!p) return;
    p.textContent = "";
    const text = cues[i]?.src || "";
    if (needle && marked.has(i)) appendMarked(p, text);
    else appendPieces(p, pieces(text));
  }

  function build() {
    lines.textContent = "";
    rows = [];
    low = [];
    cur = -1;
    focusRow = -1;
    marked = new Set();
    if (!cues.length) {
      const p = document.createElement("p");
      p.className = "empty";
      p.textContent = t("trEmpty");
      lines.append(p);
      sub.textContent = "";
      return;
    }
    const who = cues.some((c) => startsTurn(c.src)) ? speakers(cues.map((c) => c.src)) : null;
    const trDir = langDir(tl);
    const frag = document.createDocumentFragment();
    cues.forEach((c, i) => {
      const row = document.createElement("div");
      row.className = "row";
      if (i > 0 && startsTurn(c.src)) row.classList.add("turn");
      if (who) row.classList.add("sp" + who[i]);
      row.dataset.i = String(i);
      row.setAttribute("role", "listitem");
      row.tabIndex = -1;
      const tm = document.createElement("span");
      tm.className = "tm";
      tm.textContent = clock(c.start);
      const tx = document.createElement("div");
      tx.className = "tx";
      const tr = document.createElement("p");
      tr.className = "tr";
      tr.dir = trDir;
      tr.lang = tl;
      const src = document.createElement("p");
      src.className = "src";
      src.dir = srcLang === "auto" ? "auto" : langDir(srcLang);
      if (srcLang !== "auto") src.lang = srcLang;
      tx.append(tr, src);
      row.append(tm, tx);
      frag.append(row);
      rows.push(row);
      low.push({ src: c.src.toLowerCase(), tr: (trMap.get(i) || "").toLowerCase() });
    });
    lines.append(frag);
    rows.forEach((_, i) => {
      fillTr(i);
      fillSrc(i);
    });
    setFocusRow(0);
    sub.textContent = "· " + t("trLines", String(cues.length));
    if (needle) runSearch();
  }

  /* ---------- following the video ---------- */

  function scrollToRow(i: number, smooth = true) {
    const el = rows[i];
    if (!el || collapsed) return;
    const top = el.offsetTop - lines.clientHeight / 3;
    if (Math.abs(lines.scrollTop - top) < 30) return;
    ours = true;
    clearTimeout(oursTimer);
    oursTimer = setTimeout(() => (ours = false), 900);
    // The list scrolls, never the page around it.
    lines.scrollTo({ top: Math.max(0, top), behavior: smooth && !reduceMotion() ? "smooth" : "auto" });
  }

  function updateAway() {
    if (cur < 0 || !rows[cur] || needle || collapsed) {
      away = false;
    } else {
      const r = rows[cur].getBoundingClientRect();
      const v = lines.getBoundingClientRect();
      away = r.bottom < v.top + 8 || r.top > v.bottom - 8;
    }
    nowBtn.hidden = !away;
  }

  function onScroll() {
    if (ours) return;
    updateAway();
  }

  function backToNow() {
    away = false;
    nowBtn.hidden = true;
    scrollToRow(cur);
  }

  function setCurrent(i: number, frac: number) {
    if (i !== cur) {
      rows[cur]?.classList.remove("on");
      rows[cur]?.removeAttribute("aria-current");
      cur = i;
      const row = rows[i];
      if (row) {
        row.classList.add("on");
        row.setAttribute("aria-current", "true");
        row.append(bar);
        bar.style.transition = "none";
        bar.style.setProperty("--p", "0");
        void bar.offsetWidth; // the fill starts from empty on a new line
        bar.style.transition = "";
        // Keyboard focus follows the line being said, unless the user is moving through the list.
        if (!shadow.activeElement || !lines.contains(shadow.activeElement)) setFocusRow(i);
        if (!away && !needle) scrollToRow(i);
      } else bar.remove();
      if (away) updateAway();
    }
    if (rows[i]) bar.style.setProperty("--p", String(frac));
  }

  /* ---------- search ---------- */

  function runSearch() {
    const prev = marked;
    marked = new Set();
    let n = 0;
    rows.forEach((row, i) => {
      const hit = !needle || low[i].src.includes(needle) || low[i].tr.includes(needle);
      row.hidden = !hit;
      if (needle && hit) {
        marked.add(i);
        n++;
      }
    });
    for (const i of new Set([...prev, ...marked])) {
      fillTr(i);
      fillSrc(i);
    }
    count.textContent = needle ? t("trMatches", String(n)) : "";
    let empty = lines.querySelector<HTMLElement>(".empty.nomatch");
    if (needle && !n) {
      if (!empty) {
        empty = document.createElement("p");
        empty.className = "empty nomatch";
        lines.prepend(empty);
      }
      empty.textContent = t("trNoMatch", input.value.trim());
    } else empty?.remove();
    if (!needle) {
      updateAway();
      scrollToRow(cur, false);
    } else {
      nowBtn.hidden = true;
      lines.scrollTop = 0;
    }
  }

  function onInput() {
    clearTimeout(searchTimer);
    searchTimer = setTimeout(() => {
      needle = input.value.trim().toLowerCase();
      runSearch();
    }, 140);
  }

  /* ---------- keyboard and clicks ---------- */

  function setFocusRow(i: number) {
    if (rows[focusRow]) rows[focusRow].tabIndex = -1;
    focusRow = i;
    if (rows[i]) rows[i].tabIndex = 0;
  }

  function visibleRow(from: number, step: 1 | -1): number {
    for (let i = from; i >= 0 && i < rows.length; i += step) if (!rows[i].hidden) return i;
    return -1;
  }

  function onListKey(e: KeyboardEvent) {
    const row = (e.target as HTMLElement).closest<HTMLElement>(".row");
    const i = row ? Number(row.dataset.i) : -1;
    let to = -1;
    if (e.key === "ArrowDown") to = visibleRow(i + 1, 1);
    else if (e.key === "ArrowUp") to = visibleRow(i - 1, -1);
    else if (e.key === "Home") to = visibleRow(0, 1);
    else if (e.key === "End") to = visibleRow(rows.length - 1, -1);
    else if ((e.key === "Enter" || e.key === " ") && i >= 0) {
      e.preventDefault();
      seek(i);
      return;
    } else return;
    e.preventDefault();
    if (to < 0) return;
    setFocusRow(to);
    rows[to].focus({ preventScroll: true });
    // Into view within the list only (scrollIntoView would scroll the page too).
    const el = rows[to];
    if (el.offsetTop < lines.scrollTop) lines.scrollTop = el.offsetTop - 8;
    else if (el.offsetTop + el.offsetHeight > lines.scrollTop + lines.clientHeight) lines.scrollTop = el.offsetTop + el.offsetHeight - lines.clientHeight + 8;
  }

  function seek(i: number) {
    away = false;
    nowBtn.hidden = true;
    setFocusRow(i);
    opts.onSeek(i);
  }

  function onListClick(e: MouseEvent) {
    const row = (e.target as HTMLElement).closest<HTMLElement>(".row");
    if (!row) return;
    // Selecting text to copy it is not a click on the line.
    if (String(getSelection?.() || "").length > 0 && shadow.contains(e.target as Node)) return;
    seek(Number(row.dataset.i));
  }

  function setCollapsed(on: boolean) {
    collapsed = on;
    shell.classList.toggle("collapsed", on);
    foldBtn.setAttribute("aria-expanded", String(!on));
    foldBtn.title = on ? t("trUnfold") : t("trFold");
    foldBtn.setAttribute("aria-label", foldBtn.title);
    size();
    if (!on) setTimeout(() => scrollToRow(cur, false), 0);
  }

  // The page's own shortcuts (YouTube's k, j, l, arrows…) must not fire while typing or moving in here.
  for (const type of ["keydown", "keyup", "keypress"]) shadow.addEventListener(type, (e) => e.stopPropagation());
  input.addEventListener("input", onInput);
  input.addEventListener("keydown", (e) => {
    if (e.key === "Escape" && input.value) {
      input.value = "";
      onInput();
    }
  });
  lines.addEventListener("scroll", onScroll, { passive: true });
  lines.addEventListener("click", onListClick);
  lines.addEventListener("keydown", onListKey);
  lines.addEventListener("focusin", (e) => {
    const row = (e.target as HTMLElement).closest<HTMLElement>(".row");
    if (row) setFocusRow(Number(row.dataset.i));
  });
  nowBtn.addEventListener("click", backToNow);
  closeBtn.addEventListener("click", () => opts.onClose());
  foldBtn.addEventListener("click", () => setCollapsed(!collapsed));

  /* ---------- where it goes, and its size ---------- */

  function target(): { mode: Mode; parent: Element } {
    if (/(^|\.)youtube\.com$/.test(location.hostname) && location.pathname === "/watch") {
      const flexy = document.querySelector("ytd-watch-flexy");
      if (flexy && !flexy.hasAttribute("hidden")) {
        if (flexy.hasAttribute("is-two-columns_")) {
          const side = flexy.querySelector("#secondary-inner") || flexy.querySelector("#secondary");
          if (side) return { mode: "side", parent: side };
        } else {
          const below = flexy.querySelector("#below");
          if (below) return { mode: "below", parent: below };
        }
      }
    }
    const fs = document.fullscreenElement;
    return { mode: "float", parent: fs && fs.tagName !== "VIDEO" ? fs : document.documentElement };
  }

  let floatPos: { x: number; y: number } | null = null;

  function size() {
    const st = host.style;
    if (mode === "float") {
      const w = Math.min(380, innerWidth - 24);
      const h = collapsed ? 0 : Math.min(560, Math.round(innerHeight * 0.7));
      if (!floatPos) {
        // Beside the video when there is room (the side with more of it), otherwise at the reading end.
        const v = opts.player()?.getBoundingClientRect();
        const right = v ? innerWidth - v.right : 0;
        const left = v ? v.left : 0;
        let x = dir === "rtl" ? 16 : innerWidth - w - 16;
        if (v && Math.max(left, right) >= w + 24) x = right >= left ? innerWidth - w - 16 : 16;
        floatPos = { x, y: v && v.top > 8 && v.top < innerHeight / 2 ? Math.round(v.top) : 80 };
      }
      floatPos.x = Math.max(8, Math.min(innerWidth - w - 8, floatPos.x));
      floatPos.y = Math.max(8, Math.min(innerHeight - 60, floatPos.y));
      st.cssText = `position:fixed;z-index:2147483646;left:${floatPos.x}px;top:${floatPos.y}px;width:${w}px;${collapsed ? "" : `height:${h}px;`}`;
      return;
    }
    let h: number;
    if (mode === "side") {
      // Beside the video: as tall as the player. In theater mode the column starts under the player.
      const theater = !!document.querySelector("ytd-watch-flexy[theater], ytd-watch-flexy[full-bleed-player]");
      const p = opts.player()?.getBoundingClientRect();
      h = theater || !p || p.height < 200 ? Math.round(innerHeight * 0.62) : Math.round(p.height);
      h = Math.max(320, Math.min(h, innerHeight - 90));
    } else {
      h = Math.max(260, Math.min(460, Math.round(innerHeight * 0.5)));
    }
    st.cssText = `display:block;position:relative;width:100%;margin:${mode === "below" ? "12px 0 16px" : "0 0 16px"};${collapsed ? "" : `height:${h}px;`}`;
  }

  function place() {
    const want = target();
    if (want.mode !== mode) {
      mode = want.mode;
      shell.classList.toggle("float", mode === "float");
    }
    if (host.parentNode !== want.parent) {
      if (mode === "float") want.parent.appendChild(host);
      else want.parent.insertBefore(host, want.parent.firstChild);
    }
    size();
  }

  // Dragging the floating panel by its header.
  let drag: { id: number; dx: number; dy: number } | null = null;
  const head = $<HTMLElement>(".head");
  head.addEventListener("pointerdown", (e) => {
    if (mode !== "float" || e.button !== 0 || (e.target as HTMLElement).closest("button")) return;
    const r = host.getBoundingClientRect();
    drag = { id: e.pointerId, dx: e.clientX - r.left, dy: e.clientY - r.top };
    head.setPointerCapture(e.pointerId);
    shell.classList.add("dragging");
    e.preventDefault();
  });
  head.addEventListener("pointermove", (e) => {
    if (!drag || e.pointerId !== drag.id) return;
    floatPos = { x: e.clientX - drag.dx, y: e.clientY - drag.dy };
    size();
  });
  const endDrag = (e: PointerEvent) => {
    if (!drag || e.pointerId !== drag.id) return;
    drag = null;
    shell.classList.remove("dragging");
  };
  head.addEventListener("pointerup", endDrag);
  head.addEventListener("pointercancel", endDrag);
  head.addEventListener("dblclick", (e) => {
    if (mode === "float" && !(e.target as HTMLElement).closest("button")) setCollapsed(!collapsed);
  });

  // YouTube moves its columns around (theater mode, window width, navigation): check where we belong.
  const onResize = () => place();
  window.addEventListener("resize", onResize);
  document.addEventListener("fullscreenchange", onResize);
  const placeTimer = setInterval(place, 1000);

  return {
    element: host,
    setCues(list, tr, sl, target) {
      cues = list;
      trMap = tr;
      srcLang = sl || "auto";
      tl = target;
      build();
    },
    updateTr(indices, tr) {
      trMap = tr;
      for (const i of indices) {
        if (!rows[i]) continue;
        low[i].tr = (tr.get(i) || "").toLowerCase();
        fillTr(i);
      }
      if (needle) runSearch();
    },
    setTranslating(on) {
      if (on === translating) return;
      translating = on;
      rows.forEach((_, i) => !trMap.get(i) && fillTr(i));
    },
    setCurrent,
    place,
    focus() {
      if (collapsed) setCollapsed(false);
      (rows[cur] || rows[focusRow] || input).focus({ preventScroll: true });
    },
    destroy() {
      clearInterval(placeTimer);
      clearTimeout(oursTimer);
      clearTimeout(searchTimer);
      window.removeEventListener("resize", onResize);
      document.removeEventListener("fullscreenchange", onResize);
      host.remove();
    },
  };
}
