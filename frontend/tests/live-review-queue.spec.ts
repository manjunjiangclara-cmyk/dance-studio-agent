import { test, expect, type Page, type Route } from "@playwright/test";
import { DEMO_DEFER } from "../src/DemoQuestionAnswers";
import examples from "../src/data/examples.v1.json" with { type: "json" };
const booking = {
  student: { id: "3861ca04-d9bd-5994-af78-b1540c29f791", name: "Alex Morgan" },
  session: {
    id: "df96032d-5ce8-561e-948f-bda79b05887e",
    className: "Adult Ballet · Level 2",
    date: "Saturday 13 February 2027",
    time: "6 pm · Australia/Melbourne",
    location: "Merri Ballet · Brunswick",
    capacity: 2,
    students: [
      { id: "55c19f62-e578-4e33-9672-3dfe3fb65d3e", name: "Noah Ellis" },
    ],
  },
};

const sources = {
  booking: "97aa529c-2ca7-5ee9-86c6-0d7c9da03752",
  document: "3a067002-bcaf-57b7-a336-a1e6dbe29914",
  noah: "11021b1d-f2c9-5bc0-bed7-01d1418e57bf",
  riley: "e7006165-a655-507c-815c-2ead33050f7f",
};

test.beforeEach(async ({ page }) => {
  await page.route("**/api/public-demo/cases/*", (route) => {
    expect(route.request().method()).toBe("GET");
    const scenario = new URL(route.request().url()).pathname
      .split("/")
      .at(-1) as keyof typeof sources;
    const source = examples.messages.find(
      ({ id }) => id === sources[scenario],
    )!;
    return route.fulfill({
      json: {
        messages: examples.messages.filter(
          (message) =>
            message.conversation_id === source.conversation_id &&
            message.kind === "student_email" &&
            message.occurred_at <= source.occurred_at,
        ),
      },
    });
  });
});

async function mockStages(
  page: Page,
  handler: (route: Route) => Promise<unknown>,
) {
  await page.route("**/api/public-demo/**", async (route) => {
    if (route.request().method() === "GET") await route.fallback();
    else await handler(route);
  });
}

function draftResponse(body: string, booking_proposed = false) {
  return { body, booking_proposed, revision: 1, model: "test" };
}

function approveResponse(body: string, simulateBooking = false) {
  return {
    status: "approved_mock",
    revision: 1,
    body,
    booking_simulated: simulateBooking,
    ...(simulateBooking ? { booking } : {}),
  };
}

test("all unanswered emails share the same live review experience", async ({
  page,
}) => {
  await page.goto("/demo/reviews");
  await expect(page.getByText("Other unanswered emails")).toHaveCount(0);
  await expect(page.getByText("Processing failed")).toHaveCount(0);
  for (const item of [
    {
      subject: "Makeup options for next week",
      route: "noah",
      email: "Could I arrange a makeup class?",
    },
    {
      subject: "Help choosing a ballet class",
      route: "riley",
      email: "Could you help me choose a class?",
    },
  ]) {
    await page.getByRole("link", { name: new RegExp(item.subject) }).click();
    await expect(page).toHaveURL(
      new RegExp(`/demo/reviews/live-${item.route}$`),
    );
    await expect(
      page.getByRole("heading", { name: item.subject }),
    ).toBeVisible();
    await expect(
      page.getByRole("list", { name: "Student email conversation" }),
    ).toContainText(item.email);
    await expect(
      page.getByRole("heading", { name: "Draft email" }),
    ).toBeVisible();
    await expect(
      page.getByRole("button", { name: "Generate draft", exact: true }),
    ).toBeVisible();
    await page.goto("/demo/reviews");
  }
  await expect(page.getByText("maya@example.test")).toHaveCount(0);
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= window.innerWidth,
    ),
  ).toBe(true);
});

