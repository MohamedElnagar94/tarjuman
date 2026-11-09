// Loads dist/ into the installed Chrome and screenshots the pages and the overlay.
//   node scripts/screenshots.mjs [--lang=en|ar] [--out=dir] [--youtube=<video url>] [--video=<local mp4 for the captions test>]
// Needs a Tarjuman (or prototype) server running on 127.0.0.1:4318–4327 for the "online" shots.
import { chromium } from "playwright-core";
import { createServer } from "node:http";
import { createReadStream, existsSync, mkdirSync, mkdtempSync, rmSync, statSync } from "node:fs";
import { tmpdir } from "node:os";
import { join, resolve, dirname } from "node:path";
import { fileURLToPath } from "node:url";

const root = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const arg = (k, d) => (process.argv.find((a) => a.startsWith(`--${k}=`)) || "").split("=").slice(1).join("=") || d;
const lang = arg("lang", "en");
const out = resolve(arg("out", join(root, "store/screenshots")));
const youtube = arg("youtube", "");
const video = arg("video", "");
const only = arg("only", "");
const SEEK = arg("seek", "5");
const DUB = process.argv.includes("--dub");
const CHROME = process.env.CHROME || "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe";
const dist = join(root, "dist");
mkdirSync(out, { recursive: true });

const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
const want = (name) => !only || only.split(",").includes(name);

// A page with a player that has its own English captions, for the "captions" mode.
// Served on 127.0.0.1, a host the extension already has permission for.
const VTT = `WEBVTT

00:00:00.500 --> 00:00:04.000
All right, so here we are in front of the elephants.

00:00:04.200 --> 00:00:08.500
The cool thing about these guys is that they have really, really long trunks.

00:00:08.700 --> 00:00:12.000
And that's cool.

00:00:12.200 --> 00:00:19.000
And that's pretty much all there is to say.
`;
function testSite() {
  const srv = createServer((req, res) => {
    if (req.url === "/captions.vtt") return res.writeHead(200, { "Content-Type": "text/vtt" }).end(VTT);
    if (req.url === "/video.mp4" && video && existsSync(video)) {
      const size = statSync(video).size;
      const m = /bytes=(\d+)-(\d*)/.exec(req.headers.range || "");
      if (m) {
        const start = Number(m[1]);
        const end = m[2] ? Number(m[2]) : size - 1;
        res.writeHead(206, { "Content-Type": "video/mp4", "Content-Range": `bytes ${start}-${end}/${size}`, "Accept-Ranges": "bytes", "Content-Length": end - start + 1 });
        return createReadStream(video, { start, end }).pipe(res);
      }
      res.writeHead(200, { "Content-Type": "video/mp4", "Content-Length": size, "Accept-Ranges": "bytes" });
      return createReadStream(video).pipe(res);
    }
    res.writeHead(200, { "Content-Type": "text/html; charset=utf-8" }).end(`<!doctype html><title>Course player</title>
      <style>body{margin:0;background:#111;font-family:sans-serif;color:#ddd}main{max-width:1100px;margin:40px auto}video{width:100%;aspect-ratio:16/9;background:#000;display:block}</style>
      <main><h2>Lesson 1 · Elephants</h2><video controls muted crossorigin="anonymous" src="/video.mp4"><track kind="subtitles" srclang="en" label="English" src="/captions.vtt"></video></main>`);
  });
  return new Promise((r) => srv.listen(8099, "127.0.0.1", () => r(srv)));
}

