// The main journeys of the web app, in a real browser, against the offline test server.
import assert from "node:assert/strict";
import { after, before, test } from "node:test";
import { chromium } from "playwright-core";

const base = process.env.E2E_BASE || "http://127.0.0.1:4390";
const SECOND_LINE = "نتحدث اليوم عن النماذج اللغوية الكبيرة.";

let browser;
let media;
let voice; // a 30-second voice note with a transcript
let memo; // a voice note without one

before(async () => {
  browser = await chromium.launch({
    ...(process.env.CHROME ? { executablePath: process.env.CHROME } : { channel: "chrome" }),
    args: ["--autoplay-policy=no-user-gesture-required", "--mute-audio"],
  });
  // The sample video of the test server (a rerun may also hold clips uploaded by an earlier run).
  const items = (await (await fetch(base + "/api/media")).json()).items;
  media = items.find((m) => m.title === "Short lesson");
  voice = items.find((m) => m.title === "Voice note");
  memo = items.find((m) => m.title === "Silent memo");
});
after(() => browser?.close());

/** A fresh browser profile; ``prefs`` are the app's saved preferences (theme, language…). */
async function open(path, { viewport = { width: 1280, height: 800 }, prefs = {} } = {}) {
  const ctx = await browser.newContext({ viewport, reducedMotion: "reduce", acceptDownloads: true });
  await ctx.addInitScript((p) => {
    if (!localStorage.getItem("tarjuman.prefs")) localStorage.setItem("tarjuman.prefs", JSON.stringify({ liveDub: false, ...p }));
  }, prefs);
  const page = await ctx.newPage();
  const errors = [];
  page.on("pageerror", (e) => errors.push(String(e)));
  await page.goto(base + path);
  return { ctx, page, errors };
}

const watchPath = () => "/watch?url=" + encodeURIComponent(media.link);

test("home opens in Arabic and leads to the library", async () => {
  const { ctx, page, errors } = await open("/");
  assert.equal(await page.getAttribute("html", "dir"), "rtl");
  assert.match(await page.title(), /ترجمان/);
  assert.equal(await page.locator('input[type="file"]').count(), 1, "a video can be picked from the computer");
  await page.locator('a[href="/library"]').first().click();
  await page.waitForURL("**/library");
  await page.getByText("Short lesson").first().waitFor();
  assert.deepEqual(errors, []);
  await ctx.close();
});

test("a video from the library plays with its translated transcript", async () => {
  const { ctx, page, errors } = await open("/library");
  await page.locator(`a[href*="${encodeURIComponent(media.link)}"], a[href*="${media.link}"]`).first().click();
  await page.waitForURL("**/watch**");
  await page.locator(".tp__lines .row").nth(2).waitFor();
  assert.equal(await page.locator(".tp__lines .row").count(), 3);
  await page.locator('.row[data-i="1"] .tr').filter({ hasText: SECOND_LINE }).waitFor();
  assert.match(await page.locator('.row[data-i="1"] .src').innerText(), /large language models/);

  // Clicking a line's time moves the video there, also when clicked before the video has loaded.
  await page.locator('.row[data-i="1"] .tm').click();
  await page.waitForFunction(() => Math.abs(document.querySelector("video").currentTime - 3) < 0.6);
  assert.deepEqual(errors, []);
  await ctx.close();
});

test("the subtitle shows over the video while it plays", async () => {
  const { ctx, page } = await open(watchPath());
  await page.locator(".tp__lines .row").first().waitFor();
  await page.evaluate(() => {
    const v = document.querySelector("video");
    v.muted = true;
    v.currentTime = 3.2;
    return v.play();
  });
  await page.getByText(SECOND_LINE).nth(1).waitFor({ timeout: 10000 }); // once in the transcript, once on the video
  await ctx.close();
});

test("live dubbing asks for a plan and for voices", async () => {
  const { ctx, page } = await open(watchPath());
  await page.locator(".tp__lines .row").first().waitFor();
  const plan = page.waitForResponse((r) => r.url().includes("/api/dubplan") && r.ok(), { timeout: 20000 });
  const voice = page.waitForResponse((r) => r.url().includes("/api/tts") && r.ok(), { timeout: 30000 });
  await page.locator("#tab-watch").click();
  await page.locator("#panel-watch button", { hasText: "شاهد مدبلجًا" }).click();
  await plan;
  await page.evaluate(() => {
    const v = document.querySelector("video");
    v.currentTime = 0;
    return v.play();
  });
  assert.equal((await voice).headers()["content-type"], "audio/wav");
  await ctx.close();
});

