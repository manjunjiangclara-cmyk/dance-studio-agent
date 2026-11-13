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
    activation: "disabled" as "disabled" | "preparing" | "enabled" | "failed",
    activationError: null as string | null,
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
    if (parts[1] === "answer-activation") {
      if (method !== "GET")
        expect(req.headers()["x-csrf-token"]).toBe("test-csrf");
      if (method === "POST") {
        state.activation = "preparing";
        state.activationError = null;
      }
      if (method === "DELETE") state.activation = "disabled";
      return route.fulfill({
        json: { status: state.activation, error: state.activationError },
      });
    }
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
            content = Array.from(snapshot.content)
              .slice(offset, offset + 20_000)
              .join("");
          return route.fulfill({
            json: {
              revision: snapshot.current_revision,
              content,
              offset,
              next_offset:
                offset + Array.from(content).length <
                Array.from(snapshot.content).length
                  ? offset + Array.from(content).length
                  : null,
              total_characters: Array.from(snapshot.content).length,
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
  await expect(
    page.getByText("Document saved. Uploading does not enable it for answers."),
  ).toBeVisible();
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

test("citation link opens the exact saved revision at its character offset", async ({
  page,
}) => {
  const state = await documentsApi(page);
  const currentContentReads: string[] = [];
  page.on("request", (request) => {
    if (
      new URL(request.url()).pathname ===
      "/api/v1/documents/11111111-1111-4111-8111-111111111111"
    )
      currentContentReads.push(request.url());
  });
  const id = "11111111-1111-4111-8111-111111111111";
  const oldContent = "Intro 🩰\nWear comfortable clothes and bring water.";
  const currentContent = "The current revision has different advice.";
  const summary: Doc = {
    id,
    title: "Trial handbook",
    filename: "trial.md",
    content: currentContent,
    current_revision: 2,
    byte_size: Buffer.byteLength(currentContent),
    sha256: "0".repeat(64),
    hash_origin: "upload_bytes",
    ingestion_status: "ready",
    effective_from: null,
    effective_to: null,
    updated_at: "2027-01-02T00:00:00Z",
  };
  state.docs.push(summary);
  state.history.set(id, [
    summary,
    { ...summary, content: oldContent, current_revision: 1 },
  ]);
  await page.goto(
    `/workspace/knowledge/documents?document=${id}&revision=1&offset=8#revision-preview`,
  );

  await expect(
    page.getByRole("combobox", { name: "Revision", exact: true }),
  ).toHaveValue("1");
  await expect(page.getByLabel("Revision preview")).toContainText(
    "Characters 8–",
  );
  await expect(page.locator(".document-preview")).toHaveText(
    "Wear comfortable clothes and bring water.",
  );
  expect(currentContentReads).toEqual([]);
  await page.evaluate((url) => {
    window.history.pushState(null, "", url);
    window.dispatchEvent(new PopStateEvent("popstate"));
  }, `/workspace/knowledge/documents?document=${id}&revision=3&offset=8#revision-preview`);
  await expect(page.getByRole("alert")).toContainText(
    "The cited document revision is no longer available.",
  );
  await expect(page.getByLabel("Revision preview")).toHaveCount(0);
});

test("confirmed back navigation discards edits and opens the cited revision", async ({
  page,
}) => {
  const state = await documentsApi(page);
  const id = "11111111-1111-4111-8111-111111111111";
  const current: Doc = {
    id,
    title: "Trial handbook",
    filename: "trial.md",
    content: "Current advice",
    current_revision: 2,
    byte_size: 14,
    sha256: "0".repeat(64),
    hash_origin: "upload_bytes",
    ingestion_status: "ready",
    effective_from: null,
    effective_to: null,
    updated_at: "2027-01-02T00:00:00Z",
  };
  state.docs.push(current);
  state.history.set(id, [
    current,
    { ...current, current_revision: 1, content: "Cited advice" },
  ]);
  const citation = `/workspace/knowledge/documents?document=${id}&revision=1&offset=0`;
  await page.goto(citation);
  await expect(page.locator(".document-preview")).toHaveText("Cited advice");
  await page.getByRole("link", { name: "Documents", exact: true }).click();
  await page.getByRole("button", { name: "Trial handbook" }).click();
  await page.getByLabel("Document text").fill("Unsaved advice");

  await page.evaluate(() => window.history.back());
  await expect(
    page.getByRole("dialog", { name: "Leave without saving?" }),
  ).toBeVisible();
  await page.getByRole("button", { name: "Leave page" }).click();

  await expect(page).toHaveURL(citation);
  await expect(page.locator(".document-preview")).toHaveText("Cited advice");
  await expect(page.getByLabel("Document text")).toHaveCount(0);
  await expect(page.getByRole("alert")).toHaveCount(0);
});

test("delayed citation and revision requests cannot replace a newer source", async ({
  page,
}) => {
  const state = await documentsApi(page);
  const firstId = "11111111-1111-4111-8111-111111111111";
  const secondId = "22222222-2222-4222-8222-222222222222";
  for (const [id, title] of [
    [firstId, "First source"],
    [secondId, "Second source"],
  ]) {
    const doc: Doc = {
      id,
      title,
      filename: "source.md",
      content: title,
      current_revision: id === firstId ? 2 : 1,
      byte_size: title.length,
      sha256: "0".repeat(64),
      hash_origin: "upload_bytes",
      ingestion_status: "ready",
      effective_from: null,
      effective_to: null,
      updated_at: "2027-01-02T00:00:00Z",
    };
    state.docs.push(doc);
    state.history.set(
      id,
      id === firstId ? [doc, { ...doc, current_revision: 1 }] : [doc],
    );
  }
  let releaseFirst!: () => void;
  let firstStarted!: () => void;
  const held = new Promise<void>((resolve) => (releaseFirst = resolve));
  const started = new Promise<void>((resolve) => (firstStarted = resolve));
  await page.route(
    `**/api/v1/documents/${firstId}/revisions/1/preview?*`,
    async (route) => {
      firstStarted();
      await held;
      await route.fulfill({
        json: {
          revision: 1,
          content: "First source",
          offset: 0,
          next_offset: null,
          total_characters: 12,
        },
      });
    },
  );
  await page.goto(
    `/workspace/knowledge/documents?document=${firstId}&revision=1&offset=0`,
  );
  await started;
  await page.evaluate((url) => {
    window.history.pushState(null, "", url);
    window.dispatchEvent(new PopStateEvent("popstate"));
  }, `/workspace/knowledge/documents?document=${secondId}&revision=1&offset=0`);
  await expect(page.locator(".document-preview")).toHaveText("Second source");
  const oldResponse = page.waitForResponse((response) =>
    response.url().includes(`${firstId}/revisions/1/preview`),
  );
  releaseFirst();
  await oldResponse;
  await expect(page.locator(".document-preview")).toHaveText("Second source");
  await expect(page.getByLabel("Revision preview")).toContainText(
    "Second source",
  );

  await page.evaluate((url) => {
    window.history.pushState(null, "", url);
    window.dispatchEvent(new PopStateEvent("popstate"));
  }, `/workspace/knowledge/documents?document=${firstId}&revision=1&offset=0`);
  await expect(page.locator(".document-preview")).toHaveText("First source");

  let releaseRevision!: () => void;
  let revisionStarted!: () => void;
  const heldRevision = new Promise<void>(
    (resolve) => (releaseRevision = resolve),
  );
  const startedRevision = new Promise<void>(
    (resolve) => (revisionStarted = resolve),
  );
  await page.route(
    `**/api/v1/documents/${firstId}/revisions/2/preview?*`,
    async (route) => {
      revisionStarted();
      await heldRevision;
      await route.fulfill({
        json: {
          revision: 2,
          content: "First source revision 2",
          offset: 0,
          next_offset: null,
          total_characters: 23,
        },
      });
    },
  );
  await page
    .getByRole("combobox", { name: "Revision", exact: true })
    .selectOption("2");
  await startedRevision;
  await page.evaluate((url) => {
    window.history.pushState(null, "", url);
    window.dispatchEvent(new PopStateEvent("popstate"));
  }, `/workspace/knowledge/documents?document=${secondId}&revision=1&offset=0`);
  await expect(page.locator(".document-preview")).toHaveText("Second source");
  const staleRevision = page.waitForResponse((response) =>
    response.url().includes(`${firstId}/revisions/2/preview`),
  );
  releaseRevision();
  await staleRevision;
  await expect(page.locator(".document-preview")).toHaveText("Second source");
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

test("document activation reports progress, failure, retry and disabling", async ({
  page,
}) => {
  const state = await documentsApi(page);
  await page.goto("/workspace/knowledge/documents");
  await page.getByLabel(/Upload a document/).setInputFiles({
    name: "handbook.md",
    mimeType: "text/markdown",
    buffer: Buffer.from("Studio handbook"),
  });
  await page.getByRole("button", { name: "Save document" }).click();
  await page.getByRole("button", { name: "Enable for answers" }).click();
  await expect(page.getByText("Preparing document for answers…")).toBeVisible();
  await page.getByRole("button", { name: "Cancel preparation" }).click();
  await expect(page.getByText("Not enabled for answers.")).toBeVisible();
  await page.getByRole("button", { name: "Enable for answers" }).click();
  await expect(page.getByText("Preparing document for answers…")).toBeVisible();
  state.activation = "failed";
  state.activationError = "Check model configuration";
  await expect(
    page.getByText(/Preparation failed: Check model configuration/),
  ).toBeVisible({ timeout: 10000 });
  await page.getByRole("button", { name: "Retry preparation" }).click();
  await expect(page.getByText("Preparing document for answers…")).toBeVisible();
  state.activation = "enabled";
  await expect(page.getByText("Enabled for answers.")).toBeVisible({
    timeout: 10000,
  });
  await page.getByRole("button", { name: "Disable for answers" }).click();
  await expect(page.getByText("Not enabled for answers.")).toBeVisible();
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= window.innerWidth,
    ),
  ).toBe(true);
});
