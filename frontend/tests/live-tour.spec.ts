import { test, expect, type Page } from "@playwright/test";
import { tourFixtures, tourSource } from "../src/tourData";

type Scenario = "booking" | "document";
type Stage = "runs" | "evidence" | "draft";
interface Call {
  stage: Stage;
  body: Record<string, unknown>;
  authorization: string | undefined;
}
interface ResponseOverride {
  status?: number;
  json?: unknown;
}
const generatedBooking =
  "Hi Alex, I have reviewed your Saturday preference and the class details. Your teacher can approve the proposed makeup.\n\nMerri Ballet team";
const generatedDocument =
  "Hi Jules, comfortable clothes and socks are suitable for your first class. Ballet shoes are optional.\n\n[Teacher decision needed: trial fee]\n\nMerri Ballet team";

function deferred() {
  let release!: () => void;
  const promise = new Promise<void>((resolve) => {
    release = resolve;
  });
  return { promise, release };
}

async function mockLive(
  page: Page,
  override?: (
    call: Call,
    count: number,
  ) => Promise<ResponseOverride | void> | ResponseOverride | void,
) {
  const calls: Call[] = [];
  const forbidden: string[] = [];
  const tokens = new Map<string, Scenario>();
  page.on("request", (request) => {
    const path = new URL(request.url()).pathname;
    if (path.startsWith("/api/v1/") || path.startsWith("/auth/"))
      forbidden.push(path);
  });
  await page.route("**/api/v1/**", (route) => route.abort());
  await page.route("**/auth/**", (route) => route.abort());
  await page.route("**/api/public-demo/**", async (route) => {
    const request = route.request();
    const stage = new URL(request.url()).pathname.split("/").at(-1) as Stage;
    expect(["runs", "evidence", "draft"]).toContain(stage);
    expect(request.method()).toBe("POST");
    const call: Call = {
      stage,
      body: request.postData()
        ? (request.postDataJSON() as Record<string, unknown>)
        : {},
      authorization: request.headers().authorization,
    };
    calls.push(call);
    const response = await override?.(
      call,
      calls.filter((item) => item.stage === stage).length,
    );
    if (response) {
      await route
        .fulfill({ status: response.status ?? 200, json: response.json ?? {} })
        .catch(() => {});
      return;
    }
    if (stage === "runs") {
      expect(Object.keys(call.body).sort()).toEqual(["request_id", "scenario"]);
      expect(call.body.request_id).toMatch(
        /^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i,
      );
      expect(["booking", "document"]).toContain(call.body.scenario);
      const token = `demo-token-${String(call.body.request_id)}`;
      tokens.set(token, call.body.scenario as Scenario);
      await route
        .fulfill({ json: { token, scenario: call.body.scenario } })
        .catch(() => {});
      return;
    }
    expect(call.body).toEqual({});
    const scenario = tokens.get(
      call.authorization?.replace(/^Bearer /, "") ?? "",
    );
    expect(scenario).toBeDefined();
    await route
      .fulfill({
        json:
          stage === "evidence"
            ? {
                evidence: tourFixtures[scenario!].evidence,
                model: "test-live-model",
              }
            : {
                body:
                  scenario === "booking" ? generatedBooking : generatedDocument,
                model: "test-live-model",
              },
      })
      .catch(() => {});
  });
  return {
    calls,
    forbidden,
    count: (stage: Stage) =>
      calls.filter((call) => call.stage === stage).length,
  };
}

async function enterEvidence(page: Page, scenario: Scenario = "booking") {
  await page.goto(`/demo/tour?mode=live&scenario=${scenario}`);
  await expect(
    page.getByRole("heading", { name: "Email", exact: true }),
  ).toBeVisible();
  await page.getByRole("button", { name: "Next", exact: true }).click();
  await expect(
    page.getByRole("heading", { name: "Evidence", exact: true }),
  ).toBeVisible();
}

async function findEvidence(page: Page) {
  await page
    .getByRole("button", { name: "Find supporting evidence", exact: true })
    .click();
  await expect(
    page.getByRole("button", { name: "Next", exact: true }),
  ).toBeEnabled();
}

async function enterReview(page: Page) {
  await page.getByRole("button", { name: "Next", exact: true }).click();
  await expect(
    page.getByRole("heading", { name: "Teacher review", exact: true }),
  ).toBeVisible();
}

