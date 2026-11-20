import { test, expect, type Page } from "@playwright/test";

async function sandbox(
  page: Page,
  options: { failEvidence?: boolean; quota?: boolean; offer?: boolean } = {},
) {
  const calls: string[] = [],
    forbidden: string[] = [];
  let failures = 0;
  const accepted: Array<Record<string, unknown>> = [];
  let thread = {
    student: "new",
    state: {
      intents: ["trial_enquiry", "faq"],
      experience_level: "intermediate",
      preferred_day: "Saturday",
      recommended_class: null,
      booking_status: options.offer ? "offered" : "collecting",
      missing_information: [],
      next_action: "ask_customer",
      revision: 1,
    },
    turns: [] as Array<{
      request_id: string;
      email: string;
      reply: string | null;
      evidence: object | null;
      draft: object | null;
    }>,
  };
  page.on("request", (r) => {
    if (/\/(api\/v1|auth)\//.test(new URL(r.url()).pathname))
      forbidden.push(r.url());
  });
  await page.route("**/api/public-demo/**", async (route) => {
    const req = route.request(),
      url = new URL(req.url()),
      path = url.pathname;
    calls.push(`${req.method()} ${path}`);
    if (path.endsWith("/threads")) {
      thread = { ...thread, student: req.postDataJSON().student, turns: [] };
      return route.fulfill({ json: { token: "example-token" } });
    }
    if (path.endsWith("/current") && req.method() === "POST")
      return route.fulfill({ json: thread });
    if (path.endsWith("/turns")) {
      if (options.quota)
        return route.fulfill({
          status: 429,
          json: { detail: "Today's demo allowance is used." },
        });
      const body = req.postDataJSON();
      if (!thread.turns.some((t) => t.request_id === body.request_id))
        thread.turns.push({
          request_id: body.request_id,
          email: body.email_body,
          reply: null,
          evidence: null,
          draft: null,
        });
      return route.fulfill({ json: { request_id: body.request_id } });
    }
    const turn = thread.turns.at(-1)!;
    if (path.endsWith("/evidence")) {
      if (options.failEvidence && failures++ === 0)
        return route.fulfill({
          status: 502,
          json: { detail: "Temporary failure" },
        });
      turn.evidence = {
        evidence: ["Socks are suitable."],
        route: "enquiry",
        missing_information: [],
        student_information: ["Preferred day"],
        model: "test",
      };
      return route.fulfill({ json: turn.evidence });
    }
    if (path.endsWith("/draft")) {
      turn.draft = { body: "Socks are suitable. Which day?" };
      return route.fulfill({ json: turn.draft });
    }
    if (path.endsWith("/accept")) {
      accepted.push(req.postDataJSON());
      turn.reply = req.postDataJSON().body;
      return route.fulfill({ json: { accepted: true } });
    }
    return route.fulfill({ status: 404 });
  });
  return { calls, forbidden, accepted };
}

test("walkthrough retains accepted replies in chronological order and restores on refresh", async ({
  page,
}) => {
  const api = await sandbox(page);
  await page.goto("/demo/test-email");
  await page
    .getByLabel("Email body")
    .fill("I am interested in ballet. What should I wear?");
  await page.getByRole("button", { name: "Simulate email" }).click();
  await expect(
    page.getByText("Information to ask the student: Preferred day"),
  ).toBeVisible();
  await page.getByRole("button", { name: "Generate draft" }).click();
  await page.getByLabel("Response").fill("Edited answer: socks are suitable.");
  await page.getByRole("button", { name: "Accept simulated reply" }).click();
  await page.getByLabel("Email body").fill("Saturday works for me.");
  await page.getByRole("button", { name: "Simulate email" }).click();
  await expect(
    page.getByText("Edited answer: socks are suitable."),
  ).toBeVisible();
  await expect(page.getByText("Saturday works for me.")).toBeVisible();
  await page.reload();
  await expect(
    page.getByText("Edited answer: socks are suitable."),
  ).toBeVisible();
  await page.getByRole("button", { name: "Start new conversation" }).click();
  await expect(
    page.getByText("Edited answer: socks are suitable."),
  ).toHaveCount(0);
  expect(api.forbidden).toEqual([]);
});

test("failed evidence retries the same email and request", async ({ page }) => {
  const api = await sandbox(page, { failEvidence: true });
  await page.goto("/demo/test-email");
  await page.getByLabel("Email body").fill("What should I wear?");
  await page.getByRole("button", { name: "Simulate email" }).click();
  await expect(page.getByRole("alert")).toContainText("Temporary failure");
  await page.getByRole("button", { name: "Retry evidence" }).click();
  await expect(
    page.getByRole("heading", { name: "Draft email" }),
  ).toBeVisible();
  expect(api.calls.filter((c) => c.endsWith("/turns"))).toHaveLength(1);
});

test("quota failure preserves the email", async ({ page }) => {
  await sandbox(page, { quota: true });
  await page.goto("/demo/test-email");
  await page.getByLabel("Email body").fill("Tell me about trial fees.");
  await page.getByRole("button", { name: "Simulate email" }).click();
  await expect(page.getByRole("alert")).toContainText("allowance");
  await expect(page.getByLabel("Email body")).toHaveValue(
    "Tell me about trial fees.",
  );
});

test("reviewer explicitly confirms an offered class in the accepted reply", async ({
  page,
}) => {
  const api = await sandbox(page, { offer: true });
  await page.goto("/demo/test-email");
  await page
    .getByLabel("Email body")
    .fill("I am intermediate and available Saturday.");
  await page.getByRole("button", { name: "Simulate email" }).click();
  await page.getByRole("button", { name: "Generate draft" }).click();
  await page
    .getByLabel("Response")
    .fill("Would you like a trial of Level 2 on Saturday 13 February 2027?");
  await page.getByLabel(/I confirm this reply offers/).check();
  await page.getByRole("button", { name: "Accept simulated reply" }).click();
  await expect.poll(() => api.accepted.length).toBe(1);
  expect(api.accepted[0].offer_confirmed).toBe(true);
});
