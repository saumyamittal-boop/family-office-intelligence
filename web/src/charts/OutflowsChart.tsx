import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import type { Schemas } from "../api/client";
import { cr } from "../format";
import { DataTable } from "../ui/DataTable";
import type { Column } from "../ui/DataTable";
import { ChartFrame, ChartTooltip } from "./ChartFrame";
import type { TipItem } from "./ChartFrame";

type Row = Schemas["OutflowRow"];

const compact = (v: number) => cr(v, 0).replace(" Cr", "");

/** Planned spending plus dated one-off outflows, year by year. */
export function OutflowsChart({ rows }: { rows: Row[] }) {
  const total = rows.reduce((sum, r) => sum + r.total_cr, 0);
  const oneOff = rows.reduce((sum, r) => sum + r.one_off_cr, 0);
  const summary = `Planned outflows over the next ${rows.length} years total ${cr(total, 0)}, of which ${cr(oneOff, 0)} are one-off amounts.`;

  const columns: Column<Row>[] = [
    { key: "year", header: "Year", rowHeader: true, cell: (r) => String(r.year) },
    { key: "spending", header: "Spending", align: "right", cell: (r) => cr(r.spending_cr) },
    { key: "oneoff", header: "One-off", align: "right", cell: (r) => cr(r.one_off_cr) },
    { key: "total", header: "Total", align: "right", cell: (r) => cr(r.total_cr) },
  ];

  return (
    <ChartFrame
      title="Upcoming outflows"
      description="Spending grows with inflation; one-off amounts are as you entered them"
      summary={summary}
      table={<DataTable caption="Planned outflows by year" columns={columns} rows={rows} rowKey={(r) => String(r.year)} />}
      chart={
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={rows} margin={{ top: 8, right: 12, bottom: 4, left: 4 }}>
            <CartesianGrid stroke="var(--chart-grid)" vertical={false} />
            <XAxis dataKey="year" tickLine={false} axisLine={{ stroke: "var(--line)" }} tickFormatter={(y) => `Y${y}`} />
            <YAxis tickLine={false} axisLine={false} width={48} tickFormatter={compact} />
            <Tooltip
              cursor={{ fill: "var(--surface-2)" }}
              content={(p) => (
                <ChartTooltip
                  active={p.active}
                  payload={p.payload as unknown as TipItem[]}
                  label={p.label}
                  formatLabel={(l) => `Year ${l}`}
                  formatValue={(v) => cr(v)}
                />
              )}
            />
            <Bar dataKey="spending_cr" name="Spending" stackId="out" fill="var(--chart-cash)" isAnimationActive={false} />
            <Bar dataKey="one_off_cr" name="One-off" stackId="out" fill="var(--chart-gold)" radius={[4, 4, 0, 0]} isAnimationActive={false} />
          </BarChart>
        </ResponsiveContainer>
      }
    />
  );
}
