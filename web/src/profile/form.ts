import type { ProfileFull, ProfileInput } from "../api/client";

/**
 * The profile editor works in the units people think in (percent, years, rupees crore) and in boxes that may be empty
 * while someone is typing. This file turns that into the API's request (fractions) and back, and checks it with the same
 * rules the server applies (fo/profile_form.py). The server stays the judge; these checks only save a round trip.
 */
export type Num = number | null;

export type FormState = {
  name: string;
  constraint: string;
  corpus: Num;
  spending: Num;
  horizon: Num;
  maxDrawdown: Num; // %
  coverMonths: Num;
  target: Num; // % a year
  holdings: Record<string, Num>; // % of the whole corpus, including "Illiquid"
  illiquid: { description: string; expectedReturn: Num; volatility: Num; lockIn: Num; corr: Num };
  oneOffs: { id: number; year: Num; amount: Num }[];
  limits: Record<string, { min: Num; max: Num }>; // % of the liquid part
};

export const ILLIQUID = "Illiquid";
export const MAX_ONE_OFFS = 3;
export const MAX_NAME = 60;
export const MAX_ILLIQUID_PERCENT = 95;
const HOLDINGS_TOLERANCE = 0.5; // percentage points, as on the server

const toPercent = (fraction: number): number => Number((fraction * 100).toFixed(10));
const toFraction = (percent: number): number => Number((percent / 100).toFixed(10));
/**
 * Adds like Python 3.12's built-in sum() does for floats (compensated, so the result is the correctly rounded total). The
 * server decides "adds up to 100%" with that sum; a plain left-to-right sum differs in the last digit and would disagree
 * on the one case that sits exactly on the edge (99.5% or 100.5%).
 */
export function pythonSum(values: readonly number[]): number {
  let total = 0;
  let compensation = 0;
  for (const x of values) {
    const next = total + x;
    compensation += Math.abs(total) >= Math.abs(x) ? total - next + x : x - next + total;
    total = next;
  }
  return compensation !== 0 && Number.isFinite(compensation) ? total + compensation : total;
}

/** What the server works with after it has read a percent back from the fraction it was sent (api/convert.py `_pct`). */
const asServerSees = (percent: number): number => toPercent(toFraction(percent)) / 100;

let nextRowId = 1;
export const newRowId = (): number => nextRowId++;

export function toForm(p: ProfileFull | ProfileInput): FormState {
  return {
    name: p.name,
    constraint: p.deciding_constraint ?? "",
    corpus: p.corpus_cr,
    spending: p.annual_spending_cr,
    horizon: p.horizon_years,
    maxDrawdown: toPercent(p.max_drawdown),
    coverMonths: p.cover_months,
    target: toPercent(p.target_real_return),
    holdings: Object.fromEntries(Object.entries(p.holdings).map(([k, v]) => [k, toPercent(v)])),
    illiquid: {
      description: p.illiquid.description,
      expectedReturn: toPercent(p.illiquid.expected_return),
      volatility: toPercent(p.illiquid.volatility),
      lockIn: p.illiquid.lock_in_years,
      corr: p.illiquid.corr_with_equity,
    },
    oneOffs: (p.one_offs ?? []).map((o) => ({ id: newRowId(), year: o.year, amount: o.amount_cr })),
    limits: Object.fromEntries(Object.entries(p.limits).map(([k, v]) => [k, { min: toPercent(v.min), max: toPercent(v.max) }])),
  };
}

/** A neutral starting point for a new profile (the same numbers as the Streamlit app's starter). */
export function starterForm(classes: readonly string[]): FormState {
  const holdings: Record<string, number> = {
    "Large-cap equity": 20, "Mid-cap equity": 10, Debt: 30, Gold: 5, "Cash & liquid": 10, [ILLIQUID]: 25,
  };
  const limits: Record<string, [number, number]> = {
    "Large-cap equity": [5, 40], "Mid-cap equity": [0, 20], Debt: [10, 60], Gold: [0, 15], "Cash & liquid": [5, 30],
  };
  return {
    name: "New profile", constraint: "", corpus: 100, spending: 3, horizon: 15, maxDrawdown: 15, coverMonths: 24, target: 4,
    holdings: Object.fromEntries([...classes, ILLIQUID].map((c) => [c, holdings[c] ?? 0])),
    illiquid: { description: "Real estate", expectedReturn: 8, volatility: 12, lockIn: 2, corr: 0.2 },
    oneOffs: [{ id: newRowId(), year: 3, amount: 5 }],
    limits: Object.fromEntries(classes.map((c) => [c, { min: limits[c]?.[0] ?? 0, max: limits[c]?.[1] ?? 100 }])),
  };
}

export type Check = { field: string; message: string };

const outside = (v: Num, min: number, max: number, whole = false): boolean =>
  v === null || v < min || v > max || (whole && !Number.isInteger(v));

