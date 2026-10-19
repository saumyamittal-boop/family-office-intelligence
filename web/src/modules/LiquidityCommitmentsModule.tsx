import { LadderChart, ladderRunsOut } from "../charts/LadderChart";
import { OutflowsChart } from "../charts/OutflowsChart";
import { cr, times } from "../format";
import { StatTile } from "../ui/StatTile";
import { Banner } from "../ui/Status";
import { useGlossary } from "../workspace/GlossaryContext";
import { Pair } from "./Pair";
import { shownFor } from "./types";
import type { ModuleContext, ModuleMode } from "./types";

/** Whether the cash will be there when it is needed: the safety net, the ladder of yearly outflows, and what is coming. */
export function LiquidityCommitmentsModule({ ctx, mode }: { ctx: ModuleContext; mode: ModuleMode }) {
  const glossary = useGlossary();
  const shown = shownFor(ctx.analysis, ctx.choice);
  const { available_cover_cr: have, required_cover_cr: need } = shown.portfolio;
  const ratio = need > 0 ? have / need : Infinity;
  const runsOut = ladderRunsOut(shown.ladder);

  return (
    <>
      <div className="grid-tiles tiles-3">
        <StatTile label="Counted liquid assets" value={cr(have, 0)} sub="After haircuts" onInfo={() => glossary.open("liquidityCover")} />
        <StatTile label="Needed" value={cr(need, 0)} sub="Spending and one-off payments in the safety-net window" />
        <StatTile
          label="Cover" value={times(ratio)} sub="Counted assets divided by what is needed"
          tone={ratio >= 1.5 ? "good" : ratio >= 1 ? "warn" : "bad"}
        />
      </div>
      {runsOut !== null && (
        <Banner tone="bad" title="The liquid assets run out." critical>
          At expected returns, the liquid part of the {shown.portfolio.label} mix is spent by year {runsOut}.
        </Banner>
      )}
      <Pair mode={mode}>
        <LadderChart rows={shown.ladder} label={shown.portfolio.label} />
        {mode === "page" && <OutflowsChart rows={ctx.analysis.upcoming_outflows} />}
      </Pair>
      {mode === "page" && (
        <p className="hint">
          A steady projection at the mix's expected return. Proceeds from illiquid holdings after their lock-in are not included.
          Cover basis: {ctx.analysis.basis_label}.
        </p>
      )}
    </>
  );
}
