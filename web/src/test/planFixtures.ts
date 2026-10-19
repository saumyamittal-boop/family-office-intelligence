import type { PlanAnswers, PlanConfig, PlanPreview, PlanStrategies, RiskKey, Strategy } from "../api/client";
import { portfolio } from "./fixtures";

export const CLASS_NAMES = ["Large-cap equity", "Mid-cap equity", "Debt", "Gold", "Cash & liquid", "Illiquid"] as const;
const LABELS: Record<string, [string, string]> = {
  "Large-cap equity": ["Large-cap index fund", "Holds India's biggest listed companies."],
  "Mid-cap equity": ["Mid-cap index fund", "Holds mid-sized listed companies."],
  Debt: ["Government or high-quality bond fund", "Lends to the government and strong companies."],
  Gold: ["Gold ETF", "Follows the price of gold and is easy to sell."],
  "Cash & liquid": ["Liquid fund or savings", "Money you can reach within a day or two."],
  Illiquid: ["Property, business and other holdings", "Kept as they are. They cannot be sold quickly."],
};

export const CONFIG: PlanConfig = {
  steps: ["About you", "What's coming", "Your comfort", "Safety net", "What you own", "Your strategies"],
  comfort: [
    { key: "Protect", letter: "A", headline: "Protect what we have", blurb: "We would rather grow slowly than see our wealth fall much in a bad year.", max_drawdown: 0.08, target_real_return: 0.02, portfolio: "Defensive" },
    { key: "Balance", letter: "B", headline: "Balance safety and growth", blurb: "A fall in a bad year is acceptable if the wealth grows well over time.", max_drawdown: 0.15, target_real_return: 0.04, portfolio: "Balanced" },
    { key: "Grow", letter: "C", headline: "Grow as much as is sensible", blurb: "We can ride out big falls because we have time and a safety net.", max_drawdown: 0.25, target_real_return: 0.06, portfolio: "Growth" },
  ],
  classes: CLASS_NAMES.map((name) => ({ name, label: LABELS[name]?.[0] ?? name, description: LABELS[name]?.[1] ?? "" })),
  commitment_kinds: ["Education", "Wedding", "Property purchase", "Business investment", "Medical or emergency", "Custom"],
  max_commitments: 3,
  horizon_years: 25,
  wealth: { min: 1, max: 1_000_000 },
  spending: { min: 0, max: 100_000 },
  months: { min: 3, max: 36 },
  defaults: { name: "My family", wealth: 100, spending: 3, risk: "Balance", months: 12 },
  crash: {
    label: "In a severe market crash",
    description: "A stylised shock, not a replay of any real year: large-cap equity −35%, mid-cap equity −45%, debt −2%, gold +5%, and illiquid holdings −20%, all at once.",
  },
};

const TYPICAL_SHARES: Record<string, number> = { "Large-cap equity": 0.2, "Mid-cap equity": 0.08, Debt: 0.27, Gold: 0.05, "Cash & liquid": 0.1, Illiquid: 0.3 };
export const typical = (wealth: number) => Object.fromEntries(Object.entries(TYPICAL_SHARES).map(([k, s]) => [k, Math.round(wealth * s * 100) / 100]));

