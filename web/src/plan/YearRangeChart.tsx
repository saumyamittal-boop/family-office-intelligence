import type { Strategy } from "../api/client";
import { ChartFrame } from "../charts/ChartFrame";
import { pct, signedPct } from "../format";
import { DataTable } from "../ui/DataTable";
import type { Column } from "../ui/DataTable";

export const STRATEGY_COLOR: Record<string, string> = {
  Protect: "var(--chart-debt)",
  Balance: "var(--chart-large)",
  Grow: "var(--chart-gold)",
};

const W = 640;
const LEFT = 118;
const RIGHT = 20;
const ROW = 58;
const TOP = 14;

/** How a year has turned out for each strategy in the sample history: bar = middle 80% of years, dot = median, cross = worst. */
export function YearRangeChart({ strategies }: { strategies: Strategy[] }) {
  const low = Math.min(...strategies.map((s) => s.year_range.worst));
  const high = Math.max(...strategies.map((s) => s.year_range.high));
  const pad = (high - low) * 0.06;
  const [min, max] = [low - pad, high + pad];
  const x = (v: number) => LEFT + ((v - min) / (max - min)) * (W - LEFT - RIGHT);
  const ticks: number[] = [];
  for (let t = Math.ceil(min * 10) / 10; t <= max + 1e-9; t = Math.round((t + 0.1) * 10) / 10) ticks.push(t);
  const height = TOP + ROW * strategies.length + 26;

  const summary = strategies
    .map(
      (s) =>
        `Strategy ${s.letter}: a typical year between ${signedPct(s.year_range.low)} and ${signedPct(s.year_range.high)}, median ${signedPct(s.year_range.median)}, worst ${signedPct(s.year_range.worst)}`,
    )
    .join("; ") + ".";

  const columns: Column<Strategy>[] = [
    { key: "s", header: "Strategy", rowHeader: true, cell: (s) => `${s.letter} · ${s.key}` },
    { key: "typical", header: "Typical year", align: "right", cell: (s) => `${signedPct(s.year_range.low)} to ${signedPct(s.year_range.high)}` },
    { key: "median", header: "Median year", align: "right", cell: (s) => signedPct(s.year_range.median) },
    { key: "worst", header: "Worst year", align: "right", cell: (s) => signedPct(s.year_range.worst) },
    { key: "best", header: "Best year", align: "right", cell: (s) => signedPct(s.year_range.best) },
  ];

  return (
    <ChartFrame
      title="How a year can turn out"
      description="What a year was like in the sample history, for each strategy"
      summary={summary}
      height="auto"
      table={<DataTable caption="Yearly outcomes in the history by strategy" columns={columns} rows={strategies} rowKey={(s) => s.key} />}
      chart={
        <svg viewBox={`0 0 ${W} ${height}`} className="range-chart" aria-hidden="true" focusable="false">
          {ticks.map((t) => (
            <g key={t}>
              <line x1={x(t)} x2={x(t)} y1={TOP - 6} y2={height - 24} stroke={Math.abs(t) < 1e-9 ? "var(--ink-2)" : "var(--chart-grid)"} strokeWidth={Math.abs(t) < 1e-9 ? 1.5 : 1} />
              <text x={x(t)} y={height - 8} textAnchor="middle" className="recharts-text">
                {pct(t, 0)}
              </text>
            </g>
          ))}
          {strategies.map((s, i) => {
            const y = TOP + i * ROW + ROW / 2;
            const color = STRATEGY_COLOR[s.key] ?? "var(--chart-cash)";
            const { low: lo, high: hi, median, worst } = s.year_range;
            return (
              <g key={s.key}>
                <text x={LEFT - 12} y={y} textAnchor="end" dominantBaseline="central" className="recharts-text range-label">
                  {s.letter} · {s.key}
                </text>
                <rect x={x(lo)} y={y - 10} width={Math.max(2, x(hi) - x(lo))} height={20} rx={5} fill={color} opacity={0.88} />
                <circle cx={x(median)} cy={y} r={6} fill="var(--surface)" stroke={color} strokeWidth={3} />
                <path
                  d={`M${x(worst) - 5} ${y - 5}l10 10M${x(worst) + 5} ${y - 5}l-10 10`}
                  stroke="var(--bad-ink)" strokeWidth={2.4} strokeLinecap="round"
                />
              </g>
            );
          })}
        </svg>
      }
    />
  );
}
