import raw from "./data/examples.v1.json";
import schema from "./data/schema.v1.json";
import type { Examples, Page, RunSummary, StudentDetail } from "./types";

export const examples = raw as unknown as Examples;
export class ApiError extends Error {
  constructor(
    message: string,
    public status = 0,
  ) {
    super(message);
  }
}
type Params = Record<string, string | number | undefined>;

export async function request<T>(
  path: string,
  options?: RequestInit,
): Promise<T> {
  const controller = new AbortController();
  const timeout = window.setTimeout(
    () => controller.abort(),
    options?.method ? 120_000 : 20_000,
  );
  try {
    const response = await fetch(path, {
      ...options,
      signal: controller.signal,
      credentials: "same-origin",
    });
    const value = await response.json().catch(() => ({}));
    if (!response.ok)
      throw new ApiError(
        value.error?.message ||
          value.detail ||
          `Request failed (${response.status}).`,
        response.status,
      );
    return value as T;
  } catch (error) {
    if (error instanceof ApiError) throw error;
    throw new ApiError(
      "The connection was interrupted. Check the review queue before repeating an action.",
    );
  } finally {
    clearTimeout(timeout);
  }
}

export function post<T>(path: string, csrf: string, body?: unknown) {
  return request<T>(path, {
    method: "POST",
    headers: { "Content-Type": "application/json", "X-CSRF-Token": csrf },
    ...(body === undefined ? {} : { body: JSON.stringify(body) }),
  });
}

function page<T>(items: T[], params: Params): Page<T> {
  const limit = Number(params.limit || 20),
    offset = Number(params.offset || 0);
  return {
    items: items.slice(offset, offset + limit),
    total: items.length,
    limit,
    offset,
  };
}
const notFound = () => {
  throw new ApiError("This record was not found.", 404);
};

function demo(path: string, params: Params): unknown {
  const parts = path.replace(/^\//, "").split("/");
  const [resource, id, child] = parts;
  if (resource === "database") {
    if (!id)
      return schema.tables.map((table) => ({
        name: table.name,
        columns: ["id", ...table.fields, "created_at", "updated_at"],
        total: (examples[table.name as keyof Examples] as { id: string }[])
          .length,
      }));
    if (!schema.tables.some((table) => table.name === id)) return notFound();
    const records = examples[id as keyof Examples] as {
      id: string;
      created_at: string;
    }[];
    return page(
      [...records].sort(
        (a, b) =>
          a.created_at.localeCompare(b.created_at) || a.id.localeCompare(b.id),
      ),
      params,
    );
  }
  const key =
    resource === "sessions"
      ? "class_sessions"
      : resource === "agent-runs"
        ? "agent_runs"
        : resource;
  const table = examples[key as keyof Examples];
  if (!Array.isArray(table)) return notFound();
  if (id) {
    const item = table.find((row) => row.id === id);
    if (!item) return notFound();
    if (resource === "students") {
      const student = examples.students.find((row) => row.id === id)!;
      const history = examples.enrolments.filter(
        (row) => row.student_id === id,
      );
      const date = String(params.on_date || examples.as_of);
      return {
        ...student,
        as_of: date,
        enrolment_history: history,
        current_enrolments: history.filter((row) => active(row.id, date)),
      } satisfies StudentDetail;
    }
    if (resource === "conversations" && child === "messages") {
      return page(
        examples.messages
          .filter((row) => row.conversation_id === id)
          .sort(
            (a, b) =>
              a.occurred_at.localeCompare(b.occurred_at) ||
              a.created_at.localeCompare(b.created_at) ||
              a.id.localeCompare(b.id),
          ),
        params,
      );
    }
    if (resource === "sessions" && child === "students") {
      const session = examples.class_sessions.find((row) => row.id === id)!;
      const ids = session.students;
      return page(
        examples.students.filter((row) => ids.includes(row.id)),
        params,
      );
    }
    return item;
  }
  if (resource === "agent-runs") {
    let runs: RunSummary[] = examples.agent_runs.map((run) => {
      const conversation = examples.conversations.find(
        (row) => row.id === run.conversation_id,
      )!;
      const student = examples.students.find(
        (row) => row.id === conversation.student_id,
      )!;
      return {
        ...run,
        student_id: student.id,
        student_name: student.display_name,
        student_email: student.email,
        request_summary: String(run.interpretation.request_summary || ""),
        routing: run.interpretation.routing as
          Record<string, unknown> | undefined,
        flow: run.interpretation.flow as string | undefined,
      };
    });
    if (params.status)
      runs = runs.filter((run) => run.status === params.status);
    if (params.student_id)
      runs = runs.filter((run) => run.student_id === params.student_id);
    if (params.conversation_id)
      runs = runs.filter(
        (run) => run.conversation_id === params.conversation_id,
      );
    if (params.q) {
      const q = String(params.q).toLowerCase();
      runs = runs.filter((run) =>
        `${run.student_name} ${run.student_email}`.toLowerCase().includes(q),
      );
    }
    return page(
      runs.sort(
        (a, b) =>
          b.created_at.localeCompare(a.created_at) || b.id.localeCompare(a.id),
      ),
      params,
    );
  }
  let items = [...table] as unknown as Record<string, unknown>[];
  for (const field of [
    "student_id",
    "agent_run_id",
    "session_id",
    "class_id",
    "term_id",
    "location_id",
    "level",
    "status",
  ]) {
    if (params[field])
      items = items.filter((row) => row[field] === params[field]);
  }
  if (resource === "students" && params.q) {
    const q = String(params.q).toLowerCase();
    items = items.filter((row) =>
      `${row.display_name} ${row.email}`.toLowerCase().includes(q),
    );
  }
  return page(items, params);
}

function active(id: string, date: string) {
  const row = examples.enrolments.find((item) => item.id === id)!;
  const cls = examples.classes.find((item) => item.id === row.class_id)!;
  const term = examples.terms.find((item) => item.id === cls.term_id)!;
  return (
    row.status !== "cancelled" &&
    row.starts_on <= date &&
    (!row.ends_on || date <= row.ends_on) &&
    term.starts_on <= date &&
    date <= term.ends_on
  );
}

export function get<T>(
  workspace: boolean,
  path: string,
  params: Params = {},
): Promise<T> {
  if (!workspace) return Promise.resolve().then(() => demo(path, params) as T);
  const query = new URLSearchParams();
  for (const [key, value] of Object.entries(params))
    if (value !== undefined && value !== "") query.set(key, String(value));
  return request<T>(`/api/v1${path}?${query}`);
}

export async function all<T>(
  workspace: boolean,
  path: string,
  params: Params = {},
): Promise<T[]> {
  const items: T[] = [];
  let total = Infinity;
  while (items.length < total) {
    const result = await get<Page<T>>(workspace, path, {
      ...params,
      limit: 100,
      offset: items.length,
    });
    items.push(...result.items);
    total = result.total;
    if (!result.items.length) break;
  }
  return items;
}
