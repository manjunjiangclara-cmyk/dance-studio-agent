import { test, expect, type Page } from "@playwright/test";
import examples from "../src/data/examples.v1.json" with { type: "json" };
import type { QuestionResolution, Run } from "../src/types";

const example = examples.agent_runs.find(
  (run) => run.interpretation.flow === "enquiry",
)! as unknown as Run;
const feeQuestion = "What does a trial cost?";
const clothingQuestion = "What should I wear?";
const feeAnswer = "A trial costs $20.";

interface ReviewRequest {
  action: "revise" | "approve";
  expected_revision: number;
  body?: string;
  feedback?: string;
  question_resolutions?: QuestionResolution[];
}

async function mockOwner(
  page: Page,
  run: Run,
  respond?: (
    request: ReviewRequest | undefined,
    endpoint: string,
  ) => { status: number; json: unknown } | undefined,
) {
  const reviews: ReviewRequest[] = [];
  const writes: string[] = [];
  await page.route("**/auth/me", (route) =>
    route.fulfill({
      json: {
        authenticated: true,
        user: { email: "owner@example.test" },
        csrf_token: "csrf",
      },
    }),
  );
  await page.route("**/api/v1/**", async (route) => {
    const request = route.request();
    const path = new URL(request.url()).pathname.replace("/api/v1", "");
    const [resource, id, child] = path.slice(1).split("/");
    if (request.method() !== "GET") {
      writes.push(path);
      expect(request.headers()["x-csrf-token"]).toBe("csrf");
      expect(resource).toBe("agent-runs");
      expect(["review", "retry"]).toContain(child);
      const body =
        child === "review"
          ? (request.postDataJSON() as ReviewRequest)
          : undefined;
      if (body) reviews.push(body);
      const response = respond?.(body, child);
      if (response) return route.fulfill(response);
      if (body?.action === "revise") applyDecisions(run, body);
      else if (body?.action === "approve") {
        run.status = "approved";
        run.approved_response_id = "teacher-response";
      }
      return route.fulfill({ json: run });
    }
    if (resource === "agent-runs") return route.fulfill({ json: run });
    if (resource === "conversations" && child === "messages") {
      const messages = examples.messages.filter(
        (message) => message.conversation_id === id,
      );
      return route.fulfill({
        json: {
          items: messages,
          total: messages.length,
          limit: 100,
          offset: 0,
        },
      });
    }
    const table =
      resource === "sessions"
        ? examples.class_sessions
        : examples[resource as keyof typeof examples];
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
      return route.fulfill({ json: value });
    }
    return route.fulfill({ status: 404, json: {} });
  });
  return { reviews, writes };
}

function applyDecisions(run: Run, request: ReviewRequest) {
  run.revision += 1;
  run.status = "awaiting_review";
  const merged = new Map(
    (run.draft_details.question_resolutions || []).map((item) => [
      item.question_id,
      item,
    ]),
  );
  for (const item of request.question_resolutions || [])
    merged.set(item.question_id, item);
  const decisions = [...merged.values()];
  run.draft_details.question_resolutions = decisions;
  for (const decision of decisions) {
    const answer = run.draft_details.answers!.find(
      (item) => item.question_id === decision.question_id,
    )!;
    answer.status =
      decision.decision === "answer" ? "answered" : "needs_teacher";
    answer.answer =
      decision.decision === "answer"
        ? decision.answer!
        : `Regarding “${answer.question}”, I'll confirm the details and get back to you.`;
    answer.references = [
      `${decision.decision === "answer" ? "teacher_answer" : "teacher_deferral"}:${decision.question_id}`,
    ];
  }
  run.draft_details.body = run.draft_details
    .answers!.map((item) => item.answer)
    .join("\n\n");
  run.draft_details.references = run.draft_details.answers!.flatMap(
    (item) => item.references,
  );
}

async function enterDecisions(page: Page) {
  await page
    .getByRole("radio", {
      name: `Provide answer for ${feeQuestion}`,
      exact: true,
    })
    .check();
  await page
    .getByLabel(`Answer for ${feeQuestion}`, { exact: true })
    .fill(feeAnswer);
  await page
    .getByRole("radio", {
      name: `Confirm later for ${clothingQuestion}`,
      exact: true,
    })
    .check();
}

