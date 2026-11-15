import { defineConfig, devices } from "@playwright/test";

/**
 * End-to-end tests against the production build, with the backend mocked
 * (e2e/mock-api.ts). Build first with the placeholder env CI uses:
 *
 *   NEXT_PUBLIC_SUPABASE_URL=https://placeholder.supabase.co \
 *   NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY=placeholder-anon-key \
 *   NEXT_PUBLIC_API_URL=http://localhost:8000 npx next build
 *   npm run e2e
 *
 * Files end in .e2e.ts, not .spec.ts, so Vitest's default glob leaves them alone.
 */
const PORT = 3100;

export default defineConfig({
  testDir: "e2e",
  testMatch: "**/*.e2e.ts",
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 1 : 0,
  reporter: process.env.CI ? "github" : "list",
  use: {
    baseURL: `http://localhost:${PORT}`,
    trace: "retain-on-failure",
  },
  projects: [
    { name: "desktop", use: { ...devices["Desktop Chrome"] } },
    // iPhone 13's 390px viewport, driven by Chromium so CI installs one browser.
    {
      name: "phone",
      use: { ...devices["iPhone 13"], defaultBrowserType: "chromium", browserName: "chromium" },
    },
  ],
  webServer: {
    command: `npx next start -p ${PORT}`,
    url: `http://localhost:${PORT}`,
    reuseExistingServer: !process.env.CI,
    timeout: 60_000,
  },
});
