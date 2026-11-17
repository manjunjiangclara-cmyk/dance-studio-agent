import { test, expect } from "@playwright/test";

test("custom email asks teacher before generating a single draft", async ({
  page,
}) => {
  const calls: { stage: string; body: any }[] = [];
  await page.route("**/api/public-demo/**", async (route) => {
    const stage = new URL(route.request().url()).pathname.split("/").pop()!;
    const body = route.request().postDataJSON();
    calls.push({ stage, body });
    await route.fulfill({
      json:
        stage === "runs"
          ? { token: "test" }
          : stage === "evidence"
            ? {
                evidence: [],
                route: "enquiry",
                missing_information: ["Trial fee"],
                model: "test",
              }
            : {
                body: `The trial is ${body.teacher_answers[0]}.`,
                model: "test",
              },
    });
  });
  await page.goto("/demo/test-email");
  await page.getByLabel("Email body").fill("What is the trial fee?");
  await page.getByRole("button", { name: "Simulate email" }).click();
  await expect(page.getByLabel("Trial fee")).toBeVisible();
  await expect(
    page.getByRole("button", { name: "Generate draft" }),
  ).toBeDisabled();
  expect(calls.map((call) => call.stage)).toEqual(["runs", "evidence"]);
  await page.getByLabel("Trial fee").fill("$20");
  await page.getByRole("button", { name: "Generate draft" }).click();
  await expect(page.getByLabel("Draft response")).toHaveValue(
    "The trial is $20.",
  );
  expect(calls[2].body).toEqual({ teacher_answers: ["$20"] });
  await page.getByLabel("Draft response").fill("");
  await page.getByLabel("Draft response").fill("Replacement");
  await expect(page.getByLabel("Draft response")).toHaveValue("Replacement");
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