function expectedDecisions(run: Run): QuestionResolution[] {
  const answers = run.draft_details.answers!;
  return [
    {
      question_id: answers.find((item) => item.question === feeQuestion)!
        .question_id!,
      decision: "answer",
      answer: feeAnswer,
    },
    {
      question_id: answers.find((item) => item.question === clothingQuestion)!
        .question_id!,
      decision: "defer",
      answer: null,
    },
  ];
}

test("public enquiry shows each question and evidence without owner controls or API access", async ({
  page,
}) => {
  const calls: string[] = [];
  page.on("request", (request) => {
    if (/\/(api|auth)\//.test(request.url())) calls.push(request.url());
  });
  await page.goto(`/demo/reviews/${example.id}`);
  await expect(
    page.getByRole("region", { name: "Classification", exact: true }),
  ).toContainText("Enquiry workflow");
  const checklist = page.getByRole("region", { name: "Enquiry checklist" });
  await expect(checklist.getByRole("heading", { level: 3 })).toHaveCount(3);
  await expect(
    checklist.getByText("Needs teacher input", { exact: true }),
  ).toHaveCount(2);
  await expect(
    checklist.getByRole("link", { name: "View session" }),
  ).toBeVisible();
  await expect(checklist.getByRole("radio")).toHaveCount(0);
  await expect(
    page.getByRole("button", { name: "Update draft", exact: true }),
  ).toHaveCount(0);
  expect(calls).toEqual([]);
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= innerWidth,
    ),
  ).toBe(true);
});

test("owner applies a trial fee and clothing deferral before approving the generated reply", async ({
  page,
}) => {
  const run = structuredClone(example);
  const { reviews, writes } = await mockOwner(page, run);
  await page.goto(`/workspace/reviews/${run.id}`);
  const approval = page.getByRole("button", {
    name: "Approve and save response",
    exact: true,
  });
  const update = page.getByRole("button", {
    name: "Update draft",
    exact: true,
  });
  const checklist = page.getByRole("region", { name: "Enquiry checklist" });
  await expect(approval).toBeDisabled();
  await expect(update).toBeDisabled();
  await page
    .getByRole("radio", {
      name: `Provide answer for ${feeQuestion}`,
      exact: true,
    })
    .check();
  await expect(update).toBeDisabled();
  await enterDecisions(page);
  await expect(update).toBeEnabled();
  await expect(approval).toBeDisabled();
  await expect(
    checklist.getByText("Unapplied choice — update the draft to apply it.", {
      exact: true,
    }),
  ).toHaveCount(2);
  expect(reviews).toEqual([]);
  const decisions = expectedDecisions(run);
  const revision = run.revision;
  await update.click();
  await expect(
    page.getByText("A new draft revision is ready.", { exact: true }),
  ).toBeVisible();
  expect(reviews[0]).toEqual({
    action: "revise",
    expected_revision: revision,
    question_resolutions: decisions,
  });
  await expect(page.getByLabel("Final response", { exact: true })).toHaveValue(
    run.draft_details.body!,
  );
  await expect(checklist).toContainText(feeAnswer);
  await expect(checklist).toContainText("Teacher answer applied");
  await expect(checklist).toContainText(
    "Confirm later applied · still awaiting confirmation",
  );
  await expect(checklist).toContainText("Teacher-provided answer");
  await expect(checklist).toContainText("Explicit teacher deferral");
  await expect(
    checklist.getByText("Needs teacher input", { exact: true }),
  ).toHaveCount(1);
  await expect(
    checklist.getByText("Unapplied choice — update the draft to apply it.", {
      exact: true,
    }),
  ).toHaveCount(0);
  await expect(approval).toBeEnabled();
  await page
    .getByLabel(`Answer for ${feeQuestion}`, { exact: true })
    .fill("A trial costs $25.");
  await expect(approval).toBeDisabled();
  await page
    .getByLabel(`Answer for ${feeQuestion}`, { exact: true })
    .fill(feeAnswer);
  await update.click();
  await expect(approval).toBeEnabled();
  await approval.click();
  await expect(
    page.getByText("Response approved and saved. No email has been sent.", {
      exact: true,
    }),
  ).toBeVisible();
  expect(reviews.map((review) => review.action)).toEqual([
    "revise",
    "revise",
    "approve",
  ]);
  expect(reviews[2].body).toContain(feeAnswer);
  expect(reviews[2].body).toContain(
    `Regarding “${clothingQuestion}”, I'll confirm the details and get back to you.`,
  );
  expect(reviews[2].expected_revision).toBe(revision + 2);
  expect(run.draft_details.booking_session_id).toBeNull();
  expect(writes).toEqual(Array(3).fill(`/agent-runs/${run.id}/review`));
});

