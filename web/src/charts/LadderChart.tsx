import { Bar, CartesianGrid, ComposedChart, Line, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import type { Schemas } from "../api/client";
import { cr } from "../format";
import { DataTable } from "../ui/DataTable";
import type { Column } from "../ui/DataTable";
import { ChartFrame, ChartTooltip } from "./ChartFrame";
import type { TipItem } from "./ChartFrame";

type Row = Schemas["LadderRow"];

const compact = (v: number) => cr(v, 0).replace(" Cr", "");

/** The first year in which the liquid assets run out, or null when they last the whole ladder. */
export function ladderRunsOut(rows: readonly Row[]): number | null {
  return rows.find((r) => r.liquid_value_cr < 0)?.year ?? null;
}

/** Yearly outflows against the liquid part of the corpus, projected at the mix's expected return. */
export function LadderChart({ rows, label }: { rows: Row[]; label: string }) {
  const runsOut = ladderRunsOut(rows);
  const last = rows[rows.length - 1];
  const summary = last
    ? `${label}: over ${rows.length} years the liquid assets go from ${cr(rows[0]?.liquid_value_cr ?? 0, 0)} in year 1 to ${cr(last.liquid_value_cr, 0)} in year ${last.year}, ` +
      `against ${cr(rows.reduce((sum, r) => sum + r.outflows_cr, 0), 0)} of outflows.` +
      (runsOut ? ` They run out in year ${runsOut}.` : "")
    : "No ladder available.";

  const columns: Column<Row>[] = [
    { key: "year", header: "Year", rowHeader: true, cell: (r) => String(r.year) },
    { key: "out", header: "Outflows", align: "right", cell: (r) => cr(r.outflows_cr) },
    { key: "liquid", header: "Liquid assets", align: "right", cell: (r) => cr(r.liquid_value_cr) },
    { key: "months", header: "Months of spending covered", align: "right", cell: (r) => r.months_covered.toFixed(0) },
  ];

  return (
    <ChartFrame
      title="Liquidity ladder"
      description="Yearly outflows and the liquid assets left, at the mix's expected return"
      summary={summary}
      table={<DataTable caption={`Liquidity ladder, ${label}`} columns={columns} rows={rows} rowKey={(r) => String(r.year)} />}
      chart={
        <ResponsiveContainer width="100%" height="100%">
          <ComposedChart data={rows} margin={{ top: 8, right: 12, bottom: 4, left: 4 }}>
            <CartesianGrid stroke="var(--chart-grid)" vertical={false} />
            <XAxis dataKey="year" tickLine={false} axisLine={{ stroke: "var(--line)" }} tickFormatter={(y) => `Y${y}`} />
            <YAxis tickLine={false} axisLine={false} width={52} tickFormatter={compact} />
            <Tooltip
              cursor={{ fill: "var(--surface-2)" }}
              content={(p) => (
                <ChartTooltip
                  active={p.active}
                  payload={p.payload as unknown as TipItem[]}
                  label={p.label}
                  formatLabel={(l) => `Year ${l}`}
                  formatValue={(v) => cr(v, 0)}
                />
              )}
            />
            <Bar dataKey="outflows_cr" name="Outflows" fill="var(--chart-gold)" radius={[4, 4, 0, 0]} isAnimationActive={false} />
            <Line
              type="monotone" dataKey="liquid_value_cr" name="Liquid assets" stroke="var(--chart-b)" strokeWidth={2.5}
              dot={{ r: 3 }} isAnimationActive={false}
            />
          </ComposedChart>
        </ResponsiveContainer>
      }
    />
  );
}
