/** The overlay's markup and styles. Everything lives in a shadow root so the page can't restyle it. */
import { t, uiDir } from "@/shared/i18n";

const RANGES = {
  arabic: "U+0600-06FF,U+0750-077F,U+0870-088E,U+0890-0891,U+0897-08E1,U+08E3-08FF,U+200C-200E,U+2010-2011,U+204F,U+2E41,U+FB50-FDFF,U+FE70-FE74,U+FE76-FEFC",
  "latin-ext": "U+0100-02BA,U+02BD-02C5,U+02C7-02CC,U+02CE-02D7,U+02DD-02FF,U+0304,U+0308,U+0329,U+1D00-1DBF,U+1E00-1E9F,U+1EF2-1EFF,U+2020,U+20A0-20AB,U+20AD-20C0,U+2113,U+2C60-2C7F,U+A720-A7FF",
  latin: "U+0000-00FF,U+0131,U+0152-0153,U+02BB-02BC,U+02C6,U+02DA,U+02DC,U+0304,U+0308,U+0329,U+2000-206F,U+20AC,U+2122,U+2191,U+2193,U+2212,U+2215,U+FEFF,U+FFFD",
};

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
  const st = document.createElement("style");
  st.id = id;
  st.textContent = faces.join("\n");
  (document.head || document.documentElement).appendChild(st);
}

const icon = (paths: string) =>
  `<svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">${paths}</svg>`;

const ICONS = {
  subs: icon('<rect x="3" y="5" width="18" height="14" rx="3"/><path d="M7 15h4M15 15h2M7 11h2M13 11h4"/>'),
  bi: icon('<path d="m5 8 6 6"/><path d="m4 14 6-6 2-3"/><path d="M2 5h12"/><path d="M7 2h1"/><path d="m22 22-5-10-5 10"/><path d="M14 18h6"/>'),
  minus: icon('<path d="M3 18 8 6l5 12M4.8 14h6.4"/><path d="M16 12h6"/>'),
  plus: icon('<path d="M3 18 8 6l5 12M4.8 14h6.4"/><path d="M16 12h6M19 9v6"/>'),
  pos: icon('<path d="m21 16-4 4-4-4"/><path d="M17 20V4"/><path d="m3 8 4-4 4 4"/><path d="M7 4v16"/>'),
  dub: icon('<path d="M2 10v3"/><path d="M6 6v11"/><path d="M10 3v18"/><path d="M14 8v7"/><path d="M18 5v13"/><path d="M22 10v3"/>'),
  stop: icon('<path d="M18 6 6 18"/><path d="m6 6 12 12"/>'),
};

const MARK = `<svg viewBox="0 0 128 128" width="22" height="22" aria-hidden="true"><defs><linearGradient id="tj-t" x1=".15" y1="0" x2=".85" y2="1"><stop offset="0" stop-color="#3550D6"/><stop offset="1" stop-color="#121A57"/></linearGradient><linearGradient id="tj-i" x1="1" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#FFD27A"/><stop offset="1" stop-color="#F0922B"/></linearGradient></defs><rect x="4" y="4" width="120" height="120" rx="30" fill="url(#tj-t)"/><path d="M27 24 L49 37 L27 50 Z" fill="#fff" stroke="#fff" stroke-width="6" stroke-linejoin="round"/><path d="M104 46 C110 52,108 76,96 88 C86 98,72 102,58 101 C40 100,26 92,19 76 C30 84,44 88,58 88 C74 88,87 82,93 70 C97 62,97 54,95 50 Z" fill="url(#tj-i)"/><rect x="50" y="52" width="14" height="14" rx="2.5" transform="rotate(45 57 59)" fill="#FFD27A"/><rect x="69" y="45" width="14" height="14" rx="2.5" transform="rotate(45 76 52)" fill="#fff"/></svg>`;

export const CSS = `
  :host { all: initial; }
  * { box-sizing: border-box; }
  .wrap {
    position: fixed; display: flex; flex-direction: column; align-items: center;
    pointer-events: none; padding: 0 4%;
    font-family: "Tarjuman Sans", "IBM Plex Sans Arabic", "Segoe UI", "Noto Sans Arabic", Tahoma, Arial, sans-serif;
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
  .line span {
    display: inline; color: #FFFFFF; line-height: 1.5;
    background: rgba(8,10,30,var(--bgo,.78));
    padding: .08em .48em .12em; border-radius: .3em;
    -webkit-box-decoration-break: clone; box-decoration-break: clone;
    text-shadow: 0 0 2px rgba(0,0,0,.95), 0 1px 3px rgba(0,0,0,.9), 0 0 12px rgba(0,0,0,.35);
  }
  .tr { font-weight: 700; letter-spacing: 0; }
  .tr.pending span { color: #D3D6EC; font-weight: 500; }
  .src { font-size: .62em; font-weight: 500; }
  .src span { color: #ECE8DA; }
  .line:empty, .line span:empty { display: none; }

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
  @media (prefers-reduced-motion: reduce) {
    .pill, .tools, .subs, .meter > i { transition: none; }
    .pill.busy .dot { animation: none; }
  }
`;

const esc = (s: string) => s.replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" })[c]!);

/** Static markup; the only dynamic parts are our own locale strings, escaped. */
export function overlayHtml(): string {
  const dir = uiDir();
  const name = esc(t("extShortName"));
  const b = (act: string, key: string, extra = "") =>
    `<button type="button" data-act="${act}" title="${esc(t(key))}" aria-label="${esc(t(key))}" class="${extra}">${ICONS[act as keyof typeof ICONS]}</button>`;
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
      <span class="mark" title="${name}">${MARK}</span>
      ${b("subs", "tbSubs")}
      ${b("bi", "tbBilingual")}
      <span class="sep"></span>
      ${b("minus", "tbSmaller")}
      ${b("plus", "tbLarger")}
      ${b("pos", "tbPosition")}
      <span class="sep"></span>
      ${b("dub", "tbDub")}
      ${b("stop", "tbStop", "danger")}
    </div>`;
}
