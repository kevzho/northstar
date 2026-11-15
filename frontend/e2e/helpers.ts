import { expect, type Page } from "@playwright/test";

/**
 * Answer all twenty assessment prompts the way a student does, by clicking.
 * Answers persist to localStorage on every change, so this leaves the browser
 * in the state every downstream page (profile, futures, plan) reads.
 */
export async function takeAssessment(page: Page): Promise<void> {
  await page.goto("/assessment");
  const groups = page.getByRole("radiogroup");
  await expect(groups.first()).toBeVisible();
  const count = await groups.count();
  expect(count).toBe(20);
  for (let i = 0; i < count; i++) {
    const options = groups.nth(i).getByRole("radio");
    // Vary the picks so the trait profile is not flat.
    await options.nth((i * 2) % (await options.count())).check({ force: true });
  }
}

/** Assessment, profile, futures, "Chart this path": the route to /plan. */
export async function chartAPath(page: Page): Promise<void> {
  await takeAssessment(page);
  await page.getByRole("button", { name: "Continue to profile" }).click();
  await page.waitForURL("**/profile");
  await page.getByRole("button", { name: /generate futures/i }).first().click();
  await page.waitForURL("**/futures");
  await page.getByRole("button", { name: "Chart this path" }).first().click();
  await page.waitForURL("**/plan");
}
