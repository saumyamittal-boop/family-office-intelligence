import { useMemo, useState } from "react";
import type { Basis, CustomScenario, Schemas, ScenarioPreset } from "../api/client";
import { useScenarioComparison } from "../api/hooks";
import { ScenarioChart } from "../charts/ScenarioChart";
import { pct, signedCr, signedPct, tidyText, times } from "../format";
import { useDebounced } from "../plan/useDebounced";
import { Card } from "../ui/Card";
import { SegmentedControl } from "../ui/Controls";
import { DataTable } from "../ui/DataTable";
import type { Column } from "../ui/DataTable";
import { Slider } from "../ui/Slider";
import { Badge, Banner } from "../ui/Status";
import { ErrorState } from "../ui/States";
import { ApiError } from "../api/client";

/** A scenario's effect on one mix, in the shape the cards need whichever endpoint it came from. */
export type ScenarioResult = {
  name: string;
  change: number;
  changeCr: number;
  withinLimit: boolean;
  cover: number;
  coverHeld: boolean;
  realMultiple: number;
};

export const fromScenarioRow = (r: Schemas["ScenarioRow"]): ScenarioResult => ({
  name: r.scenario, change: r.value_change, changeCr: r.value_change_cr, withinLimit: r.within_drawdown_limit,
  cover: r.cover_ratio, coverHeld: r.cover_held, realMultiple: r.real_corpus_multiple,
});

export const fromCompareRow = (name: string, r: Schemas["CompareRow"]): ScenarioResult => ({
  name, change: r.value_change, changeCr: r.value_change_cr, withinLimit: r.within_drawdown_limit,
  cover: r.cover_ratio_after, coverHeld: r.cover_held, realMultiple: r.real_corpus_multiple,
});

const NOTICEABLE = 0.0005; // below this a scenario has no immediate hit; its effect is on long-run purchasing power

/** One scenario's result: the headline, and three plain yes/no checks (drawdown limit, safety net, purchasing power). */
export function ScenarioResultCard({ result, description }: { result: ScenarioResult; description?: string }) {
  const hit = Math.abs(result.change) > NOTICEABLE;
  const tone = hit ? (result.change < 0 ? "neg" : "pos") : result.realMultiple < 1 ? "neg" : "pos";
  return (
    <article className="scn" aria-label={result.name}>
      <p className="scn-name">{result.name}</p>
      {description && <p className="scn-desc">{description}</p>}
      <p className={`scn-big ${tone}`}>{hit ? signedPct(result.change) : `${result.realMultiple.toFixed(2)}x`}</p>
      <p className="scn-sub">{hit ? signedCr(result.changeCr) : "real corpus at the horizon"}</p>
      <div className="pills">
        <Badge tone={result.withinLimit ? "good" : "bad"}>{result.withinLimit ? "Within drawdown limit" : "Drawdown limit breached"}</Badge>
        <Badge tone={result.coverHeld ? "good" : "bad"}>{`Safety net ${times(result.cover)}`}</Badge>
        <Badge tone={result.realMultiple >= 1 ? "good" : "warn"}>{`Real corpus ${result.realMultiple.toFixed(2)}x`}</Badge>
      </div>
    </article>
  );
}

/** The shocks behind every built-in scenario, so nobody has to guess what "Market crash" means. */
export function PresetAssumptions({ presets }: { presets: ScenarioPreset[] }) {
  const classes = presets[0] ? Object.keys(presets[0].shocks) : [];
  const columns: Column<ScenarioPreset>[] = [
    { key: "name", header: "Scenario", rowHeader: true, cell: (p) => p.name },
    ...classes.map((c) => ({ key: c, header: c, align: "right" as const, cell: (p: ScenarioPreset) => signedPct(p.shocks[c] ?? 0, 0) })),
    { key: "ill", header: "Illiquid", align: "right" as const, cell: (p: ScenarioPreset) => signedPct(p.illiquid, 0) },
    { key: "out", header: "One-off bill", align: "right" as const, cell: (p: ScenarioPreset) => (p.extra_outflow ? pct(p.extra_outflow, 0) + " of corpus" : "None") },
    { key: "drag", header: "Return drag", align: "right" as const, cell: (p: ScenarioPreset) => (p.return_drag ? `${(p.return_drag * 100).toFixed(0)} pts a year` : "None") },
  ];
  return (
    <details className="disclosure">
      <summary>What each built-in scenario assumes</summary>
      <p className="hint">
        These are fixed placeholder sizes for the synthetic sample, not forecasts. Each shock is applied once to today's holdings.
      </p>
      <DataTable caption="Shocks applied by each built-in scenario" columns={columns} rows={presets} rowKey={(p) => p.name} />
    </details>
  );
}

// ---- Build your own ----------------------------------------------------------------------------------------------------
type DialKey = keyof CustomScenario;
type Dials = Record<DialKey, number>; // in percent (return drag in percentage points), what the sliders show

const DIAL_UI: { key: DialKey; label: string; step: number; hint?: string; format: (v: number) => string }[] = [
  { key: "equity_shock", label: "Equity shock", step: 1, hint: "Applied to large-cap; mid-cap moves 25% more.", format: (v) => `${v > 0 ? "+" : v < 0 ? "−" : ""}${Math.abs(v)}%` },
  { key: "debt_shock", label: "Debt shock", step: 1, format: (v) => `${v > 0 ? "+" : v < 0 ? "−" : ""}${Math.abs(v)}%` },
  { key: "gold_shock", label: "Gold shock", step: 1, format: (v) => `${v > 0 ? "+" : v < 0 ? "−" : ""}${Math.abs(v)}%` },
  { key: "illiquid_markdown", label: "Illiquid mark-down", step: 1, format: (v) => `${v > 0 ? "+" : v < 0 ? "−" : ""}${Math.abs(v)}%` },
  { key: "one_off_expense", label: "One-off expense", step: 1, hint: "As a share of the corpus.", format: (v) => `${v}%` },
  { key: "return_drag", label: "Return drag per year", step: 0.5, hint: "Taken off every year's return for the whole horizon.", format: (v) => `${v} pts` },
];

