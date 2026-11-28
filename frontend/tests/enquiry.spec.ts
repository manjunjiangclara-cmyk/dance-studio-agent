import { test, expect, type Page } from "@playwright/test";
import examples from "../src/data/examples.v1.json" with { type: "json" };
import ownerEnquiry from "./fixtures/owner-enquiry.json" with { type: "json" };
import type { QuestionResolution, Run } from "../src/types";

// Owner decision tests exercise multiple questions independently of the public demo.
const example = ownerEnquiry as unknown as Run;
const feeQuestion = "What does a trial cost?";
const clothingQuestion = "What should I wear?";
const feeAnswer = "A trial costs $20.";
const clothingAnswer = "Wear comfortable clothes and soft shoes.";
const generatedBody =
  "Thanks for asking! Your trial is $20; comfortable clothes and soft shoes are perfect.";

interface ReviewRequest {
  action: "revise" | "approve" | "reject";
  expected_revision: number;
  body?: string;
  feedback?: string;
  regenerate?: boolean;
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
      } else if (body?.action === "reject") {
        run.status = "closed";
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
  // Simulate a model-authored revision, rather than concatenating checklist answers.
  run.draft_details.body = generatedBody;
  run.draft_details.references = run.draft_details.answers!.flatMap(
    (item) => item.references,
  );
}

async function enterDecisions(page: Page) {
  await page
    .getByLabel(`Answer for ${feeQuestion}`, { exact: true })
    .fill(feeAnswer);
  await page
    .getByLabel(`Answer for ${clothingQuestion}`, { exact: true })
    .fill(clothingAnswer);
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
      decision: "answer",
      answer: clothingAnswer,
    },
  ];
}

test("review concerns appear separately from the student response", async ({
  page,
}) => {
  const run = structuredClone(example);
  run.draft_details.review_concerns = [
    "Confirm the trial fee before sending.",
    "<strong>Check the class time.</strong>",
  ];
  await mockOwner(page, run);
  await page.goto(`/workspace/reviews/${run.id}`);

  const concerns = page.getByRole("region", { name: "Points to review" });
  await expect(concerns).toBeVisible();
  await expect(concerns.locator("li")).toHaveCount(2);
  await expect(concerns).toContainText(
    "<strong>Check the class time.</strong>",
  );
  await expect(concerns.locator("strong")).toHaveCount(0);
  await expect(page.getByLabel("Final response")).toHaveValue(
    run.draft_details.body!,
  );
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= innerWidth,
    ),
  ).toBe(true);
});

test("document citations link to their source revision in the owner library", async ({
  page,
}) => {
  const run = structuredClone(example);
  const documentId = "11111111-1111-4111-8111-111111111111";
  const citation = {
    evidence_id: "Etrial",
    document_id: documentId,
    revision: 2,
    title: "Trial handbook",
    start: 42,
    end: 60,
    quote: "Wear comfortable clothes.",
  };
  run.evidence = [
    {
      tool: "document_answer",
      result: {
        status: "answered",
        claims: [{ text: citation.quote, citations: [citation] }],
      },
    },
  ];
  run.draft_details.references = ["document:Etrial"];
  await mockOwner(page, run);
  await page.route("**/api/v1/documents**", (route) => {
    const url = new URL(route.request().url());
    const summary = {
      id: documentId,
      title: citation.title,
      filename: "trial.md",
      current_revision: 2,
      byte_size: 70,
      ingestion_status: "ready",
      effective_from: null,
      effective_to: null,
    };
    if (url.pathname.endsWith("/answer-activation"))
      return route.fulfill({ json: { status: "disabled", error: null } });
    if (url.pathname.endsWith("/metadata"))
      return route.fulfill({ json: summary });
    if (url.pathname.endsWith("/revisions"))
      return route.fulfill({ json: [{ ...summary, revision: 2 }] });
    if (url.pathname.endsWith("/preview"))
      return route.fulfill({
        json: {
          revision: 2,
          offset: 42,
          content: citation.quote,
          next_offset: null,
          total_characters: 42 + citation.quote.length,
        },
      });
    return route.fulfill({ json: [summary] });
  });
  await page.goto(`/workspace/reviews/${run.id}`);
  await page.locator(".review-support > summary").click();
  await page.locator(".response-support > summary").click();

  const target = `/workspace/knowledge/documents?document=${documentId}&revision=2&offset=42#revision-preview`;
  await expect(
    page
      .getByRole("region", { name: "Document answer and citations" })
      .getByRole("link", { name: "Trial handbook" }),
  ).toHaveAttribute("href", target);
  await expect(
    page.getByRole("link", { name: "Trial handbook · Revision 2" }),
  ).toHaveAttribute("href", target);
  await page
    .getByRole("region", { name: "Document answer and citations" })
    .getByRole("link", { name: "Trial handbook" })
    .click();
  await expect(page).toHaveURL(new RegExp("/workspace/knowledge/documents\\?"));
  await expect(page.getByLabel("Revision preview")).toContainText(
    "Revision 2 · Characters 42–",
  );
  await expect(page.locator(".document-preview")).toHaveText(citation.quote);
});

