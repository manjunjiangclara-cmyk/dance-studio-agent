import { test, expect, type Page } from "@playwright/test";
import examples from "../src/data/examples.v1.json" with { type: "json" };
import { tourBooking, tourSource } from "../src/tourData";

const publicCalls = new WeakMap<Page, string[]>();
const editedReply =
  "Thanks, Alex. Saturday works for your makeup class. — Clara";
const teacherAnswer = "A trial costs $20, payable at the studio.";

test.beforeEach(async ({ page }) => {
  const calls: string[] = [];
  publicCalls.set(page, calls);
  page.on("request", (request) => {
    const path = new URL(request.url()).pathname;
    if (path.startsWith("/api/") || path.startsWith("/auth/"))
      calls.push(`${request.method()} ${path}`);
  });
  // A regression must fail without reaching a real owner endpoint.
  await page.route("**/api/**", (route) => route.abort());
  await page.route("**/auth/**", (route) => route.abort());
});

test.afterEach(async ({ page }) => {
  expect(publicCalls.get(page)).toEqual([]);
});

async function expectStep(page: Page, name: string) {
  const heading = page.getByRole("heading", { name, exact: true, level: 2 });
  await expect(heading).toBeVisible();
  await expect(heading).toBeFocused();
}

async function next(page: Page, name: string) {
  await page.getByRole("button", { name: "Next", exact: true }).click();
  await expectStep(page, name);
}

async function review(page: Page, scenario = "booking") {
  await page.goto(`/demo/tour?scenario=${scenario}`);
  await expectStep(page, "Email");
  await next(page, "Evidence");
  await next(page, "Teacher review");
}

test("homepage starts a clearly labelled guided demo with editable simulated booking", async ({
  page,
}) => {
  await page.goto("/demo");
  await page
    .getByRole("link", { name: "Try the guided demo", exact: true })
    .click();
  await expect(page).toHaveURL(/\/demo\/tour(?:\?.*)?$/);
  await page
    .getByRole("link", { name: "Use recorded demo", exact: true })
    .click();
  await expectStep(page, "Email");
  await expect(page.getByText(/no live model calls/i)).toBeVisible();
  await expect(page.getByText(/Actually, Saturday/)).toBeVisible();
  await next(page, "Evidence");
  await next(page, "Teacher review");
  await page.getByLabel("Final response", { exact: true }).fill(editedReply);
  await page.getByRole("button", { name: "Back", exact: true }).click();
  await expectStep(page, "Evidence");
  await next(page, "Teacher review");
  await expect(page.getByLabel("Final response", { exact: true })).toHaveValue(
    editedReply,
  );
  await page
    .getByRole("button", { name: "Simulate approval and booking", exact: true })
    .click();
  await expectStep(page, "Class booked");
  await expect(
    page.getByRole("region", { name: "Booking confirmation", exact: true }),
  ).toBeVisible();
  await expect(
    page.getByRole("region", { name: "Email delivery", exact: true }),
  ).toContainText("Email not sent");
  await expect(
    page
      .getByRole("list", { name: "Tour progress" })
      .getByRole("listitem")
      .filter({ hasText: "Confirmation" }),
  ).toHaveAttribute("aria-current", "step");
  await expect(page.getByText("Simulation", { exact: true })).toBeVisible();
  await expect(page.getByText(editedReply, { exact: true })).not.toBeVisible();
  await page.getByText("Approved response", { exact: true }).click();
  await expect(page.getByText(editedReply, { exact: true })).toBeVisible();
});

