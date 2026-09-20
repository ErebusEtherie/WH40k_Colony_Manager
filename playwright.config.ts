import { defineConfig, devices } from "@playwright/test";

/**
 * E2E configuration for WH40k Colony Manager.
 *
 * The test target is the self-contained mock stack (`npm run dev` =
 * `tsx server.ts`): an Express server on :3000 that serves the Vite SPA AND a
 * cookie-authenticated mock of the FastAPI backend on the same origin
 * (`/api/v1/*`, mirroring the real backend's auth/CSRF behavior). Using the
 * mock keeps E2E hermetic — no Python backend, database, or seeded users
 * required — and is the documented path for UI work ("npm run dev:mock" in
 * README).
 *
 * VITE_API_BASE_URL is forced to the same :3000 origin so the SPA talks to the
 * mock. Without this override the gitignored `.env.local` would point the SPA
 * at the real backend on :8000. Process-env VITE_ vars win over `.env` files
 * in Vite (dotenv never overwrites an existing process.env entry), so the
 * override is deterministic.
 *
 * Three projects consume this stack (see `projects`): a `setup` project that
 * performs a real login and snapshots the session to e2e/.auth/user.json, an
 * authenticated project that rehydrates that snapshot (no repeated login
 * interaction per spec), and an anonymous project with a fresh, cookie-less
 * context. Specs are routed to a project by filename.
 */
// Where the auth setup project snapshots its session (storage state). The
// authenticated project rehydrates these HttpOnly session cookies via
// storageState. e2e/.auth/ is gitignored, so the snapshot — which contains
// live session tokens — is never committed.
export const STORAGE_STATE = "e2e/.auth/user.json";

export default defineConfig({
  testDir: "./e2e",
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  workers: process.env.CI ? 2 : undefined,
  reporter: [["list"], ["html", { open: "never" }]],
  outputDir: "test-results",
  use: {
    baseURL: "http://localhost:3000",
    trace: "on-first-retry",
    screenshot: "only-on-failure",
    video: "retain-on-failure",
  },
  projects: [
    // Performs a real login through the browser and saves the session cookies
    // to STORAGE_STATE. Named .setup.ts (not .spec.ts) so the test-runner
    // projects below never pick it up themselves; only this project matches.
    {
      name: "setup",
      testMatch: /auth\.setup\.ts/,
    },
    {
      // Logged-in scenarios. Depends on the setup project, which must finish
      // and write STORAGE_STATE before any of these workers start.
      name: "chromium-authenticated",
      testMatch: /dashboard\.spec\.ts/,
      use: {
        ...devices["Desktop Chrome"],
        storageState: STORAGE_STATE,
      },
      dependencies: ["setup"],
    },
    {
      // Anonymous scenarios keep a genuinely fresh context — no storage state
      // and no cookies, mirroring a first-time visitor. Deliberately does NOT
      // depend on setup or reuse its snapshot.
      name: "chromium-anonymous",
      testMatch: /not-logged-in\.spec\.ts/,
      use: { ...devices["Desktop Chrome"] },
    },
  ],
  webServer: {
    command: "npm run dev",
    // Poll this endpoint until the mock (SPA + API) is accepting traffic.
    // /api/v1/health requires no session.
    url: "http://localhost:3000/api/v1/health",
    reuseExistingServer: !process.env.CI,
    timeout: 120_000,
    env: {
      VITE_API_BASE_URL: "http://localhost:3000/api/v1",
    },
  },
});
