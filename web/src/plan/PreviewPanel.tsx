import type { PlanPreview } from "../api/client";
import { cr, pct } from "../format";
import { Card } from "../ui/Card";
import { Banner } from "../ui/Status";
import { Skeleton } from "../ui/States";

/**
 * "What this means so far": a live read-out that follows the answers as they are typed. It keeps showing the previous
 * read-out while the next one loads, and says so, so it never blanks or jumps.
 */
export function PreviewPanel({ preview, updating, failed }: { preview: PlanPreview | undefined; updating: boolean; failed: boolean }) {
  return (
    <Card title="What this means so far" subtitle="Updates as you type" className="preview-card">
      <p className="preview-status" role="status">
        {updating ? "Updating…" : failed ? "Could not update just now" : "Up to date"}
      </p>
      <div className={`stack-lg preview-body ${updating ? "is-updating" : ""}`}>
        {!preview && !failed && (
          <div className="stack">
            <Skeleton height="2.2rem" />
            <Skeleton height="2.2rem" />
            <Skeleton height="5rem" />
          </div>
        )}

        {preview && preview.problems.length > 0 && (
          <Banner tone="warn" title="To fix before moving on:">
            <ul className="problem-list">
              {preview.problems.map((problem) => (
                <li key={problem}>{problem}</li>
              ))}
            </ul>
          </Banner>
        )}

        {preview && preview.corpus_cr !== null && preview.corpus_cr !== undefined && preview.safety_net && (
          <>
            <div className="mini-tiles">
              <div className="mini-tile">
                <span className="muted">Total wealth</span>
                <b>{cr(preview.corpus_cr, 0)}</b>
              </div>
              <div className="mini-tile">
                <span className="muted">Safety net ({preview.safety_net.months} months)</span>
                <b>{cr(preview.safety_net.required_cr)}</b>
              </div>
            </div>

            {preview.illiquid_share !== null && preview.illiquid_share !== undefined && (
              <figure className="split" style={{ margin: 0 }}>
                <div
                  className="split-bar"
                  role="img"
                  aria-label={`${pct(1 - preview.illiquid_share, 0)} can be invested; ${pct(preview.illiquid_share, 0)} is held in things that cannot be sold quickly`}
                >
                  <span className="split-liquid" style={{ width: `${(1 - preview.illiquid_share) * 100}%` }} />
                  <span className="split-illiquid" style={{ width: `${preview.illiquid_share * 100}%` }} />
                </div>
                <figcaption className="hint">
                  {cr(preview.liquid_cr ?? 0, 0)} can be invested · {cr(preview.illiquid_cr ?? 0, 0)} stays as it is
                </figcaption>
              </figure>
            )}

            <section aria-label="How your answers shape the plan">
              <h3 className="preview-heading">How your answers shape the plan</h3>
              <ul className="reasons">
                {preview.effects.map((line) => (
                  <li key={line}>{line}</li>
                ))}
              </ul>
            </section>
          </>
        )}
        {failed && !preview && <Banner tone="warn">The read-out could not be loaded. You can keep going; the strategies will still be worked out.</Banner>}
      </div>
    </Card>
  );
}
