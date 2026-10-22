import { expect, test } from "@playwright/test";
import { demoFamily } from "./helpers";

// The built app, served with the production security headers (web/security-headers.ts): every page must work with no policy violation.
test.use({ baseURL: "http://127.0.0.1:5181" });

const PAGES = ["/", "/plan", "/recommendation", "/risk", "/scenarios", "/holdings", "/profile", "/assistant"];

test.describe("under the production Content-Security-Policy", () => {
  test("the page is served with the policy and the other security headers", async ({ request }) => {
    const r = await request.get("/");
    const h = r.headers();
    expect(h["content-security-policy"]).toContain("default-src 'self'");
    expect(h["content-security-policy"]).toContain("script-src 'self'");
    expect(h["content-security-policy"]).toContain("frame-ancestors 'none'");
    expect(h["content-security-policy"]).toContain("object-src 'none'");
    expect(h["x-content-type-options"]).toBe("nosniff");
    expect(h["x-frame-options"]).toBe("DENY");
    expect(h["referrer-policy"]).toBe("no-referrer");
  });

  test("every page, chart and panel works without a single policy violation", async ({ page }) => {
    const violations: string[] = [];
    await page.addInitScript(() => {
      (window as unknown as { __csp: string[] }).__csp = [];
      document.addEventListener("securitypolicyviolation", (e) => (window as unknown as { __csp: string[] }).__csp.push(`${e.violatedDirective} ${e.blockedURI}`));
    });
    page.on("console", (m) => {
      if (/content security policy|refused to/i.test(m.text())) violations.push(m.text());
    });
    await demoFamily(page);
    for (const path of PAGES) {
      await page.goto(path);
      await expect(page.getByRole("heading", { level: 1 })).toBeVisible();
      await page.waitForLoadState("networkidle");
      violations.push(...(await page.evaluate(() => (window as unknown as { __csp: string[] }).__csp)));
    }
    // charts as pictures, the explanation panel, the assistant: the interactive parts too
    await page.goto("/");
    await page.getByRole("button", { name: /^Why\? Liquidity shortfall/ }).click();
    await expect(page.getByRole("dialog")).toBeVisible();
    await page.keyboard.press("Escape");
    await page.goto("/assistant");
    await page.getByRole("button", { name: "Is my liquidity enough?" }).click();
    await expect(page.getByRole("article")).toBeVisible();
    violations.push(...(await page.evaluate(() => (window as unknown as { __csp: string[] }).__csp)));
    expect(violations, violations.join("\n")).toEqual([]);
  });

  test("an injected inline script is blocked by the policy", async ({ page }) => {
    await demoFamily(page);
    await page.evaluate(() => {
      const s = document.createElement("script");
      s.textContent = "window.__injected = 1";
      document.body.appendChild(s);
    });
    expect(await page.evaluate(() => (window as unknown as { __injected?: number }).__injected)).toBeUndefined();
  });
});
