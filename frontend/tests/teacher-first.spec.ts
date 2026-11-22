import { test, expect } from "@playwright/test";

test("custom email accepts teacher information when generating a draft", async ({
  page,
}) => {
  const calls: string[] = [];
  let draft: { body: string } | null = null;
  let turnId = "";
  let evidence: object | null = null;
  await page.route("**/api/public-demo/**", async (route) => {
    const req = route.request();
    const stage = new URL(req.url()).pathname.split("/").pop()!;
    calls.push(stage);
    if (stage === "threads") return route.fulfill({ json: { token: "test" } });
    if (stage === "turns") {
      turnId = req.postDataJSON().request_id;
      return route.fulfill({ json: { request_id: turnId } });
    }
    if (stage === "evidence") {
      evidence = {
        evidence: [],
        route: "enquiry",
        missing_information: ["Trial fee"],
        model: "test",
      };
      return route.fulfill({ json: evidence });
    }
    if (stage === "draft") {
      draft = {
        body: `The trial is ${req.postDataJSON().teacher_answers[0]}.`,
      };
      return route.fulfill({ json: draft });
    }
    return route.fulfill({
      json: {
        student: "new",
        state: {
          intents: [],
          experience_level: null,
          preferred_day: null,
          customer_name: null,
          recommended_class: null,
          booking_status: "not_started",
          next_action: "answer",
          revision: 0,
        },
        turns: [
          {
            request_id: turnId,
            email: "What is the trial fee?",
            reply: null,
            evidence,
            draft,
          },
        ],
      },
    });
  });
  await page.goto("/demo/test-email");
  await page.getByLabel("Email body").fill("What is the trial fee?");
  await page.getByRole("button", { name: "Simulate email" }).click();
  await expect(page.getByLabel("Trial fee")).toBeVisible();
  await expect(
    page.getByRole("button", { name: "Generate draft" }),
  ).toBeEnabled();
  expect(calls).toEqual(["threads", "turns", "current", "evidence", "current"]);
  await page.getByLabel("Trial fee").fill("$20");
  await page.getByRole("button", { name: "Generate draft" }).click();
  await expect(
    page.getByRole("textbox", { name: "Response", exact: true }),
  ).toHaveValue("The trial is $20.");
  await page
    .getByRole("textbox", { name: "Response", exact: true })
    .fill("Replacement");
  await expect(
    page.getByRole("textbox", { name: "Response", exact: true }),
  ).toHaveValue("Replacement");
});

test("recorded document asks before generating", async ({ page }) => {
  await page.goto("/demo/tour?scenario=document&mode=recorded");
  await page.getByRole("button", { name: "Next" }).click();
  await page.getByRole("button", { name: "Next" }).click();
  const generate = page.getByRole("button", { name: "Generate draft" });
  await expect(generate).toBeDisabled();
  await page.getByLabel("Provide an answer").check();
  await page.getByLabel("Trial fee answer").fill("$20");
  await generate.click();
  await expect(page.getByLabel("Final response")).toHaveValue(/\$20/);
  await page.getByLabel("Final response").fill("");
  await page.getByLabel("Final response").fill("Replacement");
  await expect(
    page.getByRole("button", { name: "Simulate approval", exact: true }),
  ).toBeEnabled();
});
