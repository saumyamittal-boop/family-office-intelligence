import { describe, expect, it } from "vitest";
import { commitmentName, commitmentPhrase } from "./names";

describe("how a commitment is named in a sentence", () => {
  it("shows a preset kind in lower case", () => {
    expect(commitmentName({ kind: "Wedding" })).toBe("wedding");
    expect(commitmentName({ kind: "Medical or emergency" })).toBe("medical or emergency");
  });

  it("shows a custom expense by the name the family gave it, exactly as typed", () => {
    expect(commitmentName({ kind: "Custom", label: "Aarav's School Fees" })).toBe("Aarav's School Fees");
    expect(commitmentName({ kind: "Custom", label: "  a villa  " })).toBe("a villa");
  });

  it("falls back to a plain phrase when a custom expense has no name", () => {
    expect(commitmentName({ kind: "Custom" })).toBe("Custom expense");
    expect(commitmentName({ kind: "Custom", label: "   " })).toBe("Custom expense");
    expect(commitmentName({ kind: "Custom", label: null })).toBe("Custom expense");
  });

  it("builds the whole phrase with the year in the right number and the amount in rupees", () => {
    expect(commitmentPhrase({ kind: "Education", year: 5, amount_cr: 12 })).toBe("education in 5 years (₹12.0 Cr)");
    expect(commitmentPhrase({ kind: "Custom", label: "Yacht", year: 1, amount_cr: 4.25 })).toBe("Yacht in 1 year (₹4.3 Cr)");
  });
});
