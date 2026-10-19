import { fireEvent, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";
import type { PlanAnswers } from "../api/client";
import { CONFIG, SAVED, previewFor, strategiesFor } from "../test/planFixtures";
import { json, jsonBy, renderWithProviders, serve } from "../test/render";
import type { Route } from "../test/render";
import { PlanPage } from "./PlanPage";

type Call = { path: string; method: string; body?: string };
const SLOW = { timeout: 4000 };

function servePlan(extra: Record<string, Route> = {}) {
  return serve({
    "GET /api/plan/config": json(CONFIG),
    "POST /api/plan/preview": jsonBy<PlanAnswers>(previewFor),
    "POST /api/plan/strategies": jsonBy<PlanAnswers>(strategiesFor),
    "POST /api/plan/save": json(SAVED, 201),
    ...extra,
  });
}

const bodies = (calls: Call[], path: string) => calls.filter((c) => c.path === path).map((c) => JSON.parse(c.body ?? "null") as PlanAnswers);
const panel = () => screen.getByRole("complementary", { name: "Live read-out" });

async function next(user: ReturnType<typeof userEvent.setup>, label = "Continue") {
  const button = await screen.findByRole("button", { name: label });
  await waitFor(() => expect(button).toBeEnabled(), SLOW);
  await user.click(button);
}

/** Walk to the results with the form's defaults. */
async function toResults(user: ReturnType<typeof userEvent.setup>) {
  for (const label of ["Continue", "Continue", "Continue", "Continue", "See my strategies"]) await next(user, label);
  await screen.findByRole("heading", { name: /Three ways to run/ }, { timeout: 6000 });
}

afterEach(() => vi.unstubAllGlobals());

describe("the progress bar", () => {
  it("shows six steps as an ordered list, the first current, the rest locked until reached", async () => {
    servePlan();
    renderWithProviders(<PlanPage />, "/plan");
    const nav = await screen.findByRole("navigation", { name: "Plan progress" });
    const buttons = within(nav).getAllByRole("button");
    expect(buttons).toHaveLength(6);
    expect(buttons[0]).toHaveAttribute("aria-current", "step");
    expect(buttons[0]).toHaveAccessibleName("Step 1 of 6: About you");
    for (const locked of buttons.slice(1)) expect(locked).toBeDisabled();
    expect(within(nav).getByRole("list")).toBeInTheDocument();
  });

  it("shows a loading state and then the first question, and offers a retry if the questions cannot load", async () => {
    let calls = 0;
    serve({
      "GET /api/plan/config": () => (++calls === 1 ? new Response(JSON.stringify({ detail: "Down for a moment." }), { status: 503 }) : new Response(JSON.stringify(CONFIG))),
      "POST /api/plan/preview": jsonBy<PlanAnswers>(previewFor),
    });
    const user = userEvent.setup();
    renderWithProviders(<PlanPage />, "/plan");
    expect(await screen.findByRole("alert")).toHaveTextContent("Down for a moment.");
    await user.click(screen.getByRole("button", { name: "Try again" }));
    expect(await screen.findByRole("heading", { name: "Tell us about the family" })).toBeInTheDocument();
  });
});

describe("step 1: live read-out and validation", () => {
  it("keeps the old figure on screen while the new one loads, then updates", async () => {
    servePlan();
    const user = userEvent.setup();
    renderWithProviders(<PlanPage />, "/plan");
    await within(await screen.findByRole("complementary", { name: "Live read-out" })).findByText("₹100 Cr");

    const wealth = screen.getByLabelText(/total wealth/i);
    await user.clear(wealth);
    await user.type(wealth, "250");
    expect(within(panel()).getByText("Updating…")).toBeInTheDocument();
    expect(within(panel()).getByText("₹100 Cr")).toBeInTheDocument(); // still the previous answer, not a blank
    expect(await within(panel()).findByText("₹250 Cr", {}, SLOW)).toBeInTheDocument();
    expect(within(panel()).getByText("Up to date")).toBeInTheDocument();
  });

  it("explains a bad value at once, blocks Continue, and never sends it to the server", async () => {
    const calls = servePlan();
    const user = userEvent.setup();
    renderWithProviders(<PlanPage />, "/plan");
    await screen.findByRole("heading", { name: "Tell us about the family" });
    const wealth = screen.getByLabelText(/total wealth/i);
    await user.clear(wealth);
    await user.type(wealth, "0");
    expect(screen.getByText("Must be at least 1.")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Continue" })).toBeDisabled();
    await new Promise((r) => setTimeout(r, 700));
    expect(bodies(calls, "/api/plan/preview").map((b) => b.wealth)).not.toContain(0);

    await user.clear(wealth);
    await user.type(wealth, "1,25,000");
    expect(screen.getByRole("button", { name: "Continue" })).toBeEnabled();
  });

  it("will not accept an empty plan name", async () => {
    servePlan();
    const user = userEvent.setup();
    renderWithProviders(<PlanPage />, "/plan");
    const name = await screen.findByLabelText("What should we call this plan?");
    await user.clear(name);
    expect(screen.getByText("Give the plan a name.")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Continue" })).toBeDisabled();
  });

  it("moves keyboard focus to the new step's heading, but not when the page first opens", async () => {
    servePlan();
    const user = userEvent.setup();
    renderWithProviders(<PlanPage />, "/plan");
    const first = await screen.findByRole("heading", { name: "Tell us about the family" });
    expect(first).not.toHaveFocus();
    await next(user);
    const second = await screen.findByRole("heading", { name: "Anything big coming up?" });
    await waitFor(() => expect(second).toHaveFocus());
  });
});

describe("step 2: what's coming", () => {
  it("adds up to three commitments, removes them, and checks the years", async () => {
    const calls = servePlan();
    const user = userEvent.setup();
    renderWithProviders(<PlanPage />, "/plan");
    await next(user);
    expect(await screen.findByText(/Nothing planned/)).toBeInTheDocument();

    const add = screen.getByRole("button", { name: "Add a commitment" });
    await user.click(add);
    await user.click(add);
    await user.click(add);
    expect(screen.getAllByRole("listitem", { name: /Commitment \d/ })).toHaveLength(3);
    expect(add).toBeDisabled();
    expect(screen.getByText(/You can add up to 3/)).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "Remove commitment 3" }));
    await user.click(screen.getByRole("button", { name: "Remove commitment 2" }));
    expect(screen.getAllByRole("listitem", { name: /Commitment \d/ })).toHaveLength(1);
    expect(screen.getByRole("button", { name: "Add a commitment" })).toBeEnabled();

    const years = screen.getByLabelText("In how many years");
    await user.clear(years);
    await user.type(years, "40");
    expect(screen.getByText("Must be at most 25.")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Continue" })).toBeDisabled();
    await user.clear(years);
    await user.type(years, "2");
    await user.selectOptions(screen.getByLabelText("What"), "Wedding");
    await waitFor(() => expect(bodies(calls, "/api/plan/preview").some((b) => b.commitments.some((c) => c.kind === "Wedding" && c.year === 2))).toBe(true), SLOW);
    expect(screen.getByRole("button", { name: "Continue" })).toBeEnabled();
  });
});

describe("step 3: comfort and step 4: safety net", () => {
  it("shows what a bad year would cost in rupees, from the server, and the choice changes the read-out", async () => {
    servePlan();
    const user = userEvent.setup();
    renderWithProviders(<PlanPage />, "/plan");
    await next(user);
    await next(user);
    expect(await screen.findByRole("heading", { name: "How do you feel about a bad year?" })).toBeInTheDocument();
    expect(await screen.findByText(/a fall of up to ₹8\.0 Cr \(8%\)/, {}, SLOW)).toBeInTheDocument();
    expect(screen.getByText(/up to ₹25\.0 Cr \(25%\)/)).toBeInTheDocument();

    await user.click(screen.getByRole("radio", { name: /Grow as much as is sensible/ }));
    expect(screen.getByRole("radio", { name: /Grow as much as is sensible/ })).toBeChecked();
    expect(await within(panel()).findByText(/Comfort: Grow as much as is sensible/, {}, SLOW)).toBeInTheDocument();
  });

  it("sets the safety net with a slider or quick choices, and shows the need in rupees", async () => {
    servePlan();
    const user = userEvent.setup();
    renderWithProviders(<PlanPage />, "/plan");
    for (let i = 0; i < 3; i++) await next(user);
    expect(await screen.findByRole("heading", { name: "Your safety net" })).toBeInTheDocument();

    const slider = screen.getByRole("slider");
    expect(slider).toHaveAttribute("aria-valuetext", "12 months");
    fireEvent.change(slider, { target: { value: "24" } });
    expect(slider).toHaveAttribute("aria-valuetext", "24 months");
    expect(document.querySelector(".months-readout")).toHaveTextContent("24 months");
    expect(await screen.findByText(/Over 24 months the family needs about/, {}, SLOW)).toBeInTheDocument();
    expect(screen.getByRole("radio", { name: "24 months" })).toBeChecked();

    await user.click(screen.getByRole("radio", { name: "6 months" }));
    expect(screen.getByRole("slider")).toHaveAttribute("aria-valuetext", "6 months");
  });
});

describe("step 5: what the family owns", () => {
  async function toOwn(user: ReturnType<typeof userEvent.setup>) {
    for (let i = 0; i < 4; i++) await next(user);
    expect(await screen.findByRole("heading", { name: "What does the family own today?" })).toBeInTheDocument();
  }

  it("starts from a typical split and notes when the entered amounts add up to something else", async () => {
    servePlan();
    const user = userEvent.setup();
    renderWithProviders(<PlanPage />, "/plan");
    await toOwn(user);
    const large = await screen.findByRole("textbox", { name: /Large-cap index fund/ }, SLOW);
    expect(large).toHaveValue("20");
    expect(screen.getByText("Total ₹100.0 Cr")).toBeInTheDocument();

    await user.clear(large);
    await user.type(large, "220");
    expect(await screen.findByText(/These add up to ₹300\.0 Cr, so the plan uses that as the total \(you said ₹100\.0 Cr earlier\)/, {}, SLOW)).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Reset to a typical split" }));
    expect(screen.getByRole("textbox", { name: /Large-cap index fund/ })).toHaveValue("20");
  });

  it("blocks the last step while the read-out reports a problem, and lets it through once fixed", async () => {
    servePlan();
    const user = userEvent.setup();
    renderWithProviders(<PlanPage />, "/plan");
    await toOwn(user);
    const illiquid = await screen.findByRole("textbox", { name: /Property, business and other holdings/ }, SLOW);
    await user.clear(illiquid);
    await user.type(illiquid, "5000");
    expect(await within(panel()).findByText(/At least 5% of the wealth needs to be in things that can be sold/, {}, SLOW)).toBeInTheDocument();
    await waitFor(() => expect(screen.getByRole("button", { name: "See my strategies" })).toBeDisabled(), SLOW);

    await user.clear(illiquid);
    await user.type(illiquid, "30");
    await waitFor(() => expect(screen.getByRole("button", { name: "See my strategies" })).toBeEnabled(), SLOW);
  });
});

describe("the results", () => {
  it("shows a working state for the first calculation, then three strategies", async () => {
    servePlan({
      "POST /api/plan/strategies": async (init) => {
        await new Promise((r) => setTimeout(r, 400)); // the real first calculation takes a few seconds
        return jsonBy<PlanAnswers>(strategiesFor)(init);
      },
    });
    const user = userEvent.setup();
    renderWithProviders(<PlanPage />, "/plan");
    for (let i = 0; i < 4; i++) await next(user);
    await next(user, "See my strategies");
    expect(await screen.findByText(/The first calculation takes a few seconds/)).toBeInTheDocument();
    expect(screen.getByRole("status")).toHaveAttribute("aria-busy", "true");
    expect(await screen.findByRole("heading", { name: "Three ways to run ₹100 Cr" }, { timeout: 6000 })).toBeInTheDocument();
    expect(screen.getAllByRole("radio", { name: /Strategy [ABC]:/ })).toHaveLength(3);
  });

  it("marks the one that fits, says which are beyond the family's comfort, and states each fact in words", async () => {
    servePlan();
    const user = userEvent.setup();
    renderWithProviders(<PlanPage />, "/plan");
    await toResults(user);
    const cardB = screen.getByRole("radio", { name: /Strategy B: Balance/ }).closest("label") as HTMLElement;
    expect(within(cardB).getByText("Recommended for you")).toBeInTheDocument();
    expect(within(cardB).getByText("Within your comfort")).toBeInTheDocument();
    const cardC = screen.getByRole("radio", { name: /Strategy C: Grow/ }).closest("label") as HTMLElement;
    expect(within(cardC).getByText("Beyond your comfort")).toBeInTheDocument();
    expect(within(cardC).queryByText("Recommended for you")).not.toBeInTheDocument();
    for (const fact of ["Expected a year", "Worst year in the history", "In a severe market crash", "Safety net", "Meets your return goal"]) {
      expect(within(cardB).getByText(fact)).toBeInTheDocument();
    }
    expect(within(cardB).getByText(/typical year \(the middle 80% of years/)).toBeInTheDocument();
  });

  it("describes the year-by-year outcomes in words and as a table", async () => {
    servePlan();
    const user = userEvent.setup();
    renderWithProviders(<PlanPage />, "/plan");
    await toResults(user);
    const card = screen.getByRole("heading", { name: "How a year can turn out" }).closest("section") as HTMLElement;
    expect(within(card).getByRole("img")).toHaveAccessibleName(/Strategy A: a typical year between \+5\.1% and \+13\.3%, median \+7\.6%, worst −0\.1%/);
    await user.click(within(card).getByRole("radio", { name: "Table" }));
    expect(within(card).getByRole("row", { name: /A · Protect/ })).toHaveTextContent("+5.1% to +13.3%");
  });

  it("switching the comfort level is instant and asks the server for nothing", async () => {
    const calls = servePlan();
    const user = userEvent.setup();
    renderWithProviders(<PlanPage />, "/plan");
    await toResults(user);
    const before = calls.filter((c) => c.path === "/api/plan/strategies").length;
    await user.click(screen.getByRole("radio", { name: "C · Grow" }));
    const cardC = screen.getByRole("radio", { name: /Strategy C: Grow/ }).closest("label") as HTMLElement;
    expect(within(cardC).getByText("Recommended for you")).toBeInTheDocument();
    expect(within(cardC).getByText("Within your comfort")).toBeInTheDocument();
    await new Promise((r) => setTimeout(r, 900));
    expect(calls.filter((c) => c.path === "/api/plan/strategies")).toHaveLength(before);
  });

  it("recalculates when the safety net changes, keeping the old strategies on screen and marked as updating", async () => {
    const calls = servePlan();
    const user = userEvent.setup();
    renderWithProviders(<PlanPage />, "/plan");
    await toResults(user);
    const before = calls.filter((c) => c.path === "/api/plan/strategies").length;

    fireEvent.change(screen.getByRole("slider", { name: /Safety net/ }), { target: { value: "30" } });
    expect(screen.getAllByText("Updating…").length).toBeGreaterThan(0);
    expect(screen.getAllByRole("radio", { name: /Strategy [ABC]:/ })).toHaveLength(3); // nothing disappeared
    await waitFor(() => expect(calls.filter((c) => c.path === "/api/plan/strategies")).toHaveLength(before + 1), SLOW);
    expect(bodies(calls, "/api/plan/strategies").at(-1)?.months).toBe(30);
    await waitFor(() => expect(screen.getAllByText("Up to date").length).toBeGreaterThan(0), SLOW);
  });

  it("shows the detail of the strategy that is chosen: its donut, what to buy and why", async () => {
    servePlan();
    const user = userEvent.setup();
    renderWithProviders(<PlanPage />, "/plan");
    await toResults(user);
    expect(screen.getByText("Why Strategy B")).toBeInTheDocument();
    await user.click(screen.getByRole("radio", { name: /Strategy A: Protect/ }));
    expect(screen.getByText("Why Strategy A")).toBeInTheDocument();
    expect(screen.getByText("Reason two for strategy A.")).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Strategy A: your money afterwards" })).toBeInTheDocument();
  });

  it("names the kind of fund to buy or sell, never a product, and leaves the illiquid holdings alone", async () => {
    servePlan();
    const user = userEvent.setup();
    renderWithProviders(<PlanPage />, "/plan");
    await toResults(user);
    const card = screen.getByRole("heading", { name: "What to buy and sell" }).closest("section") as HTMLElement;
    expect(within(card).getByText("Large-cap index fund")).toBeInTheDocument();
    expect(within(card).getByText("Sell ₹15.0 Cr")).toBeInTheDocument();
    expect(within(card).getByText("Buy ₹20.0 Cr")).toBeInTheDocument();
    const illiquid = within(card).getByText("Property, business and other holdings").closest("li") as HTMLElement;
    expect(within(illiquid).getByText("Keep")).toBeInTheDocument();
    expect(within(card).getByText(/Kinds of product, not specific recommendations/)).toBeInTheDocument();
  });

  it("states its assumptions and limits, including the crash it uses", async () => {
    servePlan();
    const user = userEvent.setup();
    renderWithProviders(<PlanPage />, "/plan");
    await toResults(user);
    const card = screen.getByRole("heading", { name: "Assumptions and limits" }).closest("section") as HTMLElement;
    expect(within(card).getByText(/illustrative simulation on synthetic sample data, not investment advice/i)).toBeInTheDocument();
    expect(within(card).getByText(/not a replay of any real year/)).toBeInTheDocument();
    expect(within(card).getByText(/draft values, not externally validated/)).toBeInTheDocument();
    expect(card).not.toHaveTextContent("2020");
  });

  it("explains a failure to work out the strategies and recovers on retry", async () => {
    let calls = 0;
    servePlan({
      "POST /api/plan/strategies": (init) => (++calls === 1 ? new Response(JSON.stringify({ detail: "The allocation model is busy. Please try again in a minute." }), { status: 503 }) : jsonBy<PlanAnswers>(strategiesFor)(init)),
    });
    const user = userEvent.setup();
    renderWithProviders(<PlanPage />, "/plan");
    for (let i = 0; i < 4; i++) await next(user);
    await next(user, "See my strategies");
    const alert = await screen.findByRole("alert", {}, { timeout: 6000 });
    expect(alert).toHaveTextContent("The allocation model is busy");
    await user.click(within(alert).getByRole("button", { name: "Try again" }));
    expect(await screen.findByRole("heading", { name: /Three ways to run/ }, { timeout: 6000 })).toBeInTheDocument();
  });
});

describe("saving", () => {
  it("saves the chosen strategy and links to it, and a second click says it is already saved", async () => {
    let saves = 0;
    servePlan({ "POST /api/plan/save": () => new Response(JSON.stringify({ ...SAVED, created: ++saves === 1 }), { status: saves === 1 ? 201 : 200 }) });
    const user = userEvent.setup();
    renderWithProviders(<PlanPage />, "/plan");
    await toResults(user);
    await user.click(screen.getByRole("button", { name: "Save Strategy B to my profiles" }));
    const banner = await screen.findByText("Saved.");
    expect(banner.closest(".banner")).toHaveTextContent("My family · Strategy B");
    expect(screen.getByRole("link", { name: "See it on the overview" })).toHaveAttribute("href", "/?profile=42&basis=strict");

    await user.click(screen.getByRole("button", { name: "Save Strategy B to my profiles" }));
    expect(await screen.findByText("Already saved.")).toBeInTheDocument();
  });

  it("saves the strategy that is selected, not just the recommended one", async () => {
    const calls = servePlan();
    const user = userEvent.setup();
    renderWithProviders(<PlanPage />, "/plan");
    await toResults(user);
    await user.click(screen.getByRole("radio", { name: /Strategy C: Grow/ }));
    await user.click(screen.getByRole("button", { name: "Save Strategy C to my profiles" }));
    await screen.findByText("Saved.");
    expect(JSON.parse(calls.find((c) => c.path === "/api/plan/save")?.body ?? "{}").strategy).toBe("Grow");
  });

  it("shows a failure to save as an alert and does not claim success", async () => {
    servePlan({ "POST /api/plan/save": () => new Response(JSON.stringify({ detail: "An account can hold at most 25 profiles." }), { status: 409 }) });
    const user = userEvent.setup();
    renderWithProviders(<PlanPage />, "/plan");
    await toResults(user);
    await user.click(screen.getByRole("button", { name: "Save Strategy B to my profiles" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("at most 25 profiles");
    expect(screen.queryByText("Saved.")).not.toBeInTheDocument();
  });
});

describe("editing earlier answers and starting over", () => {
  it("lists every answer with an Edit button that jumps to its step and comes straight back", async () => {
    servePlan();
    const user = userEvent.setup();
    renderWithProviders(<PlanPage />, "/plan");
    await toResults(user);
    const review = screen.getByRole("heading", { name: "Your answers" }).closest("section") as HTMLElement;
    for (const label of ["plan name", "total wealth", "yearly spending", "upcoming commitments", "comfort with a bad year", "safety net", "what the family owns"]) {
      expect(within(review).getByRole("button", { name: `Edit ${label}` })).toBeInTheDocument();
    }
    expect(within(review).getByText("Nothing planned")).toBeInTheDocument();

    await user.click(within(review).getByRole("button", { name: "Edit comfort with a bad year" }));
    expect(await screen.findByRole("heading", { name: "How do you feel about a bad year?" })).toBeInTheDocument();
    await user.click(screen.getByRole("radio", { name: /Protect what we have/ }));
    await user.click(screen.getByRole("button", { name: "Back to my strategies" }));
    expect(await screen.findByRole("heading", { name: /Three ways to run/ }, SLOW)).toBeInTheDocument();
    const cardA = screen.getByRole("radio", { name: /Strategy A: Protect/ }).closest("label") as HTMLElement;
    expect(within(cardA).getByText("Recommended for you")).toBeInTheDocument();
  });

  it("lets a person jump to any step already reached from the progress bar", async () => {
    servePlan();
    const user = userEvent.setup();
    renderWithProviders(<PlanPage />, "/plan");
    await toResults(user);
    await user.click(screen.getByRole("button", { name: /Step 2 of 6/ }));
    expect(await screen.findByRole("heading", { name: "Anything big coming up?" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Step 6 of 6/ })).toBeEnabled();
  });

  it("starts over from the defaults and forgets the draft", async () => {
    servePlan();
    const user = userEvent.setup();
    renderWithProviders(<PlanPage />, "/plan");
    const name = await screen.findByLabelText("What should we call this plan?");
    await user.clear(name);
    await user.type(name, "Sharma family");
    await next(user);
    await user.click(await screen.findByRole("button", { name: "Start over" }));
    expect(await screen.findByRole("heading", { name: "Tell us about the family" })).toBeInTheDocument();
    expect(screen.getByLabelText("What should we call this plan?")).toHaveValue("My family");
    expect(screen.queryByRole("button", { name: "Start over" })).not.toBeInTheDocument();
    expect(window.sessionStorage.getItem("foi.plan.draft")).toContain("My family");
  });
});

describe("the draft survives a reload", () => {
  it("resumes at the step the person had reached, with their answers", async () => {
    servePlan();
    const user = userEvent.setup();
    const first = renderWithProviders(<PlanPage />, "/plan");
    const name = await screen.findByLabelText("What should we call this plan?");
    await user.clear(name);
    await user.type(name, "Sharma family");
    await next(user);
    await screen.findByRole("heading", { name: "Anything big coming up?" });
    first.unmount();

    servePlan();
    renderWithProviders(<PlanPage />, "/plan");
    expect(await screen.findByRole("heading", { name: "Anything big coming up?" })).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Back" }));
    expect(await screen.findByLabelText("What should we call this plan?")).toHaveValue("Sharma family");
  });

  it("cannot be jumped past by editing the address to a step not yet reached", async () => {
    servePlan();
    renderWithProviders(<PlanPage />, "/plan?step=6");
    expect(await screen.findByRole("heading", { name: "Tell us about the family" })).toBeInTheDocument();
  });
});

describe("when the live read-out fails", () => {
  it("says so quietly and does not stop the person carrying on", async () => {
    servePlan({ "POST /api/plan/preview": () => new Response(JSON.stringify({ detail: "Down." }), { status: 500 }) });
    const user = userEvent.setup();
    renderWithProviders(<PlanPage />, "/plan");
    expect(await within(await screen.findByRole("complementary", { name: "Live read-out" })).findByText(/could not be loaded/i, {}, SLOW)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Continue" })).toBeEnabled();
    await user.click(screen.getByRole("button", { name: "Continue" }));
    expect(await screen.findByRole("heading", { name: "Anything big coming up?" })).toBeInTheDocument();
  });
});
