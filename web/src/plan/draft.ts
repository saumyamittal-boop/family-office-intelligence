import type { PlanAnswers, PlanConfig } from "../api/client";

const KEY = "foi.plan.draft";
const LANDING_KEY = "foi.fresh-signup";

export type Draft = {
  answers: PlanAnswers;
  /** Furthest step reached (1-based): earlier steps and this one can be revisited from the progress bar. */
  furthest: number;
};

export function defaultAnswers(config: PlanConfig): PlanAnswers {
  const d = config.defaults;
  return { name: d.name, wealth: d.wealth, spending: d.spending, risk: d.risk, months: d.months, commitments: [], amounts: null };
}

const isNumber = (v: unknown): v is number => typeof v === "number" && Number.isFinite(v);

/** Read a saved draft defensively: anything unexpected falls back to the defaults, never to a broken form. */
export function readDraft(config: PlanConfig): Draft {
  const fresh: Draft = { answers: defaultAnswers(config), furthest: 1 };
  try {
    const parsed: unknown = JSON.parse(window.sessionStorage.getItem(KEY) ?? "null");
    if (typeof parsed !== "object" || parsed === null) return fresh;
    const { answers: a, furthest } = parsed as { answers?: Record<string, unknown>; furthest?: unknown };
    if (!a || typeof a.name !== "string" || !isNumber(a.wealth) || !isNumber(a.spending) || !isNumber(a.months)) return fresh;
    if (!config.comfort.some((c) => c.key === a.risk)) return fresh;
    const commitments = Array.isArray(a.commitments) ? a.commitments : [];
    const valid = commitments.every(
      (c) => typeof c === "object" && c !== null && typeof (c as { kind?: unknown }).kind === "string" &&
        isNumber((c as { year?: unknown }).year) && isNumber((c as { amount_cr?: unknown }).amount_cr),
    );
    if (!valid || commitments.length > config.max_commitments) return fresh;
    const amounts = a.amounts && typeof a.amounts === "object" ? (a.amounts as Record<string, number>) : null;
    if (amounts && !Object.values(amounts).every(isNumber)) return fresh;
    return {
      answers: { name: a.name, wealth: a.wealth, spending: a.spending, risk: a.risk as PlanAnswers["risk"], months: a.months, commitments: commitments as PlanAnswers["commitments"], amounts },
      furthest: isNumber(furthest) ? Math.min(Math.max(1, Math.round(furthest)), config.steps.length) : 1,
    };
  } catch {
    return fresh;
  }
}

/**
 * The draft lives in sessionStorage: it survives a reload of this tab but is gone when the tab closes, and is never sent
 * anywhere. (Real family data stays out of scope until the privacy gate in the migration plan has been passed.)
 */
export function writeDraft(draft: Draft): void {
  try {
    window.sessionStorage.setItem(KEY, JSON.stringify(draft));
  } catch {
    /* blocked storage: the draft simply lasts until the page is closed */
  }
}

export function clearDraft(): void {
  try {
    window.sessionStorage.removeItem(KEY);
  } catch {
    /* nothing to clear */
  }
}

/** A brand-new account lands on the plan, as in the Streamlit app. */
export function markFreshSignup(): void {
  try {
    window.sessionStorage.setItem(LANDING_KEY, "1");
  } catch {
    /* without storage the person simply lands on the overview */
  }
}

export function isFreshSignup(): boolean {
  try {
    return window.sessionStorage.getItem(LANDING_KEY) === "1";
  } catch {
    return false;
  }
}

export function clearFreshSignup(): void {
  try {
    window.sessionStorage.removeItem(LANDING_KEY);
  } catch {
    /* nothing to clear */
  }
}
