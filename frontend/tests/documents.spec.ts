import { test, expect, type Page } from "@playwright/test";

type Doc = {
  id: string;
  title: string;
  filename: string;
  content: string;
  current_revision: number;
  byte_size: number;
  sha256: string;
  hash_origin: string;
  ingestion_status: string;
  effective_from: string | null;
  effective_to: string | null;
  updated_at: string;
};
async function documentsApi(page: Page, failFirst = false) {
  const state = {
    docs: [] as Doc[],
    history: new Map<string, Doc[]>(),
    fail: failFirst,
    conflict: false,
  };
  await page.route("**/auth/me", (route) =>
    route.fulfill({
      json: {
        authenticated: true,
        user: { email: "owner@example.test" },
        csrf_token: "test-csrf",
      },
    }),
  );
  await page.route("**/api/v1/documents**", async (route) => {
    const req = route.request(),
      url = new URL(req.url());
    const parts = url.pathname.split("/").slice(4),
      id = parts[0];
    const found = state.docs.find((item) => item.id === id),
      method = req.method();
    if (method === "GET") {
      if (!id) return route.fulfill({ json: state.docs });
      if (!found) return route.fulfill({ status: 404, json: {} });
      if (parts[1] === "metadata")
        return route.fulfill({
          json: { ...found, content: undefined, duplicates: [] },
        });
      if (parts[1] === "revisions") {
        const history = state.history.get(id)!;
        if (parts[3] === "preview") {
          const snapshot = history.find(
            (item) => item.current_revision === Number(parts[2]),
          )!;
          const offset = Number(url.searchParams.get("offset") || 0),
            content = snapshot.content.slice(offset, offset + 20_000);
          return route.fulfill({
            json: {
              revision: snapshot.current_revision,
              content,
              offset,
              next_offset:
                offset + content.length < snapshot.content.length
                  ? offset + content.length
                  : null,
              total_characters: snapshot.content.length,
            },
          });
        }
        return route.fulfill({
          json: history.map((item) => ({
            ...item,
            content: undefined,
            revision: item.current_revision,
          })),
        });
      }
      return route.fulfill({ json: found });
    }
    expect(req.headers()["x-csrf-token"]).toBe("test-csrf");
    if (method === "DELETE") {
      state.docs = state.docs.filter((item) => item.id !== id);
      return route.fulfill({ json: { deleted: true } });
    }
    if (state.fail || state.conflict) {
      state.fail = false;
      return route.fulfill({
        status: state.conflict ? 409 : 503,
        json: {
          error: {
            message: state.conflict
              ? "The document changed. Your edits are retained."
              : "Save failed",
          },
        },
      });
    }
    let body: Record<string, string | number | null>;
    if (req.headers()["content-type"].startsWith("multipart/form-data")) {
      const boundary = req.headers()["content-type"].split("boundary=")[1];
      body = {};
      for (const part of req
        .postDataBuffer()!
        .toString("utf8")
        .split("--" + boundary)) {
        const match = /name="([^"]+)"(?:; filename="([^"]+)")?/.exec(part);
        if (!match) continue;
        const value = part
          .slice(part.indexOf("\r\n\r\n") + 4)
          .replace(/\r\n$/, "");
        if (match[2]) {
          body.filename = match[2];
          body.content = value;
        } else body[match[1]] = value;
      }
    } else body = req.postDataJSON();
    const doc: Doc = {
      id: found?.id || `doc-${state.docs.length + 1}`,
      title: String(body.title),
      filename: String(body.filename || found?.filename),
      content: String(body.content ?? found?.content ?? ""),
      current_revision: (found?.current_revision || 0) + 1,
      byte_size: Buffer.byteLength(
        String(body.content ?? found?.content ?? ""),
      ),
      sha256: "0".repeat(64),
      hash_origin: "upload_bytes",
      ingestion_status: "ready",
      effective_from: body.effective_from ? String(body.effective_from) : null,
      effective_to: body.effective_to ? String(body.effective_to) : null,
      updated_at: new Date().toISOString(),
    };
    if (found)
      expect(Number(body.expected_revision)).toBe(found.current_revision);
    state.docs = [doc, ...state.docs.filter((item) => item.id !== doc.id)];
    state.history.set(doc.id, [doc, ...(state.history.get(doc.id) || [])]);
    return route.fulfill({
      json: { ...doc, content: undefined, duplicates: [] },
    });
  });
  return state;
}

