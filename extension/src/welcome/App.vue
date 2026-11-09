<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from "vue";
import { t } from "@/shared/i18n";
import { send } from "@/shared/messages";
import { shortcutText } from "@/ui/errors";

const REPO = "https://github.com/MohamedElnagar94/tarjuman";
const found = ref<{ base: string; version: string } | null>(null);
const checked = ref(false);
const shortcut = ref("Alt+Shift+A");
const copied = ref(false);
let timer: ReturnType<typeof setInterval> | undefined;

const CMD = "python -m tarjuman";

async function check() {
  const r = await send("test-connection");
  found.value = r.ok ? { base: r.base, version: String(r.health?.version || "") } : null;
  checked.value = true;
}

async function copy() {
  try {
    await navigator.clipboard.writeText(CMD);
    copied.value = true;
    setTimeout(() => (copied.value = false), 1600);
  } catch {}
}

const statusText = computed(() =>
  !checked.value ? t("connSearching") : found.value ? t("welcomeFound", [found.value.version || "?", found.value.base.replace("http://", "")]) : t("welcomeWaiting"),
);

onMounted(async () => {
  shortcut.value = (await shortcutText()) || shortcut.value;
  await check();
  timer = setInterval(check, 2500);
});
onBeforeUnmount(() => clearInterval(timer));
</script>

<template>
  <div class="page">
    <div class="pattern" aria-hidden="true"></div>
    <header class="hero">
      <img class="mark" src="/icons/icon.svg" alt="" width="88" height="88" />
      <p class="eyebrow">{{ t("welcomeEyebrow") }}</p>
      <h1>{{ t("welcomeTitle") }}</h1>
      <p class="lede">{{ t("welcomeLede") }}</p>
      <div class="live" :class="{ ok: !!found, wait: checked && !found }" role="status" aria-live="polite">
        <i aria-hidden="true"></i>
        <span>{{ statusText }}</span>
      </div>
    </header>

    <ol class="steps">
      <li class="step" :class="{ done: !!found }">
        <span class="num" aria-hidden="true"><b>1</b></span>
        <h2>{{ t("step1Title") }}</h2>
        <p>{{ t("step1Body") }}</p>
        <a class="btn primary" :href="REPO" target="_blank" rel="noopener">
          <svg viewBox="0 0 24 24" width="16" height="16" fill="currentColor" aria-hidden="true">
            <path d="M12 .5a12 12 0 0 0-3.8 23.4c.6.1.8-.3.8-.6v-2.2c-3.3.7-4-1.4-4-1.4-.6-1.4-1.4-1.8-1.4-1.8-1-.7.1-.7.1-.7 1.2.1 1.8 1.2 1.8 1.2 1 1.8 2.8 1.3 3.5 1 .1-.8.4-1.3.8-1.6-2.7-.3-5.5-1.3-5.5-5.9 0-1.3.5-2.4 1.2-3.2-.1-.3-.5-1.5.1-3.2 0 0 1-.3 3.3 1.2a11.5 11.5 0 0 1 6 0C17.3 4.6 18.3 5 18.3 5c.7 1.7.3 2.9.1 3.2.8.8 1.2 1.9 1.2 3.2 0 4.6-2.8 5.6-5.5 5.9.4.4.8 1.1.8 2.2v3.3c0 .3.2.7.8.6A12 12 0 0 0 12 .5Z" />
          </svg>
          {{ t("step1Cta") }}
        </a>
      </li>
      <li class="step" :class="{ done: !!found }">
        <span class="num" aria-hidden="true"><b>2</b></span>
        <h2>{{ t("step2Title") }}</h2>
        <p>{{ t("step2Body") }}</p>
        <div class="cmd">
          <code>{{ CMD }}</code>
          <button type="button" class="btn ghost" @click="copy">{{ copied ? t("copied") : t("btnCopy") }}</button>
        </div>
        <p class="small">{{ t("step2Note") }}</p>
      </li>
      <li class="step">
        <span class="num" aria-hidden="true"><b>3</b></span>
        <h2>{{ t("step3Title") }}</h2>
        <p>{{ t("step3Body") }}</p>
        <p class="keys"><kbd>{{ shortcut }}</kbd> <span>{{ t("step3Keys") }}</span></p>
      </li>
    </ol>

    <section class="modes" :aria-label="t('modesTitle')">
      <h2>{{ t("modesTitle") }}</h2>
      <div class="grid">
        <div class="mode">
          <strong>{{ t("modeYouTube") }}</strong>
          <p>{{ t("hintYouTube") }}</p>
        </div>
        <div class="mode">
          <strong>{{ t("modeCaptions") }}</strong>
          <p>{{ t("hintCaptions") }}</p>
        </div>
        <div class="mode">
          <strong>{{ t("modeLive") }}</strong>
          <p>{{ t("hintLive") }}</p>
        </div>
      </div>
    </section>

    <footer class="foot">
      <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
        <rect x="4" y="10" width="16" height="11" rx="2.5" /><path d="M8 10V7a4 4 0 0 1 8 0v3" />
      </svg>
      <span>{{ t("welcomePrivacy") }}</span>
      <button type="button" class="btn ghost" @click="send('open-options')">{{ t("btnSettings") }}</button>
    </footer>
  </div>
</template>

<style>
body {
  min-height: 100vh;
  font-size: 15px;
  background:
    radial-gradient(70% 55% at 50% -5%, rgba(53, 80, 214, 0.55), transparent 70%),
    radial-gradient(50% 40% at 100% 100%, rgba(240, 146, 43, 0.1), transparent 70%),
    var(--lapis-950);
  background-attachment: fixed;
}
</style>

