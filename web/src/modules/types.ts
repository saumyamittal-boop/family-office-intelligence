import type { Analysis, Basis, PortfolioDetail, PortfolioOut, Schemas } from "../api/client";

/** What every module needs to draw itself. `choice` is "Current" or the label of a recommended mix. */
export type ModuleContext = {
  analysis: Analysis;
  profileId: number;
  corpusCr: number;
  basis: Basis;
  choice: string;
};

/** `card` is the glance on the dashboard; `page` is the full version on the analyst pages. */
export type ModuleMode = "card" | "page";

export type Shown = {
  portfolio: PortfolioOut;
  /** Undefined for the current mix, which has no action plan (there is nothing to move to). */
  detail: PortfolioDetail | undefined;
  projection: Schemas["ProjectionRow"][];
  ladder: Schemas["LadderRow"][];
  scenarios: Schemas["ScenarioRow"][];
  isCurrent: boolean;
};

/** The chosen portfolio's numbers, whether it is the current mix or one of the recommendations. */
export function shownFor(analysis: Analysis, choice: string): Shown {
  const detail = analysis.options.find((o) => o.portfolio.label === choice);
  if (!detail) {
    return {
      portfolio: analysis.current, detail: undefined, projection: analysis.current_projection,
      ladder: analysis.current_ladder, scenarios: analysis.current_scenarios, isCurrent: true,
    };
  }
  return {
    portfolio: detail.portfolio, detail, projection: detail.projection, ladder: detail.ladder,
    scenarios: detail.scenarios, isCurrent: false,
  };
}

export const DEFAULT_CHOICE = "Balanced";

/** The recommendation that explanations and comparisons are about when "Current" is on screen. */
export function referenceOption(analysis: Analysis, choice: string): PortfolioDetail | undefined {
  return (
    analysis.options.find((o) => o.portfolio.label === choice) ??
    analysis.options.find((o) => o.portfolio.label === DEFAULT_CHOICE) ??
    analysis.options[0]
  );
}
