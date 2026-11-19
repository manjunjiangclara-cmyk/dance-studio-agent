import { test, expect } from "@playwright/test";
import examples from "../src/data/examples.v1.json" with { type: "json" };

const run = examples.agent_runs.find((item) => item.revision === 2)!;
const route = {
  intents: ["enrolment", "general_enquiry"],
  reason:
    "The student asks to add a regular Monday class and asks about its location.",
  needs_clarification: true,
};

test("queue and detail expose the saved classification", async ({ page }) => {
  await page.route("**/auth/me", (response) =>
    response.fulfill({
      json: {
        authenticated: true,
        user: { email: "owner@example.test" },
        csrf_token: "csrf",
      },
    }),
  );
  await page.route("**/api/v1/**", async (response) => {
    const path = new URL(response.request().url()).pathname.replace(
      "/api/v1",
      "",
    );
    const [resource, id, child] = path.slice(1).split("/");
    const current = {
      ...run,
      interpretation: {
        ...run.interpretation,
        routing: route,
        flow: "teacher_handoff",
      },
    };
    if (resource === "agent-runs")
      return response.fulfill({
        json: id
          ? current
          : {
              items: [
                {
                  ...current,
                  routing: route,
                  flow: "teacher_handoff",
                  student_name: "Alex Morgan",
                  student_email: "alex@example.test",
                  student_id: examples.students[0].id,
                  request_summary: "Add Monday",
                },
              ],
              total: 1,
              limit: 10,
              offset: 0,
            },
      });
    const table =
      resource === "sessions"
        ? examples.class_sessions
        : examples[resource as keyof typeof examples];
    if (resource === "conversations" && child === "messages") {
      const messages = examples.messages.filter(
        (m) => m.conversation_id === id,
      );
      return response.fulfill({
        json: {
          items: messages,
          total: messages.length,
          limit: 100,
          offset: 0,
        },
      });
    }
    if (Array.isArray(table)) {
      const rows = table as { id: string }[];
      let value: unknown = id
        ? rows.find((row) => row.id === id)
        : { items: rows, total: rows.length, limit: 100, offset: 0 };
      if (resource === "students" && id)
        value = {
          ...(value as object),
          current_enrolments: [],
          enrolment_history: [],
        };
      return response.fulfill({ json: value });
    }
    return response.fulfill({ status: 404, json: {} });
  });
  await page.goto("/workspace/reviews");
  const row = page.locator(".run-row");
  await expect(row.locator(".intent-badge")).toHaveText([
    "Enrolment change",
    "General enquiry",
  ]);
  await expect(row.getByText("Intent:", { exact: true })).toHaveCount(0);
  await expect(row).not.toContainText("alex@example.test");
  await expect(row.getByText("Add Monday", { exact: true })).toBeVisible();
  await row.click();
  const supporting = page.locator(".review-support");
  await expect(supporting).not.toHaveAttribute("open", "");
  await supporting.locator(":scope > summary").click();
  const classification = page.getByRole("region", {
    name: "Classification",
    exact: true,
  });
  await expect(classification).toContainText("Enrolment change");
  await expect(
    classification.getByText("Intent:", { exact: true }),
  ).toBeVisible();
  const badge = classification.getByText("Enrolment change", { exact: true });
  await expect(badge).toBeInViewport();
  await expect(supporting).toHaveAttribute("open", "");
  await expect(classification).toContainText("General enquiry");
  await expect(classification).toContainText("Teacher handling");
  await expect(classification).toContainText("Needed");
  await expect(classification).toContainText(route.reason);
  const typography = await classification.evaluate((panel) => {
    const heading = getComputedStyle(panel.querySelector("h2")!);
    const detail = getComputedStyle(panel.querySelector("dd")!);
    return {
      headingSize: parseFloat(heading.fontSize),
      detailSize: parseFloat(detail.fontSize),
      headingWeight: parseInt(heading.fontWeight),
      detailWeight: parseInt(detail.fontWeight),
    };
  });
  expect(typography.headingSize).toBeGreaterThan(typography.detailSize * 1.4);
  expect(typography.headingWeight).toBeGreaterThan(typography.detailWeight);
  await expect(page.locator(".developer-panel")).not.toHaveAttribute(
    "open",
    "",
  );
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= innerWidth,
    ),
  ).toBe(true);
});

test("public classification is visible without API access", async ({
  page,
}) => {
  const calls: string[] = [];
  page.on("request", (request) => {
    if (/\/(api|auth)\//.test(request.url())) calls.push(request.url());
  });
  await page.goto(`/demo/reviews/${run.id}`);
  await page.locator(".review-support > summary").click();
  const classification = page.getByRole("region", {
    name: "Classification",
    exact: true,
  });
  await expect(classification).toContainText("Makeup");
  await expect(classification).toContainText("Makeup workflow");
  await expect(classification).toContainText("Not flagged by router");
  expect(calls).toEqual([]);
});

test("classification is readable in supporting context at intermediate screen widths", async ({
  page,
}) => {
  await page.setViewportSize({ width: 1100, height: 800 });
  await page.goto(`/demo/reviews/${run.id}`);
  await page.locator(".review-support > summary").click();
  const classification = page.getByRole("region", {
    name: "Classification",
    exact: true,
  });
  await expect(
    classification.getByRole("heading", {
      name: "Classification",
      exact: true,
    }),
  ).toBeInViewport();
  await expect(
    classification.locator(".intent-badge").first(),
  ).toBeInViewport();
  await expect(
    classification.getByText("Intent:", { exact: true }),
  ).toBeInViewport();
  const panel = await classification.boundingBox();
  const support = await page.locator(".review-support").boundingBox();
  expect(panel!.y).toBeGreaterThanOrEqual(support!.y);
});

test("legacy runs do not invent a classification", async ({ page }) => {
  await page.route("**/auth/me", (response) =>
    response.fulfill({
      json: { authenticated: true, user: { email: "owner@example.test" } },
    }),
  );
  await page.route("**/api/v1/**", async (response) => {
    const path = new URL(response.request().url()).pathname;
    if (path.includes("/agent-runs/"))
      return response.fulfill({ json: { ...run, interpretation: {} } });
    if (path.includes("/conversations/") && !path.endsWith("/messages"))
      return response.fulfill({
        json: examples.conversations.find((c) => c.id === run.conversation_id),
      });
    if (path.includes("/students/"))
      return response.fulfill({
        json: { ...examples.students[0], current_enrolments: [] },
      });
    return response.fulfill({
      json: { items: [], total: 0, limit: 100, offset: 0 },
    });
  });
  await page.goto(`/workspace/reviews/${run.id}`);
  await page.locator(".review-support > summary").click();
  await expect(
    page.getByRole("region", { name: "Classification", exact: true }),
  ).toContainText("Classification was not recorded");
});
