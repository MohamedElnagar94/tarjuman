import { describe, it, expect, afterEach } from "vitest";
import { replyError } from "../src/shared/errors";
import { useTable } from "../src/shared/i18n";

// Without chrome.i18n, t() gives back the key, which is what these checks compare against.
describe("replyError: failures in the user's language", () => {
  afterEach(() => useTable(null, null));

  it("gives known codes their own message", () => {
    expect(replyError({ code: "NO_SERVER" })).toBe("errNoServerShort");
    expect(replyError({ code: "YTDLP_FAILED", message: "تعذّر التنزيل" })).toBe("errDownload");
  });

  it("never shows the app's Arabic text to someone who chose English", () => {
    useTable("en", {});
    expect(replyError({ code: "SOMETHING_NEW", message: "رسالة بالعربية" })).toBe("errGenericCode");
    expect(replyError({ message: "رسالة بالعربية" })).toBe("errGeneric");
  });

  it("shows the app's own message to Arabic readers, and any non-Arabic message", () => {
    useTable("ar", {});
    expect(replyError({ code: "SOMETHING_NEW", message: "رسالة بالعربية" })).toBe("رسالة بالعربية");
    useTable("en", {});
    expect(replyError({ code: "X", message: "Disk quota reached" })).toBe("Disk quota reached");
  });

  it("uses the fallback when there is nothing to say", () => {
    expect(replyError(null, "errStart")).toBe("errStart");
  });
});