/** A stand-in for the server's live read-out that follows the answers, so tests see the panel genuinely update. */
export function previewFor(a: PlanAnswers): PlanPreview {
  const amounts = a.amounts ?? typical(a.wealth);
  const total = Object.values(amounts).reduce((x, y) => x + y, 0);
  const illiquid = amounts["Illiquid"] ?? 0;
  const comfort = CONFIG.comfort.map((c) => ({ key: c.key, max_drawdown: c.max_drawdown, loss_cr: total * c.max_drawdown }));
  const base = { typical_amounts: typical(a.wealth), comfort };
  if (illiquid / total > 0.95) return { ...base, problems: ["At least 5% of the wealth needs to be in things that can be sold, so there is something to plan with."], outflows: [], effects: [], amounts_differ_from_wealth: false };
  if (a.commitments.length > 3) return { ...base, problems: ["Enter at most 3 upcoming commitments."], outflows: [], effects: [], amounts_differ_from_wealth: false };
  const inside = a.commitments.filter((c) => 12 * c.year <= a.months).reduce((s, c) => s + c.amount_cr, 0);
  const required = a.spending * a.months / 12 + inside;
  return {
    ...base, problems: [], corpus_cr: total, liquid_cr: total - illiquid, illiquid_cr: illiquid, illiquid_share: illiquid / total,
    safety_net: { months: a.months, required_cr: required, spending_cr: required - inside, commitments_cr: inside },
    outflows: [1, 2, 3, 4, 5].map((year) => ({ year, spending_cr: a.spending, one_off_cr: 0, total_cr: a.spending })),
    near_outflows_cr: a.spending * 3, near_outflows_share_of_liquid: (a.spending * 3) / (total - illiquid),
    amounts_total_cr: total, amounts_differ_from_wealth: a.amounts !== null && a.amounts !== undefined && Math.abs(total - a.wealth) > Math.max(0.5, 0.01 * a.wealth),
    effects: [
      `Comfort: ${CONFIG.comfort.find((c) => c.key === a.risk)?.headline}.`,
      `Over the next ${a.months} months the family needs about ₹${required.toFixed(1)} Cr within easy reach.`,
    ],
  };
}

/** [class, now in INR cr, after in INR cr]: Strategy rows sell large-cap and buy the rest. */
const PLAN_ROWS: [string, number, number][] = [["Large-cap equity", 20, 5], ["Mid-cap equity", 10, 30], ["Debt", 30, 60], ["Gold", 5, 15], ["Cash & liquid", 10, 5]];

function strategy(key: RiskKey, index: number): Strategy {
  const spec = CONFIG.comfort[index]!;
  const pf = portfolio(spec.portfolio, {
    exp_return: 0.0787 + index * 0.0058, exp_real: 0.032 + index * 0.0055, max_dd: [0.0618, 0.1352, 0.1894][index]!, vol: 0.05 + index * 0.025,
    available_cover_cr: 300, required_cover_cr: 3.4 + index * 0.1,
  });
  return {
    key, letter: spec.letter, headline: spec.headline, blurb: spec.blurb, portfolio: pf,
    within_comfort_of: { Protect: index === 0, Balance: index <= 1, Grow: true },
    meets_goal_of: { Protect: true, Balance: index >= 1, Grow: index === 2 },
    year_range: { low: 0.051 - index * 0.016, median: 0.076 + index * 0.012, high: 0.133 + index * 0.035, worst: -0.001 - index * 0.06, best: 0.2 + index * 0.05 },
    crash: { value_change: -0.111 - index * 0.06, value_change_cr: -27.8 - index * 15 },
    cover_ratio: 8.8 - index * 1.2,
    description: [`Built so that a bad year costs about ${[8, 15, 25][index]}% of your wealth or less.`, `Reason two for strategy ${spec.letter}.`],
    action_plan: PLAN_ROWS.map(([name, now, next]) => ({
      asset_class: name, current_share: now / 100, recommended_share: next / 100, current_cr: now, recommended_cr: next, change_cr: next - now,
      instrument_name: LABELS[name]![0], instrument_note: LABELS[name]![1],
    })),
    illiquid_cr: 75, illiquid_name: LABELS["Illiquid"]![0], illiquid_note: LABELS["Illiquid"]![1],
  };
}

export function strategiesFor(a: PlanAnswers): PlanStrategies {
  return {
    profile_name: a.name, corpus_cr: Object.values(a.amounts ?? typical(a.wealth)).reduce((x, y) => x + y, 0),
    strategies: (["Protect", "Balance", "Grow"] as RiskKey[]).map(strategy), commitments: a.commitments, crash: CONFIG.crash,
    basis_label: "Cash, debt and gold only (stricter; equities not counted)", data_source: "sample",
  };
}

export const SAVED = { profile: { id: 42, name: "My family · Strategy B" }, created: true };
