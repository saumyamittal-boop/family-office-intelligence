import { expect } from "@playwright/test";
import type { Browser, BrowserContext, Page } from "@playwright/test";

export const PASSWORD = "correct horse battery staple";
let counter = 0;

/** A username nobody has used in this run. */
export const uniqueName = (prefix = "e2e") => `${prefix}_${Date.now().toString(36)}_${counter++}`;

export async function signUp(page: Page, username = uniqueName()): Promise<string> {
  await page.goto("/");
  await page.getByRole("tab", { name: "Create account" }).click();
  await page.getByLabel("Choose a username").fill(username);
  await page.getByLabel("Choose a password").fill(PASSWORD);
  await page.getByRole("button", { name: "Create account" }).click();
  await expect(page.getByRole("navigation", { name: "Main" })).toBeVisible();
  return username;
}

export async function demoFamily(page: Page, label: RegExp = /liquidity-gap example/) {
  await page.goto("/");
  await page.getByRole("button", { name: label }).click();
  await signedIn(page);
}

/** Signed in on any screen size: the menu is on the page on a desktop, behind a button on a phone. */
export async function signedIn(page: Page) {
  await expect(page.getByRole("navigation", { name: "Main" }).or(page.getByRole("button", { name: "Open navigation" }))).toBeVisible();
}

export async function logOut(page: Page) {
  await page.getByRole("button", { name: /^Account:/ }).click();
  await page.getByRole("menuitem", { name: "Log out" }).click();
  await expect(page.getByRole("tab", { name: "Log in" })).toBeVisible();
}

export async function goTo(page: Page, name: string) {
  await page.getByRole("navigation", { name: "Main" }).getByRole("link", { name, exact: true }).click();
}

export async function newPerson(browser: Browser): Promise<{ context: BrowserContext; page: Page }> {
  const context = await browser.newContext();
  return { context, page: await context.newPage() };
}

/** What the signed-in session says about itself, including the token a state-changing request must carry. */
export async function me(page: Page): Promise<{ user: { id: number; username: string }; csrf_token: string }> {
  const r = await page.request.get("/api/auth/me");
  expect(r.status()).toBe(200);
  return r.json();
}

/** Wait until a page has finished drawing: the network is quiet and the text has stopped changing. */
export async function settled(page: Page): Promise<string> {
  await page.waitForLoadState("networkidle");
  let last = "";
  for (let i = 0; i < 20; i++) {
    const now = await page.locator("main").innerText();
    if (now === last && now.length > 200) return now;
    last = now;
    await page.waitForTimeout(300);
  }
  return last;
}

export const csv = (rows: string[][]) => ["Name,Asset class,Account,Value (Cr)", ...rows.map((r) => r.join(","))].join("\n") + "\n";

export async function chooseFile(page: Page, name: string, text: string) {
  await page.getByLabel("Holdings file").setInputFiles({ name, mimeType: "text/csv", buffer: Buffer.from(text, "utf-8") });
}
