import type { ReactNode } from "react";
import type { ModuleId } from "../api/client";
import { MODULES } from "../modules/catalog";
import { ModuleSection } from "../modules/registry";
import { PortfolioSwitch, usePortfolioChoice } from "../modules/usePortfolioChoice";
import { AnalysisGate } from "../workspace/AnalysisGate";
import type { Ready } from "../workspace/AnalysisGate";
import { AttentionBar } from "../workspace/AttentionBar";
import { GlossaryProvider } from "../workspace/GlossaryContext";
import { WorkspaceBar } from "../workspace/WorkspaceBar";

function Body({ ready, modules }: { ready: Ready; modules: readonly ModuleId[] }) {
  const { analysis, profileId, basis, corpusCr } = ready;
  const [choice, setChoice] = usePortfolioChoice(analysis);
  const ctx = { analysis, profileId, basis, corpusCr, choice };
  return (
    <div className="stack-lg">
      <AttentionBar analysis={analysis} />
      <PortfolioSwitch analysis={analysis} value={choice} onChange={setChoice} />
      {modules.map((id) => (
        <section key={id} className="analyst-section" aria-label={MODULES[id].title}>
          <ModuleSection id={id} ctx={ctx} />
        </section>
      ))}
      <p className="hint">
        Cover basis in force: {analysis.basis_label}. Data: {analysis.data_source}. Illustrative simulation, not investment advice.
      </p>
    </div>
  );
}

/** An analyst page: a title, the family and cover-basis pickers, the warnings, and the full version of some modules. */
function AnalystPage({ title, intro, modules, extra }: { title: string; intro: string; modules: readonly ModuleId[]; extra?: ReactNode }) {
  return (
    <div className="page">
      <div className="page-head">
        <div>
          <h1>{title}</h1>
          <p>{intro}</p>
        </div>
      </div>
      <WorkspaceBar />
      <AnalysisGate>
        {(ready) => (
          <GlossaryProvider>
            <Body ready={ready} modules={modules} />
          </GlossaryProvider>
        )}
      </AnalysisGate>
      {extra}
    </div>
  );
}

export function RecommendationPage() {
  return (
    <AnalystPage
      title="Recommendation"
      intro="Growth, Balanced and Defensive mixes: what to buy and sell, what it means for the corpus, and the reasons and limits behind each."
      modules={["allocation_actions", "net_worth_projection", "recommendation_rationale"]}
    />
  );
}

export function RiskPage() {
  return (
    <AnalystPage
      title="Risk and liquidity"
      intro="How rough the ride has been, and whether cash will be there when it is needed."
      modules={["risk_exposure", "liquidity_commitments", "historical_performance"]}
    />
  );
}

export function ScenariosPage() {
  return (
    <AnalystPage
      title="Scenarios"
      intro="Stress the plan before the market does: built-in shocks, your own, and every option side by side."
      modules={["stress_scenarios"]}
    />
  );
}
