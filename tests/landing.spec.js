const { test, expect } = require("@playwright/test");

test("landing page shows hero content", async ({ page }) => {
  await page.goto("/");

  await expect(
    page.getByRole("heading", {
      name: "Turn symptoms into clear repair guidance in minutes.",
    })
  ).toBeVisible();

  await expect(page.getByRole("button", { name: "Log in with Google" })).toBeVisible();
  await expect(page.getByRole("link", { name: "How It Works" })).toBeVisible();
});
