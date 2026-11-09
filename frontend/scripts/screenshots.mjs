// Screenshots of the web app in both themes, both languages, desktop and phone.
// Usage: node scripts/screenshots.mjs [baseUrl] [outDir]
//   env PAGES=home,watch,library,words,settings  THEMES=dark,light  LANGS=ar,en  SIZES=desktop,phone
//   env VIDEO=<youtube url>  CHROME=<path to chrome.exe>
import { mkdirSync } from "node:fs";
import { join, resolve } from "node:path";
import { chromium } from "playwright-core";

const base = process.argv[2] || "http://127.0.0.1:5173";
const out = resolve(process.argv[3] || "screenshots");
const list = (v, d) => (process.env[v] || d).split(",").filter(Boolean);
const PAGES = list("PAGES", "home,watch,library,words,settings");
const THEMES = list("THEMES", "dark,light");
const LANGS = list("LANGS", "ar,en");
const SIZES = list("SIZES", "desktop,phone");
const VIDEO = process.env.VIDEO || "https://www.youtube.com/watch?v=lR931Iz8Z6U";
const VIEW = { desktop: { width: 1440, height: 900 }, phone: { width: 390, height: 844 } };
const PATHS = {
  home: "/",
  watch: "/watch?url=" + encodeURIComponent(VIDEO),
  library: "/library",
  words: "/words",
  settings: "/settings",
};

mkdirSync(out, { recursive: true });
const browser = await chromium.launch({
  executablePath: process.env.CHROME || "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe",
  args: ["--autoplay-policy=no-user-gesture-required"],
});

for (const size of SIZES) {
  for (const theme of THEMES) {
    for (const lang of LANGS) {
      const ctx = await browser.newContext({
        viewport: VIEW[size],
        deviceScaleFactor: size === "phone" ? 2 : 1,
        isMobile: size === "phone",
        hasTouch: size === "phone",
        colorScheme: theme,
        reducedMotion: "reduce",
      });
      await ctx.addInitScript(
        ([theme, lang]) => {
          const p = JSON.parse(localStorage.getItem("tarjuman.prefs") || "{}");
          localStorage.setItem("tarjuman.prefs", JSON.stringify({ ...p, theme, uiLang: lang, liveDub: false }));
        },
        [theme, lang],
      );
      const page = await ctx.newPage();
      page.on("pageerror", (e) => console.log(`  [pageerror] ${e.message}`));
      for (const name of PAGES) {
        await page.goto(base + PATHS[name], { waitUntil: "networkidle" }).catch(() => {});
        if (name === "watch") {
          await page.waitForSelector(".row", { timeout: 60000 }).catch(() => console.log("  no transcript rows"));
          await page.waitForTimeout(4000);
          // Seek a little so a subtitle and an active line are visible.
          await page.evaluate(() => document.querySelectorAll(".row .tm")[12]?.click());
          await page.waitForTimeout(3500);
        } else {
          await page.waitForTimeout(700);
        }
        const file = join(out, `${name}-${size}-${theme}-${lang}.png`);
        await page.screenshot({ path: file, fullPage: true });
        console.log(file);
      }
      await ctx.close();
    }
  }
}
await browser.close();
