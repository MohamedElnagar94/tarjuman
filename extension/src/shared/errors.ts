import { t, uiLang } from "@/shared/i18n";
import type { Reply } from "@/shared/messages";

/** Server and background codes with a message of their own in the extension's languages. */
const CODES: Record<string, string> = {
  NO_SERVER: "errNoServerShort",
  UNPLAYABLE: "errUnplayable",
  WHISPER_NOT_INSTALLED: "errWhisper",
  TIMEOUT: "errTimeout",
  EXTENSION_NOT_ALLOWED: "pillNotAllowed",
  NO_CAPTIONS: "pillNoCaptions",
  DOWNLOAD_FAILED: "errDownload",
  YTDLP_FAILED: "errDownload",
  NO_SPEECH: "errNoSpeech",
  NO_AUDIO: "errNoSpeech",
  ASR_BUSY: "errBusy",
  QUEUE_FULL: "errBusy",
  JOBS_RUNNING: "errBusy",
  FFMPEG_NOT_FOUND: "errFfmpeg",
  DISK_FULL: "errDiskFull",
  TRANSLATE_FAILED: "pillTranslateDown",
  GT_COOLDOWN: "pillTranslateDown",
  MYMEMORY_QUOTA: "pillTranslateDown",
  TTS_FAILED: "errVoice",
  TTS_ERROR: "errVoice",
};

const ARABIC = /[\u0600-\u06FF]/;

/**
 * A failure, in the user's interface language. The app writes its own messages in Arabic: shown as they
 * are to Arabic readers; for anyone else a known code gets its own message and the rest a plain one
 * with the code (so it can still be looked up), never Arabic text they can't read.
 */
export function replyError(res: Partial<Reply> | null | undefined, fallbackKey = "errGeneric"): string {
  const code = String((res && res.code) || "");
  const key = CODES[code];
  if (key) return t(key);
  const msg = String((res && res.message) || "").trim();
  if (msg && msg !== code && (uiLang() === "ar" || !ARABIC.test(msg))) return msg;
  return code && /^[A-Z_]+$/.test(code) ? t("errGenericCode", code) : t(fallbackKey);
}
