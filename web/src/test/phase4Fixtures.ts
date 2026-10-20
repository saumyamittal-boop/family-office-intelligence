import type { Analysis, Dashboard, History, ModuleId, ProfileFull, ScenarioComparison, ScenarioRequest } from "../api/client";
import { analysis as makeAnalysis, META, PRESETS, session } from "./fixtures";
import { json, jsonBy } from "./render";
import type { Route } from "./render";

export const DEFAULT_MODULES: ModuleId[] = ["allocation_actions", "liquidity_commitments", "risk_exposure", "stress_scenarios"];

const ALL_MODULES = [
  "allocation_actions", "liquidity_commitments", "risk_exposure", "stress_scenarios", "net_worth_projection",
  "historical_performance", "recommendation_rationale", "holdings_consolidation",
] as ModuleId[];

/** `notReady` lists modules the server would mark unavailable (none, now that every module is built). */
export function dashboard(modules: ModuleId[] = DEFAULT_MODULES, isDefault = true, notReady: ModuleId[] = []): Dashboard {
  const catalog = ALL_MODULES.map((id) => ({ id, available: !notReady.includes(id) }));
  return { modules, is_default: isDefault, updated: isDefault ? null : "2026-10-19T10:00:00+00:00", default_modules: DEFAULT_MODULES, catalog };
}

/** A short, believable history: eight steps over 2016 to 2019, a fall in 2018, for the current mix and the three options. */
export function history(overrides: Partial<History> = {}): History {
  const dates = ["2015-12-31", "2016-06-30", "2016-12-30", "2017-06-30", "2017-12-29", "2018-06-29", "2018-12-28", "2019-06-28"];
  const make = (label: string, scale: number) => {
    const value = [100, 104, 109, 115, 121, 112, 116, 124].map((v) => 100 + (v - 100) * scale);
    let peak = 0;
    const drawdown = value.map((v) => {
      peak = Math.max(peak, v);
      return Number((v / peak - 1).toFixed(6));
    });
    return {
      label, value, drawdown, max_drawdown: -Math.min(...drawdown), cvar21: 0.04,
      annual: [
        { year: 2016, portfolio_return: 0.09 * scale, trading_days: 260, partial: false },
        { year: 2017, portfolio_return: 0.11 * scale, trading_days: 260, partial: false },
        { year: 2018, portfolio_return: -0.04 * scale, trading_days: 261, partial: false },
        { year: 2019, portfolio_return: 0.06 * scale, trading_days: 120, partial: true },
      ],
    };
  };
  return {
    profile_id: 1, basis: "strict", data_source: "sample", dates, step_days: 5, drawdown_limit: 0.15,
    portfolios: [make("Current", 1.3), make("Growth", 1.2), make("Balanced", 1), make("Defensive", 0.7)],
    note: "The same constant mix is replayed over the sample years. Illiquid holdings accrue smoothly in this replay.",
    ...overrides,
  };
}

/** What the scenario endpoint would say: one row per option, for any built-in scenario or custom dials. */
export function comparison(request: ScenarioRequest, data: Analysis = makeAnalysis()): ScenarioComparison {
  const custom = request.custom ?? null;
  const preset = PRESETS.find((p) => p.name === request.preset) ?? PRESETS[0]!;
  const name = custom ? "Your scenario" : preset.name;
  const harsh = custom ? Math.abs(custom.equity_shock) : 0.25;
  const rows = ["Current", ...data.options.map((o) => o.portfolio.label)].map((option, i) => ({
    option, value_change: -harsh * (0.5 - i * 0.1), value_change_cr: -harsh * (0.5 - i * 0.1) * 1000,
    within_drawdown_limit: harsh * (0.5 - i * 0.1) <= 0.15, cover_ratio_after: i === 0 ? 0.4 : 3 - i * 0.2, cover_held: i !== 0,
    real_corpus_multiple: 1.1 - i * 0.02, exp_return: 0.09 - i * 0.003, exp_real: 0.04, max_dd: 0.12,
  }));
  return {
    profile_id: 1, basis: request.basis ?? "strict", name, description: custom ? "The shocks set above, applied once to today's holdings." : preset.description,
    is_custom: custom !== null, applied: { ...preset, name }, rows,
    insights: [{ tone: "info", title: null, body: `Compared under ${name}.` }],
  };
}

export const PROFILE: ProfileFull = {
  id: 1, name: "Gap family", deciding_constraint: "Liquidity cover", corpus_cr: 1000, annual_spending_cr: 20, horizon_years: 15,
  max_drawdown: 0.15, cover_months: 24, target_real_return: 0.04,
  holdings: { "Large-cap equity": 0.55, "Mid-cap equity": 0, Debt: 0, Gold: 0, "Cash & liquid": 0.05, Illiquid: 0.4 },
  illiquid: { description: "Real estate", expected_return: 0.08, volatility: 0.12, lock_in_years: 2, corr_with_equity: 0.2 },
  one_offs: [{ year: 1, amount_cr: 100 }],
  limits: {
    "Large-cap equity": { min: 0.05, max: 0.4 }, "Mid-cap equity": { min: 0, max: 0.2 }, Debt: { min: 0.1, max: 0.6 },
    Gold: { min: 0, max: 0.15 }, "Cash & liquid": { min: 0.05, max: 0.3 },
  },
};

export const PROFILES = [{ id: 1, name: "Gap family", corpus_cr: 1000 }];

/** The canned server for a signed-in family: the analysis, the history, the dashboard choice and the scenario endpoint. */
export function appRoutes(data: Analysis = makeAnalysis(), extra: Record<string, Route> = {}): Record<string, Route> {
  return {
    "GET /api/auth/me": json(session),
    "GET /api/meta": json(META),
    "GET /api/profiles": json(PROFILES),
    "GET /api/profiles/1": json(PROFILE),
    "GET /api/profiles/1/analysis": json(data),
    "GET /api/profiles/1/history": json(history()),
    "GET /api/dashboard": json(dashboard()),
    "POST /api/profiles/1/scenarios": jsonBy<ScenarioRequest>((body) => comparison(body, data)),
    ...extra,
  };
}
