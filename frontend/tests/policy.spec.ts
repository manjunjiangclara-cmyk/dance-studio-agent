import { test, expect } from "@playwright/test";

test("old rules links lead to documents", async ({ page }) => {
  await page.route("**/auth/me", (route) =>
    route.fulfill({
      json: {
        authenticated: true,
        user: { email: "owner@example.test" },
        csrf_token: "csrf",
      },
    }),
  );
  await page.route("**/api/v1/documents?*", (route) =>
    route.fulfill({ json: [] }),
  );
  await page.goto("/workspace/knowledge/rules");
  await expect(page).toHaveURL(/\/workspace\/knowledge\/documents$/);
  await expect(page.getByRole("heading", { name: "Documents" })).toBeVisible();
  await expect(
    page.getByRole("heading", { name: "Makeup settings" }),
  ).toHaveCount(0);
});

test("public policy link leads to documents", async ({ page }) => {
  await page.goto("/demo/policy");
  await expect(page).toHaveURL(/\/demo\/knowledge\/documents$/);
  await expect(page.getByRole("heading", { name: "Documents" })).toBeVisible();
  await expect(
    page.getByRole("heading", { name: "Makeup settings" }),
  ).toHaveCount(0);
});