test("new cases handle missing information and retry with the same run", async ({
  page,
}) => {
  const calls: {
    stage: string;
    body: Record<string, unknown>;
    token?: string;
  }[] = [];
  await mockStages(page, async (route) => {
    const request = route.request();
    const stage = new URL(request.url()).pathname.split("/").at(-1)!;
    calls.push({
      stage,
      body: request.postDataJSON(),
      token: request.headers().authorization,
    });
    if (stage === "runs")
      return route.fulfill({ json: { token: "test-token" } });
    if (stage === "evidence")
      return route.fulfill({
        json: {
          evidence: [],
          missing_information: ["Absence date", "Preferred date"],
          route: "makeup",
          model: "test",
        },
      });
    if (stage === "approve")
      return route.fulfill({
        json: approveResponse(String(request.postDataJSON().body)),
      });
    if (calls.filter((call) => call.stage === "draft").length === 1)
      return route.fulfill({
        status: 502,
        json: { detail: "Temporary failure" },
      });
    return route.fulfill({
      json: draftResponse("Please tell me the dates."),
    });
  });
  await page.goto("/demo/reviews/live-noah");
  await page
    .getByRole("button", { name: "Generate draft", exact: true })
    .click();
  await expect(page.getByLabel("Absence date answer")).toBeVisible();
  await page
    .getByLabel("Absence date answer")
    .fill("I will confirm the absence date.");
  await page
    .getByLabel("Preferred date answer")
    .fill("I will confirm the preferred date.");
  await page
    .getByRole("button", { name: "Generate draft", exact: true })
    .click();
  await expect(page.getByRole("alert")).toContainText("Temporary failure");
  await expect(page.getByLabel("Absence date answer")).toBeDisabled();
  await page.getByRole("button", { name: "Retry", exact: true }).click();
  await expect(
    page.getByRole("textbox", { name: "Response", exact: true }),
  ).toHaveValue("Please tell me the dates.");
  expect(calls.map((call) => call.stage)).toEqual([
    "runs",
    "evidence",
    "draft",
    "draft",
  ]);
  expect(calls[0].body).toEqual({
    request_id: expect.any(String),
    scenario: "noah",
  });
  expect(calls[2].body).toEqual({
    teacher_answers: [
      "I will confirm the absence date.",
      "I will confirm the preferred date.",
    ],
  });
  expect(calls[3].body).toEqual(calls[2].body);
  expect(calls[3].token).toBe(calls[2].token);
  await page.getByRole("button", { name: "Approve response" }).click();
  await expect(
    page.getByText(/Simulation complete. No email was sent/),
  ).toBeVisible();
  expect(calls.at(-1)).toMatchObject({
    stage: "approve",
    body: { revision: 1, body: "Please tell me the dates." },
  });
});

test("a new case accepts empty evidence when no teacher input is needed", async ({
  page,
}) => {
  const calls: { stage: string; body: Record<string, unknown> }[] = [];
  await mockStages(page, async (route) => {
    const stage = new URL(route.request().url()).pathname.split("/").at(-1)!;
    calls.push({ stage, body: route.request().postDataJSON() });
    if (stage === "runs")
      return route.fulfill({ json: { token: "test-token" } });
    if (stage === "evidence")
      return route.fulfill({
        json: {
          evidence: [],
          missing_information: [],
          route: "enquiry",
          model: "test",
        },
      });
    return route.fulfill({
      json: draftResponse("Tell me what days work for you."),
    });
  });
  await page.goto("/demo/reviews/live-riley");
  await page
    .getByRole("button", { name: "Generate draft", exact: true })
    .click();
  await expect(
    page.getByRole("textbox", { name: "Response", exact: true }),
  ).toHaveValue("Tell me what days work for you.");
  expect(calls.map((call) => call.stage)).toEqual([
    "runs",
    "evidence",
    "draft",
  ]);
  expect(calls[0].body).toEqual({
    request_id: expect.any(String),
    scenario: "riley",
  });
  expect(calls[2].body).toEqual({ teacher_answers: [] });
});