const CUSTOM = "Your scenario";
const toFraction = (percent: number) => Number((percent / 100).toFixed(4));

/** The lab: six dials, the result on the chosen mix, and every option compared under one scenario. */
export function ScenarioLab({
  profileId, basis, choice, presets, ranges, defaultPreset,
}: {
  profileId: number;
  basis: Basis;
  choice: string;
  presets: ScenarioPreset[];
  ranges: Record<string, { min: number; max: number; default: number }>;
  defaultPreset: string;
}) {
  const [dials, setDials] = useState<Dials>(() => {
    const start = {} as Dials;
    for (const { key } of DIAL_UI) start[key] = Math.round((ranges[key]?.default ?? 0) * 1000) / 10;
    return start;
  });
  const settled = useDebounced(dials, 300);
  const custom = useMemo<CustomScenario>(() => {
    const out = {} as CustomScenario;
    for (const { key } of DIAL_UI) out[key] = toFraction(settled[key]);
    return out;
  }, [settled]);
  const [compareName, setCompareName] = useState(defaultPreset);
  const mine = useScenarioComparison(profileId, { basis, custom });
  const asked = compareName === CUSTOM ? null : { basis, preset: compareName };
  const other = useScenarioComparison(profileId, asked);
  const compared = compareName === CUSTOM ? mine : other;

  const row = mine.data?.rows.find((r) => r.option === choice);
  const updating = dials !== settled || mine.isFetching;

  return (
    <>
      <Card title="Build your own scenario" subtitle="Move the dials; the result follows. Nothing here changes your saved profile.">
        <div className="lab">
          <div className="lab-dials">
            {DIAL_UI.map(({ key, label, step, hint, format }) => {
              const range = ranges[key];
              if (!range) return null;
              return (
                <Slider
                  key={key} label={label} hint={hint} format={format} step={step}
                  min={Math.round(range.min * 100)} max={Math.round(range.max * 100)}
                  value={dials[key]} onChange={(v) => setDials((d) => ({ ...d, [key]: v }))}
                />
              );
            })}
          </div>
          <div className="lab-result" aria-live="polite" aria-busy={updating}>
            {mine.isError && !mine.data ? (
              <ErrorState title="Couldn't run this scenario" message={mine.error instanceof ApiError ? mine.error.message : "Something went wrong."} onRetry={() => void mine.refetch()} />
            ) : row ? (
              <div className={updating ? "is-updating" : undefined}>
                <ScenarioResultCard result={fromCompareRow(`Your scenario on the ${choice} mix`, row)} description="The shocks set here, applied once to today's holdings." />
                {updating && <p className="hint">Updating…</p>}
              </div>
            ) : (
              <p className="muted">Working out your scenario…</p>
            )}
          </div>
        </div>
      </Card>

      <Card title="Compare your options under one scenario" subtitle="Your current mix and the three recommended options, hit by the same shock.">
        <div className="stack-lg">
          <SegmentedControl
            label="Scenario to compare"
            value={compareName}
            onChange={setCompareName}
            options={[...presets.map((p) => ({ value: p.name, label: p.name })), { value: CUSTOM, label: "Your scenario" }]}
          />
          {compared.isError && !compared.data ? (
            <ErrorState title="Couldn't compare the options" message={compared.error instanceof ApiError ? compared.error.message : "Something went wrong."} onRetry={() => void compared.refetch()} />
          ) : compared.data ? (
            <div className={compared.isPlaceholderData ? "is-updating" : undefined}>
              <div className="stack-lg">
                <ScenarioChart scenario={compared.data.name} rows={compared.data.rows} />
                <div className="stack">
                  {compared.data.insights.map((note) => (
                    <Banner key={note.body} tone={note.tone === "good" ? "good" : note.tone === "warn" ? "warn" : "info"}>
                      {tidyText(note.body)}
                    </Banner>
                  ))}
                </div>
              </div>
            </div>
          ) : (
            <p className="muted" role="status">Comparing the options…</p>
          )}
        </div>
      </Card>
    </>
  );
}

/** Every scenario's result on the chosen mix, as a table. */
export function AllResultsTable({ rows, label }: { rows: Schemas["ScenarioRow"][]; label: string }) {
  const columns: Column<Schemas["ScenarioRow"]>[] = [
    { key: "s", header: "Scenario", rowHeader: true, cell: (r) => r.scenario },
    { key: "c", header: "Value change", align: "right", cell: (r) => `${signedPct(r.value_change)} (${signedCr(r.value_change_cr)})` },
    { key: "d", header: "Within drawdown limit", align: "right", cell: (r) => (r.within_drawdown_limit ? "Yes" : "No") },
    { key: "l", header: "Safety net", align: "right", cell: (r) => `${times(r.cover_ratio)} ${r.cover_held ? "(held)" : "(short)"}` },
    { key: "r", header: "Real corpus at horizon", align: "right", cell: (r) => `${r.real_corpus_multiple.toFixed(2)}x` },
  ];
  return (
    <Card title="All results" subtitle={`Every scenario on the ${label} mix. Below 1.00x, purchasing power is not preserved.`}>
      <DataTable caption={`Results of each stress scenario on the ${label} mix`} columns={columns} rows={rows} rowKey={(r) => r.scenario} />
      <p className="hint">Amounts are in ₹ crore.</p>
    </Card>
  );
}
