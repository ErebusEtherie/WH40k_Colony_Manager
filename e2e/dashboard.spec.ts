import { test, expect } from "@playwright/test";

/**
 * Logged-in dashboard — the second E2E scenario.
 *
 * Runs in the "chromium-authenticated" project, which rehydrates the session
 * cookies captured by e2e/auth.setup.ts (storageState) instead of entering
 * credentials in-page. Entering the page as an authenticated user must mount
 * the app shell (header logout, nav tabs) rather than the login screen.
 *
 * The /auth/me 200 assertion keeps this test meaningful: the dashboard
 * appears because the snapshotted cookie is actually accepted by the mock
 * backend — not because the SPA ignored auth and painted the shell anyway.
 */
test.describe("logged in", () => {
  test("is shown the dashboard when entering the page with an existing session", async ({
    page,
  }) => {
    // The rehydrated session cookie must authenticate against the mock. A 401
    // here would mean the storage-state snapshot is stale or wrong.
    const authMeResponse = page.waitForResponse((res) =>
      res.url().includes("/api/v1/auth/me")
    );

    await page.goto("/");

    const authMe = await authMeResponse;
    expect(authMe.status()).toBe(200);

    // --- App shell (header + nav) is rendered ---
    await expect(page.locator("#header-logout-button")).toBeVisible();
    await expect(page.locator("#nav-tab-overview")).toBeVisible();
    await expect(page.locator("#nav-tab-details")).toBeVisible();
    await expect(
      page.getByRole("button", { name: "Infrastructure & Plans" })
    ).toBeVisible();

    // --- The login screen must NOT be shown to an authenticated user ---
    await expect(page.getByRole("heading", { name: "ROGUE TRADER" })).toHaveCount(0);
    await expect(page.locator("#login-username")).toHaveCount(0);

    // --- The signed-in identity is surfaced (LordCaptain, colony_manager) ---
    await expect(page.getByText("LordCaptain", { exact: true })).toBeVisible();
    await expect(page.getByText("LORD CAPTAIN", { exact: true })).toBeVisible();

    // --- The Overview tab has loaded with seed colony data ---
    // Static dossier banner proves ColonyOverview mounted, which only happens
    // once colonies have loaded from the API and one is selected.
    await expect(
      page.getByText("IMPERIAL VALANCIUS EXPANSE LOGISTICS")
    ).toBeVisible();
    // The selected colony's name heads the dossier — target the h1, since
    // that name also appears in the header dropdown and footer.
    await expect(
      page.getByRole("heading", { name: "Dargonus Prime Apex" })
    ).toBeVisible();
  });
});
