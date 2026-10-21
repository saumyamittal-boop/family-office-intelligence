import { screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import axe from "axe-core";
import { afterEach, describe, expect, it, vi } from "vitest";
import App from "./App";
import { NAV } from "./layout/nav";
import type { NavItem } from "./layout/nav";
import { analysis, META } from "./test/fixtures";
import { answerReply, assistantApp, clarifyReply, refusalReply } from "./test/explainFixtures";
import { CSV_TEXT, holdingsApp, previewWithProblems, withImports } from "./test/holdingsFixtures";
import { appRoutes, dashboard } from "./test/phase4Fixtures";
import { json, renderWithProviders, serve } from "./test/render";

/**
 * Automated WCAG checks (axe-core) on the screens a person actually sees. Colour contrast cannot be computed
 * without a real layout engine, so it is checked separately: tokens in styles/contrast.test.ts, and in a real browser.
 */
async function audit(root: Element = document.body): Promise<string[]> {
  const result = await axe.run(root, {
    runOnly: { type: "tag", values: ["wcag2a", "wcag2aa", "wcag21a", "wcag21aa", "wcag22aa", "best-practice"] },
    rules: { "color-contrast": { enabled: false } },
  });
  return result.violations.map((v) => `${v.id}: ${v.help} -> ${v.nodes.map((n) => n.target.join(" ")).join(" | ")}`);
}

describe("the audit itself", () => {
  it("catches real problems, so a clean result means something", async () => {
    const { container } = renderWithProviders(
      <main>
        <h1>Page</h1>
        <button />
        <img src="chart.png" />
        <input />
        <div role="img" />
      </main>,
    );
    const found = (await audit(container)).join("\n");
    for (const rule of ["button-name", "image-alt", "label", "role-img-alt"]) expect(found).toContain(rule);
  });
});

const signedIn = () => serve(appRoutes());

afterEach(() => vi.unstubAllGlobals());

describe.each(["light", "dark"] as const)("accessibility in the %s theme", (theme) => {
  const setTheme = () => {
    window.localStorage.setItem("foi.theme", theme);
  };

  it("sign-in screen", async () => {
    setTheme();
    serve({ "GET /api/auth/me": json({ detail: "Please sign in." }, 401), "GET /api/meta": json(META) });
    renderWithProviders(<App />);
    await screen.findByRole("button", { name: "Log in" });
    expect(document.documentElement).toHaveAttribute("data-theme", theme);
    expect(await audit()).toEqual([]);
  });

  it("sign-in screen showing a server error", async () => {
    setTheme();
    const user = userEvent.setup();
    serve({
      "GET /api/auth/me": json({ detail: "Please sign in." }, 401),
      "GET /api/meta": json(META),
      "POST /api/auth/login": json({ detail: "Wrong username or password.", problems: null }, 401),
    });
    renderWithProviders(<App />);
    await user.type(await screen.findByLabelText("Username"), "asha");
    await user.type(screen.getByLabelText("Password"), "whatever-it-is");
    await user.click(screen.getByRole("button", { name: "Log in" }));
    await screen.findByRole("alert");
    expect(await audit()).toEqual([]);
  });

  it("dashboard with every chart as a picture", async () => {
    setTheme();
    signedIn();
    renderWithProviders(<App />);
    await screen.findByText("8.8%");
    await screen.findByRole("img", { name: /the worst fall from a previous peak/ });
    expect(await audit()).toEqual([]);
  });

  it("dashboard with every chart as a table", async () => {
    setTheme();
    const user = userEvent.setup();
    signedIn();
    renderWithProviders(<App />);
    await screen.findByText("8.8%");
    await screen.findByRole("img", { name: /the worst fall from a previous peak/ });
    for (const toggle of screen.getAllByRole("radio", { name: "Table" })) await user.click(toggle);
    expect(screen.queryByRole("img")).not.toBeInTheDocument();
    expect(await audit()).toEqual([]);
  });

  it("dashboard with the explanation panel open", async () => {
    setTheme();
    const user = userEvent.setup();
    signedIn();
    renderWithProviders(<App />);
    await user.click(await screen.findByRole("button", { name: "About Expected return" }));
    await screen.findByRole("dialog", { name: "Expected return" });
    expect(await audit()).toEqual([]);
  });

  it("dashboard showing the other three modules", async () => {
    setTheme();
    serve(appRoutes(analysis(), { "GET /api/dashboard": json(dashboard(["net_worth_projection", "historical_performance", "recommendation_rationale", "allocation_actions"], false)) }));
    renderWithProviders(<App />);
    await screen.findByRole("heading", { name: "Historical performance" });
    await screen.findByRole("img", { name: /Growth of 100 invested/ });
    expect(await audit()).toEqual([]);
  });

  it("the customise panel", async () => {
    setTheme();
    const user = userEvent.setup();
    signedIn();
    renderWithProviders(<App />);
    await user.click(await screen.findByRole("button", { name: "Customise dashboard" }));
    await screen.findByRole("dialog", { name: "Customise your dashboard" });
    expect(await audit()).toEqual([]);
  });

  it("the customise panel showing a save error", async () => {
    setTheme();
    const user = userEvent.setup();
    serve(appRoutes(analysis(), { "PUT /api/dashboard": json({ detail: "That module isn't available yet.", problems: null }, 422) }));
    renderWithProviders(<App />);
    await user.click(await screen.findByRole("button", { name: "Customise dashboard" }));
    const panel = within(await screen.findByRole("dialog"));
    await user.selectOptions(panel.getByRole("combobox", { name: "Slot 4" }), "historical_performance");
    await user.click(panel.getByRole("button", { name: "Save dashboard" }));
    await panel.findByRole("alert");
    expect(await audit()).toEqual([]);
  });

  it.each([
    ["recommendation", "/recommendation", "How this was worked out, and its limits"],
    ["risk and liquidity", "/risk", "Calendar-year returns"],
    ["scenarios", "/scenarios", "Compare your options under one scenario"],
  ])("%s page, charts as pictures and as tables", async (_name, path, lastHeading) => {
    setTheme();
    const user = userEvent.setup();
    signedIn();
    renderWithProviders(<App />, path);
    await screen.findByRole("heading", { name: lastHeading });
    if (path === "/scenarios") await screen.findByRole("img", { name: /Under "Equities fall 25%"/ });
    expect(await audit()).toEqual([]);
    for (const toggle of screen.getAllByRole("radio", { name: "Table" })) await user.click(toggle);
    expect(await audit()).toEqual([]);
  });

  it("scenarios page with the assumptions table open", async () => {
    setTheme();
    const user = userEvent.setup();
    signedIn();
    renderWithProviders(<App />, "/scenarios");
    await user.click(await screen.findByText("What each built-in scenario assumes"));
    await screen.findByRole("table", { name: "Shocks applied by each built-in scenario" });
    expect(await audit()).toEqual([]);
  });

  it("family profile page, as loaded and with problems shown", async () => {
    setTheme();
    const user = userEvent.setup();
    signedIn();
    renderWithProviders(<App />, "/profile");
    await screen.findByLabelText("Profile name");
    expect(await audit()).toEqual([]);
    const debt = screen.getByRole("textbox", { name: /^Debt \(%\)$/ });
    await user.clear(debt);
    await user.type(debt, "10");
    await screen.findByText("One thing to fix before saving:");
    expect(await audit()).toEqual([]);
    await user.click(screen.getByRole("button", { name: "Add an outflow" }));
    expect(await audit()).toEqual([]);
  });

  it("navigation drawer", async () => {
    setTheme();
    const user = userEvent.setup();
    signedIn();
    renderWithProviders(<App />);
    await user.click(await screen.findByRole("button", { name: "Open navigation" }));
    const drawer = await screen.findByRole("dialog", { name: "Navigation" });
    expect(within(drawer).getByRole("navigation", { name: "Main" })).toBeInTheDocument();
    expect(await audit()).toEqual([]);
  });

  it("holdings page: choosing a file, problems in it, then the class assignment", async () => {
    setTheme();
    serve(holdingsApp({ "POST /api/profiles/1/holdings/preview": json(previewWithProblems()) }));
    renderWithProviders(<App />, "/holdings");
    await screen.findByRole("heading", { level: 1, name: "Holdings" });
    expect(await audit()).toEqual([]); // nothing imported yet
    await userEvent.setup().upload(await screen.findByLabelText("Holdings file"), new File([CSV_TEXT], "statement.csv", { type: "text/csv" }));
    await screen.findByText("2 problems to fix:");
    await userEvent.setup().click(screen.getByText(/Show the lines/));
    expect(await audit()).toEqual([]);
  });

  it("holdings page: imported data, the consolidation tables and the apply card", async () => {
    setTheme();
    serve(withImports());
    renderWithProviders(<App />, "/holdings");
    await screen.findByRole("table", { name: "Imported holdings by account" });
    await screen.findByRole("table", { name: "Profile holdings now and after using the imported holdings" });
    expect(await audit()).toEqual([]);
    await userEvent.setup().click(await screen.findByRole("button", { name: "Delete statement.csv" }));
    await screen.findByRole("button", { name: "Yes, delete statement.csv" });
    expect(await audit()).toEqual([]);
  });

  it("dashboard with the holdings consolidation module", async () => {
    setTheme();
    serve(withImports({ "GET /api/dashboard": json(dashboard(["holdings_consolidation", "allocation_actions", "risk_exposure", "stress_scenarios"], false)) }));
    renderWithProviders(<App />);
    await screen.findByRole("heading", { level: 2, name: "Holdings consolidation" });
    await screen.findByRole("img", { name: /Consolidated holdings/ });
    expect(await audit()).toEqual([]);
  });

  it("assistant page: the starter questions", async () => {
    setTheme();
    serve(assistantApp());
    renderWithProviders(<App />, "/assistant");
    await screen.findByRole("button", { name: "Is my liquidity enough?" });
    expect(await audit()).toEqual([]);
  });

  it("assistant page: an answer with its evidence open", async () => {
    setTheme();
    serve(assistantApp());
    renderWithProviders(<App />, "/assistant");
    await userEvent.setup().click(await screen.findByRole("button", { name: "Is my liquidity enough?" }));
    const answer = await screen.findByRole("article", { name: "Is my liquidity enough?" });
    await userEvent.setup().click(within(answer).getByText(/Show the evidence/));
    expect(await audit()).toEqual([]);
  });

  it("assistant page: a refusal, then a question to choose between", async () => {
    setTheme();
    let n = 0;
    serve(assistantApp(() => (n++ === 0 ? refusalReply : clarifyReply)));
    renderWithProviders(<App />, "/assistant");
    const user = userEvent.setup();
    await user.type(await screen.findByRole("textbox", { name: "Your question" }), "which fund should I buy");
    await user.click(screen.getByRole("button", { name: "Ask" }));
    await screen.findByText("Outside what I do.");
    expect(await audit()).toEqual([]);
    await user.type(screen.getByRole("textbox", { name: "Your question" }), "x");
    await user.click(screen.getByRole("button", { name: "Ask" }));
    await screen.findByText("Which did you mean?");
    expect(await audit()).toEqual([]);
  });

  it("the Why? panel beside a warning", async () => {
    setTheme();
    serve(assistantApp(() => answerReply()));
    renderWithProviders(<App />);
    const warnings = await screen.findByRole("region", { name: "Needs your attention" });
    await userEvent.setup().click(within(warnings).getByRole("button", { name: /^Why\? Liquidity shortfall/ }));
    const panel = await screen.findByRole("dialog");
    await within(panel).findByText(/Over the next 24 months/);
    expect(await audit()).toEqual([]);
  });

  it("loading, failure and placeholder pages", async () => {
    setTheme();
    serve({
      ...appRoutes(),
      "GET /api/profiles/1/analysis": json({ detail: "This profile can't be analysed yet.", problems: null }, 422),
    });
    const { unmount } = renderWithProviders(<App />);
    await screen.findByRole("alert");
    expect(await audit()).toEqual([]);
    unmount();

    signedIn();
    const planned = { to: "/later", label: "Later page", icon: "info", arrivesInPhase: 8, description: "A page that is planned." } as const;
    (NAV as NavItem[]).push(planned); // every page in the menu is built now: add a planned one for this check
    try {
      renderWithProviders(<App />, "/later");
      await waitFor(() => expect(screen.getByText("Not built yet")).toBeInTheDocument());
      expect(await audit()).toEqual([]);
    } finally {
      (NAV as NavItem[]).splice((NAV as NavItem[]).indexOf(planned), 1);
    }
  });
});
