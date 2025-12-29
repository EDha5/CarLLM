const { test, expect } = require("@playwright/test");

test("google login toggles to dashboard", async ({ page }) => {
  await page.goto("/");

  await page.getByRole("button", { name: "Log in with Google" }).click();

  await expect(page.getByRole("heading", { name: "Dashboard" })).toBeVisible();
  await expect(page.getByRole("button", { name: "Log out" })).toBeVisible();

  await page.getByRole("button", { name: "Log out" }).click();

  await expect(
    page.getByRole("heading", {
      name: "Turn symptoms into clear repair guidance in minutes.",
    })
  ).toBeVisible();
});
