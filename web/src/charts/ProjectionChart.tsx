import { useState } from "react";
import { CartesianGrid, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import type { Schemas } from "../api/client";
import { cr } from "../format";
import { SegmentedControl } from "../ui/Controls";
import { DataTable } from "../ui/DataTable";
import type { Column } from "../ui/DataTable";
import { ChartFrame, ChartTooltip } from "./ChartFrame";
import type { TipItem } from "./ChartFrame";

type Projection = Schemas["ProjectionRow"][];
type Basis = "real" | "nominal";
type Row = { year: number; current: number; selected: number };

const compact = (v: number) => cr(v, 0).replace(" Cr", "");

/** The corpus year by year at each mix's expected return, after spending and one-off outflows. */
export function ProjectionChart({
  current,
  selected,
  selectedLabel,
}: {
  current: Projection;
  selected: Projection;
  selectedLabel: string;
}) {
  const [basis, setBasis] = useState<Basis>("real");
  const pick = (row: Schemas["ProjectionRow"]) => (basis === "real" ? row.real_cr : row.nominal_cr);
  const rows: Row[] = current.map((row, i) => ({ year: row.year, current: pick(row), selected: pick(selected[i] ?? row) }));
  const last = rows[rows.length - 1];
  const unit = basis === "real" ? "in today's rupees" : "in nominal rupees";

  const summary = last
    ? `Over ${last.year} years, ${unit}, the current mix goes from ${cr(rows[0]?.current ?? 0, 0)} to ${cr(last.current, 0)} ` +
      `and the ${selectedLabel} mix to ${cr(last.selected, 0)}, after spending and planned outflows.`
    : "No projection available.";

  const columns: Column<Row>[] = [
    { key: "year", header: "Year", rowHeader: true, cell: (r) => String(r.year) },
    { key: "current", header: "Current mix", align: "right", cell: (r) => cr(r.current, 0) },
    { key: "selected", header: `${selectedLabel} mix`, align: "right", cell: (r) => cr(r.selected, 0) },
  ];

  return (
    <ChartFrame
      title="How the corpus could grow"
      description={`Expected path ${unit}, after spending and planned outflows`}
      summary={summary}
      extraActions={
        <SegmentedControl<Basis>
          label="Rupee basis"
          value={basis}
          onChange={setBasis}
          options={[
            { value: "real", label: "Today's rupees" },
            { value: "nominal", label: "Nominal" },
          ]}
        />
      }
      table={<DataTable caption="Projected corpus by year" columns={columns} rows={rows} rowKey={(r) => String(r.year)} />}
      chart={
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={rows} margin={{ top: 8, right: 12, bottom: 4, left: 4 }}>
            <CartesianGrid stroke="var(--chart-grid)" vertical={false} />
            <XAxis dataKey="year" tickLine={false} axisLine={{ stroke: "var(--line)" }} tickFormatter={(y) => `Y${y}`} />
            <YAxis tickLine={false} axisLine={false} width={56} tickFormatter={compact} />
            <Tooltip
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
            <Line
              type="monotone" dataKey="current" name="Current mix" stroke="var(--chart-a)" strokeWidth={2.5}
              strokeDasharray="7 5" dot={false} isAnimationActive={false}
            />
            <Line
              type="monotone" dataKey="selected" name={`${selectedLabel} mix`} stroke="var(--chart-b)" strokeWidth={2.5}
              dot={false} isAnimationActive={false}
            />
          </LineChart>
        </ResponsiveContainer>
      }
    />
  );
}
