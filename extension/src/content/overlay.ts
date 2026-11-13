/** The overlay's markup and styles. Everything lives in a shadow root so the page can't restyle it. */
import { t, uiDir } from "@/shared/i18n";
import { RANGES, extraFontFaces } from "@/shared/fonts";
import { OFFSET_STEPS } from "@/shared/timing";
import { SHORTCUT_KEYS, withKeys, type ShortcutAction } from "@/shared/shortcuts";


/**
 * @font-face has no effect inside a shadow root, so the subtitle font is declared
 * on the page under a name no site uses. Extension URLs aren't subject to the page's CSP.
 */
export function injectFonts() {
  const id = "__tarjuman_fonts";
  if (document.getElementById(id)) return;
  const faces: string[] = [];
  for (const [subset, range] of Object.entries(RANGES)) {
    for (const w of [500, 700]) {
      const url = chrome.runtime.getURL(`fonts/ibm-plex-sans-arabic-${subset}-${w}-normal.woff2`);
      faces.push(`@font-face{font-family:"Tarjuman Sans";font-style:normal;font-weight:${w};font-display:swap;src:url("${url}") format("woff2");unicode-range:${range};}`);
    }
  }
  faces.push(extraFontFaces((f) => chrome.runtime.getURL(`fonts/${f}`))); // downloaded only when chosen
  const st = document.createElement("style");
  st.id = id;
  st.textContent = faces.join("\n");
  (document.head || document.documentElement).appendChild(st);
}

export const icon = (paths: string, size = 18) =>
  `<svg viewBox="0 0 24 24" width="${size}" height="${size}" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">${paths}</svg>`;

export const ICONS = {
  subs: icon('<rect x="3" y="5" width="18" height="14" rx="3"/><path d="M7 15h4M15 15h2M7 11h2M13 11h4"/>'),
  bi: icon('<path d="m5 8 6 6"/><path d="m4 14 6-6 2-3"/><path d="M2 5h12"/><path d="M7 2h1"/><path d="m22 22-5-10-5 10"/><path d="M14 18h6"/>'),
  minus: icon('<path d="M3 18 8 6l5 12M4.8 14h6.4"/><path d="M16 12h6"/>'),
  plus: icon('<path d="M3 18 8 6l5 12M4.8 14h6.4"/><path d="M16 12h6M19 9v6"/>'),
  pos: icon('<path d="m21 16-4 4-4-4"/><path d="M17 20V4"/><path d="m3 8 4-4 4 4"/><path d="M7 4v16"/>'),
  dub: icon('<path d="M2 10v3"/><path d="M6 6v11"/><path d="M10 3v18"/><path d="M14 8v7"/><path d="M18 5v13"/><path d="M22 10v3"/>'),
  stop: icon('<path d="M18 6 6 18"/><path d="m6 6 12 12"/>'),
  time: icon('<circle cx="12" cy="13" r="8"/><path d="M12 9v4l2.5 1.5"/><path d="M9 2h6"/>'),
  list: icon('<path d="M8 6h13M8 12h13M8 18h9"/><path d="M3.5 6h.01M3.5 12h.01M3.5 18h.01"/>'),
  app: icon('<rect x="3" y="4" width="18" height="13" rx="2.5"/><path d="M8 21h8M12 17v4"/><path d="m10 8.5 4 2-4 2z"/>'),
  close: icon('<path d="M18 6 6 18"/><path d="m6 6 12 12"/>', 16),
  save: icon('<path d="M6 3h12v18l-6-4-6 4z"/>', 16),
  saved: icon('<path d="M6 3h12v18l-6-4-6 4z" fill="currentColor"/>', 16),
};

const MARK = `<svg viewBox="0 0 128 128" width="22" height="22" aria-hidden="true"><defs><linearGradient id="tj-t" x1=".15" y1="0" x2=".85" y2="1"><stop offset="0" stop-color="#3550D6"/><stop offset="1" stop-color="#121A57"/></linearGradient><linearGradient id="tj-i" x1="1" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#FFD27A"/><stop offset="1" stop-color="#F0922B"/></linearGradient></defs><rect x="4" y="4" width="120" height="120" rx="30" fill="url(#tj-t)"/><path d="M27 24 L49 37 L27 50 Z" fill="#fff" stroke="#fff" stroke-width="6" stroke-linejoin="round"/><path d="M104 46 C110 52,108 76,96 88 C86 98,72 102,58 101 C40 100,26 92,19 76 C30 84,44 88,58 88 C74 88,87 82,93 70 C97 62,97 54,95 50 Z" fill="url(#tj-i)"/><rect x="50" y="52" width="14" height="14" rx="2.5" transform="rotate(45 57 59)" fill="#FFD27A"/><rect x="69" y="45" width="14" height="14" rx="2.5" transform="rotate(45 76 52)" fill="#fff"/></svg>`;