test("visitors generate and review a temporary live response", async ({
  page,
}) => {
  const calls: string[] = [];
  await mockStages(page, async (route) => {
    const stage = new URL(route.request().url()).pathname.split("/").at(-1)!;
    calls.push(stage);
    if (stage === "runs") {
      expect(route.request().postDataJSON().scenario).toBe("booking");
      await route.fulfill({ json: { token: "token" } });
    } else if (stage === "evidence") {
      await route.fulfill({
        json: {
          evidence: ["Saturday is the latest preference."],
          model: "test",
        },
      });
    } else if (stage === "draft") {
      await route.fulfill({
        json: draftResponse("A live response for Alex.", true),
      });
    } else {
      expect(route.request().postDataJSON()).toEqual({
        revision: 1,
        body: "A live response for Alex.",
      });
      await route.fulfill({
        json: approveResponse("A live response for Alex.", true),
      });
    }
  });
  await page.goto("/demo/reviews");
  await expect(page.getByText("Live AI uses fictional data.")).toHaveCount(0);
  const alexRow = page.getByRole("link", {
    name: /Makeup for Monday 8 February/,
  });
  const julesRow = page.getByRole("link", {
    name: /Questions about starting ballet/,
  });
  await expect(alexRow).not.toContainText("alex@example.test");
  await expect(alexRow).toContainText("Can't attend Monday");
  await expect(alexRow).toContainText("7 Feb 2027");
  await expect(alexRow.locator("time")).toBeVisible();
  await expect(julesRow).not.toContainText("jules@example.test");
  await expect(julesRow).toContainText("Asks what to wear");
  await expect(julesRow).toContainText("7 Feb 2027");
  await expect(julesRow.locator("time")).toBeVisible();
  await expect(alexRow.locator(".intent-badge")).toHaveText("Makeup");
  await expect(julesRow.locator(".intent-badge")).toHaveText(
    "New student enquiry",
  );
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= window.innerWidth,
    ),
  ).toBe(true);
  await alexRow.click();
  await expect(
    page.getByRole("heading", { name: "Makeup for Monday 8 February" }),
  ).toBeVisible();
  await expect(page.getByText(/From alex@example.test/)).toBeVisible();
  await expect(page.getByText("alex@example.test", { exact: true })).toHaveCSS(
    "font-family",
    /monospace/,
  );
  await expect(page.locator(".page-heading .intent-badge")).toHaveText(
    "Makeup",
  );
  await expect(
    page.getByText("Hosted demos share 20 live runs per day."),
  ).toBeVisible();
  await expect(
    page.getByText("Drafts and results disappear when you leave or refresh."),
  ).toBeVisible();
  const messages = page
    .getByRole("list", { name: "Student email conversation" })
    .getByRole("listitem");
  await expect(messages).toHaveCount(2);
  for (const message of await messages.all()) {
    await expect(message.locator(".live-conversation-bubble")).not.toHaveCSS(
      "font-family",
      /monospace/,
    );
  }
  await expect(messages.nth(0).locator("time")).toHaveAttribute(
    "datetime",
    "2027-02-07T10:00:00+11:00",
  );
  await expect(messages.nth(0)).toContainText(
    "Could I make it up on 2027-02-11?",
  );
  await expect(messages.nth(1).locator("time")).toHaveAttribute(
    "datetime",
    "2027-02-07T10:05:00+11:00",
  );
  await expect(messages.nth(1)).toContainText(
    examples.messages.find(({ id }) => id === sources.booking)!.body,
  );
  expect(calls).toEqual([]);
  await expect(
    page.getByRole("heading", { name: "Draft email" }),
  ).toBeVisible();
  await expect(
    page.getByText("AI-assisted drafting", { exact: true }),
  ).toBeVisible();
  await expect(page.getByText(/AI-generated draft/)).toHaveCount(0);
  await expect(
    page.getByRole("heading", { name: "Supporting evidence" }),
  ).toHaveCount(0);
  await page
    .getByRole("button", { name: "Generate draft", exact: true })
    .click();
  await expect(
    page.getByRole("textbox", { name: "Response", exact: true }),
  ).toHaveValue("A live response for Alex.");
  await expect(page.getByText(/AI-generated draft · test/)).toBeVisible();
  await expect(
    page.getByRole("textbox", { name: "Response", exact: true }),
  ).toBeDisabled();
  await expect(
    page.getByRole("heading", { name: "Booking confirmed" }),
  ).toHaveCount(0);
  await expect(
    page.getByText(/Approval simulates the booking for the verified class/),
  ).toBeVisible();
  await page.getByRole("button", { name: "Approve response" }).click();
  await expect(page.getByRole("separator")).toHaveCount(1);
  await expect(
    page.getByText(
      "Simulation complete. No email was sent and no booking or studio record was changed.",
    ),
  ).toHaveCount(0);
  const booking = page.getByRole("region", { name: "Booking confirmed" });
  await expect(booking).toContainText("Simulation");
  await expect(booking).toContainText("Alex Morgan");
  await expect(booking).toContainText("Adult Ballet · Level 2");
  await expect(booking).toContainText("Saturday 13 February 2027");
  await expect(booking).toContainText("6 pm · Australia/Melbourne");
  await expect(booking).toContainText("Merri Ballet · Brunswick");
  await expect(booking).toContainText("No place was reserved");
  await expect(
    page.getByRole("heading", { name: "Supporting evidence" }),
  ).toBeVisible();
  await expect(
    page
      .locator(".live-evidence-card > p")
      .filter({ hasText: "Saturday is the latest preference." }),
  ).toBeVisible();
  await expect(
    page.getByRole("button", { name: "Approved", exact: true }),
  ).toBeDisabled();
  expect(calls).toEqual(["runs", "evidence", "draft", "approve"]);
  await page.reload();
  await expect(
    page.getByRole("heading", { name: "Booking confirmed" }),
  ).toHaveCount(0);
  await expect(
    page.getByRole("textbox", { name: "Response", exact: true }),
  ).toBeEmpty();
  expect(calls).toHaveLength(4);
});

