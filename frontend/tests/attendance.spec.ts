import { test, expect, type Page } from "@playwright/test";
import type {
  Enrolment,
  Location,
  Session,
  StudentDetail,
  StudioClass,
  Term,
} from "../src/types";

const record = {
  created_at: "2027-01-01T00:00:00Z",
  updated_at: "2027-01-01T00:00:00Z",
};
const studentId = "attendance-student";
const location: Location = {
  ...record,
  id: "attendance-location",
  name: "Melbourne studio",
  address: "Fictional studio address",
  timezone: "Australia/Melbourne",
};

function term(starts_on = "2027-02-01", ends_on = "2027-04-30"): Term {
  return {
    ...record,
    id: "attendance-term",
    name: "Term 1",
    starts_on,
    ends_on,
  };
}

function studioClass(id: string, name: string): StudioClass {
  return {
    ...record,
    id,
    name,
    term_id: "attendance-term",
    location_id: location.id,
    level: "Level 2",
    prerequisites: null,
  };
}

function enrolment(
  id: string,
  classId: string,
  overrides: Partial<Enrolment> = {},
): Enrolment {
  return {
    ...record,
    id,
    student_id: studentId,
    class_id: classId,
    starts_on: "2027-02-01",
    ends_on: null,
    status: "active",
    ...overrides,
  };
}

function session(id: string, classId: string, startsAt: string): Session {
  return {
    ...record,
    id,
    class_id: classId,
    starts_at: startsAt,
    ends_at: new Date(Date.parse(startsAt) + 60 * 60 * 1000).toISOString(),
    capacity: 12,
    students: [studentId],
  };
}

async function mockAttendance(
  page: Page,
  data: {
    enrolments: Enrolment[];
    current: Enrolment[];
    classes: StudioClass[];
    sessions: Session[];
    term?: Term;
  },
) {
  const student: StudentDetail = {
    ...record,
    id: studentId,
    display_name: "Attendance Example",
    email: "attendance@example.com",
    highest_level: "Level 2",
    ai_summary: null,
    context: {},
    as_of: "2027-02-11",
    current_enrolments: data.current,
    enrolment_history: data.enrolments,
  };
  const reads: string[] = [];
  const writes: string[] = [];
  await page.route("**/auth/me", (route) =>
    route.fulfill({
      json: {
        authenticated: true,
        user: { email: "owner@example.com", name: "Owner" },
        csrf_token: "attendance-csrf",
      },
    }),
  );
  await page.route("**/api/v1/**", async (route) => {
    const request = route.request();
    const url = new URL(request.url());
    const path = url.pathname.replace("/api/v1", "");
    if (request.method() !== "GET") {
      writes.push(path);
      return route.fulfill({ status: 405, json: {} });
    }
    reads.push(url.pathname + url.search);
    if (path === `/students/${studentId}`)
      return route.fulfill({ json: student });
    const tables: Record<string, unknown[]> = {
      "/classes": data.classes,
      "/sessions": data.sessions,
      "/terms": [data.term || term()],
      "/locations": [location],
      "/conversations": [],
      "/agent-runs": [],
    };
    const items = tables[path];
    if (!items)
      return route.fulfill({
        status: 404,
        json: { error: { message: `Unexpected mocked route: ${path}` } },
      });
    return route.fulfill({
      json: { items, total: items.length, limit: 100, offset: 0 },
    });
  });
  return { reads, writes };
}

function confirmedCard(page: Page) {
  return page.getByRole("region", { name: "Confirmed sessions", exact: true });
}

test("confirmed attendance shows all explicit session memberships", async ({
  page,
}) => {
  const regularClass = studioClass("regular-class", "Monday regular class");
  const makeupClass = studioClass("makeup-class", "Saturday makeup class");
  const regular = enrolment("regular-enrolment", regularClass.id);
  const regularSessions = Array.from({ length: 12 }, (_, index) => {
    const start = new Date(Date.UTC(2027, 1, 1 + 7 * index, 7));
    return session(
      `regular-${index + 1}`,
      regularClass.id,
      start.toISOString(),
    );
  });
  const makeup = session("makeup-13", makeupClass.id, "2027-04-24T07:00:00Z");
  await mockAttendance(page, {
    classes: [regularClass, makeupClass],
    enrolments: [regular],
    current: [regular],
    sessions: [makeup, ...regularSessions.toReversed()],
  });
  await page.goto(`/workspace/students/${studentId}`);
  await expect(
    page.getByRole("heading", { name: "Attendance Example" }),
  ).toBeVisible();
  const links = confirmedCard(page).locator('a[href*="/timetable?session="]');
  await expect(links).toHaveCount(13);
  expect(
    await links.evaluateAll((rows) =>
      rows.map((row) => row.getAttribute("href")),
    ),
  ).toEqual(
    [...regularSessions, makeup].map(
      (row) => `/workspace/timetable?session=${row.id}`,
    ),
  );
  await expect(
    confirmedCard(page).getByText("Session student", { exact: true }),
  ).toHaveCount(13);
});

