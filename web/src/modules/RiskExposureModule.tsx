import { useHistory } from "../api/hooks";
import { DrawdownChart } from "../charts/HistoryCharts";
import { pct } from "../format";
import { Card } from "../ui/Card";
import { QueryBlock } from "../ui/QueryBlock";
import { StatTile } from "../ui/StatTile";
import { useGlossary } from "../workspace/GlossaryContext";
import { Pair } from "./Pair";
import { shownFor } from "./types";
import type { ModuleContext, ModuleMode } from "./types";

/** How rough the ride has been: volatility, the worst fall against the person's limit, and the average bad month. */
export function RiskExposureModule({ ctx, mode }: { ctx: ModuleContext; mode: ModuleMode }) {
  const glossary = useGlossary();
  const history = useHistory(ctx.profileId, ctx.basis);
  const shown = shownFor(ctx.analysis, ctx.choice);
  const p = shown.portfolio;

  return (
    <>
      <div className="grid-tiles tiles-3">
        <StatTile label="Volatility" value={pct(p.vol)} sub="Annual, including illiquid holdings" onInfo={() => glossary.open("volatility")} />
        <StatTile
          label="Worst drawdown" value={pct(p.max_dd)} sub={p.dd_ok ? "Within your limit" : "Above your limit"}
          tone={p.dd_ok ? "good" : "bad"} onInfo={() => glossary.open("worstDrawdown")}
        />
        <StatTile label="95% 1-month CVaR" value={pct(p.cvar21)} sub="Average loss in the worst 5% of months" onInfo={() => glossary.open("cvar")} />
      </div>
      <Pair mode={mode}>
        <QueryBlock query={history} label="The drawdown history" rows={5}>
          {(h) => {
            const mine = h.portfolios.find((x) => x.label === p.label);
            return mine ? <DrawdownChart dates={h.dates} history={mine} limit={h.drawdown_limit} /> : null;
          }}
        </QueryBlock>
        {mode === "page" && (
          <Card title="How to read this">
            <ul className="reasons">
              <li>The mix is replayed over the sample years at constant weights, so this shows what the sample history would have done to it, not what will happen.</li>
              <li>Illiquid holdings accrue smoothly in the replay, so real drawdowns would look worse than shown.</li>
              <li>CVaR is the average loss across the worst 5% of rolling one-month stretches. It tells you what a bad month looks like, not how bad the worst could be.</li>
            </ul>
          </Card>
        )}
      </Pair>
    </>
  );
}
