import { Bar, BarChart, CartesianGrid, Cell, LabelList, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import type { Schemas } from "../api/client";
import { cr, pct, signedCr, signedPct, times } from "../format";
import { DataTable } from "../ui/DataTable";
import type { Column } from "../ui/DataTable";
import { Badge } from "../ui/Status";
import { ChartFrame, ChartTooltip } from "./ChartFrame";
import type { TipItem } from "./ChartFrame";

type Row = Schemas["CompareRow"];

type LabelGeometry = { x?: number | string; y?: number | string; width?: number | string; height?: number | string; index?: number };

/** A bar's value, written just left of the bar's end. Works whichever way the bar's geometry is signed. */
function BarValueLabel({ x, y, width, height, index, bars }: LabelGeometry & { bars: { label: string }[] }) {
  const [bx, by, w, h] = [Number(x), Number(y), Number(width), Number(height)];
  const row = bars[index ?? -1];
  if (!row || [bx, by, w, h].some(Number.isNaN)) return null;
  return (
    <text x={Math.min(bx, bx + w) - 8} y={by + h / 2} textAnchor="end" dominantBaseline="central" className="recharts-text">
      {row.label}
    </text>
  );
}

/** One stress scenario applied to the current mix and each alternative, side by side. */
export function ScenarioChart({ scenario, rows }: { scenario: string; rows: Row[] }) {
  // The value label says "short" in words when the safety net is not met, so colour is never the only cue.
  const bars = rows.map((r) => ({ ...r, label: `${signedCr(r.value_change_cr)}${r.cover_held ? "" : " · short"}` }));
  const summary =
    `Under "${scenario}": ` +
    rows
      .map((r) => `${r.option} ${signedCr(r.value_change_cr)} (${signedPct(r.value_change)}), safety net ${r.cover_held ? "held" : "short"} at ${times(r.cover_ratio_after)}`)
      .join("; ") +
    ".";

  const columns: Column<Row>[] = [
    { key: "option", header: "Option", rowHeader: true, cell: (r) => r.option },
    { key: "change", header: "Value change", align: "right", cell: (r) => `${signedCr(r.value_change_cr)} (${signedPct(r.value_change)})` },
    { key: "return", header: "Expected return", align: "right", cell: (r) => pct(r.exp_return) },
    {
      key: "cover", header: "Safety net after", align: "right",
      cell: (r) => (
        <>
          {times(r.cover_ratio_after)} <Badge tone={r.cover_held ? "good" : "bad"}>{r.cover_held ? "Held" : "Short"}</Badge>
        </>
      ),
    },
  ];

  return (
    <ChartFrame
      title={`Compare your options: ${scenario}`}
      description="Change in the corpus if the scenario happens today. Rust bars: the safety net would not be met."
      summary={summary}
      height={`${6 + rows.length * 3.2}rem`}
      table={<DataTable caption={`Options compared under ${scenario}`} columns={columns} rows={rows} rowKey={(r) => r.option} />}
      chart={
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={bars} layout="vertical" margin={{ top: 4, right: 12, bottom: 4, left: 4 }}>
            <CartesianGrid stroke="var(--chart-grid)" horizontal={false} />
            <XAxis
              type="number" tickLine={false} axisLine={false} tickFormatter={(v: number) => cr(v, 0).replace(" Cr", "")}
              domain={[(min: number) => Math.floor(min * 1.9), 0]} // room on the left for each bar's value label
            />
            <YAxis type="category" dataKey="option" width={84} tickLine={false} axisLine={{ stroke: "var(--line)" }} />
            <Tooltip
              cursor={{ fill: "var(--surface-2)" }}
              content={(p) => (
                <ChartTooltip
                  active={p.active}
                  payload={p.payload as unknown as TipItem[]}
                  label={p.label}
                  formatValue={(v) => signedCr(v)}
                />
              )}
            />
            <Bar dataKey="value_change_cr" name="Value change" radius={4} isAnimationActive={false}>
              {bars.map((r) => (
                <Cell key={r.option} fill={r.cover_held ? "var(--chart-debt)" : "var(--chart-illiquid)"} />
              ))}
              <LabelList content={(p) => <BarValueLabel {...(p as unknown as LabelGeometry)} bars={bars} />} />
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      }
    />
  );
}
