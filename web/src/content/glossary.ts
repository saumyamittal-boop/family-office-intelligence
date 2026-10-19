import { pct } from "../format";
import { ASSUMPTIONS } from "./assumptions";

export type GlossaryKey = "expectedReturn" | "volatility" | "worstDrawdown" | "liquidityCover" | "cvar";

export type GlossaryEntry = {
  title: string;
  /** One plain sentence. */
  summary: string;
  /** How the number is produced. */
  how: string[];
  /** What it does not tell you. These are never softened. */
  limits: string[];
};

const priors = Object.entries(ASSUMPTIONS.priors)
  .map(([name, value]) => `${name.toLowerCase()} ${pct(value)}`)
  .join(", ");

const haircuts = Object.entries(ASSUMPTIONS.haircuts)
  .map(([name, value]) => `${name.toLowerCase()} ${pct(value, 0)}`)
  .join(", ");

export const GLOSSARY: Record<GlossaryKey, GlossaryEntry> = {
  expectedReturn: {
    title: "Expected return",
    summary: "The average yearly growth the model expects for this mix, before tax and fees.",
    how: [
      `Each asset class's expected return is half its average in the sample history and half a long-run assumption (${priors}).`,
      "The classes are weighted by how much of the corpus sits in each. Illiquid holdings use the return assumed for them.",
      `"After inflation" divides by the ${pct(ASSUMPTIONS.inflation)} a year inflation assumption.`,
    ],
    limits: [
      "The long-run assumptions are drafts, not forecasts and not externally validated.",
      "The history is synthetic sample data, not real market data.",
    ],
  },
  volatility: {
    title: "Volatility",
    summary: "How much the value of this mix swings from year to year.",
    how: [
      "Measured from monthly returns of the five market asset classes, with their correlations shrunk towards zero so the estimate is not over-fitted.",
      "Illiquid holdings are included at the volatility assumed for them.",
    ],
    limits: [
      "Appraisal-based values look calmer than the true risk. Treat the volatility assumed for illiquid holdings as a floor.",
      "Volatility measures swings, not the chance of a loss of a given size.",
    ],
  },
  worstDrawdown: {
    title: "Worst drawdown",
    summary: "The biggest fall from a peak to a later low if you had held this mix through the sample history.",
    how: [
      "The mix is replayed day by day through the history at constant weights, with no trading costs.",
      "It is compared with the fall you said you could sit through. When a mix would have fallen further, the model lowers its risk until it fits, or tells you it cannot.",
    ],
    limits: [
      "Illiquid holdings grow smoothly in this replay, so real drawdowns would look worse than shown.",
      "A history cannot contain every bad outcome. A future fall can be larger.",
    ],
  },
  cvar: {
    title: "95% one-month CVaR",
    summary: "The average loss in the worst 5% of one-month stretches in the sample history.",
    how: [
      "The mix is replayed over the sample years at constant weights, and every rolling 21-trading-day stretch is measured.",
      "Take the worst 5% of those stretches and average their losses. That average is the number shown.",
    ],
    limits: [
      "It describes the sample history only. A worse month than any in the sample is possible, and the sample here is synthetic.",
      "Illiquid holdings are assumed to grow smoothly in the replay, so the true figure would be higher than shown.",
    ],
  },
  liquidityCover: {
    title: "Liquidity cover",
    summary: "How many times the money you can reach quickly covers the outflows you have to meet.",
    how: [
      "Counted assets divided by planned spending plus dated one-off outflows over your safety-net window.",
      `Each class counts after a haircut for how much it could lose when sold in a hurry (${haircuts}). Illiquid holdings never count.`,
      "The stricter basis counts only cash, debt and gold, and ignores equities.",
    ],
    limits: [
      "For the demo families this requirement never limits the optimiser, because the class limits already keep far more than needed in counted assets. A high cover is mostly a result of those limits.",
      "The haircuts are drafts, not market-tested values.",
    ],
  },
};
