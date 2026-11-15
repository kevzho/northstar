/**
 * No page scrolls sideways on a phone.
 *
 * Mobile layout was never signed off (docs/TASK_BOARD.md), and the failure it
 * guards against is silent on a laptop: one long title or a fixed-width grid
 * pushes the page past 390px and the whole screen pans left and right. The
 * check names the elements that stick out, so a failure says what to fix.
 */
import { expect, test, type Page } from "@playwright/test";
import { mockBackend } from "./mock-api";
import { chartAPath } from "./helpers";

// `charted` pages need a finished assessment and a chosen path first, or they
// render their empty state and the check would pass on a page with nothing in it.
const PAGES: { path: string; signedIn: boolean; charted?: boolean; ready: RegExp }[] = [
  { path: "/", signedIn: false, ready: /every student deserves a north star/i },
  { path: "/assessment", signedIn: false, ready: /twenty prompts/i },
  { path: "/faq", signedIn: false, ready: /what is northstar/i },
  { path: "/dashboard", signedIn: true, ready: /summer science research fellowship/i },
  { path: "/opportunities", signedIn: true, ready: /regional science and engineering fair/i },
  { path: "/profile", signedIn: true, charted: true, ready: /your details/i },
  { path: "/futures", signedIn: true, charted: true, ready: /chart this path/i },
  { path: "/plan", signedIn: true, charted: true, ready: /learn python basics/i },
];

async function overflowing(page: Page) {
  return page.evaluate(() => {
    const width = document.documentElement.clientWidth;
    const offenders: string[] = [];
    for (const el of Array.from(document.body.querySelectorAll<HTMLElement>("*"))) {
      const rect = el.getBoundingClientRect();
      if (rect.width === 0 || rect.right <= width + 1) continue;
      // Content inside a scroll container (a carousel, a code block, a zoomable
      // map) is allowed to be wider; only the page itself must not scroll.
      let clipped = false;
      for (let p = el.parentElement; p && p !== document.body; p = p.parentElement) {
        const style = getComputedStyle(p);
        if (/(auto|scroll|hidden|clip)/.test(style.overflowX)) {
          clipped = true;
          break;
        }
      }
      if (clipped || getComputedStyle(el).position === "fixed") continue;
      const label = `${el.tagName.toLowerCase()}${el.className && typeof el.className === "string" ? "." + el.className.trim().split(/\s+/).slice(0, 4).join(".") : ""}`;
      offenders.push(`${label} right=${Math.round(rect.right)} "${(el.innerText || "").slice(0, 40).replace(/\s+/g, " ")}"`);
    }
    return {
      scrollWidth: document.documentElement.scrollWidth,
      width,
      offenders: offenders.slice(0, 8),
    };
  });
}

test.describe("phone layout", () => {
  test.skip(({ isMobile }) => !isMobile, "phone viewport only");

  for (const { path, signedIn, charted, ready } of PAGES) {
    test(`${path} does not scroll sideways`, async ({ page }) => {
      await mockBackend(page, { signedIn });
      if (charted) await chartAPath(page);
      await page.goto(path);
      await expect(page.getByText(ready).first()).toBeVisible();
      await page.waitForLoadState("networkidle");

      const result = await overflowing(page);
      expect(result.offenders, `page is ${result.scrollWidth}px wide on a ${result.width}px screen`).toEqual([]);
      expect(result.scrollWidth).toBeLessThanOrEqual(result.width);
    });
  }

  // The check above forgives anything inside an overflow container, and some
  // page roots clip sideways overflow. There the nav did not widen the page,
  // it was cut off: "Profile" and "People" were simply not on the screen.
  for (const path of ["/dashboard", "/plan"]) {
    test(`every nav link on ${path} can be reached`, async ({ page }) => {
      await mockBackend(page);
      if (path === "/plan") await chartAPath(page);
      else await page.goto(path);
      const links = page.getByRole("navigation", { name: "Sections" }).getByRole("link");
      await expect(links).toHaveCount(6);
      for (const link of await links.all()) {
        await link.scrollIntoViewIfNeeded();
        await expect(link).toBeInViewport({ ratio: 1 });
      }
    });
  }
});

test("on a phone the current page's nav link starts on screen", async ({ page, isMobile }) => {
  test.skip(!isMobile, "phone viewport only");
  await mockBackend(page);
  await page.goto("/discover");
  const current = page.getByRole("navigation", { name: "Sections" }).getByRole("link", { name: "People" });
  await expect(current).toHaveAttribute("aria-current", "page");
  await expect(current).toBeInViewport({ ratio: 1 });
});
