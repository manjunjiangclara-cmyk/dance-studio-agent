import { test, expect, type Page } from "@playwright/test";
import { readFileSync } from "node:fs";
import type { Examples } from "../src/types";

const examples = JSON.parse(
  readFileSync(
    new URL("../src/data/examples.v1.json", import.meta.url),
    "utf8",
  ),
) as Examples;
interface Call {
  stage: string;
  body: Record<string, unknown>;
  token?: string;
}
async function sandbox(page: Page, failDraft = false) {
  const calls: Call[] = [],
    forbidden: string[] = [];
  page.on("request", (r) => {
    if (/\/(api\/v1|auth)\//.test(new URL(r.url()).pathname))
      forbidden.push(r.url());
  });
  await page.route("**/api/v1/**", (r) => r.abort());
  await page.route("**/auth/**", (r) => r.abort());
  await page.route("**/api/public-demo/**", async (route) => {
    const req = route.request();
    const stage = new URL(req.url()).pathname.split("/").at(-1)!;
    const body = req.postDataJSON();
    calls.push({ stage, body, token: req.headers().authorization });
    if (stage === "runs") {
      expect(body.scenario).toBe("custom");
      expect([
        "new",
        "alex",
        "jules",
        ...examples.students
          .filter(
            (item) =>
              !["Alex Morgan", "Jules Park"].includes(item.display_name),
          )
          .map((item) => item.id),
      ]).toContain(body.student);
      expect(body.email_body).toBeTruthy();
      return route.fulfill({
        json: { scenario: "custom", token: `token-${body.request_id}` },
      });
    }
    if (stage === "evidence") expect(body).toEqual({});
    else expect(body).toEqual({ teacher_answers: ["I will confirm later."] });
    expect(req.headers().authorization).toMatch(/^Bearer token-/);
    if (stage === "evidence")
      return route.fulfill({
        json: {
          evidence: ["Fictional clothing policy: socks are suitable."],
          route: "enquiry",
          missing_information: ["Trial fee"],
          model: "test-model",
        },
      });
    if (failDraft && calls.filter((c) => c.stage === "draft").length === 1)
      return route.fulfill({
        status: 502,
        json: { detail: "Temporary model failure" },
      });
    return route.fulfill({
      json: {
        body: "Hi Jules, socks are suitable. I'll confirm the trial fee for you.",
        model: "test-model",
      },
    });
  });
  return { calls, forbidden };
}

test("visitors write their own email against a fictional student without touching owner records", async ({
  page,
}, info) => {
  const api = await sandbox(page);
  await page.goto("/demo/test-email");
  await expect(
    page.getByRole("button", { name: "Simulate email", exact: true }),
  ).toBeDisabled();
  await page
    .getByLabel("Sender context", { exact: true })
    .selectOption("jules");
  const email = "I'm new. What should I wear, and how much does a trial cost?";
  await page.getByLabel("Email body", { exact: true }).fill(email);
  await expect(page.getByLabel("Email body", { exact: true })).toHaveAttribute(
    "maxlength",
    "2000",
  );
  await page
    .getByRole("button", { name: "Simulate email", exact: true })
    .dblclick();
  await expect(
    page.getByRole("heading", {
      name: "Draft email",
      exact: true,
    }),
  ).toBeVisible();
  expect(api.calls.map((c) => c.stage)).toEqual(["runs", "evidence"]);
  await page.getByLabel("Trial fee").fill("I will confirm later.");
  await page
    .getByRole("button", { name: "Generate draft", exact: true })
    .click();
  await expect(
    page.getByRole("textbox", { name: "Response", exact: true }),
  ).toHaveValue(/I'll confirm/);
  expect(api.calls.map((c) => c.stage)).toEqual(["runs", "evidence", "draft"]);
  expect(api.calls[0].body).toMatchObject({
    scenario: "custom",
    student: "jules",
    email_body: email,
  });
  await page
    .getByRole("textbox", { name: "Response", exact: true })
    .fill("My edited reply <script>plain text</script>");
  expect(api.calls).toHaveLength(3);
  await page.getByText("Supporting evidence", { exact: true }).click();
  await expect(
    page.getByText("Fictional clothing policy: socks are suitable.", {
      exact: true,
    }),
  ).toBeVisible();
  await expect
    .poll(() =>
      page.evaluate(
        () => document.documentElement.scrollWidth <= window.innerWidth,
      ),
    )
    .toBe(true);
  await page.screenshot({
    path: info.outputPath("custom-email.png"),
    fullPage: true,
  });
  expect(api.forbidden).toEqual([]);
});

test("retry reuses the custom run and evidence; changed email creates a new request identity", async ({
  page,
}) => {
  const api = await sandbox(page, true);
  await page.goto("/demo/test-email");
  await page
    .getByLabel("Email body", { exact: true })
    .fill("What should I wear?");
  await page
    .getByRole("button", { name: "Simulate email", exact: true })
    .click();
  await page.getByLabel("Trial fee").fill("I will confirm later.");
  await page
    .getByRole("button", { name: "Generate draft", exact: true })
    .click();
  await expect(page.getByRole("alert")).toContainText(
    "Temporary model failure",
  );
  await page.getByRole("button", { name: "Retry draft", exact: true }).click();
  await expect(
    page.getByRole("heading", {
      name: "Draft email",
      exact: true,
    }),
  ).toBeVisible();
  expect(api.calls.map((c) => c.stage)).toEqual([
    "runs",
    "evidence",
    "draft",
    "draft",
  ]);
  expect(api.calls[2].token).toBe(api.calls[3].token);
  await page
    .getByLabel("Email body", { exact: true })
    .fill("Can I attend the Saturday class?");
  await expect(
    page.getByRole("heading", {
      name: "Draft email",
      exact: true,
    }),
  ).toHaveCount(0);
  await page
    .getByRole("button", { name: "Simulate email", exact: true })
    .click();
  await expect(
    page.getByRole("heading", {
      name: "Draft email",
      exact: true,
    }),
  ).toBeVisible();
  const runs = api.calls.filter((c) => c.stage === "runs");
  expect(runs).toHaveLength(2);
  expect(runs[0].body.request_id).not.toBe(runs[1].body.request_id);
  expect(api.forbidden).toEqual([]);
});

test("quota failure preserves the email and does not start model stages", async ({
  page,
}) => {
  const calls: string[] = [];
  await page.route("**/api/public-demo/**", (route) => {
    calls.push(new URL(route.request().url()).pathname);
    return route.fulfill({
      status: 429,
      json: { detail: "Today's demo allowance is used." },
    });
  });
  await page.goto("/demo/test-email");
  await page.getByLabel("Email body", { exact: true }).fill("   ");
  await expect(
    page.getByRole("button", { name: "Simulate email", exact: true }),
  ).toBeDisabled();
  await page
    .getByLabel("Email body", { exact: true })
    .fill("Please tell me about trial fees.");
  await page
    .getByRole("button", { name: "Simulate email", exact: true })
    .click();
  await expect(page.getByRole("alert")).toContainText("allowance is used");
  await expect(page.getByLabel("Email body", { exact: true })).toHaveValue(
    "Please tell me about trial fees.",
  );
  expect(calls).toEqual(["/api/public-demo/runs"]);
});

test("input stays fixed while a submission is running", async ({ page }) => {
  let release!: () => void;
  const hold = new Promise<void>((resolve) => {
    release = resolve;
  });
  await page.route("**/api/public-demo/runs", async (route) => {
    await hold;
    await route.fulfill({
      status: 503,
      json: { detail: "Service unavailable" },
    });
  });
  await page.goto("/demo/test-email");
  await page
    .getByLabel("Email body", { exact: true })
    .fill("What should I wear?");
  await page
    .getByRole("button", { name: "Simulate email", exact: true })
    .click();
  await expect(
    page.getByLabel("Sender context", { exact: true }),
  ).toBeDisabled();
  await expect(page.getByLabel("Email body", { exact: true })).toBeDisabled();
  await expect(
    page.getByRole("button", { name: "Simulating email…", exact: true }),
  ).toBeDisabled();
  release();
  await expect(page.getByRole("alert")).toContainText("Service unavailable");
  await expect(page.getByLabel("Email body", { exact: true })).toBeEnabled();
});

test("a new enquiry starts without a student history", async ({ page }) => {
  const api = await sandbox(page);
  await page.goto("/demo/test-email");
  await expect(page.getByLabel("Sender context")).toHaveValue("new");
  await expect(page.getByText("No conversation summary yet.")).toBeVisible();
  await page.getByLabel("Email body").fill("What should I wear?");
  await page
    .getByRole("button", { name: "Simulate email", exact: true })
    .click();
  await expect(
    page.getByRole("heading", { name: "Draft email" }),
  ).toBeVisible();
  expect(api.calls[0].body.student).toBe("new");
  await page.getByLabel("Sender context").selectOption("alex");
  await expect(page.getByRole("heading", { name: "Draft email" })).toHaveCount(
    0,
  );
});

test("each example student can be selected and submitted with their own context", async ({
  page,
}) => {
  const api = await sandbox(page);
  await page.goto("/demo/test-email");
  const selector = page.getByLabel("Sender context");
  const options = await selector.locator("option").allTextContents();
  expect(options.slice(1)).toEqual(
    examples.students.map((item) => item.display_name),
  );
  await page.getByLabel("Email body").fill("What should I wear?");
  for (const student of examples.students) {
    const id =
      student.display_name === "Alex Morgan"
        ? "alex"
        : student.display_name === "Jules Park"
          ? "jules"
          : student.id;
    await selector.selectOption(id);
    const context = page.locator(".email-explainer");
    await expect(
      context.getByRole("heading", { name: "About this student" }),
    ).toBeVisible();
    await expect(context).toContainText(
      student.ai_summary || "No conversation summary yet.",
    );
    const memory = student.context._agent_memory as
      { request_summary?: string } | undefined;
    if (memory?.request_summary)
      await expect(context).toContainText(memory.request_summary);
    await expect(context).not.toContainText("Available sources");
    await expect(context).not.toContainText("Student profile");
    await expect(
      page.getByText(`Example sender: ${student.email}`),
    ).toHaveCount(0);
    await page
      .getByRole("button", { name: "Simulate email", exact: true })
      .click();
    await expect(
      page.getByRole("heading", { name: "Draft email" }),
    ).toBeVisible();
    expect(
      api.calls.filter((call) => call.stage === "runs").at(-1)?.body.student,
    ).toBe(id);
    await selector.selectOption("new");
    await expect(
      page.getByRole("heading", { name: "Draft email" }),
    ).toHaveCount(0);
  }
  await expect
    .poll(() =>
      page.evaluate(
        () => document.documentElement.scrollWidth <= window.innerWidth,
      ),
    )
    .toBe(true);
});