test("switching to the recorded demo uses no public or owner API calls", async ({
  page,
}) => {
  const api = await mockLive(page, () => ({
    status: 429,
    json: { detail: "Daily demo limit reached" },
  }));
  await enterEvidence(page);
  await page
    .getByRole("button", { name: "Find supporting evidence", exact: true })
    .click();
  await expect(page.getByRole("alert")).toContainText(
    "Daily demo limit reached",
  );
  await page.getByRole("link", { name: /recorded demo/i }).click();
  await expect(page).not.toHaveURL(/mode=live/);
  await expect(
    page.getByRole("heading", { name: "Email", exact: true }),
  ).toBeVisible();
  await page.getByRole("button", { name: "Next", exact: true }).click();
  await expect(
    page.getByText(tourFixtures.booking.evidence[0], { exact: true }),
  ).toBeVisible();
  await enterReview(page);
  await expect(page.getByLabel("Final response", { exact: true })).toHaveValue(
    tourFixtures.booking.draft,
  );
  expect(api.calls.map((call) => call.stage)).toEqual(["runs"]);
  expect(api.forbidden).toEqual([]);
});

test("live requests require explicit clicks, prevent double submission and reuse completed stages", async ({
  page,
}) => {
  const evidence = deferred();
  const draft = deferred();
  const api = await mockLive(page, async (call) => {
    if (call.stage === "evidence") await evidence.promise;
    if (call.stage === "draft") await draft.promise;
  });
  try {
    await page.goto("/demo/tour?mode=live");
    expect(api.calls).toEqual([]);
    await page.getByRole("button", { name: "Next", exact: true }).click();
    await expect(
      page.getByRole("button", { name: "Next", exact: true }),
    ).toBeDisabled();
    expect(api.calls).toEqual([]);
    await page
      .getByRole("button", { name: "Find supporting evidence", exact: true })
      .dblclick();
    await expect(
      page.getByRole("button", { name: "Finding evidence…", exact: true }),
    ).toBeDisabled();
    await expect.poll(() => api.count("evidence")).toBe(1);
    expect(api.count("runs")).toBe(1);
    await expect(
      page.getByRole("button", { name: "Next", exact: true }),
    ).toBeDisabled();
    evidence.release();
    await expect(
      page.getByRole("button", { name: "Next", exact: true }),
    ).toBeEnabled();
    await enterReview(page);
    expect(api.count("draft")).toBe(0);
    await expect(
      page.getByLabel("Final response", { exact: true }),
    ).toHaveValue("");
    await expect(
      page.getByRole("button", {
        name: "Simulate approval and booking",
        exact: true,
      }),
    ).toBeDisabled();
    await page
      .getByRole("button", { name: "Generate draft", exact: true })
      .dblclick();
    await expect(
      page.getByRole("button", { name: "Generating draft…", exact: true }),
    ).toBeDisabled();
    await expect.poll(() => api.count("draft")).toBe(1);
    draft.release();
    await expect(
      page.getByLabel("Final response", { exact: true }),
    ).toHaveValue(generatedBooking);
    await page.getByRole("button", { name: "Back", exact: true }).click();
    await enterReview(page);
    await expect(
      page.getByLabel("Final response", { exact: true }),
    ).toHaveValue(generatedBooking);
    await page
      .getByRole("button", {
        name: "Simulate approval and booking",
        exact: true,
      })
      .click();
    await expect(
      page.getByRole("heading", { name: "Class booked", exact: true }),
    ).toBeVisible();
    expect(api.calls.map((call) => call.stage)).toEqual([
      "runs",
      "evidence",
      "draft",
    ]);
    expect(api.forbidden).toEqual([]);
  } finally {
    evidence.release();
    draft.release();
  }
});

