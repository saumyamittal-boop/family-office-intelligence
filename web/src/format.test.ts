import { describe, expect, it } from "vitest";
import { cr, halfUp, pct, signedCr, signedPct, times } from "./format";
import vectors from "./test/format_vectors.json";

type Case = { value: number; digits: number; expected: string };
const all = vectors as unknown as Record<"pct" | "signed_pct" | "cr" | "signed_cr", Case[]>;

describe("formatters agree with the Python app on every recorded case", () => {
  const cases: [string, (v: number, d: number) => string, Case[]][] = [
    ["pct", pct, all.pct],
    ["signed_pct", signedPct, all.signed_pct],
    ["cr", cr, all.cr],
    ["signed_cr", signedCr, all.signed_cr],
  ];
  for (const [name, fn, rows] of cases) {
    it(`${name}: ${rows.length} cases`, () => {
      const wrong = rows
        .map((r) => ({ ...r, got: fn(r.value, r.digits) }))
        .filter((r) => r.got !== r.expected);
      expect(wrong.slice(0, 5)).toEqual([]);
    });
  }
});

describe("the figures the slide and the mentor care about", () => {
  it("rounds 13.75% up, which plain float formatting does not", () => {
    expect(pct(0.1375)).toBe("13.8%");
    expect(signedPct(-0.1375)).toBe("−13.8%");
    expect((1.005).toFixed(2)).toBe("1.00"); // plain toFixed is wrong for 1.005: it is stored as 1.00499999...
    expect(halfUp(1.005, 2)).toBe("1.01"); // settling float noise at 9 decimals first gives the expected answer
  });
  it("formats rupee amounts with thousands separators and a real minus sign", () => {
    expect(cr(1000)).toBe("₹1,000.0 Cr");
    expect(signedCr(-137.5)).toBe("−₹137.5 Cr");
    expect(signedCr(0)).toBe("+₹0.0 Cr");
  });
  it("never prints a negative rupee amount with a stray hyphen in signed form", () => {
    expect(signedCr(-39.7)).not.toContain("-");
  });
  it("shows n/a instead of NaN or Infinity", () => {
    for (const bad of [NaN, Infinity, -Infinity]) {
      expect(pct(bad)).toBe("n/a");
      expect(signedPct(bad)).toBe("n/a");
      expect(cr(bad)).toBe("n/a");
    }
  });
  it("formats cover ratios", () => {
    expect(times(0.4)).toBe("0.4x");
    expect(times(3.25)).toBe("3.3x");
  });
});
