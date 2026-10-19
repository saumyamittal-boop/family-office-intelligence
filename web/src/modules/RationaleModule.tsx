import { ASSUMPTIONS } from "../content/assumptions";
import { pct, tidyText } from "../format";
import { Card } from "../ui/Card";
import { Banner } from "../ui/Status";
import { Pair } from "./Pair";
import { referenceOption } from "./types";
import type { ModuleContext, ModuleMode } from "./types";

const tone = (t: "good" | "warn" | "info") => (t === "good" ? "good" : t === "warn" ? "warn" : "info");

/** The reasons behind the chosen mix, what stands out in the numbers, and what limits the result. */
export function RationaleModule({ ctx, mode }: { ctx: ModuleContext; mode: ModuleMode }) {
  const { analysis, choice } = ctx;
  const reference = referenceOption(analysis, choice);
  if (!reference) return null;
  const p = reference.portfolio;
  const full = mode === "page";
  const reasons = full ? p.explanation : p.explanation.slice(0, 4);
  const notes = full ? [...reference.insights, ...analysis.comparison_insights] : reference.insights.slice(0, 2);

  return (
    <>
      <Pair mode={mode}>
        <Card title={`Why the ${p.label} mix`} subtitle={choice === "Current" ? "You are looking at your current mix, so this explains the Balanced recommendation." : undefined}>
          <ul className="reasons">
            {reasons.map((line) => (
              <li key={line}>{tidyText(line)}</li>
            ))}
          </ul>
          {!full && p.explanation.length > reasons.length && <p className="hint">{p.explanation.length - reasons.length} more reasons on the Recommendation page.</p>}
        </Card>
        {notes.length > 0 && (
          <Card title="What stands out">
            <div className="stack">
              {notes.map((note) => (
                <Banner key={note.body} tone={tone(note.tone)} title={note.title ? `${note.title}.` : undefined}>
                  {tidyText(note.body)}
                </Banner>
              ))}
            </div>
          </Card>
        )}
      </Pair>
      {full && <Limits ctx={ctx} />}
    </>
  );
}

/** What the model assumes and where it is weak, said plainly (requirement: methodology with limitations). */
function Limits({ ctx }: { ctx: ModuleContext }) {
  const options = ctx.analysis.options.map((o) => o.portfolio);
  const touched = [...new Set(options.flatMap((o) => o.bounds_hit))];
  const unconverged = options.filter((o) => !o.optimiser_converged);
  return (
    <Card title="How this was worked out, and its limits">
      <div className="stack-lg">
        <ul className="reasons">
          <li>
            Expected returns are half the sample-history average and half a long-run assumption (
            {Object.entries(ASSUMPTIONS.priors).map(([name, v]) => `${name.toLowerCase()} ${pct(v)}`).join(", ")}). Inflation is assumed at{" "}
            {pct(ASSUMPTIONS.inflation)} a year.
          </li>
          <li>Risk comes from monthly returns with correlations shrunk towards zero. Drawdown and CVaR use the daily history.</li>
          <li>A constrained optimiser balances expected return against risk and allocates the liquid part, inside the class limits in your profile.</li>
          <li>
            The three mixes sit{" "}
            {Object.entries(ASSUMPTIONS.riskPositions).map(([name, v]) => `${name} ${pct(v, 0)}`).join(", ")} of the way from the safest mix your limits
            allow to the highest-return one. If the worst drawdown would exceed your limit, risk is tightened until it fits.
          </li>
          <li>The target real return is reported, not enforced: a mix can fall short of it and still be the best one your limits allow.</li>
          <li>Illiquid holdings are held fixed and never traded. They count for nothing in the safety net, and they are the same in every mix.</li>
          <li>The history is synthetic sample data. These figures illustrate how the model reasons; they are not forecasts and not investment advice.</li>
          {touched.length > 0 && <li>Class limits shaped the result: {touched.join(", ")}.</li>}
        </ul>
        {unconverged.length > 0 && (
          <Banner tone="bad" title="Approximate result." critical>
            The optimiser did not report a clean solution for {unconverged.map((o) => o.label).join(", ")}. Treat those weights as approximate.
          </Banner>
        )}
        <p className="hint">Cover basis in force: {ctx.analysis.basis_label}. Data: {ctx.analysis.data_source}.</p>
      </div>
    </Card>
  );
}