test("live document citations remain canonical and teacher decisions cost no extra requests", async ({
  page,
}) => {
  const api = await mockLive(page);
  await enterEvidence(page, "document");
  await findEvidence(page);
  await page
    .getByRole("button", {
      name: "Beginner clothing policy · Revision 1",
      exact: true,
    })
    .click();
  await expect(page.locator("mark")).toHaveText(tourSource.quote);
  await enterReview(page);
  await expect(
    page.getByRole("radio", { name: "Confirm later", exact: true }),
  ).toBeDisabled();
  await expect(
    page.getByRole("button", { name: "Update draft", exact: true }),
  ).toBeDisabled();
  await page
    .getByRole("button", { name: "Generate draft", exact: true })
    .click();
  await expect(page.getByLabel("Final response", { exact: true })).toHaveValue(
    generatedDocument,
  );
  const approve = page.getByRole("button", {
    name: "Simulate approval",
    exact: true,
  });
  await expect(approve).toBeDisabled();
  await page
    .getByRole("radio", { name: "Provide an answer", exact: true })
    .check();
  await page
    .getByLabel("Trial fee answer", { exact: true })
    .fill("The trial costs $20.");
  await page.getByRole("button", { name: "Update draft", exact: true }).click();
  await expect(approve).toBeEnabled();
  await expect(page.getByLabel("Final response", { exact: true })).toHaveValue(
    /The trial costs \$20/,
  );
  await expect(page.getByLabel("Final response", { exact: true })).toHaveValue(
    /Hi Jules, comfortable clothes and socks are suitable for your first class/,
  );
  await approve.click();
  await expect(
    page.getByRole("heading", { name: "Response approved", exact: true }),
  ).toBeVisible();
  expect(api.calls.map((call) => call.stage)).toEqual([
    "runs",
    "evidence",
    "draft",
  ]);
  expect(api.forbidden).toEqual([]);
});

test("evidence and draft failures retry with the existing token without fixture fallback", async ({
  page,
}) => {
  const api = await mockLive(page, (call, count) =>
    call.stage !== "runs" && count === 1
      ? {
          status: 503,
          json: { detail: `${call.stage} temporarily unavailable` },
        }
      : undefined,
  );
  await enterEvidence(page);
  await page
    .getByRole("button", { name: "Find supporting evidence", exact: true })
    .click();
  await expect(page.getByRole("alert")).toContainText(
    "evidence temporarily unavailable",
  );
  await expect(
    page.getByRole("button", { name: "Next", exact: true }),
  ).toBeDisabled();
  await expect(
    page.getByText(tourFixtures.booking.evidence[0], { exact: true }),
  ).toHaveCount(0);
  await page.getByRole("button", { name: "Retry", exact: true }).click();
  await expect(
    page.getByRole("button", { name: "Next", exact: true }),
  ).toBeEnabled();
  await enterReview(page);
  await page
    .getByRole("button", { name: "Generate draft", exact: true })
    .click();
  await expect(page.getByRole("alert")).toContainText(
    "draft temporarily unavailable",
  );
  await expect(page.getByLabel("Final response", { exact: true })).toHaveValue(
    "",
  );
  await page.getByRole("button", { name: "Retry", exact: true }).click();
  await expect(page.getByLabel("Final response", { exact: true })).toHaveValue(
    generatedBooking,
  );
  expect(api.count("runs")).toBe(1);
  expect(api.count("evidence")).toBe(2);
  expect(api.count("draft")).toBe(2);
  expect(
    new Set(
      api.calls
        .filter((call) => call.stage !== "runs")
        .map((call) => call.authorization),
    ).size,
  ).toBe(1);
  expect(api.forbidden).toEqual([]);
});

for (const status of [429, 503])
  test(`run admission ${status} shows an error and retries the same request identity`, async ({
    page,
  }) => {
    const message =
      status === 429 ? "Daily demo limit reached" : "Live demo is unavailable";
    const api = await mockLive(page, (call, count) =>
      call.stage === "runs" && count === 1
        ? { status, json: { detail: message } }
        : undefined,
    );
    await enterEvidence(page);
    await page
      .getByRole("button", { name: "Find supporting evidence", exact: true })
      .click();
    await expect(page.getByRole("alert")).toContainText(message);
    await expect(
      page.getByRole("button", { name: "Next", exact: true }),
    ).toBeDisabled();
    expect(api.count("evidence")).toBe(0);
    expect(api.count("draft")).toBe(0);
    await page.getByRole("button", { name: "Retry", exact: true }).click();
    await expect(
      page.getByRole("button", { name: "Next", exact: true }),
    ).toBeEnabled();
    const admissions = api.calls.filter((call) => call.stage === "runs");
    expect(admissions).toHaveLength(2);
    expect(admissions[0].body.request_id).toBe(admissions[1].body.request_id);
    expect(api.forbidden).toEqual([]);
  });

