import { expect, test } from "@playwright/test";
import { chooseFile, csv, demoFamily, goTo, settled } from "./helpers";

test.describe("the main journeys, in a real browser against the real engine", () => {
  test("the overview shows the headline numbers and a warning explains itself", async ({ page }) => {
    await demoFamily(page);
    await expect(page.getByText("Liquidity cover").first()).toBeVisible();
    const warnings = page.getByRole("region", { name: "Needs your attention" });
    await expect(warnings).toBeVisible();
    await warnings.getByRole("button", { name: /^Why\? Liquidity shortfall/ }).click();
    const panel = page.getByRole("dialog");
    await expect(panel.getByText(/Over the next \d+ months your planned outflows come to/)).toBeVisible();
    await expect(panel.getByRole("link", { name: "Ask something else" })).toBeVisible();
    await page.keyboard.press("Escape");
    await expect(panel).toHaveCount(0);
    await expect(warnings.getByRole("button", { name: /^Why\? Liquidity shortfall/ })).toBeFocused(); // focus goes back to where the person was
  });

  test("the dashboard choice is remembered across a reload", async ({ page }) => {
    await demoFamily(page);
    await page.getByRole("button", { name: /Customise dashboard/ }).click();
    const panel = page.getByRole("dialog");
    await panel.getByLabel("Slot 4").selectOption({ label: "Holdings consolidation" });
    await panel.getByRole("button", { name: "Save dashboard" }).click();
    await expect(page.getByRole("heading", { level: 2, name: "Holdings consolidation" })).toBeVisible();
    await page.reload();
    await expect(page.getByRole("heading", { level: 2, name: "Holdings consolidation" })).toBeVisible();
  });

  test("a statement is read, checked, imported, consolidated, and only then offered to the profile", async ({ page }) => {
    await demoFamily(page);
    await goTo(page, "Holdings");
    const statement = csv([
      ["Nifty 50 index fund", "Large-cap equity", "Demat 1", "320"], ["Mid-cap fund", "Mid-cap equity", "Demat 1", "80"], ["Government bonds", "Debt", "Bank 2", "200"],
      ["Gold ETF", "Gold", "Demat 1", "60"], ["Savings", "Cash & liquid", "Bank 2", "50"], ["Farmland", "Real estate", "", "250"], ["Flexi-cap fund", "Equity", "Demat 1", "40"],
    ]);
    await chooseFile(page, "family-statement.csv", statement);
    await expect(page.getByText("Rows read")).toBeVisible();
    await expect(page.getByText(/1 problem to fix/)).toBeVisible(); // "Equity" is not a class the model knows: nothing is guessed
    await page.getByLabel("Class for Equity").selectOption("Large-cap equity");
    await expect(page.getByRole("button", { name: /^Import 7 holdings/ })).toBeEnabled();
    await page.getByRole("button", { name: /^Import 7 holdings/ }).click();
    await expect(page.getByText("Imported.")).toBeVisible();
    await expect(page.getByRole("table", { name: "Imported holdings by account" })).toBeVisible();

    // nothing in the profile changed yet
    await goTo(page, "Family profile");
    await expect(page.getByLabel(/Large-cap equity/).first()).toHaveValue(/55/);
    await goTo(page, "Holdings");
    await page.getByRole("button", { name: "Use these holdings in my profile" }).click();
    await expect(page.getByText("Your profile now uses these holdings.")).toBeVisible();
    await goTo(page, "Overview");
    await expect(page.getByRole("heading", { level: 1 })).toBeVisible();
  });

  test("the assistant answers, declines and offers a way forward", async ({ page }) => {
    await demoFamily(page);
    await goTo(page, "Assistant");
    const box = page.getByRole("textbox", { name: "Your question" });

    await box.fill("is my liquidity enough?");
    await page.getByRole("button", { name: "Ask", exact: true }).click();
    const answer = page.getByRole("article", { name: "Is my liquidity enough?" });
    await expect(answer).toBeVisible();
    await answer.getByText(/Show the evidence/).click();
    await expect(answer.getByRole("table", { name: /Figures used in this answer/ })).toBeVisible();
    await expect(answer.getByText("current.available_cover_cr").first()).toBeVisible();

    await box.fill("which fund should I buy?");
    await page.getByRole("button", { name: "Ask", exact: true }).click();
    await expect(page.getByText("Outside what I do.")).toBeVisible();
    await expect(page.getByRole("article")).toHaveCount(0);
    await page.getByRole("group", { name: "Questions you can ask" }).getByRole("button").first().click();
    await expect(page.getByRole("article")).toBeVisible();
  });

  test("the same family gives the same page every time, wherever you have been in between", async ({ page }) => {
    await demoFamily(page);
    await goTo(page, "Risk and liquidity");
    await expect(page.getByRole("heading", { level: 1, name: "Risk and liquidity" })).toBeVisible();
    const before = await settled(page);
    await goTo(page, "Scenarios");
    await expect(page.getByRole("heading", { level: 1, name: "Scenarios" })).toBeVisible();
    await goTo(page, "Risk and liquidity");
    await expect(page.getByRole("heading", { level: 1, name: "Risk and liquidity" })).toBeVisible();
    expect(await settled(page)).toBe(before);
  });
});
