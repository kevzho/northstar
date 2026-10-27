/**
 * FastAPI's `detail`, as a sentence a student can read.
 *
 * It is a string when we raise HTTPException ourselves, and an ARRAY of
 * `{loc, msg, type}` objects when FastAPI rejects a request body. The old code
 * annotated it `string` and interpolated it, so every validation error reached
 * the UI as the literal text "[object Object]", which is what a student saw
 * when "My interests are broader" failed: a screen telling them nothing at all
 * about what went wrong, on the one screen that was supposed to explain itself.
 *
 * A type annotation is not a parse. This reads whatever actually arrived.
 */
export function readDetail(detail: unknown): string {
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail)) {
    const parts = detail
      .map((item) => {
        if (typeof item === "string") return item;
        if (item && typeof item === "object" && "msg" in item) {
          const where = Array.isArray((item as { loc?: unknown[] }).loc)
            ? (item as { loc: unknown[] }).loc.slice(1).join(".")
            : "";
          const msg = String((item as { msg: unknown }).msg);
          return where ? `${where}: ${msg}` : msg;
        }
        return "";
      })
      .filter(Boolean);
    return parts.join("; ");
  }
  if (detail && typeof detail === "object") {
    const msg = (detail as { msg?: unknown; message?: unknown });
    if (msg.msg) return String(msg.msg);
    if (msg.message) return String(msg.message);
  }
  return "";
}
