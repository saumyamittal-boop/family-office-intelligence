import { useEffect, useRef, useState } from "react";
import { ApiError } from "../api/client";
import type { PlanAnswers, PlanConfig, RiskKey } from "../api/client";
import { AllocationChart } from "../charts/AllocationChart";
import { cr } from "../format";
import { Button, ButtonLink } from "../ui/Button";
import { Card } from "../ui/Card";
import { Banner } from "../ui/Status";
import { ErrorState, LoadingBlock, Skeleton } from "../ui/States";
import { BuyList } from "./BuyList";
import { usePlanStrategies, useSavePlan } from "./hooks";
import { ReviewAnswers } from "./ReviewAnswers";
import { StrategyCards } from "./StrategyCards";
import { WhatIf } from "./WhatIf";
import { YearRangeChart } from "./YearRangeChart";

function messageOf(error: unknown): string {
  return error instanceof ApiError ? error.message : "Something went wrong.";
}

/** Step 6: three strategies, what to buy for the chosen one, what-if controls, the answers, and Save. */
export function ResultsStep({
  answers,
  update,
  config,
  onEdit,
  focusOnMount,
}: {
  answers: PlanAnswers;
  update: (patch: Partial<PlanAnswers>) => void;
  config: PlanConfig;
  onEdit: (step: number) => void;
  focusOnMount: boolean;
}) {
  const heading = useRef<HTMLHeadingElement>(null);
  const strategies = usePlanStrategies(answers, true);
  const save = useSavePlan();
  const [selected, setSelected] = useState<RiskKey>(answers.risk);
  const data = strategies.data;
  const showing = data !== undefined;
  useEffect(() => {
    if (focusOnMount && showing) heading.current?.focus();
  }, [focusOnMount, showing]);

  // Following the person's comfort choice keeps the detail on the strategy that fits them best.
  useEffect(() => setSelected(answers.risk), [answers.risk]);
  // A fresh save message only makes sense for the strategy and answers it was made for.
  const { reset: resetSave } = save;
  useEffect(() => resetSave(), [selected, answers, resetSave]);

  if (!data) {
    if (strategies.isError) {
      return <ErrorState title="The strategies could not be worked out" message={messageOf(strategies.error)} onRetry={() => strategies.refetch()} />;
    }
    return (
      <Card title="Working out three strategies">
        <LoadingBlock label="Working out three strategies" rows={4} />
        <p className="muted">The first calculation takes a few seconds. After that, changing your comfort level is instant.</p>
        <div className="strategy-skeletons" aria-hidden="true">
          <Skeleton height="12rem" />
          <Skeleton height="12rem" />
          <Skeleton height="12rem" />
        </div>
      </Card>
    );
  }

  const chosen = data.strategies.find((s) => s.key === selected) ?? data.strategies[0];
  if (!chosen) return null;
  const best = data.strategies.find((s) => s.key === answers.risk);

  return (
    <div className={`stack-lg results ${strategies.updating ? "is-updating" : ""}`}>
      {strategies.isError && (
        <Banner tone="warn" critical title="Could not update." action={<Button onClick={() => strategies.refetch()}>Try again</Button>}>
          {messageOf(strategies.error)} Showing the last result.
        </Banner>
      )}

      <div className="results-head">
        <div>
          <h2 ref={heading} tabIndex={-1} className="step-title">
            Three ways to run {cr(data.corpus_cr, 0)}
          </h2>
          <p className="muted">
            Based on what you told us, <b>Strategy {best?.letter ?? chosen.letter}</b> fits best. The other two show what you would give up or gain by taking
            less or more risk.
          </p>
        </div>
        <span className="preview-status" role="status">
          {strategies.updating ? "Updating…" : "Up to date"}
        </span>
      </div>

      <StrategyCards strategies={data.strategies} chosen={answers.risk} selected={selected} onSelect={setSelected} crashLabel={data.crash.label} />

      <YearRangeChart strategies={data.strategies} />

      <div className="grid-2">
        <AllocationChart title={`Strategy ${chosen.letter}: your money afterwards`} weights={chosen.portfolio.weights_total} corpusCr={data.corpus_cr} />
        <BuyList strategy={chosen} />
      </div>

      <Card title={`Why Strategy ${chosen.letter}`}>
        <ul className="reasons">
          {chosen.description.map((line) => (
            <li key={line}>{line}</li>
          ))}
        </ul>
        {data.commitments.length > 0 && (
          <p className="reasons-note">
            Your upcoming commitments are built in:{" "}
            {data.commitments.map((c) => `${c.kind.toLowerCase()} in ${c.year} ${c.year === 1 ? "year" : "years"} (${cr(c.amount_cr)})`).join(", ")}.
          </p>
        )}
      </Card>

      <WhatIf answers={answers} update={update} config={config} updating={strategies.updating} />

      <ReviewAnswers answers={answers} config={config} onEdit={onEdit} />

      <Card title="Assumptions and limits">
        <ul className="reasons">
          <li>This is an illustrative simulation on {data.data_source === "sample" ? "synthetic sample data" : `${data.data_source} data`}, not investment advice.</li>
          <li>
            {data.crash.label}: {data.crash.description}
          </li>
          <li>
            The safety net counts: {data.basis_label.toLowerCase()}. The comfort levels, long-run return assumptions and haircuts are draft values, not
            externally validated.
          </li>
          <li>The history cannot contain every bad outcome, and past years do not predict future ones. Real families should take professional advice.</li>
        </ul>
      </Card>

      <Card title="Keep this plan">
        <div className="save-row">
          <Button
            variant="primary"
            icon="plus"
            disabled={save.isPending}
            onClick={() => save.mutate({ answers, strategy: selected })}
          >
            Save Strategy {chosen.letter} to my profiles
          </Button>
          {save.isPending && <span className="muted" role="status">Saving…</span>}
        </div>
        {save.isError && <Banner tone="bad" critical>{messageOf(save.error)}</Banner>}
        {save.data && (
          <Banner tone="good" live title={save.data.created ? "Saved." : "Already saved."}>
            It is a profile called <b>{save.data.profile.name}</b>.{" "}
            <ButtonLink to={{ pathname: "/", search: `?profile=${save.data.profile.id}&basis=strict` }} variant="secondary">
              See it on the overview
            </ButtonLink>
          </Banner>
        )}
      </Card>
    </div>
  );
}
