import type { Analysis, PortfolioOut, SessionInfo } from "../api/client";

export const session: SessionInfo = {
  user: { id: 7, username: "demo-gap-1a2b3c4d", is_demo: true },
  csrf_token: "csrf-abc",
  default_basis: "strict",
};

export function portfolio(label: string, overrides: Partial<PortfolioOut> = {}): PortfolioOut {
  return {
    label,
    basis: "strict",
    weights_total: {
      "Large-cap equity": 0.1375,
      "Mid-cap equity": 0.05,
      Debt: 0.2,
      Gold: 0.05,
      "Cash & liquid": 0.1625,
      Illiquid: 0.4,
    },
    weights_sleeve: [0.2292, 0.0833, 0.3333, 0.0833, 0.2708],
    exp_return: 0.0875,
    exp_real: 0.0407,
    vol: 0.0912,
    max_dd: 0.1375,
    cvar21: 0.0431,
    dd_ok: true,
    meets_target: true,
    target_gap: 0.0007,
    required_cover_cr: 120,
    available_cover_cr: 50,
    cover_fraction: 0.083,
    liquidity_binding: false,
    liquidity_infeasible: false,
    cost_of_liquidity: 0,
    liquid_return: 0.081,
    lam_base: 3.2,
    lam_used: 3.2,
    bounds_hit: [],
    explanation: [`Reason one for the ${label} mix.`, "Reason two."],
    optimiser_converged: true,
    ...overrides,
  };
}

export function analysis(overrides: Partial<Analysis> = {}): Analysis {
  const option = (label: string, extra: Partial<PortfolioOut> = {}) => ({
    portfolio: portfolio(label, extra),
    action_plan: [],
    scenarios: [],
    insights: [{ tone: "warn" as const, title: "Liquidity shortfall", body: "Counted liquid assets are below the need." }],
    ladder: [],
    projection: [],
  });
  return {
    profile_id: 1,
    basis: "strict",
    basis_label: "Cash, debt and gold only (stricter; equities not counted)",
    data_source: "sample",
    current: portfolio("Current", { lam_base: null, lam_used: null }),
    current_projection: [],
    options: [option("Growth"), option("Balanced"), option("Defensive")],
    upcoming_outflows: [],
    comparison_scenario: "Equities fall 25%",
    comparison: [
      { option: "Current", value_change: -0.1375, value_change_cr: -137.5, within_drawdown_limit: true, cover_ratio_after: 0.4, cover_held: false, real_corpus_multiple: 1, exp_return: 0.098, exp_real: 0.05, max_dd: 0.15 },
      { option: "Defensive", value_change: -0.1, value_change_cr: -100, within_drawdown_limit: true, cover_ratio_after: 1.2, cover_held: true, real_corpus_multiple: 1, exp_return: 0.083, exp_real: 0.04, max_dd: 0.08 },
    ],
    comparison_insights: [{ tone: "warn", title: null, body: "Your current mix would fall short of the safety net." }],
    ...overrides,
  };
}
