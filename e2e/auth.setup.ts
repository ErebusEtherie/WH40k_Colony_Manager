import { test as setup, expect } from "@playwright/test";
import { STORAGE_STATE } from "../playwright.config";

/**
 * Authentication setup for the E2E suite.
 *
 * Signs a demo user in through the real login form (the same interaction a
 * human performs) and snapshots the session to e2e/.auth/user.json
 * (gitignored). The "chromium-authenticated" project rehydrates those
 * HttpOnly session cookies via storageState, so dashboard specs start
 * authenticated without repeating the login interaction. Anonymous specs
 * (not-logged-in.spec.ts) run in a separate project with a fresh context, so
 * this snapshot never leaks into them.
 *
 * Snapshotting only after the dashboard shell mounts guarantees the captured
 * cookie jar is one the API actually accepts: the shell only renders once the
 * /auth/me session probe succeeds.
 */
setup("authenticate as LordCaptain", async ({ page }) => {
  // Capture the login POST so we can assert it succeeded (200), not just that
  // the UI moved on.
  const loginResponse = page.waitForResponse(
    (res) =>
      res.url().includes("/api/v1/auth/login") &&
      res.request().method() === "POST"
  );

  await page.goto("/");

  await page.locator("#login-username").fill("LordCaptain");
  await page.locator("#login-password").fill("TestP@ss123");
  await page.locator("#login-submit-button").click();

  const response = await loginResponse;
  expect(response.status()).toBe(200);

  // Dashboard shell mounted → session established → safe to snapshot.
  await expect(page.locator("#header-logout-button")).toBeVisible();

  await page.context().storageState({ path: STORAGE_STATE });
});