test("older drafts without review concerns remain usable", async ({ page }) => {
  const run = structuredClone(example);
  delete run.draft_details.review_concerns;
  await mockOwner(page, run);
  await page.goto(`/workspace/reviews/${run.id}`);
  await expect(
    page.getByRole("region", { name: "Points to review" }),
  ).toHaveCount(0);
  await expect(page.getByLabel("Final response")).toBeVisible();
});

test("public enquiry shows each question and evidence without owner controls or API access", async ({
  page,
}) => {
  const calls: string[] = [];
  page.on("request", (request) => {
    if (/\/(api|auth)\//.test(request.url())) calls.push(request.url());
  });
  await page.goto(`/demo/reviews/${example.id}`);
  await page.locator(".review-support > summary").click();
  await expect(
    page.getByRole("region", { name: "Classification", exact: true }),
  ).toContainText("Enquiry workflow");
  const input = page.getByRole("region", { name: "Input needed" });
  await expect(
    input.getByRole("heading", { name: "Needs teacher input" }),
  ).toBeVisible();
  await expect(input.locator(".enquiry-question")).toHaveCount(1);
  await expect(input).toContainText(
    "What should I wear to my first ballet class?",
  );
  await expect(input).not.toContainText(
    "When and where is the Thursday class?",
  );
  await expect(
    page.getByRole("region", { name: "Classification", exact: true }),
  ).toBeVisible();
  await expect(input.getByRole("textbox")).toHaveCount(0);
  await expect(
    page.getByRole("button", { name: "Update draft", exact: true }),
  ).toHaveCount(0);
  await expect(
    page.getByRole("button", { name: "Regenerate response", exact: true }),
  ).toHaveCount(0);
  expect(calls).toEqual([]);
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= innerWidth,
    ),
  ).toBe(true);
});

test("teacher can regenerate a response without entering a change prompt", async ({
  page,
}) => {
  const run = structuredClone(example);
  run.draft_details.required_question_ids = [];
  run.draft_details.answers = [];
  const originalRevision = run.revision;
  const { reviews } = await mockOwner(page, run);
  await page.goto(`/workspace/reviews/${run.id}`);
  const regenerate = page.getByRole("button", { name: "Regenerate response" });
  await expect(regenerate).toBeEnabled();
  await regenerate.click();
  await expect(page.getByLabel("Final response", { exact: true })).toHaveValue(
    generatedBody,
  );
  await expect(page.locator("#review-response .eyebrow")).toContainText(
    `REVISION ${originalRevision + 1}`,
  );
  expect(reviews[0]).toEqual({
    action: "revise",
    expected_revision: originalRevision,
    regenerate: true,
  });
  await page.getByRole("button", { name: "Approve and save response" }).click();
  expect(reviews[1]).toEqual({
    action: "approve",
    expected_revision: originalRevision + 1,
    body: generatedBody,
  });
});

test("regeneration asks before replacing text edits and applies teacher answers", async ({
  page,
}) => {
  const run = structuredClone(example);
  const { reviews } = await mockOwner(page, run);
  await page.goto(`/workspace/reviews/${run.id}`);
  await enterDecisions(page);
  await page.getByLabel("Final response", { exact: true }).fill("My wording");
  await page.getByRole("button", { name: "Regenerate response" }).click();
  await expect(page.getByRole("alertdialog")).toBeVisible();
  expect(reviews).toEqual([]);
  await page.getByRole("button", { name: "Keep editing" }).click();
  await expect(page.getByLabel("Final response", { exact: true })).toHaveValue(
    "My wording",
  );
  await page.getByRole("button", { name: "Regenerate response" }).click();
  await page
    .getByRole("button", { name: "Replace and regenerate response" })
    .click();
  expect(reviews[0]).toEqual({
    action: "revise",
    expected_revision: example.revision,
    regenerate: true,
    question_resolutions: expectedDecisions(run),
  });
  await expect(page.getByLabel("Final response", { exact: true })).toHaveValue(
    generatedBody,
  );
});

