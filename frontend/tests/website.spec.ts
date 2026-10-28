import { test, expect, type Page } from "@playwright/test";
import examples from "../src/data/examples.v1.json" with { type: "json" };
import schema from "../src/data/schema.v1.json" with { type: "json" };

const alex = examples.students.find(
  (student) => student.display_name === "Alex Morgan",
)!;
const run = examples.agent_runs.find((item) => item.revision === 2)!;
const conversation = examples.conversations.find(
  (item) => item.id === run.conversation_id,
)!;
const session = examples.class_sessions.find((item) =>
  item.starts_at.startsWith("2027-02-13"),
)!;

test("public examples work without touching the workspace API", async ({
  page,
}, testInfo) => {
  const calls: string[] = [];
  page.on("request", (request) => {
    if (request.url().includes("/api/") || request.url().includes("/auth/"))
      calls.push(request.url());
  });
  await page.goto("/");
  await expect(
    page.getByRole("heading", { name: "A little more room to teach." }),
  ).toBeVisible();
  await page.screenshot({
    path: testInfo.outputPath("overview.png"),
    fullPage: true,
  });
  await page
    .getByRole("link", { name: "Explore the review queue", exact: true })
    .click();
  await page.getByLabel("Search enquiries").fill("Alex");
  await expect(page.locator(".run-row")).toHaveCount(2);
  await page.getByLabel("Filter by status").selectOption("awaiting_review");
  await expect(page.locator(".run-row")).toHaveCount(1);
  await page.locator(".run-row").click();
  await expect(
    page.getByRole("heading", { name: conversation.subject }),
  ).toBeVisible();
  await expect(
    page.getByText("Actually, Saturday 13 February would be better.", {
      exact: true,
    }),
  ).toBeVisible();
  await expect(
    page.getByRole("button", { name: "Approve and book class" }),
  ).toHaveCount(0);
  await expect(
    page.getByText("Read-only example.", { exact: false }),
  ).toBeVisible();
  await page.goto(`/demo/students/${alex.id}`);
  await expect(
    page.getByRole("heading", { name: "Alex Morgan" }),
  ).toBeVisible();
  await expect(
    page.getByRole("heading", { name: "Current enrolments" }),
  ).toBeVisible();
  await expect(page.getByLabel("Enrolments as of date")).toHaveCount(0);
  await expect(page.locator(".enrolment-history")).not.toHaveAttribute(
    "open",
    "",
  );
  await page.getByText("Full enrolment history", { exact: true }).click();
  await expect(page.locator(".enrolment-history")).toHaveAttribute("open", "");
  await expect(
    page.getByRole("heading", { name: "Confirmed sessions" }),
  ).toBeVisible();
  await page.goto(`/demo/timetable?session=${session.id}`);
  await expect(
    page
      .locator(".session-roster")
      .getByRole("heading", { name: "Students", exact: true }),
  ).toBeVisible();
  await expect(page.getByText("Noah Ellis", { exact: true })).toBeVisible();
  await page.goto("/demo/database");
  await expect(
    page
      .getByRole("navigation", { name: "Database tables" })
      .getByRole("button"),
  ).toHaveCount(schema.tables.length);
  await expect(
    page.getByRole("region", { name: "students data" }),
  ).toContainText(alex.email);
  await page.goto("/demo/test-email");
  await page.getByRole("link", { name: "Open the resulting example" }).click();
  await expect(
    page.getByRole("heading", { name: conversation.subject }),
  ).toBeVisible();
  expect(calls).toEqual([]);
});

test("owner workspace requires sign-in and public API is protected", async ({
  page,
  request,
}) => {
  await page.goto("/workspace");
  await expect(
    page.getByRole("heading", { name: "Your review workspace" }),
  ).toBeVisible();
  await expect(page.getByLabel("Final response")).toHaveCount(0);
  expect((await request.get("/api/v1/students")).status()).toBe(401);
  expect((await request.get("/api/v1/database")).status()).toBe(401);
  expect((await request.get("/api/v1/database/students")).status()).toBe(401);
  expect(
    (
      await request.post("/api/v1/incoming-emails", {
        data: { from: "visitor@example.test", body: "Hello" },
      })
    ).status(),
  ).toBe(401);
});