export const CSS = `
  :host { all: initial; }
  * { box-sizing: border-box; }
  .wrap {
    position: fixed; display: flex; flex-direction: column; align-items: center;
    pointer-events: none; padding: 0 4%;
    font-family: var(--sub-font, "Tarjuman Sans", "IBM Plex Sans Arabic", "Segoe UI", "Noto Sans Arabic", Tahoma, Arial, sans-serif);
    -webkit-font-smoothing: antialiased;
  }
  .wrap.bottom { justify-content: flex-end; }
  .wrap.top { justify-content: flex-start; }

  /* Status pill */
  .pill {
    display: flex; gap: 9px; align-items: center; margin: 10px 0; max-width: 92%;
    background: rgba(13,19,66,.94); border: 1px solid rgba(255,210,122,.38);
    border-radius: 999px; padding: 7px 16px 7px 14px;
    color: #F5F2EA; font-size: 13.5px; font-weight: 500; line-height: 1.35;
    box-shadow: 0 10px 30px rgba(0,0,0,.45);
    transition: opacity .25s, transform .25s;
  }
  .pill.hide { opacity: 0; transform: translateY(4px); }
  .pill .dot { width: 8px; height: 8px; border-radius: 50%; background: #FFD27A; flex: none; box-shadow: 0 0 0 3px rgba(255,210,122,.18); }
  .pill.busy .dot { animation: pulse 1.1s ease-in-out infinite; }
  .pill.err { border-color: rgba(255,138,128,.6); }
  .pill.err .dot { background: #FF8A80; box-shadow: 0 0 0 3px rgba(255,138,128,.2); }
  @keyframes pulse { 50% { opacity: .25; } }

  /* Subtitles: readability first. A dark plate (user opacity) plus an outline
     shadow, so the text stays legible on bright video even with no plate. */
  .subs { width: 100%; text-align: center; transition: opacity .15s; }
  .subs.off { opacity: 0; }
  .line { margin: .1em 0; }
  .line > span {
    display: inline; color: #FFFFFF; line-height: 1.5;
    background: rgba(8,10,30,var(--bgo,.78));
    padding: .08em .48em .12em; border-radius: .3em;
    -webkit-box-decoration-break: clone; box-decoration-break: clone;
    text-shadow: 0 0 2px rgba(0,0,0,.95), 0 1px 3px rgba(0,0,0,.9), 0 0 12px rgba(0,0,0,.35);
  }
  .tr { font-weight: 700; letter-spacing: 0; }
  .tr.pending span { color: #D3D6EC; font-weight: 500; }
  .src { font-size: .62em; font-weight: 500; }
  .src > span { color: #ECE8DA; }
  .line:empty, .line > span:empty { display: none; }
  /* The original's words can be clicked for their meaning (bilingual mode). */
  .src .w {
    pointer-events: auto; cursor: pointer; border-radius: .22em; padding: 0 .04em;
    transition: background-color .12s, box-shadow .12s;
  }
  .src .w:hover { background: rgba(255,210,122,.26); color: #fff; }
  .src .w.sel { background: rgba(255,210,122,.38); color: #fff; box-shadow: 0 .09em 0 #FFD27A; }

  /* Whisper offer */
  .whisper {
    pointer-events: auto; margin: 10px 0; display: none; flex-direction: column; align-items: center; gap: 10px;
    padding: 14px 16px; border-radius: 16px; background: rgba(13,19,66,.94); border: 1px solid rgba(255,210,122,.3);
    box-shadow: 0 12px 34px rgba(0,0,0,.45);
  }
  .whisper.show { display: flex; }
  button.go {
    border: 0; border-radius: 11px; padding: 10px 20px; cursor: pointer; min-height: 40px;
    font-family: inherit; font-size: 14px; font-weight: 700; color: #121A57;
    background: linear-gradient(180deg, #FFDC94, #FFC35C); box-shadow: 0 1px 0 rgba(255,255,255,.5) inset, 0 6px 18px rgba(240,146,43,.3);
  }
  button.go:hover { filter: brightness(1.05); }
  button.go:disabled { opacity: .65; cursor: progress; }
  button.go:focus-visible { outline: 2px solid #fff; outline-offset: 2px; }
  .meter { width: 220px; height: 5px; border-radius: 99px; background: rgba(255,255,255,.16); overflow: hidden; }
  .meter > i { display: block; height: 100%; width: 0; background: linear-gradient(90deg, #F0922B, #FFD27A); transition: width .3s; }

  /* Toolbar */
  .tools {
    position: fixed; display: flex; align-items: center; gap: 2px; padding: 4px;
    background: rgba(13,19,66,.88); border: 1px solid rgba(255,255,255,.12); border-radius: 14px;
    -webkit-backdrop-filter: blur(12px) saturate(1.2); backdrop-filter: blur(12px) saturate(1.2);
    box-shadow: 0 10px 30px rgba(0,0,0,.4);
    font-family: "Tarjuman Sans", "Segoe UI", Tahoma, sans-serif;
    pointer-events: auto; opacity: 0; transform: translateY(-4px);
    transition: opacity .18s, transform .18s, visibility .18s; visibility: hidden;
  }
  .tools.show { opacity: 1; transform: none; visibility: visible; }
  .tools .mark { display: grid; place-items: center; width: 30px; height: 32px; }
  .tools button {
    display: grid; place-items: center; width: 34px; height: 32px; padding: 0; border: 0; border-radius: 9px; cursor: pointer;
    background: transparent; color: #E8E6F2; transition: background .15s, color .15s;
  }
  .tools button:hover { background: rgba(255,255,255,.1); color: #fff; }
  .tools button:focus-visible { outline: 2px solid #FFD27A; outline-offset: 1px; }
  .tools button.on { color: #FFD27A; background: rgba(255,210,122,.13); }
  .tools button.danger:hover { background: rgba(255,138,128,.16); color: #FFB4AC; }
  .tools .sep { width: 1px; height: 18px; margin: 0 3px; background: rgba(255,255,255,.14); }
  .tools button[hidden], .tools .sep[hidden] { display: none; }
  /* A shifted timing shows as a dot on its button. */
  .tools button[data-act="time"] { position: relative; }
  .tools button[data-act="time"].on::after {
    content: ""; position: absolute; top: 5px; inset-inline-end: 6px; width: 6px; height: 6px; border-radius: 50%;
    background: #FFD27A; box-shadow: 0 0 0 2px rgba(13,19,66,.9);
  }

  /* Subtitle timing, under the toolbar */
  .tpop {
    position: absolute; top: calc(100% + 8px); inset-inline-end: 0; width: 292px; padding: 12px;
    display: grid; gap: 10px; border-radius: 14px; color: #F5F2EA; font-size: 13px; line-height: 1.4;
    background: rgba(13,19,66,.96); border: 1px solid rgba(255,255,255,.12); box-shadow: 0 14px 36px rgba(0,0,0,.45);
    transform-origin: top right; animation: popIn .16s cubic-bezier(.2,.7,.2,1);
  }
  .tpop[dir="rtl"] { transform-origin: top left; }
  .tpop[hidden] { display: none; }
  .tpop .head { display: flex; align-items: baseline; justify-content: space-between; gap: 8px; }
  .tpop .head strong { font-weight: 700; font-size: 13.5px; }
  .tpop output {
    direction: ltr; unicode-bidi: isolate; font-variant-numeric: tabular-nums; font-weight: 700; color: #FFD27A;
    padding: 2px 8px; border-radius: 99px; background: rgba(255,210,122,.12);
  }
  .tpop output.pulse { animation: bump .28s cubic-bezier(.2,.7,.2,1); }
  .tpop .steps { display: grid; grid-template-columns: repeat(4, 1fr); gap: 4px; direction: ltr; }
  .tools .tpop .steps button, .tools .tpop button.reset {
    width: auto; height: 34px; padding: 0 8px; border-radius: 9px; font-family: inherit; font-size: 12.5px; font-weight: 600; line-height: 1; white-space: nowrap;
    color: #E8E6F2; background: rgba(255,255,255,.07); border: 1px solid rgba(255,255,255,.08);
    font-variant-numeric: tabular-nums;
  }
  .tools .tpop .steps button:hover, .tools .tpop button.reset:hover:not(:disabled) { background: rgba(255,255,255,.14); color: #fff; }
  .tools .tpop button.reset:disabled { opacity: .45; cursor: default; }
  .tpop .scale { display: flex; justify-content: space-between; font-size: 11.5px; color: #AEB6DE; direction: ltr; margin-top: -4px; }
  .tpop .scale span { display: inline-flex; align-items: center; gap: 4px; }
  .tpop .foot { display: flex; align-items: center; justify-content: space-between; gap: 8px; }
  .tpop .foot small { color: #AEB6DE; font-size: 11.5px; display: inline-flex; gap: 4px; direction: ltr; }
  .tpop i { font-style: normal; }
  .tpop .note { margin: 0; font-size: 11.5px; color: #AEB6DE; }
  .tpop kbd {
    direction: ltr; unicode-bidi: isolate; font-family: inherit; font-size: 10.5px; font-weight: 600; line-height: 1; padding: 3px 5px; border-radius: 5px;
    background: rgba(255,255,255,.08); border: 1px solid rgba(255,255,255,.14); border-bottom-width: 2px;
  }
  @keyframes popIn { from { opacity: 0; transform: translateY(-4px) scale(.97); } }
  @keyframes bump { 40% { transform: scale(1.12); } }

  /* Word lookup card */
  .lk {
    position: fixed; z-index: 3; width: 300px; max-width: calc(100vw - 16px); padding: 12px 12px 12px 14px;
    display: grid; gap: 8px; pointer-events: auto; border-radius: 16px; color: #F5F2EA;
    font: 400 13.5px/1.5 "Tarjuman Sans", "Segoe UI", Tahoma, sans-serif;
    background: #0F1650; border: 1px solid rgba(255,210,122,.32);
    box-shadow: 0 18px 44px rgba(0,0,0,.5), 0 1px 0 rgba(255,255,255,.06) inset;
    animation: popIn .16s cubic-bezier(.2,.7,.2,1);
  }
  .lk[hidden] { display: none; }
  .lk-head { display: flex; align-items: center; gap: 8px; }
  .lk-word { flex: 1; min-width: 0; font-size: 18px; font-weight: 700; color: #FFD27A; overflow-wrap: anywhere; }
  .lk button.x {
    display: grid; place-items: center; width: 30px; height: 30px; padding: 0; flex: none; border: 0; border-radius: 8px; cursor: pointer;
    background: transparent; color: #AEB6DE;
  }
  .lk button.x:hover { background: rgba(255,255,255,.1); color: #fff; }
  .lk-mean { margin: 0; font-size: 16px; font-weight: 600; min-height: 1.5em; }
  .lk-mean.dim { color: #AEB6DE; font-weight: 500; font-size: 13.5px; }
  .lk .shimmer {
    display: block; height: 14px; width: 70%; margin: 5px 0; border-radius: 6px;
    background: linear-gradient(90deg, rgba(255,255,255,.06), rgba(255,255,255,.16), rgba(255,255,255,.06));
    background-size: 200% 100%; animation: shimmer 1.1s linear infinite;
  }
  .lk-sent { margin: 0; padding: 8px 10px; border-radius: 10px; background: rgba(255,255,255,.05); color: #D6DDFB; font-size: 12.5px; }
  .lk-sent mark { background: rgba(255,210,122,.25); color: #fff; border-radius: 3px; padding: 0 2px; }
  .lk-acts { display: flex; align-items: center; gap: 10px; }
  .lk button.save {
    display: inline-flex; align-items: center; gap: 7px; min-height: 36px; padding: 0 14px; border: 0; border-radius: 10px; cursor: pointer;
    font-family: inherit; font-size: 13px; font-weight: 700; line-height: 1; color: #121A57; background: linear-gradient(180deg, #FFDC94, #FFC35C);
    box-shadow: 0 1px 0 rgba(255,255,255,.5) inset, 0 6px 16px rgba(240,146,43,.28); transition: filter .15s, transform .1s, background .2s;
  }
  .lk button.save:hover:not(:disabled) { filter: brightness(1.05); }
  .lk button.save:active:not(:disabled) { transform: translateY(1px); }
  .lk button.save:disabled { cursor: default; }
  .lk button.save.done { color: #0B3B26; background: linear-gradient(180deg, #A9EFCD, #5ED3A0); box-shadow: none; }
  .lk-state { font-size: 12px; color: #AEB6DE; }
  .lk-state.err { color: #FFB4AC; }
  .lk button:focus-visible { outline: 2px solid #FFD27A; outline-offset: 2px; }
  @keyframes shimmer { to { background-position: -200% 0; } }

  @media (prefers-reduced-motion: reduce) {
    .pill, .tools, .subs, .meter > i, .src .w, .lk button.save { transition: none; }
    .pill.busy .dot { animation: none; }
    .tpop, .lk, .tpop output.pulse, .lk .shimmer { animation: none; }
  }
`;

