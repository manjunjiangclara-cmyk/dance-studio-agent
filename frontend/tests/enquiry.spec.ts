import { test, expect } from "@playwright/test";
import examples from "../src/data/examples.v1.json" with { type: "json" };

const example = examples.agent_runs.find(
  (run) => run.interpretation.flow === "enquiry",
)!;

test("public enquiry shows each question and its evidence without API access", async ({
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
  await expect(checklist).toContainText("Answered");
  await expect(
    checklist.getByText("Needs teacher input", { exact: true }),
  ).toHaveCount(2);
  await expect(
    checklist.getByRole("link", { name: "View session" }),
  ).toBeVisible();
  expect(calls).toEqual([]);
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= innerWidth,
    ),
  ).toBe(true);
});

test("owner revises an enquiry and approves the final reply without booking", async ({
  page,
}) => {
  let current = structuredClone(example);
  const reviews: Record<string, unknown>[] = [];
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
    if (resource === "agent-runs") {
      if (child === "review") {
        const body = request.postDataJSON();
        reviews.push(body);
        expect(request.headers()["x-csrf-token"]).toBe("csrf");
        if (body.action === "revise") {
          current.revision += 1;
          current.draft_details.body =
            "The Thursday class starts at 6 pm. A trial costs $20.";
          const answers = current.draft_details.answers!;
          answers[1] = {
            ...answers[1],
            status: "answered",
            answer: "A trial costs $20.",
            references: ["teacher_feedback"],
          };
        } else {
          current.status = "approved";
          current.approved_response_id = "teacher-response";
        }
      }
      return route.fulfill({ json: current });
    }
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
  await page.goto(`/workspace/reviews/${example.id}`);
  const checklist = page.getByRole("region", { name: "Enquiry checklist" });
  await expect(checklist).toBeVisible();
  await page
    .getByLabel("Revision feedback")
    .fill("A trial costs $20. Include this fee.");
  await page
    .getByRole("button", { name: "Request revision", exact: true })
    .click();
  await expect(
    page.getByText("A new draft revision is ready.", { exact: true }),
  ).toBeVisible();
  await expect(checklist).toContainText("A trial costs $20.");
  await expect(checklist).toContainText("Teacher revision feedback");
  await page
    .getByRole("button", { name: "Approve and save response", exact: true })
    .click();
  await expect(
    page.getByText("Response approved and saved. No email has been sent.", {
      exact: true,
    }),
  ).toBeVisible();
  expect(reviews.map((review) => review.action)).toEqual(["revise", "approve"]);
  expect(reviews[1].body).toContain("A trial costs $20.");
  expect(current.draft_details.booking_session_id).toBeNull();
});
