import { test, expect } from "@playwright/test";

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
  await page.route("**/api/public-demo/**", async (route) => {
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
    if (calls.filter((call) => call.stage === "draft").length === 1)
      return route.fulfill({
        status: 502,
        json: { detail: "Temporary failure" },
      });
    return route.fulfill({
      json: { body: "Please tell me the dates.", model: "test" },
    });
  });
  await page.goto("/demo/reviews/live-noah");
  await page
    .getByRole("button", { name: "Generate draft", exact: true })
    .click();
  await expect(page.getByLabel("Absence date")).toBeVisible();
  await page
    .getByLabel("Absence date")
    .fill("I will confirm the absence date.");
  await page
    .getByLabel("Preferred date")
    .fill("I will confirm the preferred date.");
  await page
    .getByRole("button", { name: "Generate draft", exact: true })
    .click();
  await expect(page.getByRole("alert")).toContainText("Temporary failure");
  await expect(page.getByLabel("Absence date")).toBeDisabled();
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
  expect(calls[0].body).toMatchObject({
    scenario: "custom",
    student: "60bbb539-91bc-5858-80f5-a1b6ae915aae",
    email_body: "Could I arrange a makeup class?",
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
});

test("a new case accepts empty evidence when no teacher input is needed", async ({
  page,
}) => {
  const calls: { stage: string; body: Record<string, unknown> }[] = [];
  await page.route("**/api/public-demo/**", async (route) => {
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
      json: { body: "Tell me what days work for you.", model: "test" },
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
  expect(calls[0].body).toMatchObject({
    scenario: "custom",
    student: "2eca4988-037e-54f9-9668-59ee06b2888b",
    email_body: "Could you help me choose a class?",
  });
  expect(calls[2].body).toEqual({ teacher_answers: [] });
});

test("visitors generate and review a temporary live response", async ({
  page,
}) => {
  const calls: string[] = [];
  await page.route("**/api/public-demo/**", async (route) => {
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
    } else {
      await route.fulfill({
        json: { body: "A live response for Alex.", model: "test" },
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
    page.getByText("Starting a draft uses one of 20 shared daily runs."),
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
  await expect(messages.nth(0)).toContainText("Could I come Thursday instead?");
  await expect(messages.nth(1).locator("time")).toHaveAttribute(
    "datetime",
    "2027-02-07T10:05:00+11:00",
  );
  await expect(messages.nth(1)).toContainText(
    "Saturday 13 February would be better.",
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
  await page
    .getByRole("textbox", { name: "Response", exact: true })
    .fill("Edited response");
  await expect(page.getByText(/AI draft edited · test/)).toBeVisible();
  await expect(
    page.getByRole("heading", { name: "Booking confirmed" }),
  ).toHaveCount(0);
  await expect(
    page.getByText(/Editing the email does not change the selected class/),
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
  expect(calls).toEqual(["runs", "evidence", "draft"]);
  await page.reload();
  await expect(
    page.getByRole("heading", { name: "Booking confirmed" }),
  ).toHaveCount(0);
  await expect(
    page.getByRole("textbox", { name: "Response", exact: true }),
  ).toBeEmpty();
  expect(calls).toHaveLength(3);
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
  await page.route("**/api/public-demo/**", async (route) => {
    const stage = new URL(route.request().url()).pathname.split("/").at(-1);
    if (stage === "runs") await route.fulfill({ json: { token: "token" } });
    else if (stage === "evidence")
      await route.fulfill({
        json: { evidence: ["Fee is unknown"], model: "test" },
      });
    else {
      answers = route.request().postDataJSON().teacher_answers;
      await route.fulfill({
        json: { body: "I will confirm the fee.", model: "test" },
      });
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
    page.getByRole("button", { name: "Generate draft with decision" }),
  ).toBeDisabled();
  await page.getByLabel("Confirm the fee later").check();
  await page
    .getByRole("button", { name: "Generate draft with decision" })
    .click();
  await expect(
    page.getByRole("textbox", { name: "Response", exact: true }),
  ).toHaveValue("I will confirm the fee.");
  expect(answers).toEqual(["I will confirm the trial fee later."]);
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
  await page.route("**/api/public-demo/**", async (route) => {
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
          : { json: { body: "Live draft", model: "test" } },
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
  await page.route("**/api/public-demo/**", async (route) => {
    calls++;
    const stage = new URL(route.request().url()).pathname.split("/").at(-1);
    if (stage === "runs") await route.fulfill({ json: { token: "token" } });
    else if (stage === "evidence")
      await route.fulfill({ json: { evidence: ["Evidence"], model: "test" } });
    else
      await route.fulfill({ json: { body: "Generated reply", model: "test" } });
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
  await page.route("**/api/public-demo/**", async (route) => {
    const stage = new URL(route.request().url()).pathname.split("/").at(-1);
    if (stage === "runs") await route.fulfill({ json: { token: "token" } });
    else if (stage === "evidence")
      await route.fulfill({ json: { evidence, model: "test" } });
    else
      await route.fulfill({ json: { body: "Live response", model: "test" } });
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
  const fact =
    "Beginner clothing policy, revision 1: Wear comfortable clothes you can move in, such as leggings and a fitted T-shirt. Socks are suitable for your first class; ballet shoes are optional.";
  await page.route("**/api/public-demo/**", async (route) => {
    const stage = new URL(route.request().url()).pathname.split("/").at(-1);
    if (stage === "runs") await route.fulfill({ json: { token: "token" } });
    else if (stage === "evidence")
      await route.fulfill({ json: { evidence: [fact], model: "test" } });
    else
      await route.fulfill({ json: { body: "Live response", model: "test" } });
  });
  await page.goto("/demo/reviews/live-document");
  await page
    .getByRole("button", { name: "Generate draft", exact: true })
    .click();
  await page.getByLabel("Confirm the fee later").check();
  await page
    .getByRole("button", { name: "Generate draft with decision" })
    .click();
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
  await expect(card.getByText(fact, { exact: true })).toBeVisible();
});

test("a failed document draft explains its locked decision and retries the same answer", async ({
  page,
}) => {
  const answers: string[][] = [];
  let runs = 0;
  await page.route("**/api/public-demo/**", async (route) => {
    const stage = new URL(route.request().url()).pathname.split("/").at(-1);
    if (stage === "runs") {
      runs++;
      await route.fulfill({ json: { token: "token" } });
    } else if (stage === "evidence")
      await route.fulfill({
        json: { evidence: ["Fee unknown"], model: "test" },
      });
    else {
      answers.push(route.request().postDataJSON().teacher_answers);
      await route.fulfill(
        answers.length === 1
          ? { status: 502, json: { detail: "Try again" } }
          : { json: { body: "I will confirm.", model: "test" } },
      );
    }
  });
  await page.goto("/demo/reviews/live-document");
  await page
    .getByRole("button", { name: "Generate draft", exact: true })
    .click();
  await page.getByLabel("Confirm the fee later").check();
  await page
    .getByRole("button", { name: "Generate draft with decision" })
    .click();
  await expect(page.getByRole("alert")).toContainText("Try again");
  await expect(
    page.getByText(/Your decision is locked for this attempt/),
  ).toBeVisible();
  await expect(page.getByLabel("Confirm the fee later")).toBeDisabled();
  await page.getByRole("button", { name: "Retry" }).click();
  await expect(page.getByRole("textbox", { name: "Response" })).toHaveValue(
    "I will confirm.",
  );
  expect(answers).toEqual([
    ["I will confirm the trial fee later."],
    ["I will confirm the trial fee later."],
  ]);
  expect(runs).toBe(1);
});
