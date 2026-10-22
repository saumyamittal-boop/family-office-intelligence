import { expect, test } from "@playwright/test";
import type { Page } from "@playwright/test";
import { chooseFile, csv, demoFamily, goTo, me } from "./helpers";

async function noScriptRan(page: Page) {
  expect(await page.evaluate(() => (window as unknown as { __pwned?: number }).__pwned)).toBeUndefined();
}

test.describe("a browser cannot be turned against the person using it", () => {
  test("a state-changing request without the CSRF token, or from another website, is refused", async ({ page }) => {
    await demoFamily(page);
    const token = (await me(page)).csrf_token;
    const body = { modules: ["allocation_actions", "liquidity_commitments", "risk_exposure", "stress_scenarios"] };

    expect((await page.request.put("/api/dashboard", { data: body })).status()).toBe(403); // no token
    expect((await page.request.put("/api/dashboard", { data: body, headers: { "X-CSRF-Token": "0".repeat(64) } })).status()).toBe(403); // a guess
    expect((await page.request.put("/api/dashboard", { data: body, headers: { "X-CSRF-Token": token, Origin: "https://evil.example" } })).status()).toBe(403);
    expect((await page.request.put("/api/dashboard", { data: body, headers: { "X-CSRF-Token": token, Origin: "null" } })).status()).toBe(403);
    expect((await page.request.put("/api/dashboard", { data: body, headers: { "X-CSRF-Token": token } })).status()).toBe(200); // the real page's own request
  });

  test("a form post from another site cannot carry the session (the cookie is SameSite and the body must be JSON)", async ({ page }) => {
    await demoFamily(page);
    const r = await page.request.post("/api/profiles", { form: { name: "x" } });
    expect(r.status()).toBe(415);
  });

  test("markup in an imported holding's name is shown as text and never runs", async ({ page }) => {
    await demoFamily(page);
    await goTo(page, "Holdings");
    const evil = '<img src=x onerror="window.__pwned=1"> <script>window.__pwned=2</script>';
    await chooseFile(page, "evil.csv", csv([[`"${evil.replace(/"/g, '""')}"`, "Debt", "Demat 1", "40"], ["Fund B", "Gold", "Demat 1", "10"]]));
    await expect(page.getByText("Rows read")).toBeVisible();
    await page.getByRole("button", { name: /^Import 2 holdings/ }).click();
    await expect(page.getByText("Imported.")).toBeVisible();
    await expect(page.getByText("<img src=x", { exact: false }).first()).toBeVisible(); // visible as literal text
    await noScriptRan(page);
    expect(await page.locator("img[src='x']").count()).toBe(0);

    // and the assistant repeats it only as quoted data
    await goTo(page, "Assistant");
    await page.getByRole("button", { name: "What have I imported?" }).click();
    await expect(page.getByRole("article")).toBeVisible();
    await noScriptRan(page);
    expect(await page.locator("article img, article script").count()).toBe(0);
  });

  test("markup typed into the assistant is never echoed back as markup", async ({ page }) => {
    await demoFamily(page);
    await goTo(page, "Assistant");
    await page.getByRole("textbox", { name: "Your question" }).fill('<img src=x onerror="window.__pwned=1"> is my liquidity enough?');
    await page.getByRole("button", { name: "Ask", exact: true }).click();
    await expect(page.getByRole("article").or(page.getByText(/Which did you mean|No match|Outside what I do/))).toBeVisible();
    await noScriptRan(page);
    expect(await page.locator("main img[src='x']").count()).toBe(0);
    expect(page.url()).not.toContain("liquidity"); // the question is never put in the address
  });

  test("a spreadsheet with formulas or hostile cells is refused in plain words and cannot be imported", async ({ page }) => {
    await demoFamily(page);
    await goTo(page, "Holdings");
    await chooseFile(page, "formula.csv", csv([["=HYPERLINK(\"http://evil.example\")", "Debt", "A", "10"], ["Bonds", "Debt", "A", "-5"], ["OK fund", "Debt", "A", "abc"]]));
    await expect(page.getByText(/problems? to fix/)).toBeVisible();
    await expect(page.getByRole("button", { name: /^Import 0 holdings|Nothing to import yet/ })).toBeDisabled();
    await expect(page.getByText("Imported.")).toHaveCount(0);
  });

  test("a file that is far too large or the wrong kind is turned away before anything is sent", async ({ page }) => {
    await demoFamily(page);
    await goTo(page, "Holdings");
    const requests: string[] = [];
    page.on("request", (r) => requests.push(`${r.method()} ${r.url()}`));
    await page.getByLabel("Holdings file").setInputFiles({ name: "huge.csv", mimeType: "text/csv", buffer: Buffer.alloc(200 * 1024, "a") });
    await expect(page.getByText(/larger than 150 KB/)).toBeVisible();
    await page.getByLabel("Holdings file").setInputFiles({ name: "report.pdf", mimeType: "application/pdf", buffer: Buffer.from("%PDF-1.4") });
    await expect(page.getByText("Choose a .csv or .xlsx file.")).toBeVisible();
    expect(requests.filter((r) => r.includes("/holdings/preview"))).toHaveLength(0);
  });

  test("the pages and the API say never to cache or frame them", async ({ page }) => {
    await demoFamily(page);
    const api = await page.request.get("/api/profiles");
    expect(api.headers()["cache-control"]).toBe("no-store");
    expect(api.headers()["x-content-type-options"]).toBe("nosniff");
    expect(api.headers()["x-frame-options"]).toBe("DENY");
    expect(api.headers()["content-security-policy"]).toContain("frame-ancestors 'none'");
    expect(api.headers()["server"] ?? "").not.toMatch(/\d/); // no version numbers volunteered
  });
});
