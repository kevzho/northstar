/**
 * The small subset of markdown a model emits, turned into blocks.
 *
 * The advisor's answer was rendered with `whitespace-pre-wrap`, so when the
 * model wrote "**Simons Summer Research Program**" the student read the
 * asterisks. The prompt now asks for plain text, which mostly works and will
 * not always: a model told not to use markdown still reaches for a bullet or a
 * bold run when it is listing things.
 *
 * So the prompt asks and this copes. Deliberately tiny, and deliberately NOT a
 * markdown library: the output goes straight into a page read by minors, the
 * input is model output, and the safe way to render untrusted text is to build
 * elements from parsed pieces rather than to hand anything an HTML string.
 * Nothing here can emit a tag.
 */

export type Span = { text: string; bold: boolean };
export type Block =
  | { kind: "paragraph"; spans: Span[] }
  | { kind: "list"; items: Span[][] };

/** Split one line into bold and plain runs. */
export function spans(line: string): Span[] {
  const out: Span[] = [];
  // **bold** or __bold__, non-greedy, never spanning a blank line.
  const pattern = /(\*\*|__)(.+?)\1/g;
  let last = 0;
  let match: RegExpExecArray | null;
  while ((match = pattern.exec(line)) !== null) {
    if (match.index > last) {
      out.push({ text: line.slice(last, match.index), bold: false });
    }
    out.push({ text: match[2], bold: true });
    last = match.index + match[0].length;
  }
  if (last < line.length) out.push({ text: line.slice(last), bold: false });
  return out.length ? out : [{ text: line, bold: false }];
}

/** Strip the markers that carry no meaning once the text is rendered. */
function clean(line: string): string {
  return line
    .replace(/^#{1,6}\s+/, "")      // headings become plain lines
    .replace(/`/g, "")              // backticks are never wanted here
    .trimEnd();
}

export function parseBlocks(text: string): Block[] {
  const blocks: Block[] = [];
  let paragraph: string[] = [];
  let items: string[] = [];

  const flushParagraph = () => {
    if (!paragraph.length) return;
    blocks.push({ kind: "paragraph", spans: spans(paragraph.join(" ")) });
    paragraph = [];
  };
  const flushList = () => {
    if (!items.length) return;
    blocks.push({ kind: "list", items: items.map(spans) });
    items = [];
  };

  for (const raw of (text || "").split("\n")) {
    const line = clean(raw);
    const bullet = /^\s*[-*•]\s+(.*)$/.exec(line);
    if (bullet) {
      flushParagraph();
      items.push(bullet[1]);
      continue;
    }
    if (!line.trim()) {
      flushParagraph();
      flushList();
      continue;
    }
    flushList();
    paragraph.push(line.trim());
  }
  flushParagraph();
  flushList();
  return blocks;
}
