import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useSearchParams } from "react-router-dom";
import type { PlanAnswers, PlanConfig } from "../api/client";
import { clearDraft, defaultAnswers, readDraft, writeDraft } from "./draft";

/**
 * The plan's answers, the step in the address (?step=3, so the browser's Back button moves between steps), and the
 * furthest step reached. Answers are kept in this tab's session storage so a reload does not lose them.
 */
export function usePlanState(config: PlanConfig) {
  const total = config.steps.length;
  const initial = useRef(readDraft(config));
  const [answers, setAnswers] = useState<PlanAnswers>(initial.current.answers);
  const [furthest, setFurthest] = useState(initial.current.furthest);
  const [params, setParams] = useSearchParams();
  const [returnToResults, setReturnToResults] = useState(false);

  const requested = Number(params.get("step"));
  // No (or a nonsense) ?step= resumes where the person left off; a step they have not reached yet is not reachable by address.
  const step = Number.isInteger(requested) && requested >= 1 && requested <= total ? Math.min(requested, furthest) : furthest;

  useEffect(() => writeDraft({ answers, furthest }), [answers, furthest]);

  const goTo = useCallback(
    (next: number, options: { replace?: boolean } = {}) => {
      const clamped = Math.max(1, Math.min(total, next));
      setFurthest((f) => Math.max(f, clamped));
      setParams(
        (previous) => {
          const out = new URLSearchParams(previous);
          out.set("step", String(clamped));
          return out;
        },
        { replace: options.replace ?? false },
      );
    },
    [setParams, total],
  );

  const update = useCallback((patch: Partial<PlanAnswers>) => setAnswers((a) => ({ ...a, ...patch })), []);

  const reset = useCallback(() => {
    clearDraft();
    setAnswers(defaultAnswers(config));
    setFurthest(1);
    setReturnToResults(false);
    goTo(1, { replace: true });
  }, [config, goTo]);

  return useMemo(
    () => ({ answers, update, step, total, furthest, goTo, reset, returnToResults, setReturnToResults }),
    [answers, update, step, total, furthest, goTo, reset, returnToResults],
  );
}
