import { describe, expect, it } from "vitest";
import vectors from "../test/profile_vectors.json";
import { PROFILE } from "../test/phase4Fixtures";
import { check, holdingsTotal, newRowId, pythonSum, sameForm, starterForm, toForm, toInput } from "./form";
import type { FormState } from "./form";

type Vector = { label: string; form: Omit<FormState, "oneOffs"> & { oneOffs: { year: number; amount: number }[] }; valid: boolean };

const asForm = (v: Vector["form"]): FormState => ({ ...v, oneOffs: v.oneOffs.map((o) => ({ id: newRowId(), ...o })) });

describe("the editor agrees with the server on what a profile may be", () => {
  const cases = (vectors as unknown as { cases: Vector[] }).cases;

  it("has a useful number of recorded verdicts, both ways", () => {
    expect(cases.length).toBeGreaterThan(100);
    expect(cases.filter((c) => c.valid).length).toBeGreaterThan(25);
    expect(cases.filter((c) => !c.valid).length).toBeGreaterThan(50);
  });

  it.each(cases.map((c) => [c.label, c] as const))("%s", (_label, c) => {
    const form = asForm(c.form);
    const problems = check(form).map((p) => p.message);
    expect({ accepted: problems.length === 0, problems }).toEqual(c.valid ? { accepted: true, problems: [] } : { accepted: false, problems: expect.any(Array) });
    // Whatever the editor accepts, it can turn into a request; whatever it refuses, it will not send.
    expect(toInput(form) !== null).toBe(c.valid);
  });
});

describe("converting between the form and the request", () => {
  it("round-trips a stored profile exactly", () => {
    const { id: _id, ...input } = PROFILE;
    expect(toInput(toForm(PROFILE))).toEqual({ ...input, deciding_constraint: "Liquidity cover" });
  });

  it("shows fractions as the percentages people type, without floating-point tails", () => {
    const form = toForm({ ...PROFILE, max_drawdown: 0.113, target_real_return: 0.07, holdings: { ...PROFILE.holdings, Debt: 0.1375 } });
    expect(form.maxDrawdown).toBe(11.3);
    expect(form.target).toBe(7);
    expect(form.holdings["Debt"]).toBe(13.75);
  });

  it("sends percentages back as fractions the server reads as the same number", () => {
    const form = toForm(PROFILE);
    form.maxDrawdown = 11.3;
    form.illiquid.expectedReturn = 7.25;
    const input = toInput(form)!;
    expect(input.max_drawdown).toBe(0.113);
    expect(input.illiquid.expected_return).toBe(0.0725);
  });

  it("trims the name and gives a blank illiquid description a plain default", () => {
    const form = toForm(PROFILE);
    form.name = "  Mehta family  ";
    form.illiquid.description = "   ";
    const input = toInput(form)!;
    expect(input.name).toBe("Mehta family");
    expect(input.illiquid.description).toBe("Illiquid holdings");
  });

  it("will not build a request while anything is missing", () => {
    const form = toForm(PROFILE);
    form.corpus = null;
    expect(toInput(form)).toBeNull();
    expect(check(form).map((c) => c.field)).toContain("corpus");
  });
});

describe("pythonSum", () => {
  it("adds like Python 3.12's sum(), where a plain sum differs in the last digit", () => {
    const shares = [0.2, 0.1, 0.305, 0.05, 0.1, 0.25];
    expect(shares.reduce((a, b) => a + b, 0)).toBe(1.005); // a plain left-to-right sum
    expect(pythonSum(shares)).toBe(1.0050000000000001); // what Python prints for the same list
  });

  it("handles empty lists, single values and cancelling values", () => {
    expect(pythonSum([])).toBe(0);
    expect(pythonSum([0.1])).toBe(0.1);
    expect(pythonSum([1e100, 1, -1e100])).toBe(1); // the compensation keeps the 1
  });
});

describe("the starter profile", () => {
  const classes = ["Large-cap equity", "Mid-cap equity", "Debt", "Gold", "Cash & liquid"];

  it("is valid as it stands, with the same numbers as the Streamlit starter", () => {
    const form = starterForm(classes);
    expect(check(form)).toEqual([]);
    expect(holdingsTotal(form)).toBe(100);
    const input = toInput(form)!;
    expect(input).toMatchObject({ corpus_cr: 100, annual_spending_cr: 3, horizon_years: 15, max_drawdown: 0.15, cover_months: 24, target_real_return: 0.04 });
    expect(input.one_offs).toEqual([{ year: 3, amount_cr: 5 }]);
    expect(input.holdings["Illiquid"]).toBe(0.25);
    expect(input.illiquid).toMatchObject({ description: "Real estate", expected_return: 0.08, volatility: 0.12, lock_in_years: 2, corr_with_equity: 0.2 });
  });
});

describe("telling whether anything changed", () => {
  it("ignores the ids of outflow rows, and notices a changed number", () => {
    const a = toForm(PROFILE);
    const b = toForm(PROFILE); // new row ids, same content
    expect(sameForm(a, b)).toBe(true);
    b.spending = 21;
    expect(sameForm(a, b)).toBe(false);
  });

  it("gives every outflow row its own id", () => {
    const ids = new Set([newRowId(), newRowId(), newRowId()]);
    expect(ids.size).toBe(3);
  });
});

describe("the messages", () => {
  it("name the real total when holdings do not add up", () => {
    const form = toForm(PROFILE);
    form.holdings["Debt"] = 10;
    expect(check(form).find((c) => c.field === "holdings")?.message).toBe("Holdings add up to 110.0%. They need to add up to 100%.");
  });

  it("say which outflow is wrong", () => {
    const form = toForm(PROFILE);
    form.oneOffs = [{ id: newRowId(), year: 99, amount: 5 }, { id: newRowId(), year: 2, amount: 0 }];
    const messages = check(form).map((c) => c.message);
    expect(messages).toContain("Outflow 1: the year must be a whole number from 1 to 15 (inside the horizon).");
    expect(messages).toContain("Outflow 2: the amount must be above zero.");
  });
});
