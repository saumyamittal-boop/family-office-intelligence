import type { IconName } from "../ui/Icon";

export type NavItem = {
  to: string;
  label: string;
  icon: IconName;
  /** Set while the page is not built yet: the phase of the migration plan in which it arrives. */
  arrivesInPhase?: number;
  /** What the page will do, shown on its placeholder. */
  description?: string;
};

export const NAV: readonly NavItem[] = [
  { to: "/", label: "Overview", icon: "overview" },
  {
    to: "/plan", label: "Plan my money", icon: "plan", arrivesInPhase: 3,
    description: "A six-step guided plan in plain language: wealth, spending, upcoming commitments, comfort with a bad year, your safety net and what you own, ending in Strategy A, B and C.",
  },
  {
    to: "/recommendation", label: "Recommendation", icon: "recommendation", arrivesInPhase: 4,
    description: "Growth, Balanced and Defensive mixes with the full action plan, the reasons behind each, and the model's assumptions and limits.",
  },
  {
    to: "/risk", label: "Risk and liquidity", icon: "risk", arrivesInPhase: 4,
    description: "Historical drawdown replay, 95% one-month CVaR, the liquidity ladder and upcoming outflows.",
  },
  {
    to: "/scenarios", label: "Scenarios", icon: "scenarios", arrivesInPhase: 4,
    description: "Preset and custom stress tests, and a side-by-side comparison of your current mix and the alternatives.",
  },
  {
    to: "/holdings", label: "Holdings", icon: "holdings", arrivesInPhase: 5,
    description: "Import holdings from a CSV or Excel file, check them, and see them consolidated by asset class.",
  },
  {
    to: "/profile", label: "Family profile", icon: "profile", arrivesInPhase: 4,
    description: "Edit every input: corpus, holdings, outflows, limits, illiquid assets and targets, with several profiles per account.",
  },
  {
    to: "/assistant", label: "Assistant", icon: "assistant", arrivesInPhase: 6,
    description: "Ask why a recommendation looks the way it does. Answers will come only from the model's own verified outputs.",
  },
];
