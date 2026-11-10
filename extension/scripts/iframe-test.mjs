// End-to-end check for sites that play the video inside an iframe from another site (most movie and
// anime sites): the page is served on 127.0.0.1 and its player on localhost, so they are different
// origins. The player has Japanese captions. Expects the overlay inside the player frame, in Arabic.
//   node scripts/iframe-test.mjs --video=<local mp4>    (a Tarjuman server must run on 127.0.0.1:4318–4327)
import { chromium } from "playwright-core";
import { createServer } from "node:http";
import { createReadStream, existsSync, mkdtempSync, rmSync, statSync } from "node:fs";
import { tmpdir } from "node:os";
import { join, resolve, dirname } from "node:path";
import { fileURLToPath } from "node:url";

const root = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const arg = (k, d) => (process.argv.find((a) => a.startsWith(`--${k}=`)) || "").split("=").slice(1).join("=") || d;
const video = arg("video", "");
const CHROME = process.env.CHROME || "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe";
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

const VTT = `WEBVTT

00:00:00.500 --> 00:00:04.000
ここが象の前です。

00:00:04.200 --> 00:00:08.500
この子たちのすごいところは、とても長い鼻があることです。

00:00:08.700 --> 00:00:12.000
それはかっこいいですね。

00:00:12.200 --> 00:00:19.000
言うことはそれくらいです。
`;

const srv = createServer((req, res) => {
  if (req.url === "/captions.vtt") return res.writeHead(200, { "Content-Type": "text/vtt", "Access-Control-Allow-Origin": "*" }).end(VTT);
  if (req.url === "/video.mp4" && existsSync(video)) {
    const size = statSync(video).size;
    const m = /bytes=(\d+)-(\d*)/.exec(req.headers.range || "");
    const start = m ? Number(m[1]) : 0;
    const end = m && m[2] ? Number(m[2]) : size - 1;
    res.writeHead(m ? 206 : 200, {
      "Content-Type": "video/mp4", "Accept-Ranges": "bytes", "Content-Length": end - start + 1,
      ...(m ? { "Content-Range": `bytes ${start}-${end}/${size}` } : {}),
    });
    return createReadStream(video, { start, end }).pipe(res);
  }
  if (req.url === "/player")
    return res.writeHead(200, { "Content-Type": "text/html; charset=utf-8" }).end(`<!doctype html><title>player</title>
      <style>html,body{margin:0;height:100%;background:#000}video{width:100%;height:100%;display:block}</style>
      <video controls muted src="/video.mp4"><track kind="subtitles" srclang="ja" label="日本語" src="/captions.vtt" default></video>`);
  res.writeHead(200, { "Content-Type": "text/html; charset=utf-8" }).end(`<!doctype html><title>Anime site</title>
    <style>body{margin:0;background:#111;color:#ddd;font-family:sans-serif}main{max-width:1100px;margin:30px auto}
    iframe{width:100%;aspect-ratio:16/9;border:0;display:block}</style>
    <main><h2>Episode 5</h2><iframe src="http://localhost:8098/player" allowfullscreen></iframe></main>`);
});
await new Promise((r) => srv.listen(8098, () => r()));

const profile = mkdtempSync(join(tmpdir(), "tarjuman-iframe-"));
const ctx = await chromium.launchPersistentContext(profile, {
  executablePath: CHROME,
  headless: false,
  viewport: { width: 1280, height: 800 },
  ignoreDefaultArgs: ["--disable-extensions"],
  args: ["--headless=new", "--enable-unsafe-extension-debugging", "--autoplay-policy=no-user-gesture-required", "--no-first-run"],
});
let failed = false;
try {
  const cdp = await ctx.browser().newBrowserCDPSession();
  const { id } = await cdp.send("Extensions.loadUnpacked", { path: join(root, "dist") });
  let sw;
  for (let i = 0; !sw && i < 50; i++) {
    sw = ctx.serviceWorkers().find((w) => w.url().includes(id));
    if (!sw) await sleep(200);
  }
  await sleep(1500);
  const pg = await ctx.newPage();
  await pg.goto("http://127.0.0.1:8098/");
  await sleep(2500);
  const tabId = await sw.evaluate(async () => {
    const tabs = await chrome.tabs.query({});
    return tabs.find((t) => (t.url || "").startsWith("http://127.0.0.1:8098"))?.id;
  });
  const pop = await ctx.newPage();
  await pop.goto(`chrome-extension://${id}/popup.html`);
  await sleep(800);
  const started = await pop.evaluate((tabId) => new Promise((r) => chrome.runtime.sendMessage({ type: "start", tabId }, r)), tabId);
  console.log("start:", JSON.stringify(started));
  await pop.close();
  await pg.bringToFront();
  const player = pg.frames().find((f) => f.url().includes("/player"));
  await player.evaluate(() => {
    const v = document.querySelector("video");
    v.currentTime = 5;
    v.play().catch(() => {});
  });
  await sleep(6000);
  const inFrame = await player.evaluate(() => {
    const sr = document.getElementById("__tarjuman_host")?.shadowRoot;
    return sr ? { tr: sr.querySelector(".tr span")?.textContent, pill: sr.querySelector(".pill .txt")?.textContent } : null;
  });
  const onPage = await pg.evaluate(() => !!document.getElementById("__tarjuman_host"));
  console.log("overlay in the player frame:", JSON.stringify(inFrame), "| overlay on the outer page:", onPage);
  await pg.screenshot({ path: join(root, "store", "screenshots", "overlay-iframe.png") });
  failed = !started?.ok || started.mode !== "captions" || !inFrame || !/[\u0600-\u06FF]/.test(inFrame.tr || "") || onPage;
  console.log(failed ? "FAIL" : "PASS");
} finally {
  await ctx.close();
  srv.close();
  rmSync(profile, { recursive: true, force: true });
}
process.exit(failed ? 1 : 0);