test("owner manages documents and retains a draft on errors", async ({
  page,
}) => {
  const state = await documentsApi(page, true);
  await page.goto("/workspace/knowledge/documents");
  await expect(page.getByText("No documents yet.")).toBeVisible();
  await page.getByLabel(/Upload a document/).setInputFiles({
    name: "welcome.md",
    mimeType: "text/markdown",
    buffer: Buffer.from("Hello studio"),
  });
  await page.getByLabel("Title", { exact: true }).fill("Welcome");
  await page.getByLabel("Effective from").fill("2027-01-01");
  await page.getByRole("button", { name: "Save document" }).click();
  await expect(page.getByRole("alert")).toContainText("Save failed");
  await expect(page.getByLabel("Document text")).toHaveValue("Hello studio");
  await page.getByRole("button", { name: "Save document" }).click();
  await expect(page.getByRole("status")).toContainText("Document saved");
  expect(state.docs[0].effective_from).toBe("2027-01-01");
  await page.reload();
  await page.getByRole("button", { name: "Welcome", exact: true }).click();
  await expect(page.getByLabel("Document text")).toHaveValue("Hello studio");
  await page.getByLabel("Document text").fill("Edited text");
  await page.getByLabel("Replace file").setInputFiles({
    name: "bad.pdf",
    mimeType: "application/pdf",
    buffer: Buffer.from("bad"),
  });
  await expect(page.getByRole("alert")).toContainText(
    "Choose a .txt or .md file",
  );
  await expect(page.getByLabel("Document text")).toHaveValue("Edited text");
  await page.getByLabel("Replace file").setInputFiles({
    name: "new.txt",
    mimeType: "text/plain",
    buffer: Buffer.from("Replacement"),
  });
  await page.getByRole("button", { name: "Save document" }).click();
  await expect(page.getByLabel("Document text")).toHaveValue("Replacement");
  expect(state.docs[0].filename).toBe("new.txt");
  expect(state.docs[0].current_revision).toBe(2);
  await page
    .getByRole("combobox", { name: "Revision", exact: true })
    .selectOption("1");
  await expect(page.locator(".document-preview")).toHaveText("Hello studio");
  page.once("dialog", (dialog) => dialog.dismiss());
  await page.getByRole("button", { name: "Delete document" }).click();
  await expect(page.getByLabel("Document text")).toBeVisible();
  page.once("dialog", (dialog) => dialog.accept());
  await page.getByRole("button", { name: "Delete document" }).click();
  await expect(page.getByText("No documents yet.")).toBeVisible();
});

test("large files use bounded previews and preserve edits on conflicts", async ({
  page,
}) => {
  const state = await documentsApi(page);
  await page.goto("/workspace/knowledge/documents");
  const text = "A".repeat(20_000) + "Second page\n" + "Z".repeat(1_000_000);
  await page.getByLabel(/Upload a document/).setInputFiles({
    name: "large.txt",
    mimeType: "text/plain",
    buffer: Buffer.from(text),
  });
  await expect(page.getByLabel("Document text")).toHaveCount(0);
  await page.getByRole("button", { name: "Save document" }).click();
  await expect(page.locator(".document-preview")).toHaveText(
    "A".repeat(20_000),
  );
  await page.getByRole("button", { name: "Next page" }).click();
  await expect(page.locator(".document-preview")).toContainText("Second page");
  await page.getByRole("button", { name: "Previous page" }).click();
  await expect(page.locator(".document-preview")).toHaveText(
    "A".repeat(20_000),
  );
  const fullReads: string[] = [];
  page.on("request", (request) => {
    if (new URL(request.url()).pathname === "/api/v1/documents/doc-1")
      fullReads.push(request.url());
  });
  await page.reload();
  await page.getByRole("button", { name: "large", exact: true }).click();
  await expect(page.locator(".document-preview")).toHaveText(
    "A".repeat(20_000),
  );
  expect(fullReads).toEqual([]);
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= window.innerWidth,
    ),
  ).toBe(true);
  state.conflict = true;
  await page.getByLabel("Title", { exact: true }).fill("My local title");
  await page.getByRole("button", { name: "Save document" }).click();
  await expect(page.getByRole("alert")).toContainText(
    "Your edits are retained",
  );
  await expect(page.getByLabel("Title", { exact: true })).toHaveValue(
    "My local title",
  );
  await expect(
    page.getByText("Unsaved changes", { exact: true }),
  ).toBeVisible();
});

