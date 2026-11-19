import { expect, test } from "@playwright/test";

test("sidebar groups navigation and keeps the demo independent of workspace APIs", async ({
  page,
}, testInfo) => {
  const calls: string[] = [];
  page.on("request", (request) => {
    if (request.url().includes("/api/v1/") || request.url().includes("/auth/"))
      calls.push(request.url());
  });
  await page.goto("/demo");
  if (testInfo.project.name === "mobile")
    await page.getByRole("button", { name: "Open menu" }).click();
  if (testInfo.project.name === "mobile")
    await expect(page.locator(".mobile-close")).toBeFocused();
  await expect(page.getByText("YOUR STUDIO, ORGANISED")).toBeVisible();
  await expect(page.getByText("A working idea, made visible.")).toHaveCount(0);
  const nav = page.getByRole("navigation", { name: "Main navigation" });
  await expect(nav.getByText("STUDIO SETUP")).toBeVisible();
  await expect(nav.getByRole("link", { name: "Overview" })).toHaveAttribute(
    "aria-current",
    "page",
  );
  await expect(
    nav.getByRole("link", { name: "Review queue", exact: true }),
  ).toBeVisible();
  expect(calls).toEqual([]);
  if (testInfo.project.name === "mobile") {
    await page.keyboard.press("Escape");
    await expect(page.getByRole("button", { name: "Open menu" })).toBeFocused();
    await expect(nav).toBeHidden();
  }
});

test("workspace badge uses the pending total", async ({ page }, testInfo) => {
  await page.route("**/auth/me", (route) =>
    route.fulfill({ json: { authenticated: true } }),
  );
  await page.route("**/api/v1/agent-runs?**", (route) =>
    route.fulfill({ json: { items: [], total: 7, limit: 1, offset: 0 } }),
  );
  await page.goto("/workspace/reviews");
  if (testInfo.project.name === "mobile")
    await page.getByRole("button", { name: "Open menu" }).click();
  await expect(
    page
      .getByRole("navigation", { name: "Main navigation" })
      .getByLabel("7 awaiting review"),
  ).toBeVisible();
});
