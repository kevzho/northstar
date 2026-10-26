/**
 * What the advisor actually emitted, and what a student actually saw.
 *
 * The answer was rendered with whitespace-pre-wrap, so "**Simons Summer
 * Research Program**" reached the student as asterisks around a name.
 */
import { describe, expect, it } from "vitest";
import { parseBlocks, spans } from "./plain-text";

describe("spans", () => {
  it("pulls a bold run out without leaving the markers behind", () => {
    expect(spans("- **Simons Summer Research Program** - an interdisciplinary")).toEqual([
      { text: "- ", bold: false },
      { text: "Simons Summer Research Program", bold: true },
      { text: " - an interdisciplinary", bold: false },
    ]);
  });

  it("leaves a plain line alone", () => {
    expect(spans("You mentioned debate and biology.")).toEqual([
      { text: "You mentioned debate and biology.", bold: false },
    ]);
  });

  it("does not treat a lone asterisk as a marker", () => {
    expect(spans("a * b")).toEqual([{ text: "a * b", bold: false }]);
  });
});

describe("parseBlocks", () => {
  it("separates paragraphs from a bullet list", () => {
    const blocks = parseBlocks(
      "You mentioned debate and biology.\n\n- **Simons** - computational biology\n- **MITES** - engineering",
    );
    expect(blocks.map((b) => b.kind)).toEqual(["paragraph", "list"]);
    expect(blocks[1].kind === "list" && blocks[1].items).toHaveLength(2);
  });

  it("joins wrapped lines into one paragraph", () => {
    const blocks = parseBlocks("one line\nstill the same sentence");
    expect(blocks).toHaveLength(1);
    expect(blocks[0].kind === "paragraph" && blocks[0].spans[0].text).toBe(
      "one line still the same sentence",
    );
  });

  it("drops heading markers and backticks rather than printing them", () => {
    const blocks = parseBlocks("## Directions\n\n`code` style");
    const text = blocks
      .map((b) => (b.kind === "paragraph" ? b.spans.map((s) => s.text).join("") : ""))
      .join(" ");
    expect(text).toContain("Directions");
    expect(text).not.toContain("#");
    expect(text).not.toContain("`");
  });

  it("cannot produce a tag from model output", () => {
    const blocks = parseBlocks("<script>alert(1)</script> and **bold**");
    const flat = JSON.stringify(blocks);
    // The text survives as TEXT; nothing here is ever interpreted as markup,
    // because the renderer builds elements rather than setting innerHTML.
    expect(flat).toContain("script");
    expect(blocks[0].kind).toBe("paragraph");
  });

  it("handles an empty answer without throwing", () => {
    expect(parseBlocks("")).toEqual([]);
  });
});