const profile = mkdtempSync(join(tmpdir(), "tarjuman-shots-"));
const ctx = await chromium.launchPersistentContext(profile, {
  executablePath: CHROME,
  headless: false,
  locale: lang,
  viewport: { width: 1280, height: 800 },
  // Branded Chrome ignores --load-extension since v137; load it over CDP instead (needs the pipe Playwright uses).
  ignoreDefaultArgs: ["--disable-extensions"],
  args: ["--headless=new", `--lang=${lang}`, "--enable-unsafe-extension-debugging", "--autoplay-policy=no-user-gesture-required", "--no-first-run"],
});
let site;
try {
  const cdp = await ctx.browser().newBrowserCDPSession();
  const { id } = await cdp.send("Extensions.loadUnpacked", { path: dist });
  let sw = ctx.serviceWorkers().find((w) => w.url().includes(id));
  for (let i = 0; !sw && i < 50; i++) {
    await sleep(200);
    sw = ctx.serviceWorkers().find((w) => w.url().includes(id));
  }
  if (!sw) throw new Error("service worker did not start");
  console.log("extension id", id);
  const ext = (p) => `chrome-extension://${id}/${p}`;
  await sleep(1500); // the welcome tab opens on install
  for (const p of ctx.pages()) if (p.url().includes("welcome.html")) console.log("welcome page opened on install: yes");

  const shot = async (name, url, size, prep) => {
    if (!want(name)) return;
    const page = await ctx.newPage();
    await page.setViewportSize(size);
    await page.goto(url);
    await page.waitForLoadState("networkidle").catch(() => {});
    if (prep) await prep(page);
    await sleep(1800);
    const file = join(out, `${name}.${lang}.png`);
    await page.screenshot({ path: file });
    console.log("saved", file);
    await page.close();
  };

  await shot("welcome", ext("welcome.html"), { width: 1280, height: 800 });
  await shot("options", ext("options.html"), { width: 1280, height: 800 });
  await shot("popup", ext("popup.html"), { width: 360, height: 580 });

  // The popup with a real video tab behind it: make the worker's "active tab" the video tab.
  // Make the worker's "active tab" this page, with its URL, as activeTab exposes it after a real click.
  // (Without the tabs permission the worker can't read URLs of pages it has no access to.)
  const pointAt = async (page) => {
    return sw.evaluate(async (url) => {
      const tabs = await chrome.tabs.query({});
      const t = tabs.find((x) => (x.url || '').startsWith(url)) || tabs.filter((x) => !x.url).sort((a, b) => b.id - a.id)[0];
      if (!t) return undefined;
      const realQuery = globalThis.__realQuery || (globalThis.__realQuery = chrome.tabs.query.bind(chrome.tabs));
      const realGet = globalThis.__realGet || (globalThis.__realGet = chrome.tabs.get.bind(chrome.tabs));
      const withUrl = async (id) => ({ ...(await realGet(id)), url: id === t.id ? url : (await realGet(id)).url });
      chrome.tabs.get = withUrl;
      chrome.tabs.query = async (q) => (q && q.active ? [await withUrl(t.id)] : realQuery(q));
      return t.id;
    }, page.url());
  };

  if (youtube && (want("youtube") || want("popup-youtube"))) {
    const yt = await ctx.newPage();
    await yt.setViewportSize({ width: 1280, height: 800 });
    await yt.goto(youtube, { waitUntil: "domcontentloaded" });
    await sleep(4000);
    // Dismiss a consent wall if one shows up.
    for (const sel of ['button[aria-label^="Accept"]', 'button:has-text("Accept all")', 'button:has-text("Reject all")']) {
      const b = yt.locator(sel).first();
      if (await b.isVisible().catch(() => false)) {
        await b.click().catch(() => {});
        await sleep(2500);
        break;
      }
    }
    const tabId = await pointAt(yt);
    console.log("youtube tab", tabId);
    // Start through the same message the popup sends.
    const pop = await ctx.newPage();
    await pop.setViewportSize({ width: 360, height: 580 });
    await pop.goto(ext("popup.html"));
    await sleep(1500);
    await pop.evaluate((dub) => new Promise((r) => chrome.runtime.sendMessage({ type: "set-settings", settings: { dub } }, r)), DUB);
    const started = await pop.evaluate((tabId) => new Promise((r) => chrome.runtime.sendMessage({ type: "start", tabId }, r)), tabId);
    console.log("start youtube:", JSON.stringify(started));
    await pop.reload();
    await sleep(2500);
    if (want("popup-youtube")) {
      await pop.screenshot({ path: join(out, `popup-youtube.${lang}.png`) });
      console.log("saved popup-youtube");
    }
    await pop.close();
    await yt.bringToFront();
    await yt.evaluate((seek) => {
      const v = document.querySelector("video");
      if (v) {
        v.muted = true;
        v.currentTime = seek;
        v.play().catch(() => {});
      }
    }, Number(SEEK));
    await sleep(9000);
    await yt.mouse.move(700, 300);
    await yt.mouse.move(720, 320);
    await sleep(600);
    const state = await yt.evaluate(() => {
      const host = document.getElementById("__tarjuman_host");
      const sr = host && host.shadowRoot;
      return sr
        ? { tr: sr.querySelector(".tr span")?.textContent, pill: sr.querySelector(".pill .txt")?.textContent, pillShown: !sr.querySelector(".pill").classList.contains("hide"), t: document.querySelector("video")?.currentTime, volume: document.querySelector("video")?.volume, paused: document.querySelector("video")?.paused }
        : null;
    });
    console.log("overlay on youtube:", JSON.stringify(state));
    await yt.screenshot({ path: join(out, `overlay-youtube.${lang}.png`) });
    console.log("saved overlay-youtube");
  }

  if (want("captions")) {
    site = await testSite();
    const pg = await ctx.newPage();
    await pg.setViewportSize({ width: 1280, height: 800 });
    await pg.goto("http://127.0.0.1:8099/");
    await sleep(1500);
    const tabId = await pointAt(pg);
    const pop = await ctx.newPage();
    await pop.goto(ext("popup.html"));
    await sleep(800);
    const started = await pop.evaluate((tabId) => new Promise((r) => chrome.runtime.sendMessage({ type: "start", tabId }, r)), tabId);
    console.log("start on a site with captions:", JSON.stringify(started));
    await pop.close();
    await pg.bringToFront();
    await pg.evaluate(() => {
      const v = document.querySelector("video");
      v.currentTime = 5;
      v.play().catch(() => {});
    });
    await sleep(5000);
    await pg.mouse.move(600, 300);
    await pg.mouse.move(620, 320);
    await sleep(500);
    const state = await pg.evaluate(() => {
      const sr = document.getElementById("__tarjuman_host")?.shadowRoot;
      return sr ? { tr: sr.querySelector(".tr span")?.textContent, pill: sr.querySelector(".pill .txt")?.textContent } : null;
    });
    console.log("overlay on the captions site:", JSON.stringify(state));
    await pg.screenshot({ path: join(out, `overlay-captions.${lang}.png`) });
    // Reload: 127.0.0.1 is a granted host, so the overlay must come back by itself.
    await pg.reload();
    await sleep(4500);
    const after = await sw.evaluate(async () => (await chrome.storage.session.get("state")).state);
    const back = await pg.evaluate(() => !!document.getElementById("__tarjuman_host"));
    console.log("state after reload:", JSON.stringify(after), "overlay back:", back);
  }
} finally {
  await ctx.close();
  site?.close();
  rmSync(profile, { recursive: true, force: true });
}