async function mockWorkspace(
  page: Page,
  options: {
    conflict?: boolean;
    approval?: boolean;
    failIntake?: boolean;
  } = {},
) {
  let current = structuredClone(run);
  let responseBody: unknown;
  let intakeCount = 0;
  const messages = examples.messages.filter(
    (item) => item.conversation_id === run.conversation_id,
  );
  await page.route("**/auth/me", (route) =>
    route.fulfill({
      json: {
        authenticated: true,
        user: { email: "owner@example.test", name: "Owner" },
        csrf_token: "mock-csrf",
      },
    }),
  );
  await page.route("**/api/v1/**", async (route) => {
    const request = route.request(),
      url = new URL(request.url()),
      path = url.pathname.replace("/api/v1", "");
    if (request.method() === "POST") {
      expect(request.headers()["x-csrf-token"]).toBe("mock-csrf");
      if (path === "/incoming-emails") {
        intakeCount++;
        return options.failIntake
          ? route.abort("failed")
          : route.fulfill({ json: current });
      }
      if (path.endsWith("/review")) {
        responseBody = request.postDataJSON();
        if (options.conflict) {
          current = { ...current, revision: 3 };
          return route.fulfill({
            status: 409,
            json: {
              error: {
                message:
                  "This draft is no longer awaiting this review revision.",
              },
            },
          });
        }
        if (options.approval) {
          current = {
            ...current,
            status: "approved",
            approved_response_id: "mock-approved",
          };
          messages.push({
            ...messages[0],
            id: "mock-approved",
            kind: "teacher_response",
            body: (responseBody as { body: string }).body,
          });
        }
        return route.fulfill({ json: current });
      }
      return route.fulfill({ status: 400, json: {} });
    }
    if (path === `/agent-runs/${run.id}`)
      return route.fulfill({ json: current });
    if (path === `/conversations/${run.conversation_id}`)
      return route.fulfill({
        json: examples.conversations.find(
          (item) => item.id === run.conversation_id,
        ),
      });
    if (path === `/students/${alex.id}`)
      return route.fulfill({
        json: {
          ...alex,
          current_enrolments: [],
          enrolment_history: [],
          as_of: examples.as_of,
        },
      });
    const items = path.endsWith("/messages")
      ? messages
      : path === "/classes"
        ? examples.classes
        : path === "/sessions"
          ? examples.class_sessions.map((session) => ({
              ...session,
              students:
                current.status === "approved" &&
                session.id === current.draft_details.booking_session_id
                  ? [...new Set([...session.students, alex.id])]
                  : session.students,
            }))
          : path === "/locations"
            ? examples.locations
            : [];
    return route.fulfill({
      json: { items, total: items.length, limit: 100, offset: 0 },
    });
  });
  return { getBody: () => responseBody, getIntakeCount: () => intakeCount };
}

test("owner approval submits edited text and the reviewed revision", async ({
  page,
}) => {
  const mock = await mockWorkspace(page, { approval: true });
  await page.goto(`/workspace/reviews/${run.id}`);
  await page
    .getByLabel("Final response", { exact: true })
    .fill("Teacher reviewed this response.");
  await page.getByRole("button", { name: "Approve and book class" }).click();
  await expect(
    page.getByText("Class booked and response saved. No email has been sent."),
  ).toBeVisible();
  expect(mock.getBody()).toEqual({
    action: "approve",
    expected_revision: 2,
    body: "Teacher reviewed this response.",
  });
  await expect(
    page.getByRole("heading", { name: "Reviewed response", exact: true }),
  ).toBeVisible();
  await expect(
    page.getByText("Booking confirmed", { exact: true }),
  ).toBeVisible();
});

test("a stale review preserves edits and requires an explicit reload", async ({
  page,
}) => {
  await mockWorkspace(page, { conflict: true });
  await page.goto(`/workspace/reviews/${run.id}`);
  await page
    .getByLabel("Final response", { exact: true })
    .fill("My unsaved response");
  await page.getByRole("button", { name: "Approve and book class" }).click();
  await expect(page.getByRole("alert")).toContainText("no longer awaiting");
  await expect(page.getByLabel("Final response", { exact: true })).toHaveValue(
    "My unsaved response",
  );
  await page
    .getByRole("main")
    .getByRole("link", { name: "Review queue", exact: true })
    .click();
  await expect(page.getByRole("alertdialog")).toBeVisible();
  await page.getByRole("button", { name: "Stay here" }).click();
  await page
    .getByRole("button", {
      name: "Load the latest draft and discard local edits",
    })
    .click();
  await expect(page.getByLabel("Final response", { exact: true })).toHaveValue(
    run.draft_details.body,
  );
});

test("an interrupted email submission is never automatically repeated", async ({
  page,
}) => {
  const mock = await mockWorkspace(page, { failIntake: true });
  await page.goto("/workspace/test-email");
  await page.getByLabel("Sender email").fill("fictional@example.test");
  await page.getByLabel("Email body").fill("A fictional class enquiry.");
  await page
    .getByRole("button", { name: "Submit email and generate draft" })
    .click();
  await expect(page.getByRole("alert")).toContainText(
    "connection was interrupted",
  );
  await expect(
    page.getByRole("link", { name: "Check the queue before submitting again" }),
  ).toBeVisible();
  expect(mock.getIntakeCount()).toBe(1);
});

