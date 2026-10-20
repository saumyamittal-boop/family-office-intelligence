import type { ComponentType } from "react";
import type { ModuleId } from "../api/client";
import { ButtonLink } from "../ui/Button";
import { Card, HeadingLevel } from "../ui/Card";
import { ErrorBoundary } from "../ui/ErrorBoundary";
import { ErrorState } from "../ui/States";
import { AllocationActionsModule } from "./AllocationActionsModule";
import { MODULES } from "./catalog";
import { HistoricalPerformanceModule } from "./HistoricalPerformanceModule";
import { HoldingsConsolidationModule } from "./HoldingsConsolidationModule";
import { LiquidityCommitmentsModule } from "./LiquidityCommitmentsModule";
import { NetWorthModule } from "./NetWorthModule";
import { RationaleModule } from "./RationaleModule";
import { RiskExposureModule } from "./RiskExposureModule";
import { StressScenariosModule } from "./StressScenariosModule";
import type { ModuleContext, ModuleMode } from "./types";

type ModuleView = ComponentType<{ ctx: ModuleContext; mode: ModuleMode }>;

/** Every dashboard module. Each is also reachable from its own page, so none is lost by leaving it off the dashboard. */
export const MODULE_VIEWS: Partial<Record<ModuleId, ModuleView>> = {
  allocation_actions: AllocationActionsModule,
  liquidity_commitments: LiquidityCommitmentsModule,
  risk_exposure: RiskExposureModule,
  stress_scenarios: StressScenariosModule,
  net_worth_projection: NetWorthModule,
  historical_performance: HistoricalPerformanceModule,
  recommendation_rationale: RationaleModule,
  holdings_consolidation: HoldingsConsolidationModule,
};

export function isBuilt(id: ModuleId): boolean {
  return id in MODULE_VIEWS;
}

/**
 * A module on the dashboard: a titled card with a link to its full page. If one module fails to draw, only that card shows
 * an error; the rest of the dashboard and the warnings above it are unaffected.
 */
export function ModuleCard({ id, ctx, search }: { id: ModuleId; ctx: ModuleContext; search: string }) {
  const info = MODULES[id];
  const View = MODULE_VIEWS[id];
  return (
    <Card
      title={info.title}
      className="module"
      actions={
        <ButtonLink to={{ pathname: info.page, search }} variant="ghost" aria-label={`${info.title}: open the full ${info.pageLabel} page`}>
          Full view
        </ButtonLink>
      }
    >
      <HeadingLevel.Provider value={3}>
        <div className="module-body">
          <ErrorBoundary
            fallback={(retry) => <ErrorState title={`${info.title} couldn't be drawn`} message="The rest of the dashboard is unaffected." onRetry={retry} />}
          >
            {View ? <View ctx={ctx} mode="card" /> : <p className="muted">This module isn't ready yet.</p>}
          </ErrorBoundary>
        </div>
      </HeadingLevel.Provider>
    </Card>
  );
}

/** A module at full size on an analyst page: no frame, just its cards. */
export function ModuleSection({ id, ctx }: { id: ModuleId; ctx: ModuleContext }) {
  const info = MODULES[id];
  const View = MODULE_VIEWS[id];
  if (!View) return null;
  return (
    <ErrorBoundary fallback={(retry) => <ErrorState title={`${info.title} couldn't be drawn`} message="The rest of this page is unaffected." onRetry={retry} />}>
      <View ctx={ctx} mode="page" />
    </ErrorBoundary>
  );
}
