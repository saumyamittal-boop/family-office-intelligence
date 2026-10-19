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
  { to: "/plan", label: "Plan my money", icon: "plan" },
  { to: "/recommendation", label: "Recommendation", icon: "recommendation" },
  { to: "/risk", label: "Risk and liquidity", icon: "risk" },
  { to: "/scenarios", label: "Scenarios", icon: "scenarios" },
  {
    to: "/holdings", label: "Holdings", icon: "holdings", arrivesInPhase: 5,
    description: "Import holdings from a CSV or Excel file, check them, and see them consolidated by asset class.",
  },
  { to: "/profile", label: "Family profile", icon: "profile" },
  {
    to: "/assistant", label: "Assistant", icon: "assistant", arrivesInPhase: 6,
    description: "Ask why a recommendation looks the way it does. Answers will come only from the model's own verified outputs.",
  },
];