test("all public pages fit the viewport and expose keyboard navigation", async ({
  page,
}) => {
  for (const path of [
    "/demo",
    "/demo/students",
    "/demo/timetable",
    "/demo/database",
    `/demo/reviews/${run.id}`,
  ]) {
    await page.goto(path);
    await expect(page.getByRole("heading", { level: 1 })).toBeVisible();
    expect(
      await page.evaluate(
        () => document.documentElement.scrollWidth <= window.innerWidth,
      ),
    ).toBe(true);
  }
  await page.goto("/demo");
  await page.keyboard.press("Tab");
  await expect(
    page.getByRole("link", { name: "Skip to content" }),
  ).toBeFocused();
});

test("database browser shows records and complete columns for every example table", async ({
  page,
}) => {
  await page.goto("/demo/database");
  const tables = page.getByRole("navigation", { name: "Database tables" });
  for (const [name, records] of Object.entries(examples)) {
    if (!Array.isArray(records)) continue;
    await tables.getByRole("button", { name: new RegExp(`^${name} `) }).click();
    const grid = page.getByRole("region", {
      name: `${name} data`,
      exact: true,
    });
    await expect(grid).toBeVisible();
    await expect(grid.locator("tbody tr")).toHaveCount(
      Math.min(records.length, 20),
    );
    for (const column of Object.keys(records[0] || {})) {
      await expect(
        grid.getByRole("columnheader", { name: column, exact: true }),
      ).toBeAttached();
    }
  }
  await tables.getByRole("button", { name: /^agent_runs / }).click();
  const grid = page.getByRole("region", {
    name: "agent_runs data",
    exact: true,
  });
  const jsonCell = grid.locator("tbody tr").first().locator("details").first();
  await jsonCell.locator("summary").click();
  await expect(jsonCell.locator("pre")).toContainText("request_summary");
  const pageHasOverflow = await page.evaluate(
    () => document.documentElement.scrollWidth > window.innerWidth,
  );
  expect(pageHasOverflow).toBe(false);
});

test("workspace database uses live rows, paginates and handles empty tables and retry", async ({
  page,
}) => {
  const offsets: string[] = [];
  let fail = true;
  await page.route("**/auth/me", (route) =>
    route.fulfill({
      json: {
        authenticated: true,
        user: { email: "owner@example.test", name: "Owner" },
        csrf_token: "mock",
      },
    }),
  );
  await page.route("**/api/v1/database**", (route) => {
    const url = new URL(route.request().url());
    if (url.pathname === "/api/v1/database")
      return route.fulfill({
        json: [
          {
            name: "students",
            columns: ["id", "display_name", "context", "highest_level"],
            total: 21,
          },
          { name: "messages", columns: ["id", "body"], total: 0 },
        ],
      });
    if (url.pathname.endsWith("/messages"))
      return route.fulfill({
        json: { items: [], total: 0, limit: 20, offset: 0 },
      });
    if (fail) {
      fail = false;
      return route.fulfill({
        status: 503,
        json: { error: { message: "Temporarily unavailable" } },
      });
    }
    const offset = Number(url.searchParams.get("offset") || "0");
    offsets.push(String(offset));
    return route.fulfill({
      json: {
        items: Array.from({ length: Math.min(20, 21 - offset) }, (_, i) => ({
          id: `live-${offset + i}`,
          display_name: `Live student ${offset + i}`,
          context: { preference: "Thursday" },
          highest_level: null,
        })),
        total: 21,
        limit: 20,
        offset,
      },
    });
  });
  await page.goto("/workspace/database");
  await expect(page.getByRole("alert")).toContainText(
    "Temporarily unavailable",
  );
  await page.getByRole("button", { name: "Try loading again" }).click();
  await expect(
    page.getByRole("region", { name: "students data" }),
  ).toContainText("Live student 0");
  await expect(
    page.getByRole("region", { name: "students data" }),
  ).toContainText("NULL");
  await page.getByRole("button", { name: "Next page" }).click();
  await expect(
    page.getByRole("region", { name: "students data" }),
  ).toContainText("Live student 20");
  await expect(page.getByRole("button", { name: "Next page" })).toBeDisabled();
  await page.getByRole("button", { name: "Previous page" }).click();
  await expect(
    page.getByRole("region", { name: "students data" }),
  ).toContainText("Live student 0");
  await page.getByRole("button", { name: "Next page" }).click();
  await expect(
    page.getByRole("region", { name: "students data" }),
  ).toContainText("Live student 20");
  await page.getByRole("button", { name: /^messages / }).click();
  await expect(page.getByText("This table has no records yet.")).toBeVisible();
  await expect(
    page.getByRole("columnheader", { name: "body", exact: true }),
  ).toBeVisible();
  await page.getByRole("button", { name: /^students / }).click();
  await expect(
    page.getByRole("region", { name: "students data" }),
  ).toContainText("Live student 0");
  expect(offsets).toEqual(["0", "20", "0", "20", "0"]);
  await page.getByRole("button", { name: "Refresh database" }).click();
  await expect(
    page.getByRole("region", { name: "students data" }),
  ).toContainText("Live student 0");
});
