import { screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";
import App from "../App";
import type { ModuleId } from "../api/client";
import { move, place } from "../dashboard/CustomisePanel";
import { analysis } from "../test/fixtures";
import { json, jsonBy, renderWithProviders, serve } from "../test/render";
import { appRoutes, dashboard, DEFAULT_MODULES, history } from "../test/phase4Fixtures";

afterEach(() => vi.unstubAllGlobals());

const NAMES: Record<string, string> = {
  allocation_actions: "Allocation and actions",
  liquidity_commitments: "Liquidity and commitments",
  risk_exposure: "Risk exposure",
  stress_scenarios: "Stress scenarios",
  net_worth_projection: "Net worth and projection",
  historical_performance: "Historical performance",
  recommendation_rationale: "Why this recommendation",
};

const grid = () => within(screen.getByRole("group", { name: "Your dashboard" }));
const moduleTitles = () => grid().getAllByRole("heading", { level: 2 }).map((h) => h.textContent);

async function openDashboard(routes = appRoutes(), path = "/") {
  const calls = serve(routes);
  renderWithProviders(<App />, path);
  await screen.findByRole("group", { name: "Your dashboard" });
  return calls;
}

describe("the dashboard", () => {
  it("shows the four default modules in order, each with a link to its full page", async () => {
    await openDashboard();
    expect(moduleTitles()).toEqual(DEFAULT_MODULES.map((id) => NAMES[id]));
    const link = screen.getByRole("link", { name: "Allocation and actions: open the full Recommendation page" });
    expect(link).toHaveAttribute("href", expect.stringMatching(/^\/recommendation/));
    expect(screen.getByRole("link", { name: /Stress scenarios: open the full Scenarios page/ })).toHaveAttribute("href", expect.stringMatching(/^\/scenarios/));
  });

  it("shows the modules a person saved, in the order they saved them", async () => {
    const saved: ModuleId[] = ["historical_performance", "net_worth_projection", "recommendation_rationale", "allocation_actions"];
    await openDashboard(appRoutes(analysis(), { "GET /api/dashboard": json(dashboard(saved, false)) }));
    expect(moduleTitles()).toEqual(saved.map((id) => NAMES[id]));
    expect(screen.queryByRole("heading", { name: "Stress scenarios" })).not.toBeInTheDocument();
  });

  it("lists the modules that are not on the dashboard and where to find them", async () => {
    await openDashboard();
    const rest = within(screen.getByRole("region", { name: "Not on your dashboard" }));
    expect(rest.getByRole("link", { name: /Net worth and projection in Recommendation/ })).toHaveAttribute("href", expect.stringMatching(/^\/recommendation/));
    expect(rest.getByRole("link", { name: /Historical performance in Risk and liquidity/ })).toHaveAttribute("href", expect.stringMatching(/^\/risk/));
    expect(rest.getByText("Holdings consolidation (arrives in phase 5)")).toBeInTheDocument();
    expect(rest.queryByText(/Allocation and actions/)).not.toBeInTheDocument();
  });

  it("each module draws real figures from the analysis", async () => {
    await openDashboard();
    const allocation = within(screen.getByRole("heading", { name: "Allocation and actions" }).closest("section") as HTMLElement);
    expect(allocation.getByText("Balanced mix")).toBeInTheDocument();
    expect(allocation.getByText("What to buy and sell")).toBeInTheDocument();
    const liquidity = within(screen.getByRole("heading", { name: "Liquidity and commitments" }).closest("section") as HTMLElement);
    expect(liquidity.getByText("Counted liquid assets")).toBeInTheDocument();
    expect(liquidity.getByText("Liquidity ladder")).toBeInTheDocument();
    const risk = within(screen.getByRole("heading", { name: "Risk exposure" }).closest("section") as HTMLElement);
    expect(await risk.findByText("Drawdown against your limit")).toBeInTheDocument();
    expect(risk.getByText("95% 1-month CVaR")).toBeInTheDocument();
    const stress = within(screen.getByRole("heading", { name: "Stress scenarios" }).closest("section") as HTMLElement);
    for (const name of ["Equities fall 25%", "Market crash", "Inflation and rate spike", "Large unexpected expense", "Lost decade"]) {
      expect(stress.getByRole("article", { name })).toBeInTheDocument();
    }
    expect(stress.getByText(/Baseline: real corpus/)).toBeInTheDocument();
  });

  it("follows the mix chosen in the address, and ignores one that does not exist", async () => {
    await openDashboard(appRoutes(), "/?mix=Growth");
    expect(screen.getByRole("radio", { name: "Growth" })).toBeChecked();
    expect(screen.getByText("Growth mix")).toBeInTheDocument();
  });

  it("falls back to Balanced for an unknown mix", async () => {
    await openDashboard(appRoutes(), "/?mix=Reckless");
    expect(screen.getByRole("radio", { name: "Balanced" })).toBeChecked();
  });
});

describe("warnings are never hidden by the modules a person chooses", () => {
  const ALL = Object.keys(NAMES) as ModuleId[];
  // Seven windows of four that between them leave out every module at least once.
  const windows = ALL.map((_, i) => [0, 1, 2, 3].map((k) => ALL[(i + k) % ALL.length]!));

  it.each(windows)("chosen: %s, %s, %s, %s", async (...modules) => {
    await openDashboard(appRoutes(analysis(), { "GET /api/dashboard": json(dashboard(modules as ModuleId[], false)) }));
    expect(moduleTitles()).toEqual(modules.map((id) => NAMES[id]));
    const warning = screen.getByRole("region", { name: "Needs your attention" });
    expect(within(warning).getByRole("alert")).toHaveTextContent("Liquidity shortfall");
    expect(screen.getByRole("button", { name: "About Liquidity cover" })).toBeInTheDocument(); // and the headline tiles stay
  });
});

describe("customising the dashboard", () => {
  const open = async () => {
    const user = userEvent.setup();
    const calls = await openDashboard(
      appRoutes(analysis(), {
        "PUT /api/dashboard": jsonBy<{ modules: ModuleId[] }>((b) => dashboard(b.modules, false)),
        "DELETE /api/dashboard": json(dashboard(DEFAULT_MODULES, true)),
      }),
    );
    await user.click(screen.getByRole("button", { name: "Customise dashboard" }));
    const panel = await screen.findByRole("dialog", { name: "Customise your dashboard" });
    return { user, calls, panel: within(panel) };
  };
  const slotValues = (panel: ReturnType<typeof within>) => [1, 2, 3, 4].map((n) => (panel.getByRole("combobox", { name: `Slot ${n}` }) as HTMLSelectElement).value);

  it("offers four slots holding the current choice, a preview, and every module with where it lives", async () => {
    const { panel } = await open();
    expect(slotValues(panel)).toEqual(DEFAULT_MODULES);
    const preview = within(panel.getByRole("list", { name: "Layout preview" }));
    expect(preview.getAllByRole("listitem").map((li) => li.textContent)).toEqual(
      DEFAULT_MODULES.map((id, i) => `Position ${i + 1}: ${NAMES[id]}`),
    );
    expect(panel.getByText("On your dashboard: 1")).toBeInTheDocument();
    expect(panel.getAllByText("On the Recommendation page")).toHaveLength(2); // net worth and the rationale
    expect(panel.getByRole("button", { name: "Save dashboard" })).toBeDisabled(); // nothing changed yet
  });

  it("will not offer the module that is not built yet", async () => {
    const { panel } = await open();
    const option = within(panel.getByRole("combobox", { name: "Slot 1" })).getByRole("option", { name: /Holdings consolidation/ });
    expect(option).toBeDisabled();
    expect(option).toHaveTextContent("arrives in phase 5");
    expect(panel.getByText("Arrives in phase 5")).toBeInTheDocument();
  });

  it("replaces a module by choosing another in its slot", async () => {
    const { user, panel } = await open();
    await user.selectOptions(panel.getByRole("combobox", { name: "Slot 4" }), "historical_performance");
    expect(slotValues(panel)).toEqual(["allocation_actions", "liquidity_commitments", "risk_exposure", "historical_performance"]);
    const list = within(panel.getByRole("heading", { name: "All modules" }).closest("section") as HTMLElement);
    expect(list.getByText("On your dashboard: 4").closest("li")).toHaveTextContent("Historical performance");
    expect(list.getByText("On the Scenarios page").closest("li")).toHaveTextContent("Stress scenarios"); // dropped, but still reachable
    expect(panel.getByRole("button", { name: "Save dashboard" })).toBeEnabled();
  });

  it("swaps two slots when a module that is already chosen is picked again", async () => {
    const { user, panel } = await open();
    await user.selectOptions(panel.getByRole("combobox", { name: "Slot 2" }), "allocation_actions");
    expect(slotValues(panel)).toEqual(["liquidity_commitments", "allocation_actions", "risk_exposure", "stress_scenarios"]);
    expect(new Set(slotValues(panel)).size).toBe(4); // always four different modules
  });

  it("reorders with the move buttons, and the ends cannot move off the list", async () => {
    const { user, panel } = await open();
    expect(panel.getByRole("button", { name: "Move Allocation and actions up" })).toBeDisabled();
    expect(panel.getByRole("button", { name: "Move Stress scenarios down" })).toBeDisabled();
    await user.click(panel.getByRole("button", { name: "Move Risk exposure up" }));
    expect(slotValues(panel)).toEqual(["allocation_actions", "risk_exposure", "liquidity_commitments", "stress_scenarios"]);
    await user.click(panel.getByRole("button", { name: "Move Allocation and actions down" }));
    expect(slotValues(panel)).toEqual(["risk_exposure", "allocation_actions", "liquidity_commitments", "stress_scenarios"]);
  });

  it("saves the exact order to the account with the CSRF token, closes, announces it and redraws the dashboard", async () => {
    const { user, calls, panel } = await open();
    await user.selectOptions(panel.getByRole("combobox", { name: "Slot 4" }), "net_worth_projection");
    await user.click(panel.getByRole("button", { name: "Move Net worth and projection up" }));
    await user.click(panel.getByRole("button", { name: "Save dashboard" }));
    await waitFor(() => expect(screen.queryByRole("dialog")).not.toBeInTheDocument());

    const put = calls.find((c) => c.method === "PUT" && c.path === "/api/dashboard")!;
    expect(JSON.parse(put.body!)).toEqual({ modules: ["allocation_actions", "liquidity_commitments", "net_worth_projection", "risk_exposure"] });
    expect(put.headers["X-CSRF-Token"]).toBe("csrf-abc");
    expect(await screen.findByText("Your dashboard is saved.")).toBeInTheDocument();
    expect(moduleTitles()).toEqual(["Allocation and actions", "Liquidity and commitments", "Net worth and projection", "Risk exposure"]);
  });

  it("cancel throws the changes away", async () => {
    const { user, panel } = await open();
    await user.selectOptions(panel.getByRole("combobox", { name: "Slot 1" }), "stress_scenarios");
    await user.click(panel.getByRole("button", { name: "Cancel" }));
    await waitFor(() => expect(screen.queryByRole("dialog")).not.toBeInTheDocument());
    expect(moduleTitles()).toEqual(DEFAULT_MODULES.map((id) => NAMES[id]));
    await user.click(screen.getByRole("button", { name: "Customise dashboard" }));
    expect(slotValues(within(await screen.findByRole("dialog")))).toEqual(DEFAULT_MODULES);
  });

  it("Escape closes the panel and focus returns to the button that opened it", async () => {
    const { user } = await open();
    await user.keyboard("{Escape}");
    await waitFor(() => expect(screen.queryByRole("dialog")).not.toBeInTheDocument());
    expect(screen.getByRole("button", { name: "Customise dashboard" })).toHaveFocus();
  });

  it("keeps the panel open and says why when saving fails", async () => {
    const user = userEvent.setup();
    await openDashboard(appRoutes(analysis(), { "PUT /api/dashboard": json({ detail: "That module isn't available yet.", problems: null }, 422) }));
    await user.click(screen.getByRole("button", { name: "Customise dashboard" }));
    const panel = within(await screen.findByRole("dialog"));
    await user.selectOptions(panel.getByRole("combobox", { name: "Slot 4" }), "historical_performance");
    await user.click(panel.getByRole("button", { name: "Save dashboard" }));
    expect(await panel.findByRole("alert")).toHaveTextContent("That module isn't available yet.");
    expect(screen.getByRole("dialog")).toBeInTheDocument();
    expect(panel.getByRole("button", { name: "Save dashboard" })).toBeEnabled(); // can try again
  });

  it("restores the default four, and says nothing to restore when it already is the default", async () => {
    const user = userEvent.setup();
    const calls = await openDashboard(
      appRoutes(analysis(), {
        "GET /api/dashboard": json(dashboard(["historical_performance", "net_worth_projection", "recommendation_rationale", "allocation_actions"], false)),
        "DELETE /api/dashboard": json(dashboard(DEFAULT_MODULES, true)),
      }),
    );
    await user.click(screen.getByRole("button", { name: "Customise dashboard" }));
    await user.click(within(await screen.findByRole("dialog")).getByRole("button", { name: "Restore default" }));
    await waitFor(() => expect(screen.queryByRole("dialog")).not.toBeInTheDocument());
    expect(calls.some((c) => c.method === "DELETE" && c.path === "/api/dashboard" && c.headers["X-CSRF-Token"] === "csrf-abc")).toBe(true);
    expect(await screen.findByText("Your dashboard is back to the default four.")).toBeInTheDocument();
    expect(moduleTitles()).toEqual(DEFAULT_MODULES.map((id) => NAMES[id]));

    await user.click(screen.getByRole("button", { name: "Customise dashboard" }));
    expect(within(await screen.findByRole("dialog")).getByRole("button", { name: "Restore default" })).toBeDisabled();
  });
});

describe("when something fails", () => {
  it("shows the default four with a warning if the saved choice cannot be loaded, and can try again", async () => {
    const user = userEvent.setup();
    let attempts = 0;
    await openDashboard(
      appRoutes(analysis(), {
        "GET /api/dashboard": () => (++attempts === 1 ? new Response(JSON.stringify({ detail: "Down." }), { status: 500 }) : new Response(JSON.stringify(dashboard(["risk_exposure", "stress_scenarios", "allocation_actions", "liquidity_commitments"], false)))),
      }),
    );
    expect(await screen.findByText("Couldn't load your saved dashboard.")).toBeInTheDocument();
    expect(moduleTitles()).toEqual(DEFAULT_MODULES.map((id) => NAMES[id]));
    expect(screen.getByRole("button", { name: "Customise dashboard" })).toBeDisabled(); // nothing to edit until it loads
    await user.click(screen.getByRole("button", { name: "Try again" }));
    await waitFor(() => expect(moduleTitles()[0]).toBe("Risk exposure"));
  });

  it("one module failing does not take the rest of the dashboard down", async () => {
    await openDashboard(appRoutes(analysis(), { "GET /api/profiles/1/history": json({ detail: "The model is busy.", problems: null }, 503) }));
    const risk = within(screen.getByRole("heading", { name: "Risk exposure" }).closest("section") as HTMLElement);
    expect(await risk.findByText("The drawdown history could not be loaded")).toBeInTheDocument();
    expect(risk.getByText("The model is busy.")).toBeInTheDocument();
    expect(risk.getByText("Volatility")).toBeInTheDocument(); // the tiles that need no history still show
    expect(screen.getByText("What to buy and sell")).toBeInTheDocument();
    expect(screen.getByText("Liquidity ladder")).toBeInTheDocument();
  });

  it("a module that throws while drawing is contained and offers a retry", async () => {
    const broken = analysis();
    // @ts-expect-error simulating a malformed response: the allocation module cannot read weights from nothing
    broken.options[1]!.portfolio.weights_total = null;
    await openDashboard(appRoutes(broken));
    const card = within(screen.getByRole("heading", { name: "Allocation and actions" }).closest("section") as HTMLElement);
    expect(await card.findByText("Allocation and actions couldn't be drawn")).toBeInTheDocument();
    expect(card.getByRole("button", { name: "Try again" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Liquidity and commitments" })).toBeInTheDocument();
  });
});

describe("the helpers behind the panel", () => {
  const four: ModuleId[] = ["allocation_actions", "liquidity_commitments", "risk_exposure", "stress_scenarios"];

  it("place puts a new module in a slot, and swaps when it was already chosen", () => {
    expect(place(four, 3, "historical_performance")).toEqual(["allocation_actions", "liquidity_commitments", "risk_exposure", "historical_performance"]);
    expect(place(four, 0, "stress_scenarios")).toEqual(["stress_scenarios", "liquidity_commitments", "risk_exposure", "allocation_actions"]);
    expect(place(four, 1, "liquidity_commitments")).toEqual(four);
    expect(four).toEqual(["allocation_actions", "liquidity_commitments", "risk_exposure", "stress_scenarios"]); // the input is untouched
  });

  it("move shifts one module and keeps the others in order", () => {
    expect(move(four, 3, 0)).toEqual(["stress_scenarios", "allocation_actions", "liquidity_commitments", "risk_exposure"]);
    expect(move(four, 0, 3)).toEqual(["liquidity_commitments", "risk_exposure", "stress_scenarios", "allocation_actions"]);
    expect(move(four, 2, 2)).toEqual(four);
  });

  it("every sequence of places and moves still leaves four different modules", () => {
    const pool = Object.keys(NAMES) as ModuleId[];
    let draft = [...four];
    for (let i = 0; i < 200; i++) {
      draft = i % 2 === 0 ? place(draft, i % 4, pool[(i * 5) % pool.length]!) : move(draft, i % 4, (i * 3) % 4);
      expect(draft).toHaveLength(4);
      expect(new Set(draft).size).toBe(4);
    }
  });
});

describe("the history fixture the module tests rely on", () => {
  it("matches the shape the server sends", () => {
    const h = history();
    for (const p of h.portfolios) expect(p.value).toHaveLength(h.dates.length);
  });
});
