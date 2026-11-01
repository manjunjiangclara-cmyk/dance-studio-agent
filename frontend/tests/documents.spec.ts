import { test, expect } from "@playwright/test";

test("owner manages documents and retains a draft on errors", async ({
  page,
}) => {
  let docs: {
    id: string;
    title: string;
    filename: string;
    content: string;
    updated_at: string;
  }[] = [];
  let fail = true;
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
    const method = route.request().method();
    const id = route.request().url().split("/").pop();
    if (method === "GET")
      return route.fulfill({
        json: id === "documents" ? docs : docs.find((doc) => doc.id === id),
      });
    expect(route.request().headers()["x-csrf-token"]).toBe("test-csrf");
    if (method === "DELETE") {
      docs = docs.filter((doc) => doc.id !== id);
      return route.fulfill({ json: { deleted: true } });
    }
    if (fail) {
      fail = false;
      return route.fulfill({
        status: 503,
        json: { error: { message: "Save failed" } },
      });
    }
    const body = route.request().postDataJSON();
    const doc = {
      id: method === "POST" ? "one" : id!,
      title: body.title,
      filename: body.filename,
      content: Buffer.from(body.content_base64, "base64").toString("utf8"),
      updated_at: new Date().toISOString(),
    };
    docs = [doc];
    return route.fulfill({ json: doc });
  });
  await page.goto("/workspace/documents");
  await expect(page.getByText("No documents yet.")).toBeVisible();
  await page.getByLabel(/Upload a document/).setInputFiles({
    name: "welcome.md",
    mimeType: "text/markdown",
    buffer: Buffer.from("Hello studio"),
  });
  await page.getByLabel("Title").fill("Welcome");
  await page.getByRole("button", { name: "Save document" }).click();
  await expect(page.getByRole("alert")).toContainText("Save failed");
  await expect(page.getByLabel("Document text")).toHaveValue("Hello studio");
  await page.getByRole("button", { name: "Save document" }).click();
  await expect(page.getByRole("status")).toContainText("Document saved");
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
  expect(docs[0].filename).toBe("new.txt");
  expect(docs[0].content).toBe("Replacement");
  page.once("dialog", (dialog) => dialog.dismiss());
  await page.getByRole("button", { name: "Delete document" }).click();
  await expect(page.getByLabel("Document text")).toBeVisible();
  page.once("dialog", (dialog) => dialog.accept());
  await page.getByRole("button", { name: "Delete document" }).click();
  await expect(page.getByText("No documents yet.")).toBeVisible();
});

test("demo documents are illustrative and read only", async ({ page }) => {
  const calls: string[] = [];
  page.on("request", (request) => {
    if (/\/(api|auth)\//.test(request.url())) calls.push(request.url());
  });
  await page.goto("/demo/documents");
  await page.getByRole("button", { name: "Studio welcome" }).click();
  await expect(page.getByLabel("Document text")).toBeDisabled();
  await expect(page.getByRole("button", { name: "Save document" })).toHaveCount(
    0,
  );
  expect(calls).toEqual([]);
});
