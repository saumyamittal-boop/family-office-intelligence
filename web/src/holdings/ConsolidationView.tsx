import type { ReactNode } from "react";
import type { Consolidation } from "../api/client";
import { useConsolidation } from "../api/hooks";
import { AllocationChart } from "../charts/AllocationChart";
import { cr, pct, signedPct } from "../format";
import { Card } from "../ui/Card";
import { DataTable } from "../ui/DataTable";
import type { Column } from "../ui/DataTable";
import { QueryBlock } from "../ui/QueryBlock";
import { EmptyState } from "../ui/States";
import { StatTile } from "../ui/StatTile";
import { accountName, className } from "./files";

/** "the same", or the signed difference between the imported total and the profile corpus. */
const gap = (crores: number) => (Math.abs(crores) < 0.05 ? "the same" : `${crores > 0 ? "+" : "−"}${cr(Math.abs(crores))}`);

type Row<T> = T & { key: string };

/** Everything the person imported, added up. Used in full on the Holdings page and in brief on the dashboard. */
export function ConsolidationView({ profileId, compact = false, empty }: { profileId: number; compact?: boolean; empty?: ReactNode }) {
  const query = useConsolidation(profileId);
  return (
    <QueryBlock query={query} label="Your holdings" rows={5}>
      {(c) =>
        c.lines === 0 ? (
          <EmptyState icon="holdings" title="No holdings imported yet" action={empty}>
            Import a statement to see everything you own in one place, by asset class and account.
          </EmptyState>
        ) : (
          <Body c={c} compact={compact} />
        )
      }
    </QueryBlock>
  );
}

function Body({ c, compact }: { c: Consolidation; compact: boolean }) {
  const named = c.by_account.filter((a) => a.account !== "").length;
  const shares = Object.fromEntries(c.by_class.map((x) => [x.asset_class, x.share]));
  return (
    <>
      <div className="grid-tiles tiles-3">
        <StatTile label="Total imported" value={cr(c.total_cr, 0)} sub={`${c.imports} import${c.imports === 1 ? "" : "s"}`} />
        <StatTile label="Holdings" value={String(c.lines)} sub="Lines across all imports" />
        <StatTile label="Accounts" value={String(named)} sub={named === 0 ? "None named in the files" : "Named in the files"} />
      </div>
      <AllocationChart title="Consolidated holdings" description="Share of everything you imported, by asset class" weights={shares} corpusCr={c.total_cr} wording={{ centre: "imported total", share: "Share of imported" }} />
      {!compact && <Details c={c} />}
    </>
  );
}

function Details({ c }: { c: Consolidation }) {
  const accountRows: Row<Consolidation["by_account"][number]>[] = c.by_account.map((a) => ({ ...a, key: a.account || "-" }));
  const accountCols: Column<Row<Consolidation["by_account"][number]>>[] = [
    { key: "a", header: "Account", rowHeader: true, cell: (r) => accountName(r.account) },
    { key: "t", header: "Total", align: "right", cell: (r) => cr(r.total_cr) },
    { key: "s", header: "Share", align: "right", cell: (r) => pct(r.share) },
    { key: "n", header: "Lines", align: "right", cell: (r) => String(r.lines) },
  ];
  const positionRows: Row<Consolidation["top_positions"][number]>[] = c.top_positions.map((p) => ({ ...p, key: `${p.name}|${p.asset_class}` }));
  const positionCols: Column<Row<Consolidation["top_positions"][number]>>[] = [
    { key: "n", header: "Holding", rowHeader: true, cell: (r) => r.name },
    { key: "c", header: "Asset class", cell: (r) => className(r.asset_class) },
    { key: "a", header: "Accounts", align: "right", cell: (r) => String(r.accounts) },
    { key: "v", header: "Value", align: "right", cell: (r) => cr(r.value_cr) },
    { key: "s", header: "Share", align: "right", cell: (r) => pct(r.share) },
  ];
  const compareRows: Row<Consolidation["compare"][number]>[] = c.compare.map((x) => ({ ...x, key: x.asset_class }));
  const compareCols: Column<Row<Consolidation["compare"][number]>>[] = [
    { key: "c", header: "Asset class", rowHeader: true, cell: (r) => className(r.asset_class) },
    { key: "i", header: "Imported", align: "right", cell: (r) => pct(r.imported_share) },
    { key: "p", header: "Profile now", align: "right", cell: (r) => pct(r.profile_share) },
    { key: "d", header: "Difference", align: "right", cell: (r) => (Math.abs(r.difference) < 0.0005 ? "Same" : signedPct(r.difference)) },
  ];
  return (
    <div className="stack-lg">
      <Card title="By account" subtitle="Where the money sits">
        <DataTable caption="Imported holdings by account" columns={accountCols} rows={accountRows} rowKey={(r) => r.key} />
      </Card>
      <Card title="Largest holdings" subtitle="The same name in several accounts is added together">
        <DataTable caption="The five largest holdings across all accounts" columns={positionCols} rows={positionRows} rowKey={(r) => r.key} />
      </Card>
      <Card
        title="Compared with your profile"
        subtitle={`Imported total ${cr(c.total_cr)} against a profile corpus of ${cr(c.profile_corpus_cr)} (${gap(c.difference_cr)})`}
      >
        <DataTable caption="Share of holdings by asset class: imported against the profile" columns={compareCols} rows={compareRows} rowKey={(r) => r.key} />
      </Card>
    </div>
  );
}
