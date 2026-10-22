import { expect, test } from "@playwright/test";

test.describe("with a keyboard and nothing else", () => {
  test("sign in with a demo family, reach the Assistant, ask a question, and read the answer", async ({ page }) => {
    await page.goto("/");
    // Tab until the demo button for the liquidity-gap family has focus, then press Enter.
    for (let i = 0; i < 30; i++) {
      await page.keyboard.press("Tab");
      const name = await page.evaluate(() => document.activeElement?.textContent ?? "");
      if (/liquidity-gap example/.test(name)) break;
    }
    await expect(page.getByRole("button", { name: /liquidity-gap example/ })).toBeFocused();
    await page.keyboard.press("Enter");
    await expect(page.getByRole("navigation", { name: "Main" })).toBeVisible();

    // The first Tab of a new page reaches the skip link, which jumps past the menu.
    await page.goto("/");
    await expect(page.getByRole("navigation", { name: "Main" })).toBeVisible();
    await page.keyboard.press("Tab");
    await expect(page.getByRole("link", { name: "Skip to main content" })).toBeFocused();
    await page.keyboard.press("Enter");
    await expect(page.locator("main#main")).toBeFocused();

    // Walk to the Assistant link in the menu and follow it.
    const assistant = page.getByRole("navigation", { name: "Main" }).getByRole("link", { name: "Assistant", exact: true });
    await assistant.focus();
    await page.keyboard.press("Enter");
    await expect(page.getByRole("heading", { level: 1, name: "Assistant" })).toBeVisible();

    await page.getByRole("textbox", { name: "Your question" }).focus();
    await page.keyboard.type("what is cvar");
    await page.keyboard.press("Enter");
    const answer = page.getByRole("article", { name: "What is CVaR?" });
    await expect(answer).toBeVisible();
    await expect(answer.locator(".answer-lead")).toContainText(/average loss in the worst/);
  });

  test("a side panel traps focus, closes with Escape, and hands focus back", async ({ page }) => {
    await page.goto("/");
    await page.getByRole("button", { name: /liquidity-gap example/ }).click();
    const warnings = page.getByRole("region", { name: "Needs your attention" });
    const why = warnings.getByRole("button", { name: /^Why\? Liquidity shortfall/ });
    await why.focus();
    await page.keyboard.press("Enter");
    const panel = page.getByRole("dialog");
    await expect(panel).toBeVisible();
    for (let i = 0; i < 40; i++) {
      await page.keyboard.press("Tab");
      const inside = await page.evaluate(() => !!document.activeElement?.closest("[role=dialog]"));
      expect(inside, "focus left the open panel").toBe(true);
    }
    await page.keyboard.press("Escape");
    await expect(panel).toHaveCount(0);
    await expect(why).toBeFocused();
  });

  test("every control in the page can be seen when it has focus", async ({ page }) => {
    await page.goto("/");
    await page.getByRole("button", { name: /liquidity-gap example/ }).click();
    await page.getByRole("navigation", { name: "Main" }).getByRole("link", { name: "Assistant", exact: true }).click();
    await page.getByRole("textbox", { name: "Your question" }).focus();
    for (let i = 0; i < 12; i++) {  // tab like a person: the focus ring only shows for keyboard focus
      await page.keyboard.press("Tab");
      if (await page.evaluate(() => document.activeElement?.classList.contains("chip"))) break;
    }
    const outline = await page.evaluate(() => {
      const el = document.activeElement as Element;
      const s = getComputedStyle(el);
      return { isChip: el.classList.contains("chip"), style: s.outlineStyle, width: parseFloat(s.outlineWidth), shadow: s.boxShadow };
    });
    expect(outline.isChip).toBe(true);
    expect((outline.style !== "none" && outline.width >= 2) || outline.shadow !== "none").toBe(true);
  });
});