test("response references show class, session, and studio names instead of IDs", async ({
  page,
}) => {
  await mockOwner(page, structuredClone(example));
  await page.goto(`/workspace/reviews/${example.id}`);
  await page.locator(".response-support > summary").click();
  const references = page.locator(".response-support .source-links");
  const classId = example.draft_details
    .references!.find((ref) => ref.startsWith("class:"))!
    .slice(6);
  const sessionId = example.draft_details
    .references!.find((ref) => ref.startsWith("session:"))!
    .slice(8);
  await expect(
    references.getByRole("link", { name: /Class: Adult Ballet/ }),
  ).toHaveAttribute("href", `/workspace/timetable?class=${classId}`);
  await expect(
    references.getByRole("link", { name: /Session: Adult Ballet/ }),
  ).toHaveAttribute("href", `/workspace/timetable?session=${sessionId}`);
  await expect(references).toContainText("Studio: Merri Ballet");
  await expect(references).not.toContainText(
    /(?:class|session|location):[0-9a-f-]{20,}/,
  );
});

test("policy, missing records, and message references remain understandable", async ({
  page,
}) => {
  const run = structuredClone(example);
  const historyMessage = examples.messages.find(
    (item) =>
      item.conversation_id === run.conversation_id &&
      item.id !== run.source_message_id,
  )!;
  run.draft_details.references = [
    "policy:version-123",
    "class:missing-record",
    "unknown:internal-456",
    run.source_message_id,
    historyMessage.id,
  ];
  await mockOwner(page, run);
  await page.goto(`/workspace/reviews/${run.id}`);
  await page.locator(".response-support > summary").click();
  const references = page.locator(".response-support .source-links");
  await expect(references).toContainText("Studio policy used for this draft");
  await expect(references).toContainText("Class record unavailable");
  await expect(references).toContainText("Other supporting record");
  await expect(references).not.toContainText("missing-record");
  await expect(references).not.toContainText("internal-456");
  await references.getByRole("link", { name: /Conversation message/ }).click();
  await expect(page.locator(".conversation-history")).toHaveAttribute(
    "open",
    "",
  );
  await expect(page.locator(`#message-${historyMessage.id}`)).toBeVisible();
  await page.locator(".developer-panel > summary").click();
  await expect(page.locator(".developer-panel")).toContainText(
    "unknown:internal-456",
  );
});

test("student clarification is visible and can be saved as a reply", async ({
  page,
}) => {
  const run = structuredClone(example);
  const answers = run.draft_details.answers!;
  run.draft_details.required_question_ids = [];
  run.draft_details.question_resolutions = [];
  for (const answer of answers) answer.status = "answered";
  answers[0].status = "needs_student";
  answers[0].answer = "Could you tell us which day works for you?";
  run.draft_details.body = answers[0].answer;
  const { reviews } = await mockOwner(page, run);
  await page.goto(`/workspace/reviews/${run.id}`);
  const input = page.getByRole("region", { name: "Input needed" });
  await expect(
    input.getByRole("heading", { name: "Needs student input" }),
  ).toBeVisible();
  await expect(input).toContainText(answers[0].question);
  await expect(
    input.getByRole("heading", { name: "Needs teacher input" }),
  ).toHaveCount(0);
  await expect(input.getByRole("textbox")).toHaveCount(0);
  const approval = page.getByRole("button", {
    name: "Approve and save response",
  });
  await expect(approval).toBeEnabled();
  await approval.click();
  expect(reviews[0]).toEqual({
    action: "approve",
    expected_revision: run.revision,
    body: "Could you tell us which day works for you?",
  });
});

test("teacher answers clear their input while student input remains", async ({
  page,
}) => {
  const run = structuredClone(example);
  run.draft_details.answers![0].status = "needs_student";
  const { reviews } = await mockOwner(page, run);
  await page.goto(`/workspace/reviews/${run.id}`);
  const input = page.getByRole("region", { name: "Input needed" });
  await expect(
    input.getByRole("heading", { name: "Needs teacher input" }),
  ).toBeVisible();
  await expect(
    input.getByRole("heading", { name: "Needs student input" }),
  ).toBeVisible();
  await enterDecisions(page);
  await page.getByRole("button", { name: "Update draft" }).click();
  await expect(
    input.getByRole("heading", { name: "Needs teacher input" }),
  ).toHaveCount(0);
  await expect(
    input.getByRole("heading", { name: "Needs student input" }),
  ).toBeVisible();
  await expect(input.getByRole("textbox")).toHaveCount(0);
  await expect(
    page.getByRole("button", { name: "Approve and save response" }),
  ).toBeEnabled();
  expect(reviews[0].question_resolutions).toHaveLength(2);
});