test("a rejected update preserves answers, deferral and feedback for resubmission", async ({
  page,
}) => {
  const run = structuredClone(example);
  let attempts = 0;
  const { reviews } = await mockOwner(page, run, (body) => {
    if (body?.action === "revise" && ++attempts === 1)
      return {
        status: 503,
        json: { detail: "Draft update temporarily unavailable." },
      };
  });
  await page.goto(`/workspace/reviews/${run.id}`);
  await enterDecisions(page);
  await page.getByLabel("Revision feedback").fill("Keep the reply friendly.");
  await page.getByRole("button", { name: "Update draft", exact: true }).click();
  await expect(
    page.getByText("Draft update temporarily unavailable.", { exact: true }),
  ).toBeVisible();
  await expect(
    page.getByLabel(`Answer for ${feeQuestion}`, { exact: true }),
  ).toHaveValue(feeAnswer);
  await expect(
    page.getByRole("radio", {
      name: `Confirm later for ${clothingQuestion}`,
      exact: true,
    }),
  ).toBeChecked();
  await expect(page.getByLabel("Revision feedback")).toHaveValue(
    "Keep the reply friendly.",
  );
  await expect(
    page.getByRole("button", {
      name: "Approve and save response",
      exact: true,
    }),
  ).toBeDisabled();
  await page.getByRole("button", { name: "Update draft", exact: true }).click();
  await expect(
    page.getByRole("button", {
      name: "Approve and save response",
      exact: true,
    }),
  ).toBeEnabled();
  expect(reviews[1]).toEqual(reviews[0]);
  await expect(page.getByLabel("Revision feedback")).toHaveValue("");
});

test("failed generation keeps pending decisions through a retry that has not applied them", async ({
  page,
}) => {
  const run = structuredClone(example);
  let failed = false;
  const { reviews, writes } = await mockOwner(page, run, (body, endpoint) => {
    if (endpoint === "retry") {
      run.status = "awaiting_review";
      return { status: 200, json: run };
    }
    if (body?.action === "revise" && !failed) {
      failed = true;
      run.status = "failed";
      run.error = "Generation failed before applying the teacher decisions.";
      return { status: 200, json: run };
    }
  });
  await page.goto(`/workspace/reviews/${run.id}`);
  await enterDecisions(page);
  await page
    .getByLabel("Revision feedback")
    .fill("Preserve the timetable answer.");
  await page.getByRole("button", { name: "Update draft", exact: true }).click();
  await expect(
    page.getByText(
      "The run needs attention. Inspect its current state before retrying.",
      { exact: true },
    ),
  ).toBeVisible();
  await page
    .getByRole("button", { name: "Retry this run", exact: true })
    .click();
  await expect(
    page.getByLabel(`Answer for ${feeQuestion}`, { exact: true }),
  ).toHaveValue(feeAnswer);
  await expect(
    page.getByRole("radio", {
      name: `Confirm later for ${clothingQuestion}`,
      exact: true,
    }),
  ).toBeChecked();
  await expect(page.getByLabel("Revision feedback")).toHaveValue(
    "Preserve the timetable answer.",
  );
  await expect(
    page.getByRole("button", {
      name: "Approve and save response",
      exact: true,
    }),
  ).toBeDisabled();
  await page.getByRole("button", { name: "Update draft", exact: true }).click();
  await expect(
    page.getByRole("button", {
      name: "Approve and save response",
      exact: true,
    }),
  ).toBeEnabled();
  expect(reviews[1].question_resolutions).toEqual(
    reviews[0].question_resolutions,
  );
  expect(writes).toContain(`/agent-runs/${run.id}/retry`);
});

