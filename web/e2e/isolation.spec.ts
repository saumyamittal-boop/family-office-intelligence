import { expect, test } from "@playwright/test";
import { goTo, me, newPerson, signUp, uniqueName } from "./helpers";

test.describe("one person's family never reaches another's", () => {
  test("another account's profile is not found, cannot be changed or deleted, and its name never appears", async ({ browser }) => {
    const a = await newPerson(browser);
    const b = await newPerson(browser);
    try {
      const marker = `PRIVATE-${uniqueName("marker")}`;
      await signUp(a.page, uniqueName("alice"));
      await signUp(b.page, uniqueName("bob"));

      // Alice renames her profile to something only she should ever see.
      const aliceMe = await me(a.page);
      const alice = (await (await a.page.request.get("/api/profiles")).json())[0];
      const full = await (await a.page.request.get(`/api/profiles/${alice.id}`)).json();
      delete full.id;
      const renamed = await a.page.request.put(`/api/profiles/${alice.id}`, { data: { ...full, name: marker }, headers: { "X-CSRF-Token": aliceMe.csrf_token } });
      expect(renamed.status()).toBe(200);

      // Bob asks for it in every way the API offers.
      const bobToken = (await me(b.page)).csrf_token;
      const csrf = { "X-CSRF-Token": bobToken };
      const base = `/api/profiles/${alice.id}`;
      for (const response of [
        await b.page.request.get(base), await b.page.request.get(`${base}/analysis`), await b.page.request.get(`${base}/history`),
        await b.page.request.get(`${base}/holdings/consolidation`), await b.page.request.get(`${base}/holdings/imports`),
        await b.page.request.put(base, { data: { ...full, name: "hijacked" }, headers: csrf }),
        await b.page.request.delete(base, { headers: csrf }),
        await b.page.request.post(`${base}/explain`, { data: { intent: "help" }, headers: csrf }),
        await b.page.request.post(`${base}/scenarios`, { data: { preset: "Market crash" }, headers: csrf }),
      ]) {
        expect(response.status(), response.url()).toBe(404);
        expect(await response.text()).not.toContain(marker);
      }
      const still = await (await a.page.request.get(`/api/profiles/${alice.id}`)).json();
      expect(still.name).toBe(marker); // nothing Bob did changed it

      // Bob's own screens, including a link that names Alice's profile, show Bob's family and never Alice's name.
      for (const path of ["/", `/profile?profile=${alice.id}`, `/recommendation?profile=${alice.id}`, `/holdings?profile=${alice.id}`, `/assistant?profile=${alice.id}`]) {
        await b.page.goto(path);
        await expect(b.page.getByRole("navigation", { name: "Main" })).toBeVisible();
        await b.page.waitForLoadState("networkidle");
        expect(await b.page.locator("body").innerText()).not.toContain(marker);
      }
      await goTo(b.page, "Assistant");
      await b.page.getByRole("button", { name: "Why the Balanced mix?" }).click();
      await expect(b.page.getByRole("article")).toBeVisible();
      expect(await b.page.locator("body").innerText()).not.toContain(marker);
    } finally {
      await a.context.close();
      await b.context.close();
    }
  });

  test("two browsers signed in as different people keep separate dashboards", async ({ browser }) => {
    const a = await newPerson(browser);
    const b = await newPerson(browser);
    try {
      await signUp(a.page, uniqueName("dash_a"));
      await signUp(b.page, uniqueName("dash_b"));
      const aliceMe = await me(a.page);
      const set = await a.page.request.put("/api/dashboard", { data: { modules: ["holdings_consolidation", "net_worth_projection", "stress_scenarios", "risk_exposure"] }, headers: { "X-CSRF-Token": aliceMe.csrf_token } });
      expect(set.status()).toBe(200);
      const bobs = await (await b.page.request.get("/api/dashboard")).json();
      expect(bobs.modules).not.toContain("holdings_consolidation");
      expect(bobs.is_default).toBe(true);
    } finally {
      await a.context.close();
      await b.context.close();
    }
  });
});
