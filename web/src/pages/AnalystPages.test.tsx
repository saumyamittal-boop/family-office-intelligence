import { fireEvent, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";
import App from "../App";
import type { ScenarioRequest } from "../api/client";
import { analysis, LADDER, portfolio } from "../test/fixtures";
import { appRoutes } from "../test/phase4Fixtures";
import { json, renderWithProviders, serve } from "../test/render";

afterEach(() => vi.unstubAllGlobals());

async function openPage(path: string, routes = appRoutes()) {
  const calls = serve(routes);
  renderWithProviders(<App />, path);
  await screen.findByRole("region", { name: "Needs your attention" }); // the fixture family has a shortfall, so the page is ready
  return calls;
}

const card = (title: string | RegExp) => within(screen.getByRole("heading", { name: title }).closest("section") as HTMLElement);
/** For cards that wait on their own data (the history), which arrives after the page is ready. */
const laterCard = async (title: string | RegExp) => within((await screen.findByRole("heading", { name: title })).closest("section") as HTMLElement);

describe("Recommendation page", () => {
  it("shows the mix, the moves, the projection, the reasons and the limits", async () => {
    await openPage("/recommendation");
    expect(screen.getByRole("heading", { level: 1, name: "Recommendation" })).toBeInTheDocument();
    for (const title of [
      "Balanced mix", "What to buy and sell", "The mixes side by side", "How the corpus could grow", "Where each mix ends up",
      "Why the Balanced mix", "What stands out", "How this was worked out, and its limits",
    ]) {
      expect(screen.getByRole("heading", { name: title })).toBeInTheDocument();
    }
  });

  it("puts the current mix and the three recommendations side by side, class by class, with illiquid marked fixed", async () => {
    await openPage("/recommendation");
    const table = within(card("The mixes side by side").getByRole("table", { name: /Share of the corpus in each asset class/ }));
    expect(table.getAllByRole("columnheader").map((h) => h.textContent)).toEqual(["Asset class", "Current", "Growth", "Balanced", "Defensive"]);
    expect(table.getByRole("row", { name: /Illiquid \(held fixed\).*40\.0%/ })).toBeInTheDocument();
    expect(table.getByRole("row", { name: /Large-cap equity.*13\.8%/ })).toBeInTheDocument();
  });

  it("compares return, risk, drawdown and liquidity across the current mix and the options, with yes and no in words", async () => {
    await openPage("/recommendation");
    const table = within(card("Compare with your current mix").getByRole("table"));
    expect(table.getAllByRole("columnheader").map((h) => h.textContent)).toEqual(["Measure", "Current", "Growth", "Balanced", "Defensive"]);
    expect(table.getByRole("row", { name: /^Expected return 8\.8% 8\.8% 8\.8% 8\.8%$/ })).toBeInTheDocument(); // 8.75% rounds half up
    expect(table.getByRole("row", { name: /^Within your drawdown limit Yes Yes Yes Yes$/ })).toBeInTheDocument();
    expect(table.getByRole("row", { name: /^Safety net counted \/ needed ₹50 Cr \/ ₹120 Cr ₹386 Cr \/ ₹120 Cr/ })).toBeInTheDocument();
    expect(table.getByRole("row", { name: /^95% 1-month CVaR 4\.3%/ })).toBeInTheDocument();
  });

  it("says where each mix ends up, in nominal and today's rupees", async () => {
    await openPage("/recommendation");
    const table = within(card("Where each mix ends up").getByRole("table"));
    expect(table.getAllByRole("row")).toHaveLength(5); // header + current + three options
    const balanced = table.getByRole("row", { name: /Balanced/ });
    expect(balanced).toHaveTextContent("₹1,274 Cr"); // 1000 * 1.084^3
    expect(balanced).toHaveTextContent("₹1,116 Cr"); // the same in today's rupees at 4.5% inflation
  });

  it("states the assumptions and limits in plain words", async () => {
    await openPage("/recommendation");
    const limits = card("How this was worked out, and its limits");
    expect(limits.getByText(/4\.5% a year/)).toBeInTheDocument();
    expect(limits.getByText(/large-cap equity 11\.0%/)).toBeInTheDocument();
    expect(limits.getByText(/held fixed and never traded/)).toBeInTheDocument();
    expect(limits.getByText(/Growth 75%, Balanced 50%, Defensive 25% of the way from the safest mix/)).toBeInTheDocument();
    expect(limits.getByText(/target real return is reported, not enforced/)).toBeInTheDocument();
    expect(limits.getByText(/risk is tightened until it fits/)).toBeInTheDocument();
    expect(limits.getByText(/synthetic sample data.*not forecasts and not investment advice/)).toBeInTheDocument();
  });

  it("explains the Balanced recommendation when the current mix is selected", async () => {
    await openPage("/recommendation?mix=Current");
    expect(screen.getByText("You are looking at your current mix, so this explains the Balanced recommendation.")).toBeInTheDocument();
    expect(screen.getByText("Where you are now")).toBeInTheDocument();
  });

  it("calls out a recommendation the optimiser could not solve cleanly", async () => {
    const data = analysis();
    data.options[0] = { ...data.options[0]!, portfolio: portfolio("Growth", { optimiser_converged: false }) };
    await openPage("/recommendation", appRoutes(data));
    const limits = card("How this was worked out, and its limits");
    expect(limits.getByRole("alert")).toHaveTextContent(/Growth.*approximate/);
  });
});

describe("Risk and liquidity page", () => {
  it("shows the risk figures, the drawdown against the person's limit, the ladder, outflows and the history", async () => {
    const calls = await openPage("/risk");
    expect(screen.getByRole("heading", { level: 1, name: "Risk and liquidity" })).toBeInTheDocument();
    expect(screen.getByText("95% 1-month CVaR")).toBeInTheDocument();
    const drawdown = await laterCard("Drawdown against your limit");
    expect(await drawdown.findByRole("img", { name: /Balanced: the worst fall from a previous peak was 7\.4%.*Your limit is 15%, so this is within it/ })).toBeInTheDocument();
    expect(card("Liquidity ladder").getByRole("img", { name: /over 4 years the liquid assets go from ₹350 Cr in year 1/ })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Upcoming outflows" })).toBeInTheDocument();
    expect(await screen.findByRole("heading", { name: "Value of 100 invested" })).toBeInTheDocument();
    expect(calls.some((c) => c.path.startsWith("/api/profiles/1/history?basis=strict"))).toBe(true); // the cover basis in force travels with it
  });

  it("describes calendar years, marks a part year, and shows the typical-year range", async () => {
    await openPage("/risk");
    const years = await screen.findByRole("heading", { name: "Calendar-year returns" });
    const frame = within(years.closest("section") as HTMLElement);
    expect(frame.getByRole("img")).toHaveAccessibleName(/1 of 4 calendar years lost money.*best was 2017 at \+11\.0%.*worst was 2018 at −4\.0%/);
    expect(frame.getByText(/A \* marks a year with only part of its days/)).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "A typical year" })).toBeInTheDocument();
    expect(screen.getByText("Middle 80% of years")).toBeInTheDocument();
  });

  it("offers every chart as a table too, with the same year-end figures", async () => {
    const user = userEvent.setup();
    await openPage("/risk");
    const frame = await laterCard("Value of 100 invested");
    await user.click(frame.getByRole("radio", { name: "Table" }));
    const table = within(frame.getByRole("table", { name: /Value of 100 invested, at the end of each year/ }));
    expect(table.getAllByRole("row")).toHaveLength(6); // header + the years 2015 (base day) to 2019 in the fixture
    expect(table.getByRole("columnheader", { name: "Current" })).toBeInTheDocument();
  });

  it("plots every mix when the current mix is selected, and only the pair when a recommendation is", async () => {
    await openPage("/risk?mix=Current");
    const all = await screen.findByRole("img", { name: /Growth of 100 invested on 2015-12-31/ });
    for (const label of ["Current", "Growth", "Balanced", "Defensive"]) expect(all).toHaveAccessibleName(new RegExp(`${label} ends at`));
  });

  it("only compares the current mix with the one chosen", async () => {
    await openPage("/risk?mix=Defensive");
    const pair = await screen.findByRole("img", { name: /Growth of 100 invested on 2015-12-31/ });
    expect(pair).toHaveAccessibleName(/Current ends at.*Defensive ends at/);
    expect(pair).not.toHaveAccessibleName(/Growth ends at/);
  });

  it("warns, as an alert, when the liquid assets run out before the end of the ladder", async () => {
    const data = analysis();
    data.options[1] = { ...data.options[1]!, ladder: LADDER.map((r, i) => (i >= 2 ? { ...r, liquid_value_cr: -40 } : r)) };
    await openPage("/risk", appRoutes(data));
    const banner = card("Liquidity ladder").getByRole("img", { name: /They run out in year 3/ });
    expect(banner).toBeInTheDocument();
    expect(screen.getAllByRole("alert").some((a) => /spent by year 3/.test(a.textContent ?? ""))).toBe(true);
  });

  it("says what failed if the history cannot be fetched, and keeps the rest of the page", async () => {
    await openPage("/risk", appRoutes(analysis(), { "GET /api/profiles/1/history": json({ detail: "The model is busy.", problems: null }, 503) }));
    expect((await screen.findAllByText("The drawdown history could not be loaded")).length).toBeGreaterThan(0);
    expect(screen.getAllByText("The model is busy.").length).toBeGreaterThan(0);
    expect(screen.getByRole("heading", { name: "Liquidity ladder" })).toBeInTheDocument();
  });
});

