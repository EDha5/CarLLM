const { test, expect } = require("@playwright/test");

test("token progress counter updates while awaiting response", async ({ page }) => {
  await page.goto("/");

  await page.getByRole("button", { name: "Log in with Google" }).click();
  await expect(page.getByRole("heading", { name: "Dashboard" })).toBeVisible();

  await page.evaluate(() => {
    window.__carllmE2E?.setView("chat");
    window.__carllmE2E?.setChatProgress({ awaiting: true, tokens: 0 });
  });

  const status = page.getByText("Working on it…");
  await expect(status).toBeVisible();
  await expect(page.getByText("0 total tokens")).toBeVisible();
  await expect(page.locator(".spinner")).toBeVisible();

  await page.evaluate(() => {
    window.__carllmE2E?.setChatProgress({ awaiting: true, tokens: 12 });
  });
  await expect(page.getByText("12 total tokens")).toBeVisible();

  await page.evaluate(() => {
    window.__carllmE2E?.setChatProgress({ awaiting: true, tokens: 48 });
  });
  await expect(page.getByText("48 total tokens")).toBeVisible();

  await page.evaluate(() => {
    window.__carllmE2E?.setChatProgress({ awaiting: false, tokens: 52 });
  });
  await expect(status).toBeHidden();
});
