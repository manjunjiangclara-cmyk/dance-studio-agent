import { test, expect, type Page } from "@playwright/test";
import examples from "../src/data/examples.v1.json" with { type: "json" };
import { tourBooking, tourSource } from "../src/tourData";

const publicCalls = new WeakMap<Page, string[]>();
const dialogs = new WeakMap<Page, string[]>();
const editedReply =
  "Thanks, Alex. Saturday works for your makeup class. — Clara";
const teacherAnswer = "A trial costs $20, payable at the studio.";

test.beforeEach(async ({ page }) => {
  const calls: string[] = [];
  publicCalls.set(page, calls);
  const openedDialogs: string[] = [];
  dialogs.set(page, openedDialogs);
  page.on("dialog", async (dialog) => {
    openedDialogs.push(dialog.message());
    await dialog.dismiss();
  });
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
  expect(dialogs.get(page)).toEqual([]);
});

async function expectStep(page: Page, name: string, focused = true) {
  const heading = page.getByRole("heading", { name, exact: true, level: 2 });
  await expect(heading).toBeVisible();
  if (focused) await expect(heading).toBeFocused();
  await expect(heading).toHaveCSS("outline-style", "none");
}

async function next(page: Page, name: string) {
  await page.getByRole("button", { name: "Next", exact: true }).click();
  await expectStep(page, name);
}

async function review(page: Page, scenario = "booking") {
  await page.goto(`/demo/tour?mode=recorded&scenario=${scenario}`);
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
  await expect(page).toHaveURL(/mode=live/);
  await expect(
    page.getByRole("link", { name: /Use (recorded demo|live AI)/ }),
  ).toHaveCount(0);
  await page.goto("/demo/tour?mode=recorded");
  await expectStep(page, "Email");
  await expect(page.getByText(/no live AI/i)).toBeVisible();
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
  await expect(
    page.getByRole("button", { name: /Reset|Restart demo|Start over/ }),
  ).toHaveCount(0);
  await expect(
    page
      .getByRole("navigation", { name: "Confirmation actions" })
      .getByRole("button", { name: /Start over|Reset|Restart demo/ }),
  ).toHaveCount(0);
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
  await page.reload();
  await expectStep(page, "Email");
  await next(page, "Evidence");
  await next(page, "Teacher review");
  await expect(page.getByLabel("Final response", { exact: true })).toHaveValue(
    initialDraft,
  );
});

test("tour has no reset button in email, evidence, review or confirmation", async ({
  page,
}) => {
  const resetButtons = page.getByRole("button", {
    name: /Reset|Restart demo|Start over/,
  });
  await page.goto("/demo/tour?mode=recorded");
  await expectStep(page, "Email");
  await expect(resetButtons).toHaveCount(0);
  await next(page, "Evidence");
  await expect(resetButtons).toHaveCount(0);
  await next(page, "Teacher review");
  await expect(resetButtons).toHaveCount(0);
  await page
    .getByRole("button", { name: "Simulate approval and booking", exact: true })
    .click();
  await expectStep(page, "Class booked");
  await expect(resetButtons).toHaveCount(0);
});

test("scenario tabs expose selection and support roving keyboard focus", async ({
  page,
}) => {
  await page.goto("/demo/tour?mode=recorded");
  const tabs = page.getByRole("tablist", {
    name: "Demo scenarios",
    exact: true,
  });
  const booking = tabs.getByRole("tab", {
    name: "Makeup booking",
    exact: true,
  });
  const document = tabs.getByRole("tab", {
    name: "Document enquiry",
    exact: true,
  });
  await expect(booking).toHaveAttribute("aria-selected", "true");
  await expect(booking).toHaveAttribute("tabindex", "0");
  await expect(document).toHaveAttribute("aria-selected", "false");
  await expect(document).toHaveAttribute("tabindex", "-1");
  const panel = page.getByRole("tabpanel");
  await expect(panel).toHaveCount(1);
  await expect(panel).toHaveAttribute(
    "aria-labelledby",
    (await booking.getAttribute("id")) ?? "missing-tab-id",
  );
  await booking.focus();
  await page.keyboard.press("ArrowRight");
  await expect(document).toBeFocused();
  await expect(document).toHaveAttribute("aria-selected", "true");
  await expect(panel).toHaveAttribute(
    "aria-labelledby",
    (await document.getAttribute("id")) ?? "missing-tab-id",
  );
  await page.keyboard.press("Home");
  await expect(booking).toBeFocused();
  await expect(booking).toHaveAttribute("aria-selected", "true");
  await page.keyboard.press("End");
  await expect(document).toBeFocused();
  await expect(document).toHaveAttribute("aria-selected", "true");
  await page.keyboard.press("ArrowLeft");
  await expect(booking).toBeFocused();
  await expect(booking).toHaveAttribute("aria-selected", "true");
});