describe("Scenarios page", () => {
  const bodies = (calls: ReturnType<typeof serve>): ScenarioRequest[] =>
    calls.filter((c) => c.method === "POST" && c.path === "/api/profiles/1/scenarios").map((c) => JSON.parse(c.body!) as ScenarioRequest);
  const lastCustom = (calls: ReturnType<typeof serve>) => bodies(calls).filter((b) => b.custom).at(-1)!;
  const lastPreset = (calls: ReturnType<typeof serve>) => bodies(calls).filter((b) => b.preset).at(-1)!;

  it("shows the five built-in scenarios for the chosen mix, each with plain yes/no checks", async () => {
    await openPage("/scenarios?mix=Growth");
    expect(screen.getByRole("heading", { level: 1, name: "Scenarios" })).toBeInTheDocument();
    const market = within(screen.getByRole("article", { name: "Market crash" }));
    expect(market.getByText("Equities fall sharply and illiquid assets are marked down.")).toBeInTheDocument();
    expect(market.getByText("−13.8%")).toBeInTheDocument();
    expect(market.getByText(/Within drawdown limit/)).toBeInTheDocument();
    const expense = within(screen.getByRole("article", { name: "Large unexpected expense" }));
    expect(expense.getByText(/Safety net 0\.8x/)).toBeInTheDocument();
    expect(expense.getByText(/Real corpus 1\.10x/)).toBeInTheDocument();
    // a scenario with no immediate hit leads with purchasing power instead
    expect(within(screen.getByRole("article", { name: "Lost decade" })).getByText("real corpus at the horizon")).toBeInTheDocument();
  });

  it("lays out exactly what each built-in scenario assumes", async () => {
    const user = userEvent.setup();
    await openPage("/scenarios");
    await user.click(screen.getByText("What each built-in scenario assumes"));
    const table = within(screen.getByRole("table", { name: "Shocks applied by each built-in scenario" }));
    const crash = table.getByRole("row", { name: /Market crash/ });
    expect(crash).toHaveTextContent("−35%"); // large-cap
    expect(crash).toHaveTextContent("−45%"); // mid-cap
    expect(crash).toHaveTextContent("−20%"); // illiquid
    expect(table.getByRole("row", { name: /Lost decade/ })).toHaveTextContent("4 pts a year");
    expect(table.getByRole("row", { name: /Large unexpected expense/ })).toHaveTextContent("8% of corpus");
  });

  it("starts the dials at the stated defaults and reads each one out in words", async () => {
    await openPage("/scenarios");
    const lab = card("Build your own scenario");
    const dial = (name: RegExp) => lab.getByRole("slider", { name }) as HTMLInputElement;
    expect(dial(/Equity shock/)).toHaveAttribute("aria-valuetext", "−25%");
    expect(dial(/Equity shock/)).toHaveAttribute("min", "-60");
    expect(dial(/Equity shock/)).toHaveAttribute("max", "20");
    expect(dial(/Gold shock/)).toHaveAttribute("aria-valuetext", "+5%");
    expect(dial(/One-off expense/)).toHaveAttribute("aria-valuetext", "5%");
    expect(dial(/Return drag/)).toHaveAttribute("aria-valuetext", "0 pts");
    expect(dial(/Return drag/)).toHaveAttribute("step", "0.5");
  });

  it("sends the dials to the server as fractions, after a pause, and shows the result for the chosen mix", async () => {
    const calls = await openPage("/scenarios?mix=Balanced");
    const lab = card("Build your own scenario");
    await waitFor(() => expect(bodies(calls).some((b) => b.custom)).toBe(true)); // the defaults, on arrival
    expect(lastCustom(calls)).toEqual({
      basis: "strict",
      custom: { equity_shock: -0.25, debt_shock: -0.03, gold_shock: 0.05, illiquid_markdown: -0.1, one_off_expense: 0.05, return_drag: 0 },
    });
    const before = calls.length;

    fireEvent.change(lab.getByRole("slider", { name: /Equity shock/ }), { target: { value: "-50" } });
    fireEvent.change(lab.getByRole("slider", { name: /Return drag/ }), { target: { value: "1.5" } });
    expect(calls.length).toBe(before); // nothing sent while the dials are still moving
    await waitFor(() => expect(calls.length).toBeGreaterThan(before));
    expect(lastCustom(calls).custom).toMatchObject({ equity_shock: -0.5, return_drag: 0.015 });
    expect(await lab.findByRole("article", { name: "Your scenario on the Balanced mix" })).toBeInTheDocument();
  });

  it("keeps the last result on screen, dimmed, while the next one is worked out", async () => {
    let release: (() => void) | undefined;
    const gate = new Promise<void>((resolve) => (release = resolve));
    const routes = appRoutes();
    const original = routes["POST /api/profiles/1/scenarios"]!;
    let held = false;
    routes["POST /api/profiles/1/scenarios"] = async (init) => {
      const request = JSON.parse(String(init?.body)) as ScenarioRequest;
      if (request.custom?.equity_shock === -0.5) {
        held = true;
        await gate;
      }
      return original(init);
    };
    await openPage("/scenarios", routes);
    const lab = card("Build your own scenario");
    await lab.findByRole("article", { name: "Your scenario on the Balanced mix" });
    fireEvent.change(lab.getByRole("slider", { name: /Equity shock/ }), { target: { value: "-50" } });
    await waitFor(() => expect(held).toBe(true));
    expect(lab.getByRole("article", { name: "Your scenario on the Balanced mix" })).toBeInTheDocument(); // still there
    expect(await lab.findByText("Updating…")).toBeInTheDocument();
    release?.();
    await waitFor(() => expect(lab.queryByText("Updating…")).not.toBeInTheDocument());
  });

  it("compares every option under any one scenario, built-in or the person's own", async () => {
    const user = userEvent.setup();
    const calls = await openPage("/scenarios");
    const compare = card("Compare your options under one scenario");
    await user.click(compare.getByRole("radio", { name: "Market crash" }));
    expect(await compare.findByRole("img", { name: /Under "Market crash"/ })).toBeInTheDocument();
    expect(lastPreset(calls)).toEqual({ basis: "strict", preset: "Market crash" });
    await user.click(compare.getByRole("radio", { name: "Your scenario" }));
    expect(await compare.findByRole("img", { name: /Under "Your scenario"/ })).toBeInTheDocument();
    expect(bodies(calls).some((b) => b.custom)).toBe(true); // asked with the dials, not a built-in name
    expect(compare.getByText("Compared under Your scenario.")).toBeInTheDocument();
  });

  it("lists every result for the chosen mix in a table", async () => {
    await openPage("/scenarios?mix=Defensive");
    const table = within(card("All results").getByRole("table"));
    expect(table.getAllByRole("row")).toHaveLength(7); // header + baseline + five
    expect(table.getByRole("row", { name: /Baseline/ })).toBeInTheDocument();
    expect(table.getByRole("row", { name: /Large unexpected expense/ })).toHaveTextContent("(short)");
  });

  it("explains a refused scenario and lets the person retry", async () => {
    let fail = true;
    const routes = appRoutes();
    const working = routes["POST /api/profiles/1/scenarios"]!;
    routes["POST /api/profiles/1/scenarios"] = (init) =>
      fail ? new Response(JSON.stringify({ detail: "This profile can't be analysed yet.", problems: null }), { status: 422 }) : working(init);
    const user = userEvent.setup();
    await openPage("/scenarios", routes);
    const lab = card("Build your own scenario");
    expect(await lab.findByText("Couldn't run this scenario")).toBeInTheDocument();
    expect(lab.getByText("This profile can't be analysed yet.")).toBeInTheDocument();
    fail = false;
    await user.click(lab.getByRole("button", { name: "Try again" }));
    expect(await lab.findByRole("article", { name: "Your scenario on the Balanced mix" })).toBeInTheDocument();
    expect(lab.queryByText("Couldn't run this scenario")).not.toBeInTheDocument();
  });
});
