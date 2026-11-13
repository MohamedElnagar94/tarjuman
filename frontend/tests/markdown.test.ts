import { describe, expect, it } from "vitest";
import { markdownToHtml } from "@/lib/markdown";

describe("markdownToHtml (release notes)", () => {
  it("reads headings, lists, bold, code and links", () => {
    const html = markdownToHtml("### Desktop app\n\n- A **tray** icon\n- `api` field, see [the docs](https://example.com/x)\n\nDone.");
    expect(html).toBe(
      '<h5>Desktop app</h5><ul><li>A <strong>tray</strong> icon</li><li><code>api</code> field, see <a href="https://example.com/x" target="_blank" rel="noopener">the docs</a></li></ul><p>Done.</p>',
    );
  });
  it("never lets the notes add markup or script links", () => {
    const html = markdownToHtml('<img src=x onerror=alert(1)>\n\n[x](javascript:alert(1)) "q"');
    expect(html).not.toContain("<img");
    expect(html).not.toContain('href="javascript');
    expect(html).toContain("&lt;img");
  });
  it("reads rules and italic", () => {
    expect(markdownToHtml("one\n\n---\n\nchoose *More info*")).toBe("<p>one</p><hr><p>choose <em>More info</em></p>");
  });
  it("joins a list item that wraps onto the next line", () => {
    expect(markdownToHtml("- one\n  two")).toBe("<ul><li>one two</li></ul>");
  });
});
