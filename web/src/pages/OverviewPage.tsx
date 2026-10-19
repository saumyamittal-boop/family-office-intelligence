import { useState } from "react";
import { ApiError } from "../api/client";
import type { Analysis, PortfolioOut, SessionInfo } from "../api/client";
import { AllocationChart } from "../charts/AllocationChart";
import { OutflowsChart } from "../charts/OutflowsChart";
import { ProjectionChart } from "../charts/ProjectionChart";
import { ScenarioChart } from "../charts/ScenarioChart";
import type { GlossaryKey } from "../content/glossary";
import { cr, pct, tidyText, times } from "../format";
import { displayName } from "../user";
import { ButtonLink } from "../ui/Button";
import { Card } from "../ui/Card";
import { SegmentedControl } from "../ui/Controls";
import { StatTile } from "../ui/StatTile";
import { Banner } from "../ui/Status";
import { EmptyState, ErrorState, LoadingBlock } from "../ui/States";
import { ActionPlanCard } from "../workspace/ActionPlanCard";
import { AttentionBar } from "../workspace/AttentionBar";
import { GlossaryPanel } from "../workspace/GlossaryPanel";
import { useWorkspace } from "../workspace/WorkspaceProvider";
import { WorkspaceBar } from "../workspace/WorkspaceBar";
import { useLocation } from "react-router-dom";

const DEFAULT_CHOICE = "Balanced";

function Headline({ portfolio, onInfo }: { portfolio: PortfolioOut; onInfo: (term: GlossaryKey) => void }) {
  const ratio = portfolio.required_cover_cr > 0 ? portfolio.available_cover_cr / portfolio.required_cover_cr : Infinity;
  return (
    <div className="grid-tiles">
      <StatTile
        label="Expected return"
        value={pct(portfolio.exp_return)}
        sub={`${pct(portfolio.exp_real)} after inflation`}
        tone={portfolio.meets_target ? "good" : "warn"}
        onInfo={() => onInfo("expectedReturn")}
      />
      <StatTile
        label="Volatility"
        value={pct(portfolio.vol)}
        sub="Annual, including illiquid holdings"
        onInfo={() => onInfo("volatility")}
      />
      <StatTile
        label="Worst drawdown"
        value={pct(portfolio.max_dd)}
        sub={portfolio.dd_ok ? "Within your limit" : "Above your limit"}
        tone={portfolio.dd_ok ? "good" : "bad"}
        onInfo={() => onInfo("worstDrawdown")}
      />
      <StatTile
        label="Liquidity cover"
        value={times(ratio)}
        sub={`${cr(portfolio.available_cover_cr, 0)} counted vs ${cr(portfolio.required_cover_cr, 0)} needed`}
        tone={ratio >= 1.5 ? "good" : ratio >= 1 ? "warn" : "bad"}
        onInfo={() => onInfo("liquidityCover")}
      />
    </div>
  );
}

function Loaded({ analysis, corpusCr }: { analysis: Analysis; corpusCr: number }) {
  const labels = ["Current", ...analysis.options.map((o) => o.portfolio.label)];
  const [choice, setChoice] = useState(labels.includes(DEFAULT_CHOICE) ? DEFAULT_CHOICE : (labels[1] ?? "Current"));
  const [term, setTerm] = useState<GlossaryKey | null>(null);

  const isCurrent = choice === "Current";
  const detail = analysis.options.find((o) => o.portfolio.label === choice);
  // The comparison pages need a recommendation to compare with; when "Current" is shown, use Balanced.
  const reference = detail ?? analysis.options.find((o) => o.portfolio.label === DEFAULT_CHOICE) ?? analysis.options[0];
  const shown = isCurrent ? analysis.current : (detail?.portfolio ?? analysis.current);

  return (
    <div className="stack-lg">
      <AttentionBar analysis={analysis} />

      <SegmentedControl
        label="Portfolio to show"
        value={choice}
        onChange={setChoice}
        options={labels.map((l) => ({ value: l, label: l }))}
      />

      <Headline portfolio={shown} onInfo={setTerm} />

      <div className="grid-2">
        <AllocationChart title={isCurrent ? "Your current mix" : `${choice} mix`} weights={shown.weights_total} corpusCr={corpusCr} />
        {isCurrent || !detail ? (
          <Card title="Where you are now">
            <p className="muted">
              This is your current mix. Choose Growth, Balanced or Defensive above to see what to buy and sell to move
              towards it.
            </p>
          </Card>
        ) : (
          <ActionPlanCard rows={detail.action_plan} label={choice} />
        )}
      </div>

      {reference && (
        <div className="grid-2">
          <ProjectionChart
            current={analysis.current_projection}
            selected={reference.projection}
            selectedLabel={reference.portfolio.label}
          />
          <OutflowsChart rows={analysis.upcoming_outflows} />
        </div>
      )}

      <ScenarioChart scenario={analysis.comparison_scenario} rows={analysis.comparison} />

      {reference && (
        <div className="grid-2">
          <Card title={isCurrent ? `Why the ${reference.portfolio.label} mix` : `Why the ${choice} mix`}>
            <ul className="reasons">
              {reference.portfolio.explanation.map((line) => (
                <li key={line}>{tidyText(line)}</li>
              ))}
            </ul>
          </Card>
          <Card title="What stands out">
            <div className="stack">
              {[...reference.insights, ...analysis.comparison_insights].map((note) => (
                <Banner key={note.body} tone={note.tone === "good" ? "good" : note.tone === "warn" ? "warn" : "info"} title={note.title ? `${note.title}.` : undefined}>
                  {tidyText(note.body)}
                </Banner>
              ))}
            </div>
          </Card>
        </div>
      )}

      <p className="hint">
        Cover basis in force: {analysis.basis_label}. Data: {analysis.data_source}. Illustrative simulation, not
        investment advice.
      </p>
      <GlossaryPanel term={term} onClose={() => setTerm(null)} />
    </div>
  );
}

export function OverviewPage({ session }: { session: SessionInfo }) {
  const { profiles, profile, analysis } = useWorkspace();
  const { search } = useLocation();

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

      {profiles.isPending && <LoadingBlock label="Loading your family profiles" />}
      {profiles.isError && (
        <ErrorState
          title="Can't load your profiles"
          message={profiles.error instanceof ApiError ? profiles.error.message : "Something went wrong."}
          onRetry={() => profiles.refetch()}
        />
      )}
      {profiles.isSuccess && !profile && (
        <EmptyState icon="profile" title="No family profile yet">
          Profile creation arrives with the guided plan in phase 3.
        </EmptyState>
      )}

      {profile && analysis.isPending && <LoadingBlock label="Running the allocation model" rows={5} />}
      {profile && analysis.isError && (
        <ErrorState
          title="The analysis could not be run"
          message={analysis.error instanceof ApiError ? analysis.error.message : "Something went wrong."}
          onRetry={() => analysis.refetch()}
        />
      )}
      {profile && analysis.data && (
        <Loaded key={`${analysis.data.profile_id}-${analysis.data.basis}`} analysis={analysis.data} corpusCr={profile.corpus_cr} />
      )}
    </div>
  );
}
