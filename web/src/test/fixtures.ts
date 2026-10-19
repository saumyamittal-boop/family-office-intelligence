import type { Analysis, PortfolioDetail, PortfolioOut, SessionInfo } from "../api/client";

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
    available_cover_cr: 386,
    cover_fraction: 0.386,
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

const ACTION_PLAN: PortfolioDetail["action_plan"] = [
  { asset_class: "Large-cap equity", current_share: 0.55, recommended_share: 0.06, current_cr: 550, recommended_cr: 60, change_cr: -490 },
  { asset_class: "Mid-cap equity", current_share: 0, recommended_share: 0.12, current_cr: 0, recommended_cr: 120, change_cr: 120 },
  { asset_class: "Debt", current_share: 0, recommended_share: 0.343, current_cr: 0, recommended_cr: 343, change_cr: 343 },
  { asset_class: "Gold", current_share: 0, recommended_share: 0.047, current_cr: 0, recommended_cr: 47, change_cr: 47 },
  { asset_class: "Cash & liquid", current_share: 0.05, recommended_share: 0.03, current_cr: 50, recommended_cr: 30, change_cr: -20 },
];

export const SCENARIOS: PortfolioDetail["scenarios"] = [
  { scenario: "Baseline (no shock)", value_change: 0, value_change_cr: 0, within_drawdown_limit: true, cover_ratio: 3.2, cover_held: true, real_corpus_multiple: 1.4 },
  { scenario: "Equities fall 25%", value_change: -0.0594, value_change_cr: -59.4, within_drawdown_limit: true, cover_ratio: 2.9, cover_held: true, real_corpus_multiple: 1.3 },
  { scenario: "Market crash", value_change: -0.1375, value_change_cr: -137.5, within_drawdown_limit: true, cover_ratio: 2.1, cover_held: true, real_corpus_multiple: 1.2 },
  { scenario: "Inflation and rate spike", value_change: -0.0921, value_change_cr: -92.1, within_drawdown_limit: true, cover_ratio: 2.6, cover_held: true, real_corpus_multiple: 1.25 },
  { scenario: "Large unexpected expense", value_change: -0.08, value_change_cr: -80, within_drawdown_limit: true, cover_ratio: 0.8, cover_held: false, real_corpus_multiple: 1.1 },
  { scenario: "Lost decade", value_change: 0, value_change_cr: 0, within_drawdown_limit: true, cover_ratio: 3.2, cover_held: true, real_corpus_multiple: 0.93 },
];

export const LADDER: PortfolioDetail["ladder"] = [1, 2, 3, 4].map((year) => ({
  year, outflows_cr: year === 1 ? 120 : 20 + year, liquid_value_cr: 380 - year * 30, months_covered: 150 - year * 18,
}));

const projection = (growth: number): PortfolioDetail["projection"] =>
  [0, 1, 2, 3].map((year) => ({ year, nominal_cr: 1000 * (1 + growth) ** year, real_cr: (1000 * (1 + growth) ** year) / 1.045 ** year }));

export function analysis(overrides: Partial<Analysis> = {}): Analysis {
  const option = (label: string, extra: Partial<PortfolioOut> = {}, growth = 0.08): PortfolioDetail => ({
    portfolio: portfolio(label, extra),
    action_plan: ACTION_PLAN,
    scenarios: SCENARIOS,
    insights: [{ tone: "warn", title: "Liquidity shortfall", body: "Counted liquid assets are below the need." }],
    ladder: LADDER,
    projection: projection(growth),
    year_range: { low: -0.03, median: 0.09, high: 0.21, worst: -0.12, best: 0.33 },
  });
  return {
    profile_id: 1,
    basis: "strict",
    basis_label: "Cash, debt and gold only (stricter; equities not counted)",
    data_source: "sample",
    current: portfolio("Current", { lam_base: null, lam_used: null, available_cover_cr: 50 }),
    current_projection: projection(0.098),
    current_ladder: LADDER,
    current_scenarios: SCENARIOS,
    options: [option("Growth", {}, 0.087), option("Balanced", {}, 0.084), option("Defensive", {}, 0.083)],
    upcoming_outflows: [
      { year: 1, spending_cr: 20, one_off_cr: 100, total_cr: 120 },
      { year: 2, spending_cr: 20.9, one_off_cr: 0, total_cr: 20.9 },
      { year: 3, spending_cr: 21.8, one_off_cr: 0, total_cr: 21.8 },
    ],
    comparison_scenario: "Equities fall 25%",
    comparison: [
      { option: "Current", value_change: -0.1375, value_change_cr: -137.5, within_drawdown_limit: true, cover_ratio_after: 0.4, cover_held: false, real_corpus_multiple: 1, exp_return: 0.098, exp_real: 0.05, max_dd: 0.15 },
      { option: "Defensive", value_change: -0.04, value_change_cr: -39.7, within_drawdown_limit: true, cover_ratio_after: 3.4, cover_held: true, real_corpus_multiple: 1, exp_return: 0.083, exp_real: 0.04, max_dd: 0.08 },
    ],
    comparison_insights: [{ tone: "warn", title: null, body: "Your current mix would fall short of the safety net." }],
    ...overrides,
  };
}

const CLASSES = ["Large-cap equity", "Mid-cap equity", "Debt", "Gold", "Cash & liquid"];
const shocks = (large: number, mid: number, debt: number, gold: number) => ({
  "Large-cap equity": large, "Mid-cap equity": mid, Debt: debt, Gold: gold, "Cash & liquid": 0,
});

export const PRESETS = [
  { name: "Equities fall 25%", description: "Shares fall 25% and nothing else changes.", shocks: shocks(-0.25, -0.25, 0, 0), illiquid: 0, extra_outflow: 0, return_drag: 0 },
  { name: "Market crash", description: "Equities fall sharply and illiquid assets are marked down.", shocks: shocks(-0.35, -0.45, -0.02, 0.05), illiquid: -0.2, extra_outflow: 0, return_drag: 0 },
  { name: "Inflation and rate spike", description: "Rates and prices jump. Bonds and equities both fall.", shocks: shocks(-0.12, -0.15, -0.09, 0.08), illiquid: -0.05, extra_outflow: 0, return_drag: 0 },
  { name: "Large unexpected expense", description: "A one-off bill of 8% of the corpus arrives.", shocks: shocks(0, 0, 0, 0), illiquid: 0, extra_outflow: 0.08, return_drag: 0 },
  { name: "Lost decade", description: "Returns run 4 points a year lower for the whole horizon.", shocks: shocks(0, 0, 0, 0), illiquid: 0, extra_outflow: 0, return_drag: 0.04 },
];

export const RANGES = {
  equity_shock: { min: -0.6, max: 0.2, default: -0.25 },
  debt_shock: { min: -0.2, max: 0.1, default: -0.03 },
  gold_shock: { min: -0.3, max: 0.4, default: 0.05 },
  illiquid_markdown: { min: -0.5, max: 0.1, default: -0.1 },
  one_off_expense: { min: 0, max: 0.4, default: 0.05 },
  return_drag: { min: 0, max: 0.08, default: 0 },
};

export const META = {
  app: "Family Office Intelligence", version: "0.1.0", data_source: "sample",
  disclaimer: "Illustrative simulation on synthetic data, not investment advice.",
  asset_classes: CLASSES, demo_login: true, demo_families: ["legacy", "business", "nextgen", "gap"],
  cover_bases: {
    all: "All liquid tiers, haircut-adjusted (as specified)",
    strict: "Cash, debt and gold only (stricter; equities not counted)",
  },
  scenario_presets: PRESETS,
  custom_scenario_ranges: RANGES,
};
