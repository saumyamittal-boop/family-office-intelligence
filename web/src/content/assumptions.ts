/**
 * The protected financial assumptions, as quoted in explanations on screen.
 * Mirrors docs/protected-assumptions.md. assumptions.test.ts compares every value with the golden master of the
 * Python engine, so this file cannot drift from the model without a failing test.
 */
export const ASSUMPTIONS = {
  inflation: 0.045,
  priors: {
    "Large-cap equity": 0.11,
    "Mid-cap equity": 0.125,
    Debt: 0.07,
    Gold: 0.065,
    "Cash & liquid": 0.06,
  },
  /** How far from the safest mix to the highest-return mix each recommendation sits. */
  riskPositions: { Growth: 0.75, Balanced: 0.5, Defensive: 0.25 },
  haircuts: {
    "Cash & liquid": 0,
    Debt: 0.08,
    Gold: 0.15,
    "Large-cap equity": 0.3,
    "Mid-cap equity": 0.4,
  },
} as const;
