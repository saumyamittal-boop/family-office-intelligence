import { ProjectionChart } from "../charts/ProjectionChart";
import { cr, pct } from "../format";
import { Card } from "../ui/Card";
import { DataTable } from "../ui/DataTable";
import type { Column } from "../ui/DataTable";
import { StatTile } from "../ui/StatTile";
import { referenceOption } from "./types";
import type { ModuleContext, ModuleMode } from "./types";

const ILLIQUID = "Illiquid";

/** What the family holds today, and how the corpus could grow after spending and planned outflows. */
export function NetWorthModule({ ctx, mode }: { ctx: ModuleContext; mode: ModuleMode }) {
  const { analysis, corpusCr, choice } = ctx;
  const reference = referenceOption(analysis, choice);
  const illiquidShare = analysis.current.weights_total[ILLIQUID] ?? 0;

  return (
    <>
      <div className="grid-tiles tiles-3">
        <StatTile label="Corpus today" value={cr(corpusCr, 0)} sub="Everything in the profile" />
        <StatTile label="Liquid part" value={cr(corpusCr * (1 - illiquidShare), 0)} sub="Can be bought and sold" />
        <StatTile label="Illiquid (held fixed)" value={cr(corpusCr * illiquidShare, 0)} sub={`${pct(illiquidShare, 0)} of the corpus, not traded by the model`} />
      </div>
      {reference && (
        <ProjectionChart current={analysis.current_projection} selected={reference.projection} selectedLabel={reference.portfolio.label} />
      )}
      {mode === "page" && <ProjectionTable ctx={ctx} />}
    </>
  );
}

type Row = { label: string; expected: number; real: number; endNominal: number; endReal: number };

/** Where each mix ends up at the horizon, for the current mix and each recommendation. */
function ProjectionTable({ ctx }: { ctx: ModuleContext }) {
  const { analysis } = ctx;
  const last = (rows: { year: number; nominal_cr: number; real_cr: number }[]) => rows[rows.length - 1];
  const items = [
    { portfolio: analysis.current, projection: analysis.current_projection },
    ...analysis.options.map((o) => ({ portfolio: o.portfolio, projection: o.projection })),
  ];
  const rows: Row[] = items.map(({ portfolio, projection }) => ({
    label: portfolio.label, expected: portfolio.exp_return, real: portfolio.exp_real,
    endNominal: last(projection)?.nominal_cr ?? 0, endReal: last(projection)?.real_cr ?? 0,
  }));
  const horizon = last(analysis.current_projection)?.year ?? 0;
  const columns: Column<Row>[] = [
    { key: "label", header: "Mix", rowHeader: true, cell: (r) => r.label },
    { key: "exp", header: "Expected return", align: "right", cell: (r) => pct(r.expected) },
    { key: "real", header: "After inflation", align: "right", cell: (r) => pct(r.real) },
    { key: "nom", header: `Corpus in year ${horizon}`, align: "right", cell: (r) => cr(r.endNominal, 0) },
    { key: "today", header: "In today's rupees", align: "right", cell: (r) => cr(r.endReal, 0) },
  ];
  return (
    <Card title="Where each mix ends up" subtitle="At its expected return, after spending and planned one-off outflows.">
      <DataTable caption="Expected return and projected corpus for each mix" columns={columns} rows={rows} rowKey={(r) => r.label} />
    </Card>
  );
}
