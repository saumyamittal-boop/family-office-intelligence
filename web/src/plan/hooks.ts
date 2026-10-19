import { keepPreviousData, useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useMemo } from "react";
import { api } from "../api/client";
import type { PlanAnswers, RiskKey } from "../api/client";
import { keys } from "../api/hooks";
import { useDebounced } from "./useDebounced";

export const PREVIEW_DELAY_MS = 350;
export const STRATEGIES_DELAY_MS = 600;

export function usePlanConfig() {
  return useQuery({ queryKey: ["plan", "config"], queryFn: api.planConfig, staleTime: Infinity });
}

/**
 * The instant read-out of the answers so far. It follows the answers about a third of a second after the person stops
 * typing, and keeps showing the previous read-out until the new one arrives, so the panel never blanks or jumps.
 */
export function usePlanPreview(answers: PlanAnswers, enabled = true) {
  const settled = useDebounced(answers, PREVIEW_DELAY_MS);
  const query = useQuery({
    queryKey: ["plan", "preview", settled],
    queryFn: () => api.planPreview(settled),
    placeholderData: keepPreviousData,
    enabled,
    retry: false,
    staleTime: 60_000,
  });
  return { ...query, settling: settled !== answers };
}

/**
 * Strategy A, B and C. The comfort level is left out of the key (and the request always sends the same one), because the
 * three strategies do not depend on it: switching comfort never fetches anything and the cards update at once.
 */
export function usePlanStrategies(answers: PlanAnswers, enabled: boolean) {
  const canonical = useMemo<PlanAnswers>(() => ({ ...answers, risk: "Balance" }), [answers]); // stable between renders, or the debounce never settles
  const settled = useDebounced(canonical, STRATEGIES_DELAY_MS);
  const query = useQuery({
    queryKey: ["plan", "strategies", settled],
    queryFn: () => api.planStrategies(settled),
    placeholderData: keepPreviousData,
    enabled,
    retry: false,
    staleTime: 5 * 60_000,
  });
  const pending = settled !== canonical;
  return { ...query, settling: pending, updating: pending || query.isFetching };
}

export function useSavePlan() {
  const client = useQueryClient();
  return useMutation({
    mutationFn: ({ answers, strategy }: { answers: PlanAnswers; strategy: RiskKey }) => api.planSave(answers, strategy),
    onSuccess: () => client.invalidateQueries({ queryKey: keys.profiles }),
  });
}
