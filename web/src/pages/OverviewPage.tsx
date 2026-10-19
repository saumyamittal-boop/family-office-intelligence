import { useEffect, useState } from "react";
import { useLocation } from "react-router-dom";
import type { ModuleId, PortfolioOut, SessionInfo } from "../api/client";
import { useDashboard } from "../api/hooks";
import { CustomisePanel } from "../dashboard/CustomisePanel";
import { cr, pct, times } from "../format";
import { MODULES, MODULE_ORDER } from "../modules/catalog";
import { ModuleCard, isBuilt } from "../modules/registry";
import { PortfolioSwitch, usePortfolioChoice } from "../modules/usePortfolioChoice";
import { shownFor } from "../modules/types";
import { displayName } from "../user";
import { Button, ButtonLink } from "../ui/Button";
import { LoadingBlock } from "../ui/States";
import { StatTile } from "../ui/StatTile";
import { Banner } from "../ui/Status";
import { AnalysisGate } from "../workspace/AnalysisGate";
import type { Ready } from "../workspace/AnalysisGate";
import { AttentionBar } from "../workspace/AttentionBar";
import { GlossaryProvider, useGlossary } from "../workspace/GlossaryContext";
import { useWorkspace } from "../workspace/WorkspaceProvider";
import { WorkspaceBar } from "../workspace/WorkspaceBar";

/** Used only if the saved choice can't be fetched, so the page is never empty. The server's default is the same four. */
const FALLBACK: ModuleId[] = ["allocation_actions", "liquidity_commitments", "risk_exposure", "stress_scenarios"];

function Headline({ portfolio }: { portfolio: PortfolioOut }) {
  const glossary = useGlossary();
  const ratio = portfolio.required_cover_cr > 0 ? portfolio.available_cover_cr / portfolio.required_cover_cr : Infinity;
  return (
    <div className="grid-tiles">
      <StatTile
        label="Expected return"
        value={pct(portfolio.exp_return)}
        sub={`${pct(portfolio.exp_real)} after inflation`}
        tone={portfolio.meets_target ? "good" : "warn"}
        onInfo={() => glossary.open("expectedReturn")}
      />
      <StatTile label="Volatility" value={pct(portfolio.vol)} sub="Annual, including illiquid holdings" onInfo={() => glossary.open("volatility")} />
      <StatTile
        label="Worst drawdown"
        value={pct(portfolio.max_dd)}
        sub={portfolio.dd_ok ? "Within your limit" : "Above your limit"}
        tone={portfolio.dd_ok ? "good" : "bad"}
        onInfo={() => glossary.open("worstDrawdown")}
      />
      <StatTile
        label="Liquidity cover"
        value={times(ratio)}
        sub={`${cr(portfolio.available_cover_cr, 0)} counted vs ${cr(portfolio.required_cover_cr, 0)} needed`}
        tone={ratio >= 1.5 ? "good" : ratio >= 1 ? "warn" : "bad"}
        onInfo={() => glossary.open("liquidityCover")}
      />
    </div>
  );
}

/** Modules not on the dashboard, each still one click away on its own page. */
function ElsewhereList({ shown, search }: { shown: readonly ModuleId[]; search: string }) {
  const rest = MODULE_ORDER.filter((id) => !shown.includes(id));
  if (rest.length === 0) return null;
  return (
    <section aria-labelledby="elsewhere-title" className="elsewhere">
      <h2 id="elsewhere-title">Not on your dashboard</h2>
      <ul>
        {rest.map((id) => (
          <li key={id}>
            {isBuilt(id) ? (
              <ButtonLink to={{ pathname: MODULES[id].page, search }} variant="ghost">
                {MODULES[id].title}{" "}
                <span className="sr-only">in {MODULES[id].pageLabel}</span>
              </ButtonLink>
            ) : (
              <span className="muted">{MODULES[id].title} (arrives in phase 5)</span>
            )}
          </li>
        ))}
      </ul>
    </section>
  );
}

function DashboardBody({ ready, dashboard }: { ready: Ready; dashboard: ReturnType<typeof useDashboard> }) {
  const { analysis, profileId, basis, corpusCr } = ready;
  const [choice, setChoice] = usePortfolioChoice(analysis);
  const [panel, setPanel] = useState(false);
  const [notice, setNotice] = useState("");
  const { search } = useLocation();
  const ctx = { analysis, profileId, basis, corpusCr, choice };
  const shown = shownFor(analysis, choice);
  const modules: ModuleId[] = dashboard.data?.modules ?? FALLBACK;

  useEffect(() => {
    if (!notice) return;
    const timer = window.setTimeout(() => setNotice(""), 5000);
    return () => window.clearTimeout(timer);
  }, [notice]);

  return (
    <div className="stack-lg">
      <AttentionBar analysis={analysis} />

      <div className="dash-toolbar">
        <PortfolioSwitch analysis={analysis} value={choice} onChange={setChoice} />
        <Button icon="customise" onClick={() => setPanel(true)} disabled={!dashboard.data}>
          Customise dashboard
        </Button>
      </div>

      {notice && (
        <Banner tone="good" live>
          {notice}
        </Banner>
      )}

      <Headline portfolio={shown.portfolio} />

      {dashboard.isError && (
        <Banner tone="warn" title="Couldn't load your saved dashboard." action={<Button onClick={() => void dashboard.refetch()}>Try again</Button>}>
          Showing the default four modules for now.
        </Banner>
      )}

      {dashboard.isPending ? (
        <LoadingBlock label="Loading your dashboard" rows={6} />
      ) : (
        <div className="module-grid" role="group" aria-label="Your dashboard">
          {modules.map((id) => (
            <ModuleCard key={id} id={id} ctx={ctx} search={search} />
          ))}
        </div>
      )}

      <ElsewhereList shown={modules} search={search} />

      <p className="hint">
        Cover basis in force: {analysis.basis_label}. Data: {analysis.data_source}. Illustrative simulation, not investment advice.
      </p>

      {dashboard.data && (
        <CustomisePanel
          open={panel}
          onOpenChange={setPanel}
          saved={dashboard.data}
          onDone={(message) => {
            setPanel(false);
            if (message) setNotice(message);
          }}
        />
      )}
    </div>
  );
}

export function OverviewPage({ session }: { session: SessionInfo }) {
  const { profile } = useWorkspace();
  const { search } = useLocation();
  const dashboard = useDashboard();

  return (
    <div className="page">
      <div className="page-head">
        <div>
          <h1>{session.user.is_demo ? "Welcome to the demo" : `Welcome back, ${displayName(session.user)}`}</h1>
          <p>{profile ? `${profile.name}: ${cr(profile.corpus_cr, 0)}` : "Your family's wealth, in one place."}</p>
        </div>
        <ButtonLink to={{ pathname: "/plan", search }} variant="primary" icon="plan">
          Plan my money
        </ButtonLink>
      </div>

      <WorkspaceBar />

      <AnalysisGate>
        {(ready) => (
          <GlossaryProvider>
            <DashboardBody ready={ready} dashboard={dashboard} />
          </GlossaryProvider>
        )}
      </AnalysisGate>
    </div>
  );
}
