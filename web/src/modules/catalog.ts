import type { ModuleId } from "../api/client";
import type { IconName } from "../ui/Icon";

export type ModuleInfo = {
  title: string;
  /** One sentence, shown in the customise panel. */
  summary: string;
  icon: IconName;
  /** The analyst page that shows this module in full. */
  page: "/recommendation" | "/risk" | "/scenarios" | "/holdings";
  pageLabel: string;
};

/** What each dashboard module is called and where its full version lives. The server only knows the ids. */
export const MODULES: Record<ModuleId, ModuleInfo> = {
  allocation_actions: {
    title: "Allocation and actions",
    summary: "How your money is divided today and exactly what to buy or sell to reach a recommended mix.",
    icon: "recommendation", page: "/recommendation", pageLabel: "Recommendation",
  },
  liquidity_commitments: {
    title: "Liquidity and commitments",
    summary: "Whether the cash will be there when it is needed: the safety net, yearly outflows and planned one-off payments.",
    icon: "risk", page: "/risk", pageLabel: "Risk and liquidity",
  },
  risk_exposure: {
    title: "Risk exposure",
    summary: "How rough the ride has been in the sample history, against the fall you said you could sit through.",
    icon: "risk", page: "/risk", pageLabel: "Risk and liquidity",
  },
  stress_scenarios: {
    title: "Stress scenarios",
    summary: "What a crash, an inflation spike, a large bill or a lost decade would do to the chosen mix.",
    icon: "scenarios", page: "/scenarios", pageLabel: "Scenarios",
  },
  net_worth_projection: {
    title: "Net worth and projection",
    summary: "What the family holds today and how the corpus could grow, after spending and planned outflows.",
    icon: "overview", page: "/recommendation", pageLabel: "Recommendation",
  },
  historical_performance: {
    title: "Historical performance",
    summary: "How the mix would have grown and fallen over the sample years, and how each calendar year went.",
    icon: "chart", page: "/risk", pageLabel: "Risk and liquidity",
  },
  recommendation_rationale: {
    title: "Why this recommendation",
    summary: "The reasons behind the chosen mix, what stands out, and the limits of the result.",
    icon: "info", page: "/recommendation", pageLabel: "Recommendation",
  },
  holdings_consolidation: {
    title: "Holdings consolidation",
    summary: "Everything held across accounts, imported from a file and combined by asset class.",
    icon: "holdings", page: "/holdings", pageLabel: "Holdings",
  },
};

export const MODULE_ORDER = Object.keys(MODULES) as ModuleId[];
