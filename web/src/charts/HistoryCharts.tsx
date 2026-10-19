import { Area, AreaChart, Bar, BarChart, CartesianGrid, Cell, Line, LineChart, ReferenceLine, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import type { PortfolioHistory } from "../api/client";
import { pct, signedPct } from "../format";
import { DataTable } from "../ui/DataTable";
import type { Column } from "../ui/DataTable";
import { ChartFrame, ChartTooltip } from "./ChartFrame";
import type { TipItem } from "./ChartFrame";

const year = (isoDate: string) => isoDate.slice(0, 4);

/** The first date of each calendar year, used as the x-axis ticks so every label is a different year. */
export function yearTicks(dates: readonly string[]): string[] {
  const seen = new Set<string>();
  const ticks: string[] = [];
  for (const d of dates) {
    if (!seen.has(year(d))) {
      seen.add(year(d));
      ticks.push(d);
    }
  }
  return ticks;
}

type YearRow = { year: string; end: number[]; deepest: number };

/** One row per calendar year: where each series ended the year, and the deepest fall of `drawdown` within it. */
export function yearRows(dates: readonly string[], series: readonly (readonly number[])[], drawdown: readonly number[]): YearRow[] {
  const rows = new Map<string, YearRow>();
  dates.forEach((d, i) => {
    const y = year(d);
    const row = rows.get(y) ?? { year: y, end: [], deepest: 0 };
    row.end = series.map((s) => s[i] ?? 0);
    row.deepest = Math.min(row.deepest, drawdown[i] ?? 0);
    rows.set(y, row);
  });
  return [...rows.values()];
}

const growth = (v: number) => v.toFixed(1);

const LINE_STYLE: Record<string, { stroke: string; dash?: string }> = {
  Current: { stroke: "var(--chart-a)", dash: "7 5" },
  Growth: { stroke: "var(--chart-large)" },
  Balanced: { stroke: "var(--chart-b)" },
  Defensive: { stroke: "var(--chart-gold)", dash: "2 4" },
};

/** Growth of 100 invested at the start of the sample, for the current mix and the chosen recommendation(s). */
export function HistoryValueChart({ dates, lines }: { dates: readonly string[]; lines: PortfolioHistory[] }) {
  const rows = dates.map((date, i) => {
    const row: Record<string, number | string> = { date };
    for (const l of lines) row[l.label] = l.value[i] ?? 0;
    return row;
  });
  const first = dates[0] ?? "";
  const lastDate = dates[dates.length - 1] ?? "";
  const summary =
    `Growth of 100 invested on ${first}, to ${lastDate}: ` +
    lines.map((l) => `${l.label} ends at ${growth(l.value[l.value.length - 1] ?? 100)}`).join(", ") +
    ". Past sample returns do not predict future ones.";

  const table = yearRows(dates, lines.map((l) => l.value), lines[0]?.drawdown ?? []);
  const columns: Column<YearRow>[] = [
    { key: "year", header: "Year end", rowHeader: true, cell: (r) => r.year },
    ...lines.map((l, i) => ({ key: l.label, header: l.label, align: "right" as const, cell: (r: YearRow) => growth(r.end[i] ?? 0) })),
  ];

  return (
    <ChartFrame
      title="Value of 100 invested"
      description="The same mix, held constant, replayed over the sample years"
      summary={summary}
      table={<DataTable caption="Value of 100 invested, at the end of each year" columns={columns} rows={table} rowKey={(r) => r.year} />}
      chart={
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={rows} margin={{ top: 8, right: 12, bottom: 4, left: 4 }}>
            <CartesianGrid stroke="var(--chart-grid)" vertical={false} />
            <XAxis dataKey="date" ticks={yearTicks(dates)} tickFormatter={year} tickLine={false} axisLine={{ stroke: "var(--line)" }} />
            <YAxis tickLine={false} axisLine={false} width={44} domain={["auto", "auto"]} tickFormatter={(v: number) => v.toFixed(0)} />
            <Tooltip
              content={(p) => (
                <ChartTooltip active={p.active} payload={p.payload as unknown as TipItem[]} label={p.label} formatValue={growth} />
              )}
            />
            {lines.map((l) => (
              <Line
                key={l.label} type="monotone" dataKey={l.label} name={l.label} dot={false} strokeWidth={2.25}
                stroke={LINE_STYLE[l.label]?.stroke ?? "var(--chart-cash)"} strokeDasharray={LINE_STYLE[l.label]?.dash}
                isAnimationActive={false}
              />
            ))}
          </LineChart>
        </ResponsiveContainer>
      }
    />
  );
}

/** How far the mix fell from its previous peak, with the person's own limit drawn across it. */
export function DrawdownChart({ dates, history, limit }: { dates: readonly string[]; history: PortfolioHistory; limit: number }) {
  const rows = dates.map((date, i) => ({ date, drawdown: history.drawdown[i] ?? 0 }));
  let deepestAt = 0;
  history.drawdown.forEach((v, i) => {
    if (v < (history.drawdown[deepestAt] ?? 0)) deepestAt = i;
  });
  const within = history.max_drawdown <= limit;
  const summary =
    `${history.label}: the worst fall from a previous peak was ${pct(history.max_drawdown)}, around ${dates[deepestAt] ?? "n/a"}. ` +
    `Your limit is ${pct(limit, 0)}, so this is ${within ? "within" : "above"} it.`;

  const perYear = yearRows(dates, [history.value], history.drawdown);
  const columns: Column<YearRow>[] = [
    { key: "year", header: "Year", rowHeader: true, cell: (r) => r.year },
    { key: "deepest", header: "Deepest fall in the year", align: "right", cell: (r) => (r.deepest === 0 ? "None" : signedPct(r.deepest)) },
  ];

  return (
    <ChartFrame
      title="Drawdown against your limit"
      description="Fall from the previous peak. The dashed line is the fall you said you could sit through."
      summary={summary}
      table={<DataTable caption={`Deepest fall in each year, ${history.label}`} columns={columns} rows={perYear} rowKey={(r) => r.year} />}
      chart={
        <ResponsiveContainer width="100%" height="100%">
          <AreaChart data={rows} margin={{ top: 8, right: 12, bottom: 4, left: 4 }}>
            <CartesianGrid stroke="var(--chart-grid)" vertical={false} />
            <XAxis dataKey="date" ticks={yearTicks(dates)} tickFormatter={year} tickLine={false} axisLine={{ stroke: "var(--line)" }} />
            <YAxis
              tickLine={false} axisLine={false} width={48} tickFormatter={(v: number) => pct(v, 0)}
              domain={[(min: number) => Math.min(min * 1.1, -limit * 1.25), 0]}
            />
            <Tooltip
              content={(p) => (
                <ChartTooltip active={p.active} payload={p.payload as unknown as TipItem[]} label={p.label} formatValue={(v) => signedPct(v)} />
              )}
            />
            <Area
              type="monotone" dataKey="drawdown" name="Drawdown" stroke="var(--chart-illiquid)" strokeWidth={1.75}
              fill="var(--chart-illiquid)" fillOpacity={0.18} isAnimationActive={false}
            />
            <ReferenceLine
              y={-limit} stroke="var(--ink)" strokeDasharray="6 4" ifOverflow="extendDomain"
              label={{ value: `Your limit ${pct(limit, 0)}`, position: "insideBottomRight", className: "recharts-text" }}
            />
          </AreaChart>
        </ResponsiveContainer>
      }
    />
  );
}

/** Each calendar year's return for one mix. Part years are marked in the table and the axis. */
export function AnnualReturnsChart({ history }: { history: PortfolioHistory }) {
  const rows = history.annual.map((a) => ({ ...a, label: a.partial ? `${a.year}*` : String(a.year) }));
  const best = [...rows].sort((a, b) => b.portfolio_return - a.portfolio_return)[0];
  const worst = [...rows].sort((a, b) => a.portfolio_return - b.portfolio_return)[0];
  const negatives = rows.filter((r) => r.portfolio_return < 0).length;
  const summary =
    best && worst
      ? `${history.label}: ${negatives} of ${rows.length} calendar years lost money. The best was ${best.year} at ${signedPct(best.portfolio_return)}; the worst was ${worst.year} at ${signedPct(worst.portfolio_return)}.`
      : "No calendar years available.";

  const columns: Column<(typeof rows)[number]>[] = [
    { key: "year", header: "Year", rowHeader: true, cell: (r) => (r.partial ? `${r.year} (part year)` : String(r.year)) },
    { key: "ret", header: "Return", align: "right", cell: (r) => signedPct(r.portfolio_return) },
    { key: "days", header: "Trading days", align: "right", cell: (r) => String(r.trading_days) },
  ];

  return (
    <ChartFrame
      title="Calendar-year returns"
      description={rows.some((r) => r.partial) ? "A * marks a year with only part of its days in the sample." : "Each full calendar year in the sample."}
      summary={summary}
      table={<DataTable caption={`Return in each calendar year, ${history.label}`} columns={columns} rows={rows} rowKey={(r) => String(r.year)} />}
      chart={
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={rows} margin={{ top: 8, right: 12, bottom: 4, left: 4 }}>
            <CartesianGrid stroke="var(--chart-grid)" vertical={false} />
            <XAxis dataKey="label" tickLine={false} axisLine={{ stroke: "var(--line)" }} />
            <YAxis tickLine={false} axisLine={false} width={48} tickFormatter={(v: number) => pct(v, 0)} />
            <ReferenceLine y={0} stroke="var(--line)" />
            <Tooltip
              cursor={{ fill: "var(--surface-2)" }}
              content={(p) => (
                <ChartTooltip active={p.active} payload={p.payload as unknown as TipItem[]} label={p.label} formatValue={(v) => signedPct(v)} />
              )}
            />
            <Bar dataKey="portfolio_return" name="Return" radius={3} isAnimationActive={false}>
              {rows.map((r) => (
                <Cell key={r.year} fill={r.portfolio_return >= 0 ? "var(--chart-debt)" : "var(--chart-illiquid)"} />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      }
    />
  );
}
