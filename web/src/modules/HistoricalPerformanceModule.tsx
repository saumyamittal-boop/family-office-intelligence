import { useHistory } from "../api/hooks";
import { AnnualReturnsChart, HistoryValueChart } from "../charts/HistoryCharts";
import { pct, signedPct } from "../format";
import { Card } from "../ui/Card";
import { QueryBlock } from "../ui/QueryBlock";
import { StatTile } from "../ui/StatTile";
import { Pair } from "./Pair";
import { shownFor } from "./types";
import type { ModuleContext, ModuleMode } from "./types";

/** How the mix would have grown and fallen over the sample years, and how each calendar year went. */
export function HistoricalPerformanceModule({ ctx, mode }: { ctx: ModuleContext; mode: ModuleMode }) {
  const history = useHistory(ctx.profileId, ctx.basis);
  const shown = shownFor(ctx.analysis, ctx.choice);

  return (
    <QueryBlock query={history} label="The history" rows={5}>
      {(h) => {
        const mine = h.portfolios.find((x) => x.label === shown.portfolio.label);
        const current = h.portfolios.find((x) => x.label === "Current");
        if (!mine || !current) return null;
        // With the current mix on screen there is nothing to compare it to, so show every mix.
        const lines = shown.isCurrent ? h.portfolios : [current, mine];
        const years = [...mine.annual].sort((a, b) => a.portfolio_return - b.portfolio_return);
        const worst = years[0];
        const best = years[years.length - 1];
        const lost = years.filter((y) => y.portfolio_return < 0).length;
        const range = shown.detail?.year_range;
        return (
          <>
            <div className="grid-tiles tiles-3">
              <StatTile label="Best calendar year" value={best ? signedPct(best.portfolio_return) : "n/a"} sub={best ? String(best.year) : undefined} />
              <StatTile label="Worst calendar year" value={worst ? signedPct(worst.portfolio_return) : "n/a"} sub={worst ? String(worst.year) : undefined} tone={worst && worst.portfolio_return < 0 ? "warn" : "neutral"} />
              <StatTile label="Years that lost money" value={`${lost} of ${years.length}`} sub={`${shown.portfolio.label} mix`} />
            </div>
            <Pair mode={mode}>
              <HistoryValueChart dates={h.dates} lines={lines} />
              {mode === "page" && <AnnualReturnsChart history={mine} />}
            </Pair>
            {mode === "page" && range && (
              <Card title="A typical year" subtitle="Across every rolling 12-month stretch in the sample history">
                <div className="grid-tiles">
                  <StatTile label="Middle 80% of years" value={`${signedPct(range.low)} to ${signedPct(range.high)}`} />
                  <StatTile label="Median year" value={pct(range.median)} />
                  <StatTile label="Worst year" value={signedPct(range.worst)} tone="warn" />
                  <StatTile label="Best year" value={signedPct(range.best)} />
                </div>
              </Card>
            )}
            <p className="hint">{h.note}</p>
          </>
        );
      }}
    </QueryBlock>
  );
}