test("input area stays hidden when no teacher or student answer is needed", async ({
  page,
}) => {
  const run = structuredClone(example);
  run.draft_details.required_question_ids = [];
  for (const answer of run.draft_details.answers!) answer.status = "answered";
  run.interpretation.requested_actions = ["Check the student's level"];
  await mockOwner(page, run);
  await page.goto(`/workspace/reviews/${run.id}`);
  await expect(page.getByRole("region", { name: "Input needed" })).toHaveCount(
    0,
  );
  await expect(
    page.getByRole("button", { name: "Approve and save response" }),
  ).toBeEnabled();
  await page.locator(".response-support > summary").click();
  await expect(page.locator(".response-support")).toContainText(
    "Check the student's level",
  );
});

test("a decision to confirm later is no longer shown as teacher input", async ({
  page,
}) => {
  const run = structuredClone(example);
  const fee = run.draft_details.answers!.find(
    (answer) => answer.question === feeQuestion,
  )!;
  run.draft_details.question_resolutions = [
    { question_id: fee.question_id!, decision: "defer", answer: null },
  ];
  await mockOwner(page, run);
  await page.goto(`/workspace/reviews/${run.id}`);
  const input = page.getByRole("region", { name: "Input needed" });
  await expect(input).not.toContainText(feeQuestion);
  await expect(input).toContainText(clothingQuestion);
});

test("teacher can defer a studio fact and update the draft", async ({
  page,
}) => {
  const run = structuredClone(example);
  const feeId = run.draft_details.answers!.find(
    (answer) => answer.question === feeQuestion,
  )!.question_id!;
  const { reviews } = await mockOwner(page, run);
  await page.goto(`/workspace/reviews/${run.id}`);
  const input = page.getByRole("region", { name: "Input needed" });
  await input.getByLabel("I’ll confirm this later").first().check();
  await page
    .getByLabel(`Answer for ${clothingQuestion}`, { exact: true })
    .fill(clothingAnswer);
  await page.getByRole("button", { name: "Update draft" }).click();
  expect(reviews[0].question_resolutions).toEqual([
    { question_id: feeId, decision: "defer", answer: null },
    expectedDecisions(run)[1],
  ]);
  await expect(input).toHaveCount(0);
  await expect(
    page.getByRole("button", { name: "Approve and save response" }),
  ).toBeEnabled();
});

