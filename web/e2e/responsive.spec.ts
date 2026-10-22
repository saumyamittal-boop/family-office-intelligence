import { expect, test } from "@playwright/test";
import { demoFamily } from "./helpers";

const PAGES = ["/", "/recommendation", "/risk", "/scenarios", "/holdings", "/profile", "/assistant", "/plan"];

test.describe("on a phone", () => {
  test.use({ viewport: { width: 375, height: 812 }, hasTouch: true, isMobile: true });

  test("no page needs sideways scrolling, and the menu opens as a drawer", async ({ page }) => {
    await demoFamily(page);
    for (const path of PAGES) {
      await page.goto(path);
      await expect(page.getByRole("heading", { level: 1 })).toBeVisible();
      await page.waitForLoadState("networkidle");
      const overflow = await page.evaluate(() => document.documentElement.scrollWidth - window.innerWidth);
      expect(overflow, `${path} is wider than the screen by ${overflow}px`).toBeLessThanOrEqual(0);
    }
    await page.getByRole("button", { name: "Open navigation" }).click();
    await expect(page.getByRole("dialog").getByRole("link", { name: "Assistant" })).toBeVisible();
  });

  test("every button and link is big enough to tap", async ({ page }) => {
    await demoFamily(page);
    await page.goto("/assistant");
    await expect(page.getByRole("button", { name: "Is my liquidity enough?" })).toBeVisible();
    const small = await page.evaluate(() =>
      [...document.querySelectorAll<HTMLElement>("main button, main a, main select, main input")]
        .filter((el) => { const r = el.getBoundingClientRect(); return r.width > 0 && r.height > 0 && (r.height < 24 || r.width < 24); })
        .map((el) => `${el.tagName} ${el.textContent?.trim().slice(0, 20)}`),
    );
    expect(small).toEqual([]); // WCAG 2.2 AA minimum target size
  });
});

test.describe("themes", () => {
  test("the dark theme is chosen from the menu, applies at once and is remembered", async ({ page }) => {
    await demoFamily(page);
    await page.getByRole("button", { name: /Theme/ }).click();
    await page.getByRole("menuitemradio", { name: "Dark" }).click();
    await expect(page.locator("html")).toHaveAttribute("data-theme", "dark");
    const background = await page.evaluate(() => getComputedStyle(document.body).backgroundColor);
    expect(background).not.toBe("rgb(255, 255, 255)");
    await page.reload();
    await expect(page.locator("html")).toHaveAttribute("data-theme", "dark");
  });
});
