import { useId } from "react";
import type { RiskKey, Strategy } from "../api/client";
import { pct, signedCr, signedPct, times } from "../format";
import { Badge } from "../ui/Status";
import { STRATEGY_COLOR } from "./YearRangeChart";

/**
 * Strategy A, B and C side by side. The cards are radio buttons: choosing one shows its detail below. Each fact is a
 * row of words and numbers, so nothing depends on colour.
 */
export function StrategyCards({
  strategies,
  chosen,
  selected,
  onSelect,
  crashLabel,
}: {
  strategies: Strategy[];
  chosen: RiskKey;
  selected: RiskKey;
  onSelect: (key: RiskKey) => void;
  crashLabel: string;
}) {
  const name = useId();
  return (
    <fieldset className="strategy-cards">
      <legend className="sr-only">Choose a strategy to see what to buy and sell</legend>
      {strategies.map((s) => {
        const within = s.within_comfort_of[chosen] ?? false;
        const meets = s.meets_goal_of[chosen] ?? false;
        const rows: [string, string][] = [
          ["Expected a year", `${pct(s.portfolio.exp_return)} (${pct(s.portfolio.exp_real)} after inflation)`],
          ["Worst year in the history", signedPct(s.year_range.worst)],
          [crashLabel, `${signedPct(s.crash.value_change)} (${signedCr(s.crash.value_change_cr)})`],
          ["Safety net", `${times(s.cover_ratio)} what you need`],
          ["Meets your return goal", meets ? "Yes" : "Not quite"],
        ];
        return (
          <label key={s.key} className={`strategy-card ${selected === s.key ? "is-selected" : ""}`} style={{ ["--strategy" as string]: STRATEGY_COLOR[s.key] }}>
            <input type="radio" name={name} value={s.key} checked={selected === s.key} onChange={() => onSelect(s.key)} />
            <span className="strategy-body">
              <span className="strategy-head">
                <span className="strategy-letter" aria-hidden="true">{s.letter}</span>
                <b>
                  Strategy {s.letter}: {s.key}
                </b>
              </span>
              <span className="strategy-badges">
                {s.key === chosen && <Badge tone="good">Recommended for you</Badge>}
                <Badge tone={within ? "good" : "warn"}>{within ? "Within your comfort" : "Beyond your comfort"}</Badge>
              </span>
              <span className="strategy-range">
                {signedPct(s.year_range.low)} to {signedPct(s.year_range.high)}
              </span>
              <span className="muted strategy-range-label">In a typical year (the middle 80% of years in the history)</span>
              <dl className="strategy-facts">
                {rows.map(([k, v]) => (
                  <div key={k}>
                    <dt>{k}</dt>
                    <dd>{v}</dd>
                  </div>
                ))}
              </dl>
            </span>
          </label>
        );
      })}
    </fieldset>
  );
}
