import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import App from "./App";
import { AnalysisView } from "./pages/HomePage";
import { analysis, portfolio, session } from "./test/fixtures";

const META = {
  app: "Family Office Intelligence", version: "0.1.0", data_source: "sample",
  disclaimer: "Illustrative simulation on synthetic data, not investment advice.",
  asset_classes: [], demo_login: true, demo_families: ["legacy", "business", "nextgen", "gap"],
  cover_bases: { all: "All liquid tiers, haircut-adjusted (as specified)", strict: "Cash, debt and gold only (stricter; equities not counted)" },
};

type Route = (init: RequestInit | undefined) => Response | Promise<Response>;
function serve(routes: Record<string, Route>) {
  const calls: { path: string; method: string }[] = [];
  vi.stubGlobal("fetch", (path: string, init?: RequestInit) => {
    const method = init?.method ?? "GET";
    calls.push({ path, method });
    const route = routes[`${method} ${path.split("?")[0]}`];
    return Promise.resolve(route ? route(init) : new Response(JSON.stringify({ detail: "Not found." }), { status: 404 }));
  });
  return calls;
}
const json = (body: unknown, status = 200) => () => new Response(JSON.stringify(body), { status });

function renderApp() {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={client}>
      <App />
    </QueryClientProvider>,
  );
}

describe("signed out", () => {
  beforeEach(() => {
    serve({
      "GET /api/auth/me": json({ detail: "Please sign in." }, 401),
      "GET /api/meta": json(META),
      "POST /api/auth/demo": json(session),
      "GET /api/profiles": json([{ id: 1, name: "Gap family", corpus_cr: 1000 }]),
      "GET /api/profiles/1/analysis": json(analysis()),
    });
  });
  afterEach(() => vi.unstubAllGlobals());

  it("shows the sign-in screen with the four demo families and the synthetic-data warning", async () => {
    renderApp();
    expect(await screen.findByRole("button", { name: "Log in" })).toBeInTheDocument();
    for (const label of ["Legacy-conservative family", "Business-heavy family", "Next-gen growth family", "₹1,000 Cr liquidity-gap example"]) {
      expect(await screen.findByRole("button", { name: label })).toBeInTheDocument();
    }
    expect(screen.getByText(/synthetic data only/i)).toBeInTheDocument();
  });

  it("opens a demo family, defaults to the stricter cover and shows the figures", async () => {
    const user = userEvent.setup();
    renderApp();
    await user.click(await screen.findByRole("button", { name: /liquidity-gap example/ }));
    expect(await screen.findByText(/demo copy/)).toBeInTheDocument();
    await waitFor(() => expect(screen.getByLabelText(/safety net/i)).toHaveValue("strict"));
    expect(await screen.findByText("8.8%")).toBeInTheDocument(); // 8.75% rounds half up
    expect(screen.getByText("0.4x")).toBeInTheDocument(); // the slide's 0.4x liquidity cover
    expect(screen.getByText(/Illustrative simulation, not investment advice/)).toBeInTheDocument();
  });

  it("keeps the log-in button disabled until both fields are filled and shows server errors", async () => {
    vi.unstubAllGlobals();
    serve({
      "GET /api/auth/me": json({ detail: "Please sign in." }, 401),
      "GET /api/meta": json(META),
      "POST /api/auth/login": json({ detail: "Wrong username or password.", problems: null }, 401),
    });
    const user = userEvent.setup();
    renderApp();
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
  afterEach(() => vi.unstubAllGlobals());
  it("says so instead of showing a blank page", async () => {
    vi.stubGlobal("fetch", () => Promise.reject(new TypeError("fetch failed")));
    renderApp();
    expect(await screen.findByRole("alert")).toHaveTextContent(/Can't reach the server/);
  });
});

describe("analysis view", () => {
  it("warns loudly when the optimiser did not converge, naming the portfolio", () => {
    const data = analysis();
    data.options[2] = { ...data.options[2]!, portfolio: portfolio("Defensive", { optimiser_converged: false }) };
    render(<AnalysisView analysis={data} />);
    expect(screen.getByRole("alert")).toHaveTextContent("Defensive");
    expect(screen.getByRole("alert")).toHaveTextContent(/approximate/);
  });

  it("shows no warning when every solve was clean", () => {
    render(<AnalysisView analysis={analysis()} />);
    expect(screen.queryByRole("alert")).not.toBeInTheDocument();
  });

  it("switches between the current mix and the recommendations", async () => {
    const user = userEvent.setup();
    render(<AnalysisView analysis={analysis()} />);
    expect(screen.getByText("Why the Balanced mix")).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Current" }));
    expect(screen.getByText("Where you are now")).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Growth" }));
    expect(screen.getByText("Reason one for the Growth mix.")).toBeInTheDocument();
  });

  it("flags a liquidity shortfall in the comparison and names the basis in force", () => {
    render(<AnalysisView analysis={analysis()} />);
    const table = screen.getByRole("table", { name: /Options compared under: Equities fall 25%/ });
    const current = within(table).getByRole("row", { name: /Current/ });
    expect(current).toHaveTextContent("−₹137.5 Cr");
    expect(current).toHaveTextContent("0.4x short");
    expect(screen.getByText(/Cover basis in force: Cash, debt and gold only/)).toBeInTheDocument();
  });

  it("labels the illiquid holding as fixed", () => {
    render(<AnalysisView analysis={analysis()} />);
    expect(screen.getByRole("rowheader", { name: "Illiquid (fixed)" })).toBeInTheDocument();
  });
});
