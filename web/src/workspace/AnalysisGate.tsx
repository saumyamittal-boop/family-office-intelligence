import type { ReactNode } from "react";
import { ApiError } from "../api/client";
import type { Analysis, Basis, ProfileSummary } from "../api/client";
import { EmptyState, ErrorState, LoadingBlock } from "../ui/States";
import { ButtonLink } from "../ui/Button";
import { useLocation } from "react-router-dom";
import { useWorkspace } from "./WorkspaceProvider";

export type Ready = { analysis: Analysis; profile: ProfileSummary; profileId: number; basis: Basis; corpusCr: number };

/**
 * Shows loading, error and empty states until the chosen family's analysis is ready, then hands it to `children`.
 * Every analyst page and the dashboard use it, so they all fail and wait the same way.
 */
export function AnalysisGate({ children }: { children: (ready: Ready) => ReactNode }) {
  const { profiles, profile, analysis, basis } = useWorkspace();
  const { search } = useLocation();

  if (profiles.isPending) return <LoadingBlock label="Loading your family profiles" />;
  if (profiles.isError) {
    return (
      <ErrorState
        title="Can't load your profiles"
        message={profiles.error instanceof ApiError ? profiles.error.message : "Something went wrong."}
        onRetry={() => profiles.refetch()}
      />
    );
  }
  if (!profile) {
    return (
      <EmptyState
        icon="profile"
        title="No family profile yet"
        action={
          <ButtonLink to={{ pathname: "/plan", search }} variant="primary">
            Plan my money
          </ButtonLink>
        }
      >
        Answer a few questions and your first plan will be saved here.
      </EmptyState>
    );
  }
  if (analysis.isPending) return <LoadingBlock label="Running the allocation model" rows={5} />;
  if (analysis.isError || !analysis.data) {
    return (
      <ErrorState
        title="The analysis could not be run"
        message={analysis.error instanceof ApiError ? analysis.error.message : "Something went wrong."}
        onRetry={() => analysis.refetch()}
      />
    );
  }
  // Keyed by what the analysis is for, so switching family or basis starts the page's own state afresh.
  return (
    <div key={`${analysis.data.profile_id}-${analysis.data.basis}`}>
      {children({ analysis: analysis.data, profile, profileId: profile.id, basis, corpusCr: profile.corpus_cr })}
    </div>
  );
}