test("attendance uses session membership independently of enrolment dates and status", async ({
  page,
}) => {
  const endedClass = studioClass("ended-class", "Ended attendance period");
  const boundedClass = studioClass("bounded-class", "Term bounded class");
  const cancelledClass = studioClass("cancelled-class", "Cancelled course");
  const ended = enrolment("ended", endedClass.id, {
    starts_on: "2027-02-02",
    ends_on: "2027-02-08",
    status: "ended",
  });
  const bounded = enrolment("bounded", boundedClass.id, {
    starts_on: "2027-01-01",
    ends_on: "2027-03-31",
  });
  const cancelled = enrolment("cancelled", cancelledClass.id, {
    status: "cancelled",
  });
  const included = [
    session("term-start", boundedClass.id, "2027-01-31T13:30:00Z"),
    session("enrolment-start", endedClass.id, "2027-02-01T13:30:00Z"),
    session("enrolment-end", endedClass.id, "2027-02-07T13:30:00Z"),
    session("term-end", boundedClass.id, "2027-02-28T12:30:00Z"),
    session("cancelled-session", cancelledClass.id, "2027-02-05T07:00:00Z"),
  ];
  const excluded = [
    session("before-term", boundedClass.id, "2027-01-31T12:30:00Z"),
    session("after-term", boundedClass.id, "2027-02-28T13:30:00Z"),
    session("before-enrolment", endedClass.id, "2027-01-31T13:30:00Z"),
    session("after-enrolment", endedClass.id, "2027-02-08T13:30:00Z"),
  ].map((row) => ({ ...row, students: [] }));
  await mockAttendance(page, {
    classes: [endedClass, boundedClass, cancelledClass],
    enrolments: [ended, bounded, cancelled],
    current: [bounded],
    sessions: [...excluded, ...included.toReversed()],
    term: term("2027-02-01", "2027-02-28"),
  });
  await page.goto(`/workspace/students/${studentId}`);
  const links = confirmedCard(page).locator('a[href*="/timetable?session="]');
  await expect(links).toHaveCount(5);
  expect(
    await links.evaluateAll((rows) =>
      rows.map((row) => row.getAttribute("href")),
    ),
  ).toEqual(
    [...included]
      .sort((a, b) => a.starts_at.localeCompare(b.starts_at))
      .map((row) => `/workspace/timetable?session=${row.id}`),
  );
  await expect(
    confirmedCard(page).locator(
      'a[href*="/timetable?session=enrolment-start"]',
    ),
  ).toHaveCount(1);
});

test("student enrolments default to current records with expandable history and no date control", async ({
  page,
}) => {
  const currentClass = studioClass("current-class", "Current course");
  const historicalClass = studioClass("historical-class", "Historical course");
  const current = enrolment("current", currentClass.id);
  const historical = enrolment("historical", historicalClass.id, {
    starts_on: "2026-11-01",
    ends_on: "2026-12-01",
    status: "ended",
  });
  const calls = await mockAttendance(page, {
    classes: [currentClass, historicalClass],
    enrolments: [current, historical],
    current: [current],
    sessions: [],
  });
  await page.goto(`/workspace/students/${studentId}`);
  await expect(
    page.getByRole("heading", { name: "Attendance Example" }),
  ).toBeVisible();
  await expect(page.getByLabel("Enrolments as of date")).toHaveCount(0);
  await expect(
    page.getByRole("link", { name: "Current course", exact: true }),
  ).toBeVisible();
  await expect(
    page.getByRole("link", { name: "Historical course", exact: true }),
  ).not.toBeVisible();
  const history = page.locator("details").filter({
    has: page.locator("summary").filter({ hasText: "Full enrolment history" }),
  });
  await expect(history).toHaveCount(1);
  await expect(history).not.toHaveAttribute("open");
  await history.locator("summary").focus();
  await page.keyboard.press("Enter");
  await expect(history).toHaveAttribute("open", "");
  await expect(
    history.getByRole("link", { name: "Historical course", exact: true }),
  ).toBeVisible();
  await history.locator("summary").click();
  await expect(history).not.toHaveAttribute("open");
  const studentReads = calls.reads.filter((url) =>
    url.includes(`/students/${studentId}`),
  );
  expect(studentReads).toHaveLength(1);
  expect(
    new URL(studentReads[0], "http://localhost").searchParams.has("on_date"),
  ).toBe(false);
  expect(calls.writes).toEqual([]);
});

test("owner records actual attendance on a completed session", async ({
  page,
}) => {
  const cls = studioClass("recorded-class", "Recorded class");
  const completed = session("recorded-session", cls.id, "2020-02-01T07:00:00Z");
  await mockAttendance(page, {
    enrolments: [],
    current: [],
    classes: [cls],
    sessions: [completed],
  });
  const student = {
    ...record,
    id: studentId,
    display_name: "Attendance Example",
    email: "attendance@example.com",
    highest_level: "Level 2",
    ai_summary: null,
    context: {},
  };
  let status = "unknown";
  await page.route("**/api/v1/sessions/recorded-session/students?*", (route) =>
    route.fulfill({
      json: { items: [student], total: 1, limit: 100, offset: 0 },
    }),
  );
  await page.route(
    "**/api/v1/sessions/recorded-session/attendance**",
    async (route) => {
      if (route.request().method() === "PUT") {
        expect(route.request().headers()["x-csrf-token"]).toBe(
          "attendance-csrf",
        );
        status = route.request().postDataJSON().status;
        return route.fulfill({ json: { student_id: studentId, status } });
      }
      return route.fulfill({
        json: status === "unknown" ? {} : { [studentId]: status },
      });
    },
  );
  await page.goto("/workspace/timetable?session=recorded-session");
  const attendance = page.getByLabel("Attendance for Attendance Example");
  await expect(attendance).toHaveValue("unknown");
  await attendance.selectOption("attended");
  await expect(attendance).toHaveValue("attended");
  expect(status).toBe("attended");
});