<style scoped>
.page {
  position: relative;
  max-width: 1080px;
  margin: 0 auto;
  padding: 56px 32px 48px;
}
/* An eight-pointed star lattice, as on manuscript borders, faded into the ground. */
.pattern {
  position: fixed;
  inset: 0;
  z-index: -1;
  opacity: 0.07;
  background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='64' height='64' viewBox='0 0 64 64'%3E%3Cg fill='none' stroke='%23FFD27A' stroke-width='1'%3E%3Cpath d='M32 14 37 27 50 32 37 37 32 50 27 37 14 32 27 27Z'/%3E%3Crect x='20' y='20' width='24' height='24' transform='rotate(45 32 32)'/%3E%3Crect x='20' y='20' width='24' height='24'/%3E%3C/g%3E%3C/svg%3E");
  -webkit-mask-image: radial-gradient(70% 60% at 50% 20%, #000, transparent 80%);
  mask-image: radial-gradient(70% 60% at 50% 20%, #000, transparent 80%);
}
.hero {
  text-align: center;
  display: flex;
  flex-direction: column;
  align-items: center;
}
.mark {
  filter: drop-shadow(0 18px 30px rgba(0, 0, 0, 0.45));
  animation: rise 0.6s var(--ease) both;
}
.eyebrow {
  margin: 22px 0 0;
  color: var(--saffron-300);
  font-weight: 600;
  letter-spacing: 0.08em;
  font-size: 12.5px;
  text-transform: uppercase;
}
[dir="rtl"] .eyebrow {
  letter-spacing: 0;
}
h1 {
  margin: 8px 0 0;
  font: 600 44px/1.15 var(--display);
  max-width: 22ch;
  animation: rise 0.6s 0.05s var(--ease) both;
}
.lede {
  margin: 14px 0 0;
  max-width: 58ch;
  color: var(--muted);
  font-size: 16px;
  line-height: 1.65;
  animation: rise 0.6s 0.1s var(--ease) both;
}
.live {
  display: inline-flex;
  align-items: center;
  gap: 10px;
  margin-top: 26px;
  padding: 9px 16px;
  border-radius: 99px;
  background: rgba(0, 0, 0, 0.25);
  border: 1px solid var(--line-strong);
  font-weight: 600;
  font-size: 14px;
  transition: background 0.3s, border-color 0.3s;
}
.live i {
  width: 9px;
  height: 9px;
  border-radius: 50%;
  background: var(--saffron-300);
  animation: pulse 1.4s ease-in-out infinite;
}
.live.wait {
  color: #FFE3A8;
}
.live.ok {
  color: #C5F2DD;
  background: rgba(94, 211, 160, 0.12);
  border-color: rgba(94, 211, 160, 0.4);
}
.live.ok i {
  background: var(--ok);
  box-shadow: 0 0 0 4px rgba(94, 211, 160, 0.2);
  animation: none;
}
@keyframes pulse {
  50% {
    opacity: 0.3;
  }
}
@keyframes rise {
  from {
    opacity: 0;
    transform: translateY(10px);
  }
}

.steps {
  list-style: none;
  padding: 0;
  margin: 52px 0 0;
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 18px;
}
.step {
  position: relative;
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  padding: 26px 22px 22px;
  border-radius: var(--radius-lg);
  background: linear-gradient(180deg, rgba(255, 255, 255, 0.06), rgba(255, 255, 255, 0.025));
  border: 1px solid var(--line);
  animation: rise 0.6s var(--ease) both;
}
.step:nth-child(2) {
  animation-delay: 0.08s;
}
.step:nth-child(3) {
  animation-delay: 0.16s;
}
.num {
  display: grid;
  place-items: center;
  width: 34px;
  height: 34px;
  border-radius: 10px;
  transform: rotate(45deg);
  background: linear-gradient(135deg, var(--saffron-300), var(--saffron-500));
  color: var(--lapis-900);
  font: 700 15px/1 var(--display);
}
.num b {
  display: block;
  transform: rotate(-45deg);
}
.step.done .num {
  background: linear-gradient(135deg, #8BE6BE, var(--ok));
}
.step h2 {
  margin: 20px 0 6px;
  font: 600 19px/1.3 var(--display);
}
.step p {
  margin: 0 0 16px;
  color: var(--muted);
  line-height: 1.6;
}
.step .btn {
  margin-top: auto;
}
.cmd {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  width: 100%;
  padding: 6px 6px 6px 14px;
  border-radius: 10px;
  background: rgba(0, 0, 0, 0.32);
  border: 1px solid var(--line);
  direction: ltr;
}
.cmd code {
  color: var(--saffron-200);
  font-size: 14px;
}
.small {
  font-size: 13px;
  color: var(--faint) !important;
  margin: 10px 0 0 !important;
}
.keys {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-top: auto !important;
}
.keys kbd {
  font-size: 13px;
  padding: 6px 9px;
}

.modes {
  margin-top: 40px;
}
.modes h2 {
  margin: 0 0 14px;
  font: 600 18px/1.3 var(--display);
  color: var(--muted);
  text-align: center;
}
.grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 12px;
}
.mode {
  padding: 16px 18px;
  border-radius: var(--radius);
  border: 1px dashed var(--line-strong);
}
.mode strong {
  font-weight: 600;
}
.mode p {
  margin: 4px 0 0;
  color: var(--muted);
  font-size: 13.5px;
  line-height: 1.55;
}

.foot {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 10px;
  margin-top: 40px;
  color: var(--muted);
  font-size: 13.5px;
}
.foot svg {
  color: var(--saffron-300);
}

@media (max-width: 860px) {
  .steps,
  .grid {
    grid-template-columns: minmax(0, 1fr);
  }
  h1 {
    font-size: 34px;
  }
  .page {
    padding: 40px 16px;
  }
}
</style>