test("owner enters fee and clothing decisions before approving the generated reply", async ({
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
  await expect(
    page.locator(".review-main").getByRole("button", {
      name: "Update draft",
      exact: true,
    }),
  ).toBeVisible();
  const checklist = page.getByRole("region", { name: "Input needed" });
  await expect(checklist).toContainText(
    "Add the studio facts or mark what you’ll confirm later, then update",
  );
  await expect(
    checklist.getByRole("heading", {
      name: "When and where is the Thursday class?",
    }),
  ).toHaveCount(0);
  await expect(
    checklist.getByRole("heading", { name: "Needs teacher input" }),
  ).toBeVisible();
  await expect(approval).toBeDisabled();
  await expect(update).toBeDisabled();
  await expect(checklist.getByRole("checkbox")).toHaveCount(2);
  await page
    .getByLabel(`Answer for ${feeQuestion}`, { exact: true })
    .fill("   ");
  await expect(update).toBeDisabled();
  await enterDecisions(page);
  await expect(page.locator(".review-main .approval-guidance")).toContainText(
    "Update the draft to apply your decisions or feedback.",
  );
  await expect(update).toBeEnabled();
  await expect(approval).toBeDisabled();
  await expect(
    checklist.getByText("Unapplied choice — update the draft to use it.", {
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
    generatedBody,
  );
  await expect(checklist).toHaveCount(0);
  await expect(
    page.getByRole("button", { name: "Edit previous teacher answers" }),
  ).toBeVisible();
  await expect(approval).toBeEnabled();
  await page
    .getByRole("button", { name: "Edit previous teacher answers" })
    .click();
  await page
    .getByLabel(`Answer for ${feeQuestion}`, { exact: true })
    .fill("A trial costs $25.");
  await expect(approval).toBeDisabled();
  await page
    .getByLabel(`Answer for ${feeQuestion}`, { exact: true })
    .fill(feeAnswer);
  await update.click();
  await expect(checklist).toHaveCount(0);
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
  expect(reviews[2].body).toBe(generatedBody);
  expect(reviews[2].expected_revision).toBe(revision + 2);
  expect(run.draft_details.booking_session_id).toBeNull();
  expect(writes).toEqual(Array(3).fill(`/agent-runs/${run.id}/review`));
});

test("a rejected update preserves decisions and feedback for resubmission", async ({
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
  await page.getByLabel("Change prompt").fill("Keep the reply friendly.");
  await page.getByRole("button", { name: "Update draft", exact: true }).click();
  await expect(
    page.getByText("Draft update temporarily unavailable.", { exact: true }),
  ).toBeVisible();
  await expect(
    page.getByLabel(`Answer for ${feeQuestion}`, { exact: true }),
  ).toHaveValue(feeAnswer);
  await expect(
    page.getByLabel(`Answer for ${clothingQuestion}`, { exact: true }),
  ).toHaveValue(clothingAnswer);
  await expect(page.getByLabel("Change prompt")).toHaveValue(
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
  await expect(page.getByLabel("Change prompt")).toHaveValue("");
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
  await page.getByLabel("Change prompt").fill("Preserve the timetable answer.");
  await page.getByRole("button", { name: "Update draft", exact: true }).click();
  await expect(
    page.getByText(
      "The run needs attention. Inspect its current state before retrying.",
      { exact: true },
    ),
  ).toBeVisible();
  await expect(
    page.getByRole("heading", { name: "Recover this review" }),
  ).toBeVisible();
  await page
    .getByRole("button", { name: "Retry this run", exact: true })
    .click();
  await expect(
    page.getByLabel(`Answer for ${feeQuestion}`, { exact: true }),
  ).toHaveValue(feeAnswer);
  await expect(
    page.getByLabel(`Answer for ${clothingQuestion}`, { exact: true }),
  ).toHaveValue(clothingAnswer);
  await expect(page.getByLabel("Change prompt")).toHaveValue(
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

test("failed unapproved review can be closed without a response", async ({
  page,
}) => {
  const run = structuredClone(example);
  run.status = "failed";
  run.error = "The combined question checklist exceeds 20 questions.";
  run.draft_details.failure_code = "question_limit_exceeded";
  const { reviews } = await mockOwner(page, run);
  await page.goto(`/workspace/reviews/${run.id}`);
  await expect(page.getByText(run.error)).toBeVisible();
  await expect(
    page.getByRole("button", { name: "Retry this run" }),
  ).toHaveCount(0);
  await page.getByRole("button", { name: "Close review", exact: true }).click();
  await expect(
    page.getByText("Review closed without approving a response."),
  ).toBeVisible();
  expect(reviews).toEqual([
    { action: "reject", expected_revision: run.revision },
  ]);
});

test("failed finalization retains retry without a close control", async ({
  page,
}) => {
  const run = structuredClone(example);
  run.status = "failed";
  run.approved_response_id = "teacher-response";
  run.draft_details.failure_code = "question_limit_exceeded";
  await mockOwner(page, run);
  await page.goto(`/workspace/reviews/${run.id}`);
  await expect(
    page.getByRole("button", { name: "Retry this run" }),
  ).toBeVisible();
  await expect(page.getByRole("button", { name: "Close review" })).toHaveCount(
    0,
  );
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
  const checklist = page.getByRole("region", { name: "Input needed" });
  await expect(
    checklist.getByText(
      "This older review needs an updated question checklist. Select Update draft first.",
      { exact: true },
    ),
  ).toHaveCount(2);
  await expect(checklist.getByRole("textbox")).toHaveCount(0);
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
  await expect(checklist.getByRole("textbox")).toHaveCount(2);
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
    page.getByLabel(`Answer for ${clothingQuestion}`, { exact: true }),
  ).toHaveValue(clothingAnswer);
  await expect(
    page.getByRole("button", {
      name: "Approve and save response",
      exact: true,
    }),
  ).toBeDisabled();
  await expect(
    page.locator("#review-response .section-heading .eyebrow"),
  ).toContainText(`REVISION ${originalRevision + 1}`);
  await page
    .getByRole("button", {
      name: "Load the latest draft and discard local edits",
      exact: true,
    })
    .click();
  await expect(
    page.getByLabel(`Answer for ${feeQuestion}`, { exact: true }),
  ).toHaveValue("");
  await expect(
    page.getByLabel(`Answer for ${clothingQuestion}`, { exact: true }),
  ).toHaveValue("");
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

test("applied decision disappears while unanswered questions remain and can be corrected", async ({
  page,
}) => {
  const run = structuredClone(example);
  const { reviews } = await mockOwner(page, run);
  await page.goto(`/workspace/reviews/${run.id}`);
  const checklist = page.getByRole("region", { name: "Input needed" });
  await page
    .getByLabel(`Answer for ${feeQuestion}`, { exact: true })
    .fill(feeAnswer);
  await page.getByRole("button", { name: "Update draft", exact: true }).click();
  await expect(
    checklist.getByRole("heading", { name: feeQuestion }),
  ).toHaveCount(0);
  await expect(
    checklist.getByRole("heading", { name: clothingQuestion }),
  ).toBeVisible();
  await expect(
    page.getByRole("button", { name: "Approve and save response" }),
  ).toBeDisabled();
  expect(reviews[0].question_resolutions).toHaveLength(1);
  await page.reload();
  await expect(
    checklist.getByRole("heading", { name: feeQuestion }),
  ).toHaveCount(0);
  await expect(
    checklist.getByRole("heading", { name: clothingQuestion }),
  ).toBeVisible();
  await page
    .getByRole("button", { name: "Edit previous teacher answers" })
    .click();
  await expect(page.getByLabel(`Answer for ${feeQuestion}`)).toHaveValue(
    feeAnswer,
  );
});

test("document answers show revision-bound quotes as safe text", async ({
  page,
}) => {
  const run = structuredClone(example);
  const quote = '<img src=x onerror="window.__documentInjected=true"> Café 💃';
  run.evidence = [
    {
      tool: "document_answer",
      finding: "What does a trial cost?",
      result: {
        status: "answered",
        as_of: "2026-11-09",
        answer: "A trial costs $20. [Etrial]",
        missing_information: [],
        references: ["document:Etrial"],
        claims: [
          {
            text: "A trial costs $20.",
            citations: [
              {
                evidence_id: "Etrial",
                title: "Trial handbook",
                revision: 3,
                document_id: "00000000-0000-0000-0000-000000000001",
                start: 20,
                end: 80,
                quote,
              },
            ],
          },
        ],
      },
    },
  ];
  run.draft_details.references = ["document:Etrial"];
  await mockOwner(page, run);
  await page.goto(`/workspace/reviews/${run.id}`);
  await page
    .getByText("Student, classification and supporting evidence", {
      exact: true,
    })
    .click();
  const evidence = page.getByRole("region", {
    name: "Document answer and citations",
  });
  // section receives an accessible region name from aria-label.
  await expect(evidence).toContainText("Trial handbook");
  await expect(evidence).toContainText("Revision 3");
  await expect(evidence).toContainText("Characters 20–80");
  await expect(evidence.locator("blockquote")).toHaveText(quote);
  await expect(evidence.locator("img")).toHaveCount(0);
  expect(
    await page.evaluate(() => Reflect.get(window, "__documentInjected")),
  ).toBeUndefined();
});

test("source-change approval conflict preserves the teacher's edited reply", async ({
  page,
}) => {
  const run = structuredClone(example);
  run.draft_details.answers = [];
  run.draft_details.required_question_ids = [];
  run.draft_details.questions = [];
  await mockOwner(page, run, (request) =>
    request?.action === "approve"
      ? {
          status: 409,
          json: {
            detail:
              "Document sources changed or were disabled. Regenerate the draft before approval.",
          },
        }
      : undefined,
  );
  await page.goto(`/workspace/reviews/${run.id}`);
  const reply = page.getByLabel("Final response", { exact: true });
  await reply.fill("My local teacher edits must stay here.");
  await page
    .getByRole("button", { name: "Approve and save response", exact: true })
    .click();
  await expect(
    page.getByText(
      "Document sources changed or were disabled. Regenerate the draft before approval.",
      { exact: true },
    ),
  ).toBeVisible();
  await expect(reply).toHaveValue("My local teacher edits must stay here.");
});
