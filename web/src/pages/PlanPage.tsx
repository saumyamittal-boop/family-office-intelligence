import { useCallback, useRef, useState } from "react";
import { ApiError } from "../api/client";
import { PreviewPanel } from "../plan/PreviewPanel";
import { ResultsStep } from "../plan/ResultsStep";
import { Stepper } from "../plan/Stepper";
import { StepFrame } from "../plan/StepFrame";
import { usePlanConfig, usePlanPreview } from "../plan/hooks";
import { AboutStep, ComfortStep, ComingStep, OwnStep, SafetyStep } from "../plan/steps";
import type { StepProps } from "../plan/steps";
import { usePlanState } from "../plan/usePlanState";
import type { PlanConfig } from "../api/client";
import { Button } from "../ui/Button";
import { ErrorState, LoadingBlock } from "../ui/States";

const TITLES = [
  "Tell us about the family",
  "Anything big coming up?",
  "How do you feel about a bad year?",
  "Your safety net",
  "What does the family own today?",
];
const STEP_COMPONENTS = [AboutStep, ComingStep, ComfortStep, SafetyStep, OwnStep] as const;

function PlanFlow({ config }: { config: PlanConfig }) {
  const { answers, update, step, total, furthest, goTo: rawGoTo, reset, returnToResults, setReturnToResults } = usePlanState(config);
  // Focus follows the person to a new step, but is left alone when the page first opens.
  const navigated = useRef(false);
  const goTo = useCallback(
    (target: number) => {
      navigated.current = true;
      rawGoTo(target);
    },
    [rawGoTo],
  );
  const preview = usePlanPreview(answers, step < total);
  const [valid, setValid] = useState(false);
  const onValid = useCallback((v: boolean) => setValid(v), []);

  const isResults = step === total;
  const Step = STEP_COMPONENTS[step - 1];
  const stepProps: StepProps = { answers, update, config, preview: preview.data, onValid };
  const previewBusy = preview.settling || preview.isFetching;

  // The last question waits for the live read-out to catch up, so a stale "fix this" message never blocks or lets through a plan.
  const canContinue = valid && !(step === total - 1 && previewBusy);

  function next() {
    if (returnToResults && !isResults) {
      setReturnToResults(false);
      goTo(total);
    } else {
      goTo(step + 1);
    }
  }
  function edit(target: number) {
    setReturnToResults(true);
    goTo(target);
  }
  const nextLabel = step === total - 1 ? "See my strategies" : returnToResults ? "Back to my strategies" : "Continue";

  return (
    <div className="page plan-page">
      <div className="page-head">
        <div>
          <h1>Plan my money</h1>
          <p>Answer a few plain questions. Get three strategies, with exactly what to buy.</p>
        </div>
        {furthest > 1 && (
          <Button variant="ghost" icon="close" onClick={reset}>
            Start over
          </Button>
        )}
      </div>

      <Stepper steps={config.steps} current={step} furthest={furthest} onSelect={(s) => goTo(s)} />

      {isResults ? (
        <ResultsStep answers={answers} update={update} config={config} onEdit={edit} focusOnMount={navigated.current} />
      ) : (
        <div className="plan-layout">
          <div key={step} className="step-anim">
            <StepFrame
              step={step}
              title={TITLES[step - 1] ?? ""}
              canContinue={canContinue}
              nextLabel={nextLabel}
              focusOnMount={navigated.current}
              onBack={step > 1 ? () => goTo(step - 1) : undefined}
              onNext={next}
            >
              {Step && <Step {...stepProps} />}
            </StepFrame>
          </div>
          <aside className="plan-aside" aria-label="Live read-out">
            <PreviewPanel preview={preview.data} updating={previewBusy} failed={preview.isError && !preview.data} />
          </aside>
        </div>
      )}
    </div>
  );
}

export function PlanPage() {
  const config = usePlanConfig();
  if (config.isPending) {
    return (
      <div className="page">
        <h1>Plan my money</h1>
        <LoadingBlock label="Loading the questions" />
      </div>
    );
  }
  if (config.isError || !config.data) {
    return (
      <div className="page">
        <h1>Plan my money</h1>
        <ErrorState
          title="The questions could not be loaded"
          message={config.error instanceof ApiError ? config.error.message : "Something went wrong."}
          onRetry={() => config.refetch()}
        />
      </div>
    );
  }
  return <PlanFlow config={config.data} />;
}