test("the translated subtitles download as an SRT file", async () => {
  const { ctx, page } = await open(watchPath());
  await page.locator(".tp__lines .row").first().waitFor();
  await page.locator("#tab-export").click();
  const download = page.waitForEvent("download");
  await page.locator("#panel-export button", { hasText: "نزّل الملف" }).click();
  const file = await download;
  assert.match(file.suggestedFilename(), /\.srt$/);
  const { readFile } = await import("node:fs/promises");
  const text = await readFile(await file.path(), "utf8");
  assert.ok(text.includes(SECOND_LINE) && text.includes("-->"), "an SRT with the Arabic lines");
  await ctx.close();
});

test("a video picked from the computer is uploaded and opens", async () => {
  const { ctx, page } = await open("/");
  const bytes = Buffer.from(await (await fetch(`${base}/api/media/file?id=${media.id}`)).arrayBuffer());
  await page.locator('input[type="file"]').setInputFiles({ name: "my clip.mp4", mimeType: "video/mp4", buffer: bytes });
  await page.waitForURL("**/watch**", { timeout: 20000 });
  const items = (await (await fetch(base + "/api/media")).json()).items;
  assert.ok(items.some((m) => m.title === "my clip" && m.size === bytes.length), "it is in the library, whole");
  await ctx.close();
});

test("settings: language switch, phone pairing code, storage and privacy", async () => {
  const { ctx, page, errors } = await open("/settings#phone");
  await page.locator("#phone .qr svg").waitFor();
  assert.match(await page.locator("#phone .link code").innerText(), /\/pair\?code=/);
  // One section at a time: the others are hidden until their tab is picked.
  assert.equal(await page.locator("#storage").isVisible(), false);
  await page.locator('.toc a[href="#storage"]').click();
  await page.locator("#storage table tr").first().waitFor();
  assert.equal(await page.locator("#phone").isVisible(), false);
  await page.locator('.toc a[href="#privacy"]').click();
  assert.equal(await page.locator("#privacy .row").count(), 10);

  await page.locator('.toc a[href="#appearance"]').click();
  await page.locator("#appearance button", { hasText: "English" }).click();
  await page.waitForFunction(() => document.documentElement.dir === "ltr");
  await page.locator('.toc a[href="#privacy"]').click();
  await page.locator("#h-privacy", { hasText: "Privacy" }).waitFor();
  await page.reload();
  await page.waitForFunction(() => document.documentElement.dir === "ltr", null, { timeout: 5000 });
  assert.deepEqual(errors, []);
  await ctx.close();
});

test("nothing overflows sideways on a small phone", async () => {
  for (const path of ["/", "/library", "/settings", "/words", watchPath()]) {
    const { ctx, page } = await open(path, { viewport: { width: 320, height: 640 } });
    await page.waitForLoadState("networkidle");
    const over = await page.evaluate(() => document.documentElement.scrollWidth - window.innerWidth);
    assert.ok(over <= 1, `${path} is ${over}px wider than a 320px screen`);
    // The last thing on the page can be scrolled clear of the bottom navigation.
    const hidden = await page.evaluate(() => {
      window.scrollTo(0, document.documentElement.scrollHeight);
      const nav = [...document.querySelectorAll("nav")].find((n) => getComputedStyle(n).position === "fixed" && n.getBoundingClientRect().bottom >= innerHeight - 1);
      const main = document.querySelector("main");
      if (!nav || !main) return 0;
      const last = [...main.querySelectorAll("*")].filter((e) => e.getBoundingClientRect().height > 0 && !e.children.length).pop();
      return last ? Math.max(0, last.getBoundingClientRect().bottom - nav.getBoundingClientRect().top) : 0;
    });
    assert.ok(hidden <= 1, `${path}: the bottom navigation covers ${hidden}px of the page's end`);
    await ctx.close();
  }
});

test("an unknown address shows the not-found page, not a blank one", async () => {
  const { ctx, page } = await open("/no-such-page");
  await page.locator('a[href="/"]').first().waitFor();
  assert.ok((await page.locator("main").innerText()).trim().length > 10);
  await ctx.close();
});

const watchOf = (m) => "/watch?url=" + encodeURIComponent(m.link);