const esc = (s: string) => s.replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" })[c]!);

/** Static markup; the only dynamic parts are our own locale strings, escaped. */
export function overlayHtml(): string {
  const dir = uiDir();
  const name = esc(t("extShortName"));
  // Arrows written for people; aria-keyshortcuts wants key names.
  const ariaKey = (k: string) => k.replace("←", "ArrowLeft").replace("→", "ArrowRight").replace("↓", "ArrowDown");
  const b = (act: string, key: string, extra = "", keys: ShortcutAction[] = []) => {
    const label = esc(t(key));
    const tip = keys.length ? esc(`${t(key)} (${keys.map((k) => SHORTCUT_KEYS[k][0]).join(" / ")})`) : label;
    const shortcut = keys.length ? ` aria-keyshortcuts="${esc(keys.map((k) => ariaKey(SHORTCUT_KEYS[k][0])).join(" "))}"` : "";
    return `<button type="button" data-act="${act}" title="${tip}" aria-label="${label}"${shortcut} class="${extra}">${ICONS[act as keyof typeof ICONS]}</button>`;
  };
  // The mark's tooltip lists the line keys, which have no button.
  const lineKeys = esc([withKeys(t("keyPrev"), "prev"), withKeys(t("keyNext"), "next"), withKeys(t("keyRepeat"), "repeat")].join("\n"));
  const step = (d: number) =>
    `<button type="button" data-nudge="${d}" title="${esc(t(d < 0 ? "timingEarlierBy" : "timingLaterBy", String(Math.abs(d))))}" aria-label="${esc(t(d < 0 ? "timingEarlierBy" : "timingLaterBy", String(Math.abs(d))))}">${d < 0 ? "−" : "+"}${Math.abs(d)}</button>`;
  return `
    <style>${CSS}</style>
    <div class="wrap bottom">
      <div class="pill hide" dir="${dir}" role="status" aria-live="polite"><span class="dot"></span><span class="txt"></span></div>
      <div class="subs"><div class="line src" dir="auto"><span></span></div><div class="line tr"><span></span></div></div>
      <div class="whisper" dir="${dir}">
        <button class="go" type="button"></button>
        <div class="meter"><i></i></div>
      </div>
    </div>
    <div class="tools" role="toolbar" aria-label="${name}" dir="${dir}">
      <span class="mark" title="${name}&#10;${lineKeys}">${MARK}</span>
      ${b("subs", "tbSubs", "", ["subs"])}
      ${b("bi", "tbBilingual")}
      <span class="sep"></span>
      ${b("minus", "tbSmaller")}
      ${b("plus", "tbLarger")}
      ${b("pos", "tbPosition")}
      <span class="sep"></span>
      ${b("time", "tbTiming", "", ["earlier", "later"])}
      ${b("list", "tbTranscript", "", ["transcript"])}
      ${b("dub", "tbDub", "", ["dub"])}
      <span class="sep"></span>
      ${b("app", "tbOpenInApp")}
      ${b("stop", "tbStop", "danger")}
      <div class="tpop" role="group" aria-label="${esc(t("timingTitle"))}" dir="${dir}" hidden>
        <div class="head"><strong>${esc(t("timingTitle"))}</strong><output aria-live="polite">0.00</output></div>
        <div class="steps">${OFFSET_STEPS.map(step).join("")}</div>
        <div class="scale" aria-hidden="true"><span><i>←</i>${esc(t("timingEarlier"))}</span><span>${esc(t("timingLater"))}<i>→</i></span></div>
        <p class="note"></p>
        <div class="foot">
          <small><kbd>${esc(SHORTCUT_KEYS.earlier[0])}</kbd><kbd>${esc(SHORTCUT_KEYS.later[0])}</kbd><kbd>${esc(SHORTCUT_KEYS.resetTiming[0])}</kbd></small>
          <button type="button" class="reset" data-nudge="reset">${esc(t("btnReset"))}</button>
        </div>
      </div>
    </div>
    <div class="lk" role="dialog" aria-labelledby="lk-word" dir="${dir}" hidden>
      <div class="lk-head">
        <span class="lk-word" id="lk-word" dir="auto"></span>
        <button type="button" class="x" aria-label="${esc(t("btnClose"))}" title="${esc(t("btnClose"))}">${ICONS.close}</button>
      </div>
      <p class="lk-mean" aria-live="polite"></p>
      <p class="lk-sent" dir="auto"></p>
      <div class="lk-acts">
        <button type="button" class="save">${ICONS.save}<span>${esc(t("lookupSave"))}</span></button>
        <span class="lk-state" role="status"></span>
      </div>
    </div>`;
}
