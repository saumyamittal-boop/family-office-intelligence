import { useId } from "react";
import { Cell, Pie, PieChart, ResponsiveContainer, Tooltip } from "recharts";
import { cr, pct } from "../format";
import { DataTable } from "../ui/DataTable";
import type { Column } from "../ui/DataTable";
import { ChartFrame, ChartTooltip } from "./ChartFrame";
import type { TipItem } from "./ChartFrame";
import { classColor, HATCH_CSS } from "./colors";

const ILLIQUID = "Illiquid";

type Row = { name: string; share: number; amountCr: number };

/** The mix as a donut with a legend, and as a table. Shares are fractions of the whole corpus. */
export function AllocationChart({
  title,
  weights,
  corpusCr,
  description = "Share of the whole corpus by asset class",
  wording = { centre: "total corpus", share: "Share of corpus" },
}: {
  title: string;
  weights: Record<string, number>;
  corpusCr: number;
  description?: string;
  /** What the centre of the donut and the share column call the whole: "corpus" unless the mix is of something else. */
  wording?: { centre: string; share: string };
}) {
  const patternId = useId().replace(/:/g, "");
  const names = [...Object.keys(weights).filter((n) => n !== ILLIQUID), ILLIQUID].filter((n) => n in weights);
  const rows: Row[] = names.map((name) => ({ name, share: weights[name] ?? 0, amountCr: (weights[name] ?? 0) * corpusCr }));
  const shown = rows.filter((r) => r.share > 0);

  const label = (name: string) => (name === ILLIQUID ? "Illiquid (fixed)" : name);
  const summary =
    `${title}: ` + shown.map((r) => `${label(r.name)} ${pct(r.share)}`).join(", ") + `, of ${cr(corpusCr, 0)}.`;

  const columns: Column<Row>[] = [
    { key: "class", header: "Asset class", rowHeader: true, cell: (r) => label(r.name) },
    { key: "share", header: wording.share, align: "right", cell: (r) => pct(r.share) },
    { key: "amount", header: "Amount", align: "right", cell: (r) => cr(r.amountCr) },
  ];

  return (
    <ChartFrame
      title={title}
      description={description}
      summary={summary}
      height="auto"
      table={<DataTable caption={title} columns={columns} rows={rows} rowKey={(r) => r.name} />}
      chart={
        <div className="donut-layout">
          <div className="donut-wrap">
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <defs>
                  <pattern id={patternId} patternUnits="userSpaceOnUse" width="7" height="7" patternTransform="rotate(45)">
                    <rect width="7" height="7" fill="var(--chart-illiquid)" />
                    <rect width="3" height="7" fill="var(--surface)" opacity="0.6" />
                  </pattern>
                </defs>
                <Pie
                  data={shown}
                  dataKey="share"
                  nameKey="name"
                  innerRadius="64%"
                  outerRadius="100%"
                  startAngle={90}
                  endAngle={-270}
                  paddingAngle={1}
                  stroke="var(--surface)"
                  strokeWidth={2}
                  isAnimationActive={false}
                >
                  {shown.map((r) => (
                    <Cell key={r.name} fill={r.name === ILLIQUID ? `url(#${patternId})` : classColor(r.name)} />
                  ))}
                </Pie>
                <Tooltip
                  content={(p) => (
                    <ChartTooltip
                      active={p.active}
                      payload={(p.payload as unknown as { name: string; value: number }[] | undefined)?.map(
                        (item): TipItem => ({ name: label(String(item.name)), value: item.value, dataKey: item.name }),
                      )}
                      formatValue={(v) => pct(v)}
                    />
                  )}
                />
              </PieChart>
            </ResponsiveContainer>
            <div className="donut-centre">
              <b>{cr(corpusCr, 0)}</b>
              <span>{wording.centre}</span>
            </div>
          </div>
          <ul className="legend">
            {rows.map((r) => (
              <li key={r.name}>
                <span
                  className="swatch"
                  style={{ background: r.name === ILLIQUID ? HATCH_CSS : classColor(r.name) }}
                  aria-hidden="true"
                />
                <span>{label(r.name)}</span>
                <span className="amount">{cr(r.amountCr, 0)}</span>
                <span className="share">{pct(r.share)}</span>
              </li>
            ))}
          </ul>
        </div>
      }
    />
  );
}