test("scenario changes ignore late evidence and preserve live mode with a new request identity", async ({
  page,
}) => {
  const pending = deferred();
  const api = await mockLive(page, async (call, count) => {
    if (call.stage === "evidence" && count === 1) await pending.promise;
  });
  try {
    await enterEvidence(page);
    await page
      .getByRole("button", { name: "Find supporting evidence", exact: true })
      .click();
    await expect.poll(() => api.count("evidence")).toBe(1);
    await page
      .getByRole("link", { name: "Document enquiry", exact: true })
      .click();
    await expect(page).toHaveURL(/mode=live/);
    await expect(page).toHaveURL(/scenario=document/);
    pending.release();
    await expect(
      page.getByRole("heading", { name: "Email", exact: true }),
    ).toBeVisible();
    await page.getByRole("button", { name: "Next", exact: true }).click();
    await expect(
      page.getByRole("button", { name: "Next", exact: true }),
    ).toBeDisabled();
    await expect(
      page.getByText(tourFixtures.booking.evidence[0], { exact: true }),
    ).toHaveCount(0);
    await findEvidence(page);
    const admissions = api.calls.filter((call) => call.stage === "runs");
    expect(admissions).toHaveLength(2);
    expect(admissions[0].body.request_id).not.toBe(
      admissions[1].body.request_id,
    );
    expect(admissions.map((call) => call.body.scenario)).toEqual([
      "booking",
      "document",
    ]);
    expect(api.forbidden).toEqual([]);
  } finally {
    pending.release();
  }
});

test("reset ignores a late draft and starts a fresh empty live run", async ({
  page,
}) => {
  const pending = deferred();
  const api = await mockLive(page, async (call) => {
    if (call.stage === "draft") await pending.promise;
  });
  try {
    await enterEvidence(page);
    await findEvidence(page);
    await enterReview(page);
    await page
      .getByRole("button", { name: "Generate draft", exact: true })
      .click();
    await expect.poll(() => api.count("draft")).toBe(1);
    await page.getByRole("button", { name: "Reset", exact: true }).click();
    pending.release();
    await expect(
      page.getByRole("heading", { name: "Email", exact: true }),
    ).toBeVisible();
    await page.getByRole("button", { name: "Next", exact: true }).click();
    await expect(
      page.getByRole("button", { name: "Next", exact: true }),
    ).toBeDisabled();
    await findEvidence(page);
    await enterReview(page);
    await expect(
      page.getByLabel("Final response", { exact: true }),
    ).toHaveValue("");
    const admissions = api.calls.filter((call) => call.stage === "runs");
    expect(admissions).toHaveLength(2);
    expect(admissions[0].body.request_id).not.toBe(
      admissions[1].body.request_id,
    );
    expect(api.forbidden).toEqual([]);
  } finally {
    pending.release();
  }
});

for (const scenario of ["booking", "document"] as const) {
  test(`completion link preserves live mode after ${scenario}`, async ({
    page,
  }) => {
    const api = await mockLive(page);
    await enterEvidence(page, scenario);
    await findEvidence(page);
    await enterReview(page);
    await page
      .getByRole("button", { name: "Generate draft", exact: true })
      .click();
    await expect(
      page.getByLabel("Final response", { exact: true }),
    ).toHaveValue(
      scenario === "booking" ? generatedBooking : generatedDocument,
    );
    if (scenario === "document") {
      await page
        .getByRole("radio", { name: "Confirm later", exact: true })
        .check();
      await page
        .getByRole("button", { name: "Update draft", exact: true })
        .click();
    }
    await page
      .getByRole("button", {
        name:
          scenario === "booking"
            ? "Simulate approval and booking"
            : "Simulate approval",
        exact: true,
      })
      .click();
    await page
      .getByRole("link", {
        name:
          scenario === "booking"
            ? "Try document enquiry"
            : "Try makeup booking",
        exact: true,
      })
      .click();
    const destination = new URL(page.url());
    expect(destination.searchParams.get("mode")).toBe("live");
    expect(destination.searchParams.get("scenario")).toBe(
      scenario === "booking" ? "document" : "booking",
    );
    await expect(
      page.getByRole("heading", { name: "Email", exact: true }),
    ).toBeVisible();
    await page.getByRole("button", { name: "Next", exact: true }).click();
    await expect(
      page.getByRole("button", {
        name: "Find supporting evidence",
        exact: true,
      }),
    ).toBeEnabled();
    await expect(
      page.getByRole("button", { name: "Next", exact: true }),
    ).toBeDisabled();
    expect(api.calls.map((call) => call.stage)).toEqual([
      "runs",
      "evidence",
      "draft",
    ]);
    expect(api.forbidden).toEqual([]);
  });
}