test("booking confirmation shows a consistent roster snapshot and reapproval replaces it", async ({
  page,
}, testInfo) => {
  await review(page);
  const initialDraft = await page
    .getByLabel("Final response", { exact: true })
    .inputValue();
  await page.getByLabel("Final response", { exact: true }).fill(editedReply);
  await page
    .getByRole("button", { name: "Simulate approval and booking", exact: true })
    .click();
  await expectStep(page, "Class booked");
  const booking = page.getByRole("region", {
    name: "Booking confirmation",
    exact: true,
  });
  await expect(booking).toContainText("Alex Morgan");
  await expect(booking).toContainText("Saturday 13 February 2027");
  await expect(booking).toContainText("Brunswick");
  const database = page.getByRole("region", {
    name: "Database update",
    exact: true,
  });
  const before = database.getByRole("list", {
    name: "Before approval",
    exact: true,
  });
  const after = database.getByRole("list", {
    name: "After approval",
    exact: true,
  });
  await expect(before.getByRole("listitem")).toHaveCount(1);
  await expect(before).toContainText("Noah Ellis");
  await expect(before).not.toContainText("Alex Morgan");
  await expect(after.getByRole("listitem")).toHaveCount(2);
  await expect(
    after.getByRole("listitem").filter({ hasText: "Alex Morgan" }),
  ).toHaveCount(1);
  await expect(after).toContainText("Noah Ellis");
  await expect(
    database.getByText("1 place remaining", { exact: true }),
  ).toBeVisible();
  await expect(
    database.getByText("0 places remaining", { exact: true }),
  ).toBeVisible();
  const record = page
    .locator("details")
    .filter({ has: page.getByText("View saved record", { exact: true }) });
  const response = page
    .locator("details")
    .filter({ has: page.getByText("Approved response", { exact: true }) });
  await expect(record).not.toHaveAttribute("open", "");
  await expect(response).not.toHaveAttribute("open", "");
  await expect(
    page.getByRole("region", { name: "Email delivery", exact: true }),
  ).toContainText("Email not sent");
  await expect(
    page.getByRole("link", { name: "Try document enquiry", exact: true }),
  ).toBeVisible();
  await expect
    .poll(() =>
      page.evaluate(
        () => document.documentElement.scrollWidth <= window.innerWidth,
      ),
    )
    .toBe(true);
  await page.screenshot({
    path: testInfo.outputPath("tour-booking-confirmation.png"),
    fullPage: true,
  });
  await page.getByText("View saved record", { exact: true }).click();
  await expect(record).toContainText("class_sessions.students");
  await expect(record).toContainText(tourBooking.session.id);
  await expect(record).toContainText(tourBooking.student.id);
  for (const member of tourBooking.session.students)
    await expect(record).toContainText(member.id);
  await page.getByText("Approved response", { exact: true }).click();
  await expect(response.getByText(editedReply, { exact: true })).toBeVisible();
  await page
    .getByRole("button", { name: "Back to review", exact: true })
    .click();
  await expectStep(page, "Teacher review");
  await expect(page.getByLabel("Final response", { exact: true })).toHaveValue(
    editedReply,
  );
  const replacement = "Revised response after inspecting the confirmation.";
  await page.getByLabel("Final response", { exact: true }).fill(replacement);
  await page
    .getByRole("button", { name: "Simulate approval and booking", exact: true })
    .click();
  await expectStep(page, "Class booked");
  await expect(after.getByRole("listitem")).toHaveCount(2);
  await expect(
    after.getByRole("listitem").filter({ hasText: "Alex Morgan" }),
  ).toHaveCount(1);
  await page.getByText("Approved response", { exact: true }).click();
  await expect(response.getByText(replacement, { exact: true })).toBeVisible();
  await expect(response.getByText(editedReply, { exact: true })).toHaveCount(0);
  await page.getByRole("button", { name: "Restart demo", exact: true }).click();
  await expectStep(page, "Email");
  await next(page, "Evidence");
  await next(page, "Teacher review");
  await expect(page.getByLabel("Final response", { exact: true })).toHaveValue(
    initialDraft,
  );
});

