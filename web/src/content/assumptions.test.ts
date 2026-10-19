import { describe, expect, it } from "vitest";
import golden from "../../../tests/golden/engine_golden.json";
import { pct } from "../format";
import { ASSUMPTIONS } from "./assumptions";
import { GLOSSARY } from "./glossary";

const frozen = golden.assumptions;

describe("the assumptions quoted on screen match the frozen Python golden master", () => {
  it("inflation", () => expect(ASSUMPTIONS.inflation).toBe(frozen.inflation));
  it("long-run return priors", () => expect(ASSUMPTIONS.priors).toEqual(frozen.prior_returns));
  it("liquidity haircuts", () => expect(ASSUMPTIONS.haircuts).toEqual(frozen.haircuts));
  it("where Growth, Balanced and Defensive sit between the safest and the highest-return mix", () =>
    expect(Object.entries(ASSUMPTIONS.riskPositions)).toEqual(frozen.risk_positions));
});

describe("the glossary wording", () => {
  const text = (key: keyof typeof GLOSSARY) => [GLOSSARY[key].summary, ...GLOSSARY[key].how, ...GLOSSARY[key].limits].join(" ");

  it("quotes every prior and the inflation rate exactly as the model uses them", () => {
    const expected = text("expectedReturn");
    for (const value of Object.values(frozen.prior_returns)) expect(expected).toContain(pct(value));
    expect(expected).toContain(pct(frozen.inflation));
  });

  it("quotes every haircut", () => {
    const cover = text("liquidityCover");
    for (const value of Object.values(frozen.haircuts)) expect(cover).toContain(pct(value, 0));
  });

  it("never softens the limits: each entry says what the number does not tell you", () => {
    for (const entry of Object.values(GLOSSARY)) expect(entry.limits.length).toBeGreaterThan(0);
    expect(text("liquidityCover")).toMatch(/never limits the optimiser/);
    expect(text("worstDrawdown")).toMatch(/Illiquid holdings grow smoothly/);
    expect(text("expectedReturn")).toMatch(/not externally validated/);
  });
});
