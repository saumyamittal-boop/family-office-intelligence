import { expect, test } from "@playwright/test";
import { PASSWORD, demoFamily, logOut, me, signUp, uniqueName } from "./helpers";

test.describe("signing in and out", () => {
  test("a new account lands on the guided plan, survives a reload, and can log out and back in", async ({ page }) => {
    const name = await signUp(page);
    await expect(page).toHaveURL(/\/plan/);
    await expect(page.getByRole("heading", { level: 1, name: "Plan my money" })).toBeVisible();

    await page.reload();
    await expect(page.getByRole("navigation", { name: "Main" })).toBeVisible(); // the session is on the server, not in the page

    await logOut(page);
    await page.getByLabel("Username").fill(name);
    await page.getByLabel("Password").fill(PASSWORD);
    await page.getByRole("button", { name: "Log in" }).click();
    await expect(page.getByRole("navigation", { name: "Main" })).toBeVisible();
  });

  test("a wrong password is refused in plain words and reveals nothing about the account", async ({ page }) => {
    const name = await signUp(page, uniqueName("wrongpw"));
    await logOut(page);
    for (const username of [name, "nobody_" + uniqueName()]) {
      await page.getByLabel("Username").fill(username);
      await page.getByLabel("Password").fill("not the password");
      await page.getByRole("button", { name: "Log in" }).click();
      await expect(page.getByRole("alert")).toContainText("Wrong username or password.");
    }
  });

  test("six wrong guesses lock a username for a while, even against the right password", async ({ page }) => {
    const name = await signUp(page, uniqueName("lock"));
    await logOut(page);
    for (let i = 0; i < 5; i++) {
      await page.getByLabel("Username").fill(name);
      await page.getByLabel("Password").fill(`wrong guess ${i}`);
      await page.getByRole("button", { name: "Log in" }).click();
      await expect(page.getByRole("alert")).toContainText("Wrong username or password.");
    }
    await page.getByLabel("Password").fill(PASSWORD);
    await page.getByRole("button", { name: "Log in" }).click();
    await expect(page.getByRole("alert")).toContainText(/Too many attempts/);
    await expect(page.getByRole("navigation", { name: "Main" })).toHaveCount(0);
  });

  test("a demo family opens a private copy and shows its warnings", async ({ page }) => {
    await demoFamily(page);
    await expect(page.getByRole("heading", { level: 1 })).toBeVisible();
    await expect(page.getByRole("region", { name: "Needs your attention" })).toBeVisible();
  });
});

test.describe("what the browser can and cannot see of the session", () => {
  test("the session cookie is invisible to scripts, and the server ends the session on log out", async ({ page, context }) => {
    await demoFamily(page);
    const cookie = (await context.cookies()).find((c) => c.name === "fo_session");
    expect(cookie, "a session cookie is set").toBeTruthy();
    expect(cookie!.httpOnly).toBe(true);
    expect(cookie!.sameSite).toBe("Lax");
    expect(await page.evaluate(() => document.cookie)).not.toContain("fo_session");
    const stored = await page.evaluate(() => JSON.stringify({ ...localStorage, ...sessionStorage }));
    expect(stored).not.toContain(cookie!.value);
    expect(stored.toLowerCase()).not.toContain("csrf");

    const token = (await me(page)).csrf_token;
    expect(token.length).toBeGreaterThan(20);
    await logOut(page);
    const after = await page.request.get("/api/auth/me");
    expect(after.status()).toBe(401);
    // the old cookie, replayed by somebody who copied it, no longer works
    const replay = await page.request.get("/api/auth/me", { headers: { Cookie: `fo_session=${cookie!.value}` } });
    expect(replay.status()).toBe(401);
  });

  test("pressing Back after logging out does not bring private pages back", async ({ page }) => {
    await demoFamily(page);
    await page.getByRole("navigation", { name: "Main" }).getByRole("link", { name: "Family profile", exact: true }).click();
    await expect(page.getByRole("heading", { level: 1, name: "Family profile" })).toBeVisible();
    await logOut(page);
    await page.goBack();
    await expect(page.getByRole("tab", { name: "Log in" })).toBeVisible();
    await expect(page.getByRole("heading", { level: 1, name: "Family profile" })).toHaveCount(0);
  });
});
