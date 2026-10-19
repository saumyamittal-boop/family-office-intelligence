import { screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";
import App from "./App";
import type { Analysis } from "./api/client";
import { analysis, META, portfolio, session } from "./test/fixtures";
import { json, renderWithProviders, serve } from "./test/render";

const PROFILES = [{ id: 1, name: "Gap family", corpus_cr: 1000 }];

function signedIn(data: Analysis = analysis()) {
  return serve({
    "GET /api/auth/me": json(session),
    "GET /api/meta": json(META),
    "GET /api/profiles": json(PROFILES),
    "GET /api/profiles/1/analysis": json(data),
  });
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
      "GET /api/auth/me": json({ detail: "Please sign in." }, 401),
      "GET /api/meta": json(META),
      "POST /api/auth/demo": json(session),
      "GET /api/profiles": json(PROFILES),
      "GET /api/profiles/1/analysis": json(analysis()),
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
    expect(await screen.findByText("Why the Balanced mix")).toBeInTheDocument();
    await user.click(screen.getByRole("radio", { name: "Current" }));
    expect(screen.getByText("Where you are now")).toBeInTheDocument();
    await user.click(screen.getByRole("radio", { name: "Growth" }));
    expect(screen.getByText("Reason one for the Growth mix.")).toBeInTheDocument();
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

  it("flags the liquidity shortfall in the comparison and names the basis in force", async () => {
    const user = userEvent.setup();
    signedIn();
    renderWithProviders(<App />);
    const card = (await screen.findByRole("heading", { name: /Compare your options/ })).closest("section") as HTMLElement;
    // The visible text joins "−₹" and "137.5 Cr" with invisible characters so it cannot wrap mid-amount.
    expect(within(card).getByText(/Current −⁠?₹137\.5\sCr/)).toBeInTheDocument();
    await user.click(within(card).getByRole("radio", { name: "Table" }));
    const row = within(card).getByRole("row", { name: /Current/ });
    expect(row).toHaveTextContent("0.4x");
    expect(row).toHaveTextContent("Short");
    expect(screen.getByText(/Cover basis in force: Cash, debt and gold only/)).toBeInTheDocument();
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
