import { screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";
import App from "./App";
import type { Analysis, PlanAnswers } from "./api/client";
import { analysis, META, portfolio, session } from "./test/fixtures";
import { json, jsonBy, renderWithProviders, serve } from "./test/render";
import { CONFIG, previewFor } from "./test/planFixtures";
import { appRoutes, PROFILES } from "./test/phase4Fixtures";

function signedIn(data: Analysis = analysis()) {
  return serve(appRoutes(data));
}

afterEach(() => vi.unstubAllGlobals());

describe("signed out", () => {
  it("shows the sign-in screen with the four demo families and the synthetic-data warning", async () => {
    serve({ "GET /api/auth/me": json({ detail: "Please sign in." }, 401), "GET /api/meta": json(META) });
    renderWithProviders(<App />);
    expect(await screen.findByRole("button", { name: "Log in" })).toBeInTheDocument();
    for (const label of ["Legacy-conservative family", "Business-heavy family", "Next-gen growth family", "₹1,000 Cr liquidity-gap example"]) {
      expect(await screen.findByRole("button", { name: label })).toBeInTheDocument();
    }
    expect(screen.getByText(/synthetic data only/i)).toBeInTheDocument();
  });

  it("opens a demo family, defaults to the stricter cover and shows the figures", async () => {
    serve({
      ...appRoutes(),
      "GET /api/auth/me": json({ detail: "Please sign in." }, 401),
      "POST /api/auth/demo": json(session),
    });
    const user = userEvent.setup();
    renderWithProviders(<App />);
    await user.click(await screen.findByRole("button", { name: /liquidity-gap example/ }));
    expect(await screen.findByRole("heading", { name: "Welcome to the demo" })).toBeInTheDocument();
    await waitFor(() => expect(screen.getByRole("combobox", { name: /towards the safety net/i })).toHaveValue("strict"));
    expect(await screen.findByText("8.8%")).toBeInTheDocument(); // 8.75% rounds half up
    expect(screen.getByRole("alert")).toHaveTextContent("0.4x"); // the slide's liquidity gap is flagged at once
    expect(screen.getAllByText(/Illustrative simulation, not investment advice/).length).toBeGreaterThan(0);
  });

  it("keeps the log-in button disabled until both fields are filled and shows server errors", async () => {
    serve({
      "GET /api/auth/me": json({ detail: "Please sign in." }, 401),
      "GET /api/meta": json(META),
      "POST /api/auth/login": json({ detail: "Wrong username or password.", problems: null }, 401),
    });
    const user = userEvent.setup();
    renderWithProviders(<App />);
    const button = await screen.findByRole("button", { name: "Log in" }); // the tabs have role "tab", so this is the submit
    expect(button).toBeDisabled();
    await user.type(screen.getByLabelText("Username"), "asha");
    await user.type(screen.getByLabelText("Password"), "not-the-password");
    expect(button).toBeEnabled();
    await user.click(button);
    expect(await screen.findByRole("alert")).toHaveTextContent("Wrong username or password.");
  });
});

describe("server unreachable", () => {
  it("says so instead of showing a blank page, and offers a retry", async () => {
    vi.stubGlobal("fetch", () => Promise.reject(new TypeError("fetch failed")));
    renderWithProviders(<App />);
    expect(await screen.findByRole("alert")).toHaveTextContent(/Can't reach the server/);
    expect(screen.getByRole("button", { name: "Try again" })).toBeInTheDocument();
  });
});

describe("overview", () => {
  it("shows a loading state first, then the analysis", async () => {
    signedIn();
    renderWithProviders(<App />);
    expect(await screen.findByRole("status")).toBeInTheDocument();
    expect(await screen.findByText("8.8%")).toBeInTheDocument();
  });

  it("explains an analysis failure and lets the person retry", async () => {
    serve({
      "GET /api/auth/me": json(session),
      "GET /api/meta": json(META),
      "GET /api/profiles": json(PROFILES),
      "GET /api/profiles/1/analysis": json({ detail: "This profile can't be analysed yet: limits.", problems: null }, 422),
    });
    renderWithProviders(<App />);
    expect(await screen.findByRole("alert")).toHaveTextContent("This profile can't be analysed yet");
    expect(screen.getByRole("button", { name: "Try again" })).toBeInTheDocument();
  });

  it("warns loudly when the optimiser did not converge, naming the portfolio", async () => {
    const data = analysis();
    data.options[2] = { ...data.options[2]!, portfolio: portfolio("Defensive", { optimiser_converged: false }) };
    signedIn(data);
    renderWithProviders(<App />);
    const banner = await screen.findByText(/did not report a clean solution/);
    expect(banner).toHaveTextContent("Defensive");
    expect(banner).toHaveTextContent(/approximate/);
  });

  it("shows no alert when nothing needs attention", async () => {
    signedIn(analysis({ current: portfolio("Current", { lam_base: null, lam_used: null }) }));
    renderWithProviders(<App />);
    await screen.findByText("8.8%");
    expect(screen.queryByRole("alert")).not.toBeInTheDocument();
  });

  it("switches between the current mix and the recommendations", async () => {
    const user = userEvent.setup();
    signedIn();
    renderWithProviders(<App />);
    expect(await screen.findByText("Balanced mix")).toBeInTheDocument(); // the default choice
    await user.click(screen.getByRole("radio", { name: "Current" }));
    expect(screen.getByText("Where you are now")).toBeInTheDocument();
    expect(screen.getByText("Your current mix")).toBeInTheDocument();
    await user.click(screen.getByRole("radio", { name: "Growth" }));
    expect(screen.getByText("Growth mix")).toBeInTheDocument();
    expect(screen.getByText("What to buy and sell")).toBeInTheDocument();
  });

  it("lists what to buy and what to sell, with words as well as colour", async () => {
    signedIn();
    renderWithProviders(<App />);
    const card = (await screen.findByText("What to buy and sell")).closest("section") as HTMLElement;
    expect(within(card).getByText("Buy ₹510.0 Cr")).toBeInTheDocument();
    expect(within(card).getByText("Sell ₹510.0 Cr")).toBeInTheDocument();
    expect(within(card).getAllByText("Sell").length).toBe(2);
    expect(within(card).getByText("−₹490.0 Cr")).toBeInTheDocument();
  });

  it("names the cover basis in force on the dashboard", async () => {
    signedIn();
    renderWithProviders(<App />);
    expect(await screen.findByText(/Cover basis in force: Cash, debt and gold only/)).toBeInTheDocument();
  });

  it("flags the liquidity shortfall in the scenario comparison on the Scenarios page", async () => {
    const user = userEvent.setup();
    signedIn();
    renderWithProviders(<App />, "/scenarios");
    const card = (await screen.findByRole("heading", { name: /Compare your options under one scenario/ })).closest("section") as HTMLElement;
    const chart = await within(card).findByRole("img", { name: /Under "Equities fall 25%"/ });
    expect(chart).toHaveAccessibleName(/Current .*safety net short at 0\.4x/);
    await user.click(within(card).getAllByRole("radio", { name: "Table" })[0]!);
    const row = within(card).getByRole("row", { name: /Current/ });
    expect(row).toHaveTextContent("0.4x");
    expect(row).toHaveTextContent("Short");
  });

  it("labels the illiquid holding as fixed", async () => {
    signedIn();
    renderWithProviders(<App />);
    expect((await screen.findAllByText("Illiquid (fixed)")).length).toBeGreaterThan(0);
  });

  it("opens the explanation behind a number and closes it with Escape", async () => {
    const user = userEvent.setup();
    signedIn();
    renderWithProviders(<App />);
    await user.click(await screen.findByRole("button", { name: "About Liquidity cover" }));
    const panel = await screen.findByRole("dialog", { name: "Liquidity cover" });
    expect(within(panel).getByText(/never limits the optimiser/)).toBeInTheDocument();
    await user.keyboard("{Escape}");
    await waitFor(() => expect(screen.queryByRole("dialog")).not.toBeInTheDocument());
  });

  it("keeps the chosen profile and basis in the address, so a reload or shared link keeps your place", async () => {
    signedIn();
    renderWithProviders(<App />, "/?profile=1&basis=all");
    await screen.findByText("8.8%");
    expect(screen.getByRole("combobox", { name: /towards the safety net/i })).toHaveValue("all");
  });
});

describe("where a person lands after signing in", () => {
  const asha = { ...session, user: { id: 9, username: "asha", is_demo: false } };
  const routes = (extra: Record<string, () => Response> = {}) =>
    serve({
      "GET /api/auth/me": json({ detail: "Please sign in." }, 401),
      "GET /api/meta": json(META),
      "GET /api/profiles": json(PROFILES),
      "GET /api/profiles/1/analysis": json(analysis()),
      "GET /api/plan/config": json(CONFIG),
      "POST /api/plan/preview": jsonBy<PlanAnswers>(previewFor),
      "POST /api/auth/signup": json(asha, 201),
      "POST /api/auth/login": json(asha),
      ...extra,
    });

  it("a brand-new account lands on the guided plan, as in the Streamlit app", async () => {
    routes();
    const user = userEvent.setup();
    renderWithProviders(<App />);
    await user.click(await screen.findByRole("tab", { name: "Create account" }));
    await user.type(screen.getByLabelText("Choose a username"), "asha");
    await user.type(screen.getByLabelText("Choose a password"), "a long enough pass");
    await user.click(screen.getByRole("button", { name: "Create account" }));
    expect(await screen.findByRole("heading", { name: "Plan my money" })).toBeInTheDocument();
    expect(await screen.findByRole("heading", { name: "Tell us about the family" })).toBeInTheDocument();
    await waitFor(() => expect(window.sessionStorage.getItem("foi.fresh-signup")).toBeNull()); // used up
  });

  it("an existing account that logs in lands on the overview, not the plan", async () => {
    routes();
    const user = userEvent.setup();
    renderWithProviders(<App />);
    await user.type(await screen.findByLabelText("Username"), "asha");
    await user.type(screen.getByLabelText("Password"), "a long enough pass");
    await user.click(screen.getByRole("button", { name: "Log in" }));
    expect(await screen.findByRole("heading", { name: "Welcome back, asha" })).toBeInTheDocument();
    expect(screen.queryByRole("heading", { name: "Plan my money" })).not.toBeInTheDocument();
  });

  it("a demo family still opens on the overview", async () => {
    routes({ "POST /api/auth/demo": json(session) });
    const user = userEvent.setup();
    renderWithProviders(<App />);
    await user.click(await screen.findByRole("button", { name: /liquidity-gap example/ }));
    expect(await screen.findByRole("heading", { name: "Welcome to the demo" })).toBeInTheDocument();
  });
});