test("document evidence opens its exact saved source and requires a teacher decision", async ({
  page,
}, testInfo) => {
  await page.goto("/demo/tour?mode=recorded&scenario=document");
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
  await expect(
    page.getByRole("region", { name: "Saved source revision" }),
  ).toHaveCSS("outline-style", "none");
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
  await page
    .getByRole("button", { name: "Generate draft", exact: true })
    .click();
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

test("teacher deferral composes a draft and locks the applied decision", async ({
  page,
}) => {
  await review(page, "document");
  await page.getByRole("radio", { name: "Confirm later", exact: true }).check();
  await page
    .getByRole("button", { name: "Generate draft", exact: true })
    .click();
  await expect(page.getByLabel("Final response", { exact: true })).toHaveValue(
    /I'll confirm the trial fee/,
  );
  await expect(
    page.getByRole("radio", { name: "Provide an answer", exact: true }),
  ).toBeDisabled();
  await page
    .getByRole("button", { name: "Simulate approval", exact: true })
    .click();
  await expectStep(page, "Response approved");
});

test("teacher answer is preserved literally in the generated draft", async ({
  page,
}) => {
  await review(page, "document");
  await page
    .getByRole("radio", { name: "Provide an answer", exact: true })
    .check();
  const literalAnswer =
    "A trial costs $25; literal tokens $& $' $` remain teacher text.";
  await page
    .getByLabel("Trial fee answer", { exact: true })
    .fill(literalAnswer);
  await page
    .getByRole("button", { name: "Generate draft", exact: true })
    .click();
  expect(
    await page.getByLabel("Final response", { exact: true }).inputValue(),
  ).toContain(literalAnswer);
  await expect(
    page.getByLabel("Trial fee answer", { exact: true }),
  ).toBeDisabled();
});

test("blank response blocks approval and an invalid scenario uses the booking default", async ({
  page,
}) => {
  await review(page, "unknown");
  await expect(
    page.getByRole("tab", { name: "Makeup booking", exact: true }),
  ).toHaveAttribute("aria-selected", "true");
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

test("reload, leaving and scenario changes discard local review state", async ({
  page,
}) => {
  await review(page);
  await page.getByLabel("Final response", { exact: true }).fill(editedReply);
  await page.reload();
  await expectStep(page, "Email");
  await next(page, "Evidence");
  await next(page, "Teacher review");
  await expect(
    page.getByLabel("Final response", { exact: true }),
  ).not.toHaveValue(editedReply);
  await page
    .getByRole("tab", { name: "Document enquiry", exact: true })
    .click();
  await expectStep(page, "Email", false);
  await expect(page).toHaveURL(/scenario=document/);
  await next(page, "Evidence");
  await next(page, "Teacher review");
  await expect(
    page.getByRole("button", { name: "Simulate approval", exact: true }),
  ).toBeDisabled();
  await page.getByRole("tab", { name: "Makeup booking", exact: true }).click();
  await expectStep(page, "Email", false);
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
  await page.goto("/demo/tour?mode=recorded&scenario=document");
  await expectStep(page, "Email");
  const nextButton = page.getByRole("button", { name: "Next", exact: true });
  await page.keyboard.press("Tab");
  await expect(nextButton).toBeFocused();
  await expect(nextButton).toHaveCSS("outline-style", "solid");
  await page.keyboard.press("Enter");
  await expectStep(page, "Evidence");
  const citation = page.getByRole("button", {
    name: "Beginner clothing policy · Revision 1",
    exact: true,
  });
  await citation.focus();
  await page.keyboard.press("Enter");
  const source = page.getByRole("region", { name: "Saved source revision" });
  await expect(source).toBeFocused();
  await expect(source).toHaveCSS("outline-style", "none");
  await expect
    .poll(() =>
      page.evaluate(
        () => document.documentElement.scrollWidth <= window.innerWidth,
      ),
    )
    .toBe(true);
  await nextButton.focus();
  await expect(nextButton).toHaveCSS("outline-style", "solid");
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
