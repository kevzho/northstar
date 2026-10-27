/**
 * Error details that a student can actually read.
 *
 * `detail` is a string when the backend raises HTTPException and an ARRAY of
 * {loc, msg, type} objects when FastAPI rejects a request body. The client
 * annotated it `string` and interpolated it, so a validation error arrived in
 * the UI as the literal text "[object Object]", which is exactly what someone
 * saw when "My interests are broader" failed. A type annotation is not a parse.
 */

import { describe, expect, it } from "vitest";
import { readDetail } from "./error-detail";

describe("readDetail", () => {
  it("passes a plain string through", () => {
    expect(readDetail("Your current path is unchanged.")).toBe(
      "Your current path is unchanged.",
    );
  });

  it("never returns [object Object] for a FastAPI validation array", () => {
    const fastapi = [
      { type: "missing", loc: ["body", "reason"], msg: "Field required" },
    ];
    const out = readDetail(fastapi);
    expect(out).not.toContain("[object Object]");
    expect(out).toContain("Field required");
    expect(out).toContain("reason");
  });

  it("joins several validation errors", () => {
    const out = readDetail([
      { loc: ["body", "a"], msg: "Field required" },
      { loc: ["body", "b"], msg: "Input should be a valid string" },
    ]);
    expect(out).toBe("a: Field required; b: Input should be a valid string");
  });

  it("handles a bare object with a message", () => {
    expect(readDetail({ msg: "Too many requests" })).toBe("Too many requests");
    expect(readDetail({ message: "Gateway timeout" })).toBe("Gateway timeout");
  });

  it("returns empty for shapes it cannot read, so the status speaks instead", () => {
    for (const value of [undefined, null, 42, {}, [], [{}]]) {
      expect(readDetail(value)).toBe("");
    }
  });
});
