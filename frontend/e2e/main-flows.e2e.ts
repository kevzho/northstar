/**
 * The flows a student actually walks, end to end in a real browser.
 *
 * The backend is mocked (e2e/mock-api.ts), so these test the frontend's half
 * of each flow: that the pages connect, that the right requests go out, and
 * that what comes back is shown. The backend's half has its own suite.
 */
import { expect, test } from "@playwright/test";
import { mockBackend, OPPORTUNITIES } from "./mock-api";
import { chartAPath } from "./helpers";

test("a new student goes from the assessment to a charted plan", async ({ page }) => {
  await mockBackend(page);
  const profileSync = page.waitForRequest((r) => r.url().endsWith("/assessment-profile") && r.method() === "POST");
  const pathSync = page.waitForRequest((r) => r.url().endsWith("/chosen-path") && r.method() === "POST");

  await chartAPath(page);

  // The trait scores the assessment computed reach the backend.
  const sent = (await profileSync).postDataJSON() as { trait_scores: Record<string, number> };
  expect(Object.keys(sent.trait_scores).length).toBeGreaterThan(0);
  expect((await pathSync).postDataJSON()).toHaveProperty("archetype_id");

  await expect(page.getByRole("heading", { name: "30-day plan" })).toBeVisible();
  // The roadmap from the API is drawn, application step included.
  await expect(page.getByText("Learn Python basics with a genomics dataset").first()).toBeVisible();
  await expect(page.getByText("Email two lab coordinators about summer openings").first()).toBeVisible();
  await expect(page.getByRole("link", { name: OPPORTUNITIES[0].title }).first()).toBeVisible();
});

test("extending the path shows the steps the API returns", async ({ page }) => {
  await mockBackend(page, {
    overrides: {
      "POST /roadmap/extend": (route) =>
        route.fulfill({
          json: {
            steps: [
              { title: "Present your analysis at a local science fair", detail: "Bring the poster." },
              { title: "Ask your lab mentor for a recommendation letter", detail: "Two weeks ahead." },
            ],
            added: 2,
            room_left: 4,
          },
        }),
    },
  });
  await chartAPath(page);

  const request = page.waitForRequest((r) => r.url().endsWith("/roadmap/extend"));
  await page.getByRole("button", { name: "Extend the path" }).click();
  expect((await request).postDataJSON()).toMatchObject({ scope: "path" });

  await expect(page.getByText("Present your analysis at a local science fair").first()).toBeVisible();
  await expect(page.getByText("Ask your lab mentor for a recommendation letter").first()).toBeVisible();
});

test("the dashboard lists matches and opens one", async ({ page }) => {
  await mockBackend(page);
  await page.goto("/dashboard");

  const top = OPPORTUNITIES[0];
  await page.getByRole("link", { name: new RegExp(top.title.slice(0, 40)) }).first().click();
  await page.waitForURL(`**/opportunities/${top.id}`);
  await expect(page.getByRole("heading", { name: top.title })).toBeVisible();
  await expect(page.getByText(top.host).first()).toBeVisible();
});

test("a visitor who opens a signed-in page is sent to sign in", async ({ page }) => {
  await mockBackend(page, { signedIn: false });
  await page.goto("/dashboard");
  await page.waitForURL(/\/login/);
});