test("quota failure is visible without a fabricated response", async ({
  page,
}) => {
  await page.route("**/api/public-demo/runs", (route) =>
    route.fulfill({ status: 429, json: { detail: "Daily limit reached" } }),
  );
  await page.goto("/demo/reviews/live-booking");
  await page
    .getByRole("button", { name: "Generate draft", exact: true })
    .click();
  await expect(page.getByRole("alert")).toContainText("Daily limit reached");
  await expect(
    page.getByRole("textbox", { name: "Response", exact: true }),
  ).toBeEmpty();
});

test("document enquiry requires a teacher decision", async ({ page }) => {
  let answers: string[] = [];
  await mockStages(page, async (route) => {
    const stage = new URL(route.request().url()).pathname.split("/").at(-1);
    if (stage === "runs") await route.fulfill({ json: { token: "token" } });
    else if (stage === "evidence")
      await route.fulfill({
        json: {
          evidence: ["Fee is unknown"],
          missing_information: ["Trial fee"],
          model: "test",
        },
      });
    else if (stage === "draft") {
      answers = route.request().postDataJSON().teacher_answers;
      await route.fulfill({ json: draftResponse("I will confirm the fee.") });
    } else {
      await route.fulfill({ json: approveResponse("I will confirm the fee.") });
    }
  });
  await page.goto("/demo/reviews/live-document");
  await expect(
    page
      .getByRole("list", { name: "Student email conversation" })
      .getByRole("listitem"),
  ).toHaveCount(1);
  await page
    .getByRole("button", { name: "Generate draft", exact: true })
    .click();
  await expect(
    page.getByRole("button", { name: "Generate draft" }),
  ).toBeDisabled();
  await page.getByRole("checkbox", { name: "Confirm later" }).check();
  await page.getByRole("button", { name: "Generate draft" }).click();
  await expect(
    page.getByRole("textbox", { name: "Response", exact: true }),
  ).toHaveValue("I will confirm the fee.");
  expect(answers).toEqual([DEMO_DEFER]);
  await page.getByRole("button", { name: "Approve response" }).click();
  await expect(page.getByRole("separator")).toHaveCount(0);
  await expect(
    page.getByRole("button", { name: "Approved", exact: true }),
  ).toBeDisabled();
  await expect(
    page.getByRole("heading", { name: "Booking confirmed" }),
  ).toHaveCount(0);
});

test("student links keep their filtered predefined records", async ({
  page,
}) => {
  await page.goto("/demo/reviews?q=Alex");
  await expect(page.getByLabel("Search enquiries")).toHaveValue("Alex");
  await expect(page.locator(".run-row")).toHaveCount(2);
  await expect(
    page.getByText("These predefined examples", { exact: false }),
  ).toBeVisible();
});

