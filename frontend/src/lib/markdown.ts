// A small Markdown reader for release notes: headings, lists, paragraphs, rules, **bold**, *italic*,
// `code` and links.
// Everything is escaped first, so nothing from the notes can become markup of its own; links keep
// only http(s) addresses.

const esc = (s: string) => s.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");

function inline(s: string): string {
  return esc(s)
    .replace(/`([^`]+)`/g, "<code>$1</code>")
    .replace(/\*\*([^*]+)\*\*/g, "<strong>$1</strong>")
    .replace(/(^|[^*\w])\*([^*\s][^*]*?)\*(?!\w)/g, "$1<em>$2</em>")
    .replace(/\[([^\]]+)\]\((https?:\/\/[^\s)]+)\)/g, '<a href="$2" target="_blank" rel="noopener">$1</a>');
}

export function markdownToHtml(md: string): string {
  const out: string[] = [];
  let list = false;
  let para: string[] = [];
  const flush = () => {
    if (para.length) out.push(`<p>${inline(para.join(" "))}</p>`);
    para = [];
  };
  const endList = () => {
    if (list) out.push("</ul>");
    list = false;
  };
  for (const raw of md.replace(/\r\n?/g, "\n").split("\n")) {
    const line = raw.trimEnd();
    const h = /^(#{1,6})\s+(.*)$/.exec(line);
    const li = /^\s*[-*]\s+(.*)$/.exec(line);
    if (/^\s*(-{3,}|\*{3,})\s*$/.test(line)) {
      flush();
      endList();
      out.push("<hr>");
    } else if (h) {
      flush();
      endList();
      const level = Math.min(6, h[1]!.length + 2); // release notes start at ##; keep them under the page's own headings
      out.push(`<h${level}>${inline(h[2]!)}</h${level}>`);
    } else if (li) {
      flush();
      if (!list) out.push("<ul>");
      list = true;
      out.push(`<li>${inline(li[1]!)}</li>`);
    } else if (!line.trim()) {
      flush();
      endList();
    } else if (list && /^\s{2,}\S/.test(raw)) {
      out[out.length - 1] = out[out.length - 1]!.replace(/<\/li>$/, ` ${inline(line.trim())}</li>`); // a wrapped list item
    } else {
      endList();
      para.push(line.trim());
    }
  }
  flush();
  endList();
  return out.join("");
}
