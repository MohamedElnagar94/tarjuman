import { t } from "@/shared/i18n";
import type { Reply } from "@/shared/messages";

/** A start/stop failure from the background, in the user's language. */
export function startError(r: Reply | null | undefined): string {
  switch (r && r.code) {
    case "NO_SERVER":
      return t("errNoServer");
    case "PROTECTED":
      return t("errProtected");
    case "NO_ACCESS":
      return t("errNoAccess");
    case "WHISPER_NOT_INSTALLED":
      return t("errWhisper");
    case "CAPTURE_FAILED":
      return t("errCapture");
    case "NO_TAB":
      return t("errNoTab");
    default:
      return (r && r.message) || t("errStart");
  }
}

export async function shortcutText(): Promise<string> {
  try {
    const cmds = await chrome.commands.getAll();
    return cmds.find((c) => c.name === "toggle-translation")?.shortcut || "";
  } catch {
    return "";
  }
}