test("legacy questions require regeneration before individual decisions or approval", async ({
  page,
}) => {
  const run = structuredClone(example);
  delete run.interpretation.question_ids;
  delete run.draft_details.required_question_ids;
  delete run.draft_details.question_resolutions;
  for (const answer of run.draft_details.answers!) delete answer.question_id;
  const { reviews } = await mockOwner(page, run, (body) => {
    if (body?.action === "revise" && !run.interpretation.question_ids) {
      run.revision += 1;
      run.interpretation.question_ids = structuredClone(
        example.interpretation.question_ids,
      );
      run.draft_details.answers = structuredClone(
        example.draft_details.answers,
      );
      run.draft_details.required_question_ids = structuredClone(
        example.draft_details.required_question_ids,
      );
      run.draft_details.question_resolutions = [];
      return { status: 200, json: run };
    }
  });
  await page.goto(`/workspace/reviews/${run.id}`);
  const checklist = page.getByRole("region", { name: "Enquiry checklist" });
  await expect(
    checklist.getByText(
      "This older review needs an updated question checklist. Select Update draft first.",
      { exact: true },
    ),
  ).toHaveCount(2);
  await expect(checklist.getByRole("radio")).toHaveCount(0);
  await expect(
    page.getByRole("button", {
      name: "Approve and save response",
      exact: true,
    }),
  ).toBeDisabled();
  await page.getByRole("button", { name: "Update draft", exact: true }).click();
  expect(reviews[0]).toEqual({
    action: "revise",
    expected_revision: example.revision,
    feedback: "Regenerate the question checklist for this older review.",
  });
  await expect(checklist.getByRole("radio")).toHaveCount(4);
  await expect(
    page.getByRole("button", {
      name: "Approve and save response",
      exact: true,
    }),
  ).toBeDisabled();
  await enterDecisions(page);
  await page.getByRole("button", { name: "Update draft", exact: true }).click();
  await expect(
    page.getByRole("button", {
      name: "Approve and save response",
      exact: true,
    }),
  ).toBeEnabled();
});

test("a stale revision preserves choices until the owner explicitly loads the latest draft", async ({
  page,
}) => {
  const run = structuredClone(example);
  const originalRevision = run.revision;
  let conflict = true;
  const { reviews } = await mockOwner(page, run, (body) => {
    if (body?.action === "revise" && conflict) {
      conflict = false;
      run.revision += 1;
      return {
        status: 409,
        json: { detail: "This draft changed. Review the current revision." },
      };
    }
  });
  await page.goto(`/workspace/reviews/${run.id}`);
  await enterDecisions(page);
  await page.getByRole("button", { name: "Update draft", exact: true }).click();
  await expect(
    page.getByText("This draft changed. Review the current revision.", {
      exact: true,
    }),
  ).toBeVisible();
  await expect(
    page.getByLabel(`Answer for ${feeQuestion}`, { exact: true }),
  ).toHaveValue(feeAnswer);
  await expect(
    page.getByRole("radio", {
      name: `Confirm later for ${clothingQuestion}`,
      exact: true,
    }),
  ).toBeChecked();
  await expect(
    page.getByRole("button", {
      name: "Approve and save response",
      exact: true,
    }),
  ).toBeDisabled();
  await expect(
    page.getByText(`REVISION ${originalRevision + 1}`, { exact: true }),
  ).toBeVisible();
  await page
    .getByRole("button", {
      name: "Load the latest draft and discard local edits",
      exact: true,
    })
    .click();
  await expect(
    page.getByLabel(`Answer for ${feeQuestion}`, { exact: true }),
  ).toHaveCount(0);
  await expect(
    page.getByRole("radio", {
      name: `Confirm later for ${clothingQuestion}`,
      exact: true,
    }),
  ).not.toBeChecked();
  await enterDecisions(page);
  await page.getByRole("button", { name: "Update draft", exact: true }).click();
  await expect(
    page.getByRole("button", {
      name: "Approve and save response",
      exact: true,
    }),
  ).toBeEnabled();
  expect(reviews[0].expected_revision).toBe(originalRevision);
  expect(reviews[1].expected_revision).toBe(originalRevision + 1);
  expect(reviews[1].question_resolutions).toEqual(
    reviews[0].question_resolutions,
  );
});