test("document evidence opens its exact saved source and requires a teacher decision", async ({
  page,
}, testInfo) => {
  await page.goto("/demo/tour?scenario=document");
  await next(page, "Evidence");
  await page
    .getByRole("button", {
      name: "Beginner clothing policy · Revision 1",
      exact: true,
    })
    .click();
  const highlight = page.locator("mark");
  await expect(highlight).toHaveCount(1);
  await expect(highlight).toBeVisible();
  await expect(highlight).toHaveText(tourSource.quote);
  await expect(
    page.getByRole("region", { name: "Saved source revision" }).locator("pre"),
  ).toHaveText(tourSource.text);
  expect(tourSource.text.slice(tourSource.start, tourSource.end)).toBe(
    tourSource.quote,
  );
  await expect(
    page.getByRole("region", { name: "Saved source revision" }),
  ).toBeFocused();
  await page.screenshot({
    path: testInfo.outputPath("tour-source.png"),
    fullPage: true,
  });
  await next(page, "Teacher review");
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
    .fill(teacherAnswer);
  await expect(approve).toBeDisabled();
  await page.getByRole("button", { name: "Update draft", exact: true }).click();
  await expect(page.getByLabel("Final response", { exact: true })).toHaveValue(
    /A trial costs \$20/,
  );
  await expect(approve).toBeEnabled();
  const finalReply =
    "My reviewed reply, saved exactly as typed. <script>plain text</script>";
  await page.getByLabel("Final response", { exact: true }).fill(finalReply);
  await approve.click();
  await expectStep(page, "Response approved");
  await expect(
    page.getByRole("region", { name: "Booking confirmation", exact: true }),
  ).toHaveCount(0);
  await expect(
    page.getByRole("region", { name: "Database update", exact: true }),
  ).toHaveCount(0);
  await expect(
    page.getByRole("region", { name: "Email delivery", exact: true }),
  ).toContainText("Email not sent");
  await page.screenshot({
    path: testInfo.outputPath("tour-document-confirmation.png"),
    fullPage: true,
  });
  await page.getByText("Approved response", { exact: true }).click();
  await expect(page.getByText(finalReply, { exact: true })).toBeVisible();
  await expect(
    page.getByRole("link", { name: "Try makeup booking", exact: true }),
  ).toBeVisible();
});

test("teacher deferral composes a draft and changing the decision blocks approval again", async ({
  page,
}) => {
  await review(page, "document");
  const approve = page.getByRole("button", {
    name: "Simulate approval",
    exact: true,
  });
  await page.getByRole("radio", { name: "Confirm later", exact: true }).check();
  await expect(approve).toBeDisabled();
  await page.getByRole("button", { name: "Update draft", exact: true }).click();
  await expect(approve).toBeEnabled();
  await expect(page.getByLabel("Final response", { exact: true })).toHaveValue(
    /confirm/i,
  );
  await page
    .getByRole("radio", { name: "Provide an answer", exact: true })
    .check();
  await expect(approve).toBeDisabled();
  await page.getByLabel("Trial fee answer", { exact: true }).fill("   ");
  await expect(
    page.getByRole("button", { name: "Update draft", exact: true }),
  ).toBeDisabled();
  await expect(approve).toBeDisabled();
  await page.getByRole("radio", { name: "Confirm later", exact: true }).check();
  await page.getByRole("button", { name: "Update draft", exact: true }).click();
  await approve.click();
  await expectStep(page, "Response approved");
});

test("editing an applied teacher answer requires updating the draft again", async ({
  page,
}) => {
  await review(page, "document");
  await page
    .getByRole("radio", { name: "Provide an answer", exact: true })
    .check();
  const answer = page.getByLabel("Trial fee answer", { exact: true });
  const approve = page.getByRole("button", {
    name: "Simulate approval",
    exact: true,
  });
  await answer.fill(teacherAnswer);
  await page.getByRole("button", { name: "Update draft", exact: true }).click();
  await expect(approve).toBeEnabled();
  await answer.fill("A trial costs $25.");
  await expect(approve).toBeDisabled();
  await page.getByRole("button", { name: "Update draft", exact: true }).click();
  await expect(page.getByLabel("Final response", { exact: true })).toHaveValue(
    /\$25/,
  );
  await expect(approve).toBeEnabled();
  const literalAnswer =
    "A trial costs $25; literal tokens $& $' $` remain teacher text.";
  await answer.fill(literalAnswer);
  await page.getByRole("button", { name: "Update draft", exact: true }).click();
  expect(
    await page.getByLabel("Final response", { exact: true }).inputValue(),
  ).toContain(literalAnswer);
});

