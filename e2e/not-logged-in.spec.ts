import { test, expect } from "@playwright/test";

/**
 * Anonymous visitor — the first E2E scenario.
 *
 * A fresh browser context carries no session cookies. Entering the page must
 * therefore land on the login screen: the backend's /auth/me returns 401
 * without an access-token cookie, the app's session probe fails, and App gates
 * the dashboard behind a session. The assertion that /auth/me actually got a
 * 401 (rather than a network error) keeps this test meaningful — it proves the
 * login screen appears because the backend rejected the anonymous request.
 */
test.describe("not logged in", () => {
  test("is shown the login screen when entering the page without a session", async ({
    page,
  }) => {
    // The unauthenticated session probe must be rejected with 401 — that
    // rejection is what flips the SPA from the dashboard gate to the login
    // screen.
    const authMeResponse = page.waitForResponse((res) =>
      res.url().includes("/api/v1/auth/me")
    );

    await page.goto("/");

    const authMe = await authMeResponse;
    expect(authMe.status()).toBe(401);

    // --- Login screen is rendered ---
    await expect(
      page.getByRole("heading", { name: "ROGUE TRADER" })
    ).toBeVisible();
    await expect(
      page.getByText("Administrative Terminal • Rogue Trader Colony Manager")
    ).toBeVisible();
    await expect(
      page.getByText("SECURITY CLEARANCE & IDENTITY CIPHER")
    ).toBeVisible();

    // The credential entry form is present and enabled.
    await expect(page.locator("#login-username")).toBeVisible();
    await expect(page.locator("#login-password")).toBeVisible();
    await expect(page.locator("#login-submit-button")).toContainText(
      "Access Colonial Registry"
    );

    // --- The dashboard must NOT be shown to anonymous visitors ---
    // Header logout control and navigation tabs only exist once a session is
    // established, so their absence confirms we never mounted the app shell.
    await expect(page.locator("#header-logout-button")).toHaveCount(0);
    await expect(page.locator("#nav-tab-overview")).toHaveCount(0);
  });
});
