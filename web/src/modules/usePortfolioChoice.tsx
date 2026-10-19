import { useCallback } from "react";
import { useSearchParams } from "react-router-dom";
import type { Analysis } from "../api/client";
import { SegmentedControl } from "../ui/Controls";
import { DEFAULT_CHOICE } from "./types";

const PARAM = "mix";

/**
 * Which mix the modules are about: "Current", or one of the recommendations. Kept in the address (?mix=Growth) next to the
 * family and cover basis, so a reload, a shared link and a move between pages all keep it.
 */
export function usePortfolioChoice(analysis: Analysis): [string, (choice: string) => void] {
  const [params, setParams] = useSearchParams();
  const labels = ["Current", ...analysis.options.map((o) => o.portfolio.label)];
  const requested = params.get(PARAM);
  const choice = requested && labels.includes(requested) ? requested : labels.includes(DEFAULT_CHOICE) ? DEFAULT_CHOICE : (labels[1] ?? "Current");

  const setChoice = useCallback(
    (next: string) =>
      setParams(
        (previous) => {
          const out = new URLSearchParams(previous);
          out.set(PARAM, next);
          return out;
        },
        { replace: true },
      ),
    [setParams],
  );
  return [choice, setChoice];
}

export function PortfolioSwitch({
  analysis,
  value,
  onChange,
}: {
  analysis: Analysis;
  value: string;
  onChange: (choice: string) => void;
}) {
  const labels = ["Current", ...analysis.options.map((o) => o.portfolio.label)];
  return (
    <SegmentedControl label="Mix to show" value={value} onChange={onChange} options={labels.map((l) => ({ value: l, label: l }))} />
  );
}