test("a voice note plays as sound: waveform, its transcript, and words about a recording", async () => {
  const { ctx, page, errors } = await open(watchOf(voice));
  // A stage for sound instead of a black video, with the transcript beside it.
  await page.locator(".audio canvas.viz").waitFor();
  assert.equal(await page.locator("video:visible").count(), 0, "no video picture for a sound file");
  await page.locator(".tp__lines .row").nth(2).waitFor();
  await page.locator('.row[data-i="1"] .tr').filter({ hasText: "ترجمة: Here is the middle part." }).waitFor();
  // The waveform of the file itself (peaks from the server).
  const peaks = await (await fetch(base + `/api/media/peaks?id=${voice.id}`)).json();
  assert.ok(peaks.ok && peaks.peaks.length > 20, "the server measures the sound for the waveform");
  // A line click plays from there.
  await page.locator('.row[data-i="2"] .tm').click();
  await page.waitForFunction(() => Math.abs(document.querySelector("audio, video").currentTime - 23) < 0.8);

  // A recording with no transcript yet is offered as a recording, not as "this video".
  await page.goto(base + watchOf(memo));
  await page.getByRole("heading", { name: "لنفرّغ هذا التسجيل" }).waitFor();
  await page.getByRole("button", { name: "فرّغ التسجيل وترجمه" }).waitFor();
  assert.equal(await page.getByText("هذا الفيديو").count(), 0);
  assert.deepEqual(errors, []);
  await ctx.close();
});

test("transcription settings: a model per use, and the words list is saved", async () => {
  const { ctx, page, errors } = await open("/settings#transcription");
  // The computer's own recommendation, and one choice for each use.
  for (const u of ["audio", "video", "live"]) await page.locator(`#asr-use-${u}`).waitFor({ timeout: 30000 });
  await page.locator("#asr-use-video").selectOption("small");
  await page.waitForFunction(async (b) => (await (await fetch(b + "/api/asr")).json()).settings.models.video === "small", base);

  // A word to get right, written the way it should be.
  await page.getByRole("button", { name: /أضف كلمة|Add a word/ }).click();
  const rows = page.locator("input.t-from");
  const n = await rows.count();
  await rows.nth(n - 1).fill("زووم");
  await page.getByLabel(`الكتابة الصحيحة، رقم ${n}`).fill("Zoom");
  await page.locator("#transcription").getByRole("button", { name: "حفظ" }).last().click();
  await page.waitForFunction(
    async (b) => (await (await fetch(b + "/api/asr")).json()).settings.terms.some((t) => t.from === "زووم" && t.to === "Zoom"),
    base,
  );
  await page.reload();
  await page.waitForFunction(() => [...document.querySelectorAll("input.t-from")].some((e) => e.value === "زووم"), null, { timeout: 30000 });
  const saved = await page.locator("input.t-from").evaluateAll((els) => els.map((e) => e.value));
  assert.ok(saved.includes("زووم"), "the word is still there after a reload");
  // Back to automatic, so other tests see the defaults.
  await page.locator("#asr-use-video").selectOption("auto");
  assert.deepEqual(errors, []);
  await ctx.close();
});

test("chapters from the AI summary appear in the transcript and on the timeline", async () => {
  const { ctx, page, errors } = await open(watchOf(voice));
  await page.locator(".tp__lines .row").nth(2).waitFor();
  assert.equal(await page.locator(".tp__lines .chap").count(), 0, "no chapters before the summary");
  await page.locator("#tab-ask").click();
  await page.locator("#panel-ask button.btn--primary").first().click();
  await page.locator(".tp__lines .chap").nth(2).waitFor();
  assert.deepEqual(await page.locator(".tp__lines .chap .chap__t").allInnerTexts(), ["البداية", "الوسط", "النهاية"]);
  // Each heading sits above the first line of its chapter.
  assert.equal(await page.locator('.tp__lines .chap + .row').nth(1).getAttribute("data-i"), "1");
  // A heading takes you to its chapter, and the timeline names the one playing.
  await page.locator(".tp__lines .chap").nth(2).click();
  await page.waitForFunction(() => Math.abs(document.querySelector("audio, video").currentTime - 22) < 0.8);
  await page.locator(".audio .chap-now", { hasText: "النهاية" }).waitFor(); // the sound stage names the chapter playing
  assert.deepEqual(errors, []);
  await ctx.close();
});