test("preview renders markup as text and inline edits create revisions", async ({
  page,
}) => {
  const state = await documentsApi(page);
  await page.goto("/workspace/knowledge/documents");
  const text =
    '<script>window.documentInjected = true</script>\n<img src=x onerror="alert(1)">';
  await page.getByLabel(/Upload a document/).setInputFiles({
    name: "markup.md",
    mimeType: "text/markdown",
    buffer: Buffer.from(text),
  });
  await page.getByRole("button", { name: "Save document" }).click();
  await expect(page.locator(".document-preview")).toHaveText(text);
  expect(await page.evaluate(() => "documentInjected" in window)).toBe(false);
  await page.getByLabel("Document text").fill("Safe edited content");
  await page.getByRole("button", { name: "Save document" }).click();
  await expect(page.locator(".document-preview")).toHaveText(
    "Safe edited content",
  );
  expect(state.docs[0].current_revision).toBe(2);
});

test("demo documents are illustrative and read only", async ({ page }) => {
  const calls: string[] = [];
  page.on("request", (request) => {
    if (/\/(api|auth)\//.test(request.url())) calls.push(request.url());
  });
  await page.goto("/demo/knowledge/documents");
  await page.getByRole("button", { name: "Studio welcome" }).click();
  await expect(page.getByLabel("Document text")).toBeDisabled();
  await expect(page.getByRole("button", { name: "Save document" })).toHaveCount(
    0,
  );
  expect(calls).toEqual([]);
});

test("cancelled conflict reload retains replacement, accepted reload uses saved revision", async ({
  page,
}) => {
  const state = await documentsApi(page);
  await page.goto("/workspace/knowledge/documents");
  await page.getByLabel(/Upload a document/).setInputFiles({
    name: "handbook.md",
    mimeType: "text/markdown",
    buffer: Buffer.from("Original text"),
  });
  await page.getByRole("button", { name: "Save document" }).click();
  await expect(page.locator(".document-preview")).toHaveText("Original text");
  const old = state.docs[0];
  const latest = { ...old, current_revision: 2, content: "Changed elsewhere" };
  state.docs = [latest];
  state.history.set(old.id, [latest, old]);
  state.conflict = true;
  await page.getByLabel("Replace file").setInputFiles({
    name: "local.txt",
    mimeType: "text/plain",
    buffer: Buffer.from("My replacement"),
  });
  await page.getByRole("button", { name: "Save document" }).click();
  await expect(page.getByRole("alert")).toContainText(
    "Your edits are retained",
  );
  page.once("dialog", (dialog) => dialog.dismiss());
  await page.getByRole("button", { name: "Reload current version" }).click();
  await expect(page.getByLabel("Document text")).toHaveValue("My replacement");
  await expect(
    page.getByText("File: local.txt", { exact: false }),
  ).toBeVisible();
  page.once("dialog", (dialog) => dialog.accept());
  await page.getByRole("button", { name: "Reload current version" }).click();
  await expect(page.getByLabel("Document text")).toHaveValue(
    "Changed elsewhere",
  );
  await expect(
    page.getByRole("button", { name: "Save document" }),
  ).toBeDisabled();
  await expect(page.getByText("Unsaved changes", { exact: true })).toHaveCount(
    0,
  );
});

test("revision mismatch while loading does not overwrite local replacement text", async ({
  page,
}) => {
  const state = await documentsApi(page);
  await page.goto("/workspace/knowledge/documents");
  await page.getByLabel(/Upload a document/).setInputFiles({
    name: "handbook.md",
    mimeType: "text/markdown",
    buffer: Buffer.from("Original text"),
  });
  await page.getByRole("button", { name: "Save document" }).click();
  await expect(page.locator(".document-preview")).toHaveText("Original text");
  const old = state.docs[0];
  state.docs = [{ ...old, current_revision: 2, content: "Changed elsewhere" }];
  await page.route(`**/api/v1/documents/${old.id}/metadata`, (route) =>
    route.fulfill({ json: { ...old, content: undefined, duplicates: [] } }),
  );
  await page.getByLabel("Replace file").setInputFiles({
    name: "local.txt",
    mimeType: "text/plain",
    buffer: Buffer.from("Keep this local text"),
  });
  page.once("dialog", (dialog) => dialog.accept());
  await page.getByRole("button", { name: "handbook", exact: true }).click();
  await expect(page.getByRole("alert")).toContainText("changed while loading");
  await expect(page.getByLabel("Document text")).toHaveValue(
    "Keep this local text",
  );
  await expect(
    page.getByText("Unsaved changes", { exact: true }),
  ).toBeVisible();
});