test("blank response blocks approval and an invalid scenario uses the booking default", async ({
  page,
}) => {
  await review(page, "unknown");
  await expect(
    page.getByRole("link", { name: "Makeup booking", exact: true }),
  ).toHaveAttribute("aria-current", "page");
  await page.getByLabel("Final response", { exact: true }).fill("   ");
  await expect(
    page.getByRole("button", {
      name: "Simulate approval and booking",
      exact: true,
    }),
  ).toBeDisabled();
  await page.getByLabel("Final response", { exact: true }).fill(editedReply);
  await expect(
    page.getByRole("button", {
      name: "Simulate approval and booking",
      exact: true,
    }),
  ).toBeEnabled();
});

test("reset, reload, leaving and scenario changes discard local review state", async ({
  page,
}) => {
  await review(page);
  await page.getByLabel("Final response", { exact: true }).fill(editedReply);
  await page.getByRole("button", { name: "Reset", exact: true }).click();
  await expectStep(page, "Email");
  await next(page, "Evidence");
  await next(page, "Teacher review");
  await expect(
    page.getByLabel("Final response", { exact: true }),
  ).not.toHaveValue(editedReply);
  await page.getByLabel("Final response", { exact: true }).fill(editedReply);
  await page.reload();
  await expectStep(page, "Email");
  await next(page, "Evidence");
  await next(page, "Teacher review");
  await expect(
    page.getByLabel("Final response", { exact: true }),
  ).not.toHaveValue(editedReply);
  await page
    .getByRole("link", { name: "Document enquiry", exact: true })
    .click();
  await expectStep(page, "Email");
  await expect(page).toHaveURL(/scenario=document/);
  await next(page, "Evidence");
  await next(page, "Teacher review");
  await expect(
    page.getByRole("button", { name: "Simulate approval", exact: true }),
  ).toBeDisabled();
  await page.getByRole("link", { name: "Makeup booking", exact: true }).click();
  await expectStep(page, "Email");
  await next(page, "Evidence");
  await next(page, "Teacher review");
  await expect(
    page.getByLabel("Final response", { exact: true }),
  ).not.toHaveValue(editedReply);
  await page.getByLabel("Final response", { exact: true }).fill(editedReply);
  await page.goto("/demo/reviews");
  await page.goBack();
  await expectStep(page, "Email");
});

test("simulation leaves the existing public student and review fixtures unchanged", async ({
  page,
}) => {
  const alex = examples.students.find(
    (student) => student.display_name === "Alex Morgan",
  )!;
  const run = examples.agent_runs.find((item) => item.revision === 2)!;
  await page.goto(`/demo/students/${alex.id}`);
  await expect(
    page.getByRole("heading", { name: "Alex Morgan", exact: true }),
  ).toBeVisible();
  const originalProfile = await page.getByRole("main").innerText();
  await review(page);
  await page.getByLabel("Final response", { exact: true }).fill(editedReply);
  await page
    .getByRole("button", { name: "Simulate approval and booking", exact: true })
    .click();
  await expectStep(page, "Class booked");
  await page.goto(`/demo/students/${alex.id}`);
  await expect(page.getByRole("main")).toHaveText(originalProfile, {
    useInnerText: true,
  });
  await page.goto(`/demo/reviews/${run.id}`);
  await expect(
    page.getByText("Read-only example.", { exact: false }),
  ).toBeVisible();
  await expect(page.getByText(editedReply, { exact: true })).toHaveCount(0);
  await expect(
    page.getByRole("button", { name: "Approve and book class", exact: true }),
  ).toHaveCount(0);
});

test("tour navigation works by keyboard without horizontal overflow", async ({
  page,
}) => {
  await page.goto("/demo/tour");
  await expectStep(page, "Email");
  const nextButton = page.getByRole("button", { name: "Next", exact: true });
  await nextButton.focus();
  await page.keyboard.press("Enter");
  await expectStep(page, "Evidence");
  await expect
    .poll(() =>
      page.evaluate(
        () => document.documentElement.scrollWidth <= window.innerWidth,
      ),
    )
    .toBe(true);
  await nextButton.focus();
  await page.keyboard.press("Enter");
  await expectStep(page, "Teacher review");
  await expect
    .poll(() =>
      page.evaluate(
        () => document.documentElement.scrollWidth <= window.innerWidth,
      ),
    )
    .toBe(true);
});
