import { useState } from "react";
import { ApiError } from "../api/client";
import type { ApplyResult } from "../api/client";
import { useApplyHoldings, useApplyPreview, useConsolidation } from "../api/hooks";
import { cr, pct, signedPct } from "../format";
import { Button, ButtonLink } from "../ui/Button";
import { Card } from "../ui/Card";
import { DataTable } from "../ui/DataTable";
import type { Column } from "../ui/DataTable";
import { Banner } from "../ui/Status";
import { className, HOLDING_CLASSES } from "./files";

type Row = { cls: string; before: number; after: number };

/** Using the imported holdings as the profile's own is a separate, deliberate step, with the change shown first. */
export function ApplyCard({ profileId, search }: { profileId: number; search: string }) {
  const consolidation = useConsolidation(profileId);
  const c = consolidation.data;
  const [setCorpus, setSetCorpus] = useState(false);
  const [done, setDone] = useState<ApplyResult | null>(null);
  const preview = useApplyPreview(c && c.lines > 0 ? profileId : null, setCorpus, c ? `${c.imports}:${c.lines}:${c.total_cr}` : "none");
  const apply = useApplyHoldings(profileId);

  if (!c || c.lines === 0) return null;
  const result = preview.data;
  const reasons = preview.error instanceof ApiError ? (preview.error.problems?.length ? preview.error.problems : [preview.error.message]) : [];

  const rows: Row[] = result ? HOLDING_CLASSES.map((cls) => ({ cls, before: result.before.shares[cls] ?? 0, after: result.after.shares[cls] ?? 0 })) : [];
  const columns: Column<Row>[] = [
    { key: "c", header: "Asset class", rowHeader: true, cell: (r) => className(r.cls) },
    { key: "b", header: "Profile now", align: "right", cell: (r) => pct(r.before) },
    { key: "a", header: "After using the imported holdings", align: "right", cell: (r) => pct(r.after) },
    { key: "d", header: "Change", align: "right", cell: (r) => (Math.abs(r.after - r.before) < 0.0005 ? "Same" : signedPct(r.after - r.before)) },
  ];

  return (
    <Card title="Use these holdings in your profile" subtitle="Your profile keeps its own numbers until you choose this. Only the asset-class shares change, and the corpus too if you tick the box.">
      <div className="stack-lg">
        <label className="check">
          <input type="checkbox" checked={setCorpus} onChange={(e) => { setSetCorpus(e.target.checked); setDone(null); }} />
          <span>Also set the profile's corpus to the imported total ({cr(c.total_cr, 1)})</span>
        </label>

        {reasons.length > 0 && (
          <Banner tone="warn" title="These holdings can't be used in the profile:" live>
            <ul className="reasons">{reasons.map((r) => <li key={r}>{r}</li>)}</ul>
          </Banner>
        )}
        {result && (
          <>
            <DataTable caption="Profile holdings now and after using the imported holdings" columns={columns} rows={rows} rowKey={(r) => r.cls} />
            <p className="hint">
              Corpus: {cr(result.before.corpus_cr)} now, {cr(result.after.corpus_cr)} after.
            </p>
            {result.notes.map((n) => <Banner key={n} tone="info">{n}</Banner>)}
          </>
        )}
        {done && (
          <Banner tone="good" live title="Your profile now uses these holdings.">
            The dashboard and analysis pages are recalculating with them.{" "}
            <ButtonLink to={{ pathname: "/", search }} variant="ghost">Open the dashboard</ButtonLink>
          </Banner>
        )}
        {apply.isError && !done && (
          <Banner tone="bad" critical>{apply.error instanceof ApiError ? apply.error.message : "The profile could not be updated."}</Banner>
        )}
        <div className="form-actions">
          <Button
            variant="primary" disabled={!result || !result.changed || apply.isPending || reasons.length > 0}
            onClick={() => apply.mutate(setCorpus, { onSuccess: (r) => setDone(r) })}
          >
            {apply.isPending ? "Updating…" : "Use these holdings in my profile"}
          </Button>
          {result && !result.changed && !done && <span className="muted">Your profile already matches these holdings.</span>}
        </div>
      </div>
    </Card>
  );
}
