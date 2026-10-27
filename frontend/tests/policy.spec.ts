import { test, expect } from "@playwright/test";

test("owner can edit, retry a failed save, and reload persisted policy", async ({
  page,
}) => {
  let policy = {
    version: "1",
    absence_notice_before_start: true,
    explanation: "Notice before class.",
    level_order: ["Beginner", "Intermediate"],
  };
  let failSave = true;
  await page.route("**/auth/me", (route) =>
    route.fulfill({
      json: {
        authenticated: true,
        user: { email: "owner@example.test" },
        csrf_token: "policy-csrf",
      },
    }),
  );
  await page.route("**/api/v1/policy", async (route) => {
    if (route.request().method() === "PUT") {
      expect(route.request().headers()["x-csrf-token"]).toBe("policy-csrf");
      if (failSave)
        return route.fulfill({
          status: 503,
          json: { error: { message: "Policy could not be saved." } },
        });
      policy = route.request().postDataJSON();
    }
    await route.fulfill({ json: policy });
  });
  await page.goto("/workspace/policy");
  await expect(page.getByLabel("Policy version")).toHaveValue("1");
  await expect(
    page.getByRole("button", { name: "Save policy" }),
  ).toBeDisabled();
  await page.getByLabel("Policy version").fill("2");
  await page
    .getByLabel("Require absence notice before the session starts")
    .uncheck();
  await page
    .getByLabel(/Class levels, easiest to most difficult/)
    .fill("Beginner\nIntermediate\nAdvanced");
  await page
    .getByLabel("Policy explanation")
    .fill("Teacher reviews each request.\nNo automatic entitlement.");
  // Navigation preserves unsaved edits when the owner chooses to stay.
  const menu = page.getByRole("button", { name: "Open menu" });
  if (await menu.isVisible()) await menu.click();
  await page.getByRole("link", { name: "Database", exact: true }).click();
  await expect(page.getByRole("dialog")).toBeVisible();
  await page.getByRole("button", { name: "Stay here" }).click();
  const closeMenu = page.getByRole("button", { name: "Close menu" });
  if (await closeMenu.isVisible()) await closeMenu.click();
  await page.getByRole("button", { name: "Save policy" }).click();
  await expect(page.getByRole("alert")).toContainText(
    "Policy could not be saved",
  );
  await expect(page.getByLabel("Policy version")).toHaveValue("2");
  failSave = false;
  await page.getByRole("button", { name: "Save policy" }).click();
  await expect(page.getByRole("status")).toContainText("Policy saved");
  expect(policy).toEqual({
    version: "2",
    absence_notice_before_start: false,
    explanation: "Teacher reviews each request.\nNo automatic entitlement.",
    level_order: ["Beginner", "Intermediate", "Advanced"],
  });
  await page.reload();
  await expect(page.getByLabel("Policy version")).toHaveValue("2");
  await expect(
    page.getByLabel(/Class levels, easiest to most difficult/),
  ).toHaveValue("Beginner\nIntermediate\nAdvanced");
  await expect(
    page.getByLabel("Require absence notice before the session starts"),
  ).not.toBeChecked();
  await page.getByLabel("Policy explanation").fill("Unsaved replacement");
  await page.getByRole("button", { name: "Discard changes" }).click();
  await expect(page.getByLabel("Policy explanation")).toHaveValue(
    policy.explanation,
  );
});

test("policy load errors can be retried", async ({ page }) => {
  await page.route("**/auth/me", (route) =>
    route.fulfill({
      json: {
        authenticated: true,
        user: { email: "owner@example.test" },
        csrf_token: "csrf",
      },
    }),
  );
  let fail = true;
  await page.route("**/api/v1/policy", (route) =>
    route.fulfill(
      fail
        ? { status: 503, json: { error: { message: "Policy unavailable" } } }
        : {
            json: {
              version: "1",
              absence_notice_before_start: true,
              explanation: "Example",
              level_order: [],
            },
          },
    ),
  );
  await page.goto("/workspace/policy");
  await expect(page.getByRole("alert")).toContainText("Policy unavailable");
  fail = false;
  await page.getByRole("button", { name: "Try loading again" }).click();
  await expect(page.getByLabel("Policy version")).toHaveValue("1");
});

test("public policy example is read-only and fits the viewport", async ({
  page,
}) => {
  const calls: string[] = [];
  page.on("request", (request) => {
    if (/\/(api|auth)\//.test(request.url())) calls.push(request.url());
  });
  await page.goto("/demo/policy");
  await expect(
    page.getByRole("heading", { name: "Policy", exact: true }),
  ).toBeVisible();
  await expect(page.getByLabel("Policy version")).toBeDisabled();
  await expect(page.getByLabel("Policy explanation")).toBeDisabled();
  await expect(page.getByRole("button", { name: "Save policy" })).toHaveCount(
    0,
  );
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= innerWidth,
    ),
  ).toBe(true);
  expect(calls).toEqual([]);
});