test("retry reuses the run after a failed draft", async ({ page }) => {
  let runs = 0;
  let drafts = 0;
  await mockStages(page, async (route) => {
    const stage = new URL(route.request().url()).pathname.split("/").at(-1);
    if (stage === "runs") {
      runs++;
      await route.fulfill({ json: { token: "token" } });
    } else if (stage === "evidence")
      await route.fulfill({ json: { evidence: ["Evidence"], model: "test" } });
    else {
      drafts++;
      await route.fulfill(
        drafts === 1
          ? { status: 502, json: { detail: "Try again" } }
          : { json: draftResponse("Live draft") },
      );
    }
  });
  await page.goto("/demo/reviews/live-booking");
  await page
    .getByRole("button", { name: "Generate draft", exact: true })
    .click();
  await expect(page.getByRole("alert")).toContainText("Try again");
  await page.getByRole("button", { name: "Retry" }).click();
  await expect(page.getByRole("textbox", { name: "Response" })).toHaveValue(
    "Live draft",
  );
  expect(runs).toBe(1);
  expect(drafts).toBe(2);
});

test("manual draft is editable and protected before generating", async ({
  page,
}) => {
  let calls = 0;
  await mockStages(page, async (route) => {
    calls++;
    const stage = new URL(route.request().url()).pathname.split("/").at(-1);
    if (stage === "runs") await route.fulfill({ json: { token: "token" } });
    else if (stage === "evidence")
      await route.fulfill({ json: { evidence: ["Evidence"], model: "test" } });
    else await route.fulfill({ json: draftResponse("Generated reply") });
  });
  await page.goto("/demo/reviews/live-booking");
  const field = page.getByRole("textbox", { name: "Response" });
  const button = page.getByRole("button", {
    name: "Generate draft",
    exact: true,
  });
  await expect(field).toBeEditable();
  await field.fill("My own reply");
  await expect(
    page.getByText("AI-assisted drafting", { exact: true }),
  ).toBeVisible();
  await expect(page.getByText(/AI-generated draft/)).toHaveCount(0);
  const fieldBox = await field.boundingBox();
  const buttonBox = await button.boundingBox();
  expect(
    buttonBox!.y - (fieldBox!.y + fieldBox!.height),
  ).toBeGreaterThanOrEqual(12);
  page.once("dialog", (dialog) => dialog.dismiss());
  await button.click();
  await expect(field).toHaveValue("My own reply");
  expect(calls).toBe(0);
  page.once("dialog", (dialog) => dialog.accept());
  await button.click();
  await expect(field).toHaveValue("Generated reply");
  await field.fill("Edited generated reply");
  await expect(field).toHaveValue("Edited generated reply");
  expect(calls).toBe(3);
});

test("failed generation preserves a manually written response", async ({
  page,
}) => {
  await page.route("**/api/public-demo/runs", (route) =>
    route.fulfill({ status: 429, json: { detail: "Daily limit reached" } }),
  );
  await page.goto("/demo/reviews/live-booking");
  const field = page.getByRole("textbox", { name: "Response" });
  await field.fill("My own reply");
  page.once("dialog", (dialog) => dialog.accept());
  await page
    .getByRole("button", { name: "Generate draft", exact: true })
    .click();
  await expect(page.getByRole("alert")).toContainText("Daily limit reached");
  await expect(field).toBeEditable();
  await expect(field).toHaveValue("My own reply");
});

