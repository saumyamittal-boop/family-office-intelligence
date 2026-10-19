import { useState } from "react";
import type { ReactNode } from "react";
import { tidyText } from "../format";
import { Card } from "../ui/Card";
import { SegmentedControl } from "../ui/Controls";
import { ErrorBoundary } from "../ui/ErrorBoundary";
import { ErrorState } from "../ui/States";

type View = "chart" | "table";

/**
 * A card around a chart that always offers the same numbers as a table.
 * `summary` is the text alternative: one sentence with the key figures, read out instead of the picture.
 */
export function ChartFrame({
  title,
  description,
  summary,
  chart,
  table,
  extraActions,
  height = "16rem",
}: {
  title: string;
  description?: string;
  summary: string;
  chart: ReactNode;
  table: ReactNode;
  extraActions?: ReactNode;
  height?: string;
}) {
  const [view, setView] = useState<View>("chart");
  return (
    <Card
      title={title}
      subtitle={description}
      actions={
        <>
          {extraActions}
          <SegmentedControl<View>
            label={`${title}: show as`}
            value={view}
            onChange={setView}
            options={[
              { value: "chart", label: "Chart" },
              { value: "table", label: "Table" },
            ]}
          />
        </>
      }
    >
      {view === "chart" ? (
        <figure style={{ margin: 0 }}>
          <div className="chart-box" style={{ height }} role="img" aria-label={summary}>
            <ErrorBoundary
              fallback={(retry) => (
                <ErrorState
                  title="This chart couldn't be drawn"
                  message="The Table view has the same numbers."
                  onRetry={retry}
                />
              )}
            >
              {chart}
            </ErrorBoundary>
          </div>
          <figcaption className="chart-caption">{tidyText(summary)}</figcaption>
        </figure>
      ) : (
        table
      )}
    </Card>
  );
}

export type TipItem = { name?: string | number; value?: number | string; color?: string; dataKey?: string | number };

/** The hover/focus tooltip shared by every chart. */
export function ChartTooltip({
  active,
  payload,
  label,
  formatValue,
  formatLabel = (l) => String(l),
}: {
  active?: boolean;
  payload?: readonly TipItem[];
  label?: string | number;
  formatValue: (value: number) => string;
  formatLabel?: (label: string | number) => string;
}) {
  if (!active || !payload || payload.length === 0) return null;
  return (
    <div className="chart-tooltip">
      {label !== undefined && <b>{formatLabel(label)}</b>}
      {payload.map((item) => (
        <div key={String(item.dataKey ?? item.name)}>
          <span style={{ color: item.color }}>{item.name}</span>
          <span>{formatValue(Number(item.value))}</span>
        </div>
      ))}
    </div>
  );
}
