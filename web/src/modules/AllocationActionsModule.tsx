import { AllocationChart } from "../charts/AllocationChart";
import { cr, pct } from "../format";
import { Card } from "../ui/Card";
import { DataTable } from "../ui/DataTable";
import type { Column } from "../ui/DataTable";
import { ActionPlanCard } from "../workspace/ActionPlanCard";
import { Pair } from "./Pair";
import { shownFor } from "./types";
import type { ModuleContext, ModuleMode } from "./types";

const ILLIQUID = "Illiquid";

/** The chosen mix as a donut, what to buy and sell to reach it, and (on the full page) all the mixes side by side. */
export function AllocationActionsModule({ ctx, mode }: { ctx: ModuleContext; mode: ModuleMode }) {
  const { analysis, corpusCr, choice } = ctx;
  const shown = shownFor(analysis, choice);

  return (
    <>
      <Pair mode={mode}>
        <AllocationChart
          title={shown.isCurrent ? "Your current mix" : `${choice} mix`}
          weights={shown.portfolio.weights_total}
          corpusCr={corpusCr}
        />
        {shown.detail ? (
          <ActionPlanCard rows={shown.detail.action_plan} label={choice} />
        ) : (
          <Card title="Where you are now">
            <p className="muted">
              This is your current mix. Choose Growth, Balanced or Defensive above to see what to buy and sell to move towards it.
            </p>
          </Card>
        )}
      </Pair>
      {mode === "page" && <MixComparison ctx={ctx} />}
      {mode === "page" && <MeasuresTable ctx={ctx} />}
    </>
  );
}

type Row = { name: string; shares: number[] };

/** Current and recommended shares of the whole corpus, class by class. */
function MixComparison({ ctx }: { ctx: ModuleContext }) {
  const portfolios = [ctx.analysis.current, ...ctx.analysis.options.map((o) => o.portfolio)];
  const names = [...Object.keys(ctx.analysis.current.weights_total).filter((n) => n !== ILLIQUID), ILLIQUID];
  const rows: Row[] = names.map((name) => ({ name, shares: portfolios.map((p) => p.weights_total[name] ?? 0) }));
  const columns: Column<Row>[] = [
    { key: "class", header: "Asset class", rowHeader: true, cell: (r) => (r.name === ILLIQUID ? "Illiquid (held fixed)" : r.name) },
    ...portfolios.map((p, i) => ({ key: p.label, header: p.label, align: "right" as const, cell: (r: Row) => pct(r.shares[i] ?? 0) })),
  ];
  return (
    <Card title="The mixes side by side" subtitle="Share of the whole corpus. Illiquid holdings are the same in every mix: the model does not trade them.">
      <DataTable caption="Share of the corpus in each asset class, for the current mix and each recommendation" columns={columns} rows={rows} rowKey={(r) => r.name} />
    </Card>
  );
}

type Measure = { name: string; values: string[] };

/** Return, risk, drawdown and liquidity for the current mix and each recommendation, one column each. */
function MeasuresTable({ ctx }: { ctx: ModuleContext }) {
  const portfolios = [ctx.analysis.current, ...ctx.analysis.options.map((o) => o.portfolio)];
  const yesNo = (ok: boolean) => (ok ? "Yes" : "No");
  const measures: Measure[] = [
    { name: "Expected return", values: portfolios.map((p) => pct(p.exp_return)) },
    { name: "Expected real return", values: portfolios.map((p) => pct(p.exp_real)) },
    { name: "Meets the target real return", values: portfolios.map((p) => yesNo(p.meets_target)) },
    { name: "Volatility", values: portfolios.map((p) => pct(p.vol)) },
    { name: "Worst drawdown in history", values: portfolios.map((p) => pct(p.max_dd)) },
    { name: "Within your drawdown limit", values: portfolios.map((p) => yesNo(p.dd_ok)) },
    { name: "95% 1-month CVaR", values: portfolios.map((p) => pct(p.cvar21)) },
    { name: "Safety net counted / needed", values: portfolios.map((p) => `${cr(p.available_cover_cr, 0)} / ${cr(p.required_cover_cr, 0)}`) },
  ];
  const columns: Column<Measure>[] = [
    { key: "measure", header: "Measure", rowHeader: true, cell: (m) => m.name },
    ...portfolios.map((p, i) => ({ key: p.label, header: p.label, align: "right" as const, cell: (m: Measure) => m.values[i] ?? "" })),
  ];
  return (
    <Card title="Compare with your current mix" subtitle="Return, risk, drawdown and liquidity side by side. Yes and No are written out, not only coloured.">
      <DataTable caption="Return, risk, drawdown and liquidity measures for the current mix and each recommendation" columns={columns} rows={measures} rowKey={(m) => m.name} />
    </Card>
  );
}