test("evidence cards retain complete facts in returned order with a safe fallback", async ({
  page,
}) => {
  const evidence = [
    "Saturday 13 February 2027, 6 pm, Adult Ballet Level 2. One place available.",
    "A new source with unfamiliar wording.",
    "The fictional absence notice arrived before Monday's class started.",
  ];
  await mockStages(page, async (route) => {
    const stage = new URL(route.request().url()).pathname.split("/").at(-1);
    if (stage === "runs") await route.fulfill({ json: { token: "token" } });
    else if (stage === "evidence")
      await route.fulfill({ json: { evidence, model: "test" } });
    else await route.fulfill({ json: draftResponse("Live response") });
  });
  await page.goto("/demo/reviews/live-booking");
  await page
    .getByRole("button", { name: "Generate draft", exact: true })
    .click();
  const section = page.locator(".live-draft-evidence");
  const cards = section.getByRole("listitem");
  await expect(cards).toHaveCount(3);
  for (let i = 0; i < evidence.length; i++)
    await expect(cards.nth(i)).toContainText(evidence[i]);
  await expect(cards.nth(0)).toContainText("Class availability");
  await expect(cards.nth(1)).toContainText("Supporting information");
  await expect(cards.nth(2)).toContainText("Absence notice");
  await expect(
    cards
      .nth(0)
      .getByText(
        "The Saturday Level 2 class has one place available in this example.",
      ),
  ).toBeVisible();
  await expect(cards.nth(0).getByText(evidence[0])).toBeHidden();
  await cards.nth(0).getByText("View source").click();
  await expect(cards.nth(0).getByText(evidence[0])).toBeVisible();
  await expect(cards.nth(0).getByText("Fictional demo input")).toBeVisible();
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= window.innerWidth,
    ),
  ).toBe(true);
});

test("policy evidence links to the fictional original and its version", async ({
  page,
}) => {
  const policy = [
    "Merri Ballet — Beginner clothing policy",
    "For adult beginners attending a first class:\nWear comfortable clothes you can move in, such as leggings and a fitted T-shirt. Socks are suitable for your first class; ballet shoes are optional.",
    "Bring water and tie long hair back. This document does not specify trial fees.",
  ].join("\n\n");
  const fact = `Beginner clothing policy, revision 1: ${policy}`;
  await mockStages(page, async (route) => {
    const stage = new URL(route.request().url()).pathname.split("/").at(-1);
    if (stage === "runs") await route.fulfill({ json: { token: "token" } });
    else if (stage === "evidence")
      await route.fulfill({
        json: {
          evidence: [fact],
          missing_information: ["Trial fee"],
          model: "test",
        },
      });
    else await route.fulfill({ json: draftResponse("Live response") });
  });
  await page.goto("/demo/reviews/live-document");
  await page
    .getByRole("button", { name: "Generate draft", exact: true })
    .click();
  await page.getByRole("checkbox", { name: "Confirm later" }).check();
  await page.getByRole("button", { name: "Generate draft" }).click();
  const card = page.locator(".live-evidence-card");
  await expect(card).toContainText(
    "Comfortable clothes and socks are suitable",
  );
  await card.getByText("View source").click();
  await expect(
    card.getByText("Beginner clothing policy · Revision 1"),
  ).toBeVisible();
  await expect(
    card.getByText("Bring water and tie long hair back.", { exact: false }),
  ).toBeVisible();
  await expect(card.getByText(policy, { exact: true })).toBeVisible();
});

test("a failed document draft explains its locked decision and retries the same answer", async ({
  page,
}) => {
  const answers: string[][] = [];
  let runs = 0;
  await mockStages(page, async (route) => {
    const stage = new URL(route.request().url()).pathname.split("/").at(-1);
    if (stage === "runs") {
      runs++;
      await route.fulfill({ json: { token: "token" } });
    } else if (stage === "evidence")
      await route.fulfill({
        json: {
          evidence: ["Fee unknown"],
          missing_information: ["Trial fee"],
          model: "test",
        },
      });
    else {
      answers.push(route.request().postDataJSON().teacher_answers);
      await route.fulfill(
        answers.length === 1
          ? { status: 502, json: { detail: "Try again" } }
          : { json: draftResponse("I will confirm.") },
      );
    }
  });
  await page.goto("/demo/reviews/live-document");
  await page
    .getByRole("button", { name: "Generate draft", exact: true })
    .click();
  await page.getByRole("checkbox", { name: "Confirm later" }).check();
  await page.getByRole("button", { name: "Generate draft" }).click();
  await expect(page.getByRole("alert")).toContainText("Try again");
  await expect(
    page.getByRole("checkbox", { name: "Confirm later" }),
  ).toBeDisabled();
  await page.getByRole("button", { name: "Retry" }).click();
  await expect(page.getByRole("textbox", { name: "Response" })).toHaveValue(
    "I will confirm.",
  );
  expect(answers).toEqual([[DEMO_DEFER], [DEMO_DEFER]]);
  expect(runs).toBe(1);
});