/** Everything wrong with the form, field by field. An empty list means it can be saved. */
export function check(f: FormState): Check[] {
  const out: Check[] = [];
  const add = (field: string, message: string) => out.push({ field, message });

  if (f.name.trim() === "") add("name", "Give the profile a name.");
  else if (f.name.length > MAX_NAME) add("name", `Keep the name to ${MAX_NAME} characters or fewer.`);
  if (outside(f.corpus, 1, 1_000_000)) add("corpus", "Total corpus must be between ₹1 Cr and ₹1,000,000 Cr.");
  if (outside(f.spending, 0, 100_000)) add("spending", "Annual spending must be between 0 and ₹100,000 Cr.");
  if (outside(f.horizon, 1, 60, true)) add("horizon", "Investment horizon must be a whole number of years from 1 to 60.");
  if (outside(f.maxDrawdown, 1, 80)) add("maxDrawdown", "Maximum drawdown must be between 1% and 80%.");
  if (outside(f.coverMonths, 1, 240, true)) add("coverMonths", "Liquidity cover must be a whole number of months from 1 to 240.");
  if (outside(f.target, -5, 25)) add("target", "Target real return must be between −5% and 25% a year.");

  const shares = Object.values(f.holdings);
  if (shares.some((v) => outside(v, 0, 100))) add("holdings", "Each holding must be between 0% and 100%.");
  else {
    // The same sum the server makes, so the two agree even on the edge (exactly 99.5% or 100.5% is refused there).
    const serverTotal = pythonSum(shares.map((v) => asServerSees(v ?? 0)));
    if (Math.abs(serverTotal - 1.0) > HOLDINGS_TOLERANCE / 100) {
      add("holdings", `Holdings add up to ${holdingsTotal(f).toFixed(1)}%. They need to add up to 100%.`);
    } else if (serverTotal > 0 && asServerSees(f.holdings[ILLIQUID] ?? 0) / serverTotal > MAX_ILLIQUID_PERCENT / 100) {
      add("holdings", "Illiquid holdings can be at most 95% of the corpus; the model needs a liquid part to allocate.");
    }
  }

  const ill = f.illiquid;
  if (outside(ill.expectedReturn, -10, 40)) add("illReturn", "Assumed return must be between −10% and 40% a year.");
  if (outside(ill.volatility, 0, 80)) add("illVol", "Assumed volatility must be between 0% and 80%.");
  if (outside(ill.lockIn, 0, 30, true)) add("illLock", "Lock-in must be a whole number of years from 0 to 30.");
  if (outside(ill.corr, 0, 1)) add("illCorr", "Correlation must be between 0 and 1.");

  if (f.oneOffs.length > MAX_ONE_OFFS) add("oneOffs", "Enter at most three one-off outflows.");
  f.oneOffs.forEach((row, i) => {
    const horizon = f.horizon ?? 60;
    if (outside(row.year, 1, horizon, true)) add(`oneOff${i}Year`, `Outflow ${i + 1}: the year must be a whole number from 1 to ${horizon} (inside the horizon).`);
    if (row.amount === null || row.amount <= 0) add(`oneOff${i}Amount`, `Outflow ${i + 1}: the amount must be above zero.`);
  });

  const mins: number[] = [];
  const maxes: number[] = [];
  let limitsComplete = true;
  for (const [name, { min, max }] of Object.entries(f.limits)) {
    const lo = min === null ? NaN : asServerSees(min);
    const hi = max === null ? NaN : asServerSees(max);
    if (!(lo >= 0 && lo <= hi && hi <= 1)) {
      add(`limit-${name}`, `${name}: the minimum must be between 0% and the maximum, and the maximum at most 100%.`);
      limitsComplete = false;
    } else {
      mins.push(lo);
      maxes.push(hi);
    }
  }
  if (limitsComplete && (pythonSum(mins) > 1 + 1e-9 || pythonSum(maxes) < 1 - 1e-9)) {
    add("limits", "The class limits can't add up to 100% of the liquid part: minimums must total at most 100% and maximums at least 100%.");
  }
  return out;
}

export function holdingsTotal(f: FormState): number {
  return Object.values(f.holdings).reduce<number>((sum, v) => sum + (v ?? 0), 0);
}

/** The API request, or null if a number is still missing (check() says which). */
export function toInput(f: FormState): ProfileInput | null {
  if (check(f).length > 0) return null;
  const n = (v: Num): number => v as number;
  return {
    name: f.name.trim(),
    deciding_constraint: f.constraint,
    corpus_cr: n(f.corpus),
    annual_spending_cr: n(f.spending),
    horizon_years: n(f.horizon),
    max_drawdown: toFraction(n(f.maxDrawdown)),
    cover_months: n(f.coverMonths),
    target_real_return: toFraction(n(f.target)),
    holdings: Object.fromEntries(Object.entries(f.holdings).map(([k, v]) => [k, toFraction(n(v))])),
    illiquid: {
      description: f.illiquid.description.trim() || "Illiquid holdings",
      expected_return: toFraction(n(f.illiquid.expectedReturn)),
      volatility: toFraction(n(f.illiquid.volatility)),
      lock_in_years: n(f.illiquid.lockIn),
      corr_with_equity: n(f.illiquid.corr),
    },
    one_offs: f.oneOffs.map((o) => ({ year: n(o.year), amount_cr: n(o.amount) })),
    limits: Object.fromEntries(Object.entries(f.limits).map(([k, v]) => [k, { min: toFraction(n(v.min)), max: toFraction(n(v.max)) }])),
  };
}

/** True when two forms say the same thing (so "Save" can stay off until something changed). */
export function sameForm(a: FormState, b: FormState): boolean {
  const strip = (f: FormState) => ({ ...f, oneOffs: f.oneOffs.map(({ year, amount }) => ({ year, amount })) });
  return JSON.stringify(strip(a)) === JSON.stringify(strip(b));
}
