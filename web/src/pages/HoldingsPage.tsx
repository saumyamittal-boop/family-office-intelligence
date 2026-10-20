import { useState } from "react";
import { useLocation } from "react-router-dom";
import type { HoldingsImport } from "../api/client";
import { ApplyCard } from "../holdings/ApplyCard";
import { ConsolidationView } from "../holdings/ConsolidationView";
import { ImportFlow } from "../holdings/ImportFlow";
import { ImportsList } from "../holdings/ImportsList";
import { cr } from "../format";
import { Select } from "../ui/Controls";
import { ErrorState, LoadingBlock } from "../ui/States";
import { Banner } from "../ui/Status";
import { ApiError } from "../api/client";
import { useWorkspace } from "../workspace/WorkspaceProvider";

/** Bring in statements, see everything in one place, and (only if chosen) use it as the profile's holdings. */
export function HoldingsPage() {
  const { profiles, profile, profileId, setProfileId } = useWorkspace();
  const { search } = useLocation();
  const [notice, setNotice] = useState<HoldingsImport | null>(null);

  return (
    <div className="page">
      <div className="page-head">
        <div>
          <h1>Holdings</h1>
          <p>Bring in your statements and see everything you own in one place.</p>
        </div>
      </div>

      {profiles.isPending && <LoadingBlock label="Loading your family profiles" />}
      {profiles.isError && (
        <ErrorState
          title="Can't load your profiles" onRetry={() => profiles.refetch()}
          message={profiles.error instanceof ApiError ? profiles.error.message : "Something went wrong."}
        />
      )}
      {profiles.isSuccess && !profile && <ErrorState title="No family profile yet" message="Create a plan first, then bring your holdings in." />}

      {profile && profileId !== null && (
        <>
          <div className="workspace-bar">
            <Select label="Holdings belong to this family" value={profileId} onChange={(e) => { setProfileId(Number(e.target.value)); setNotice(null); }}>
              {(profiles.data ?? []).map((p) => (
                <option key={p.id} value={p.id}>{p.name} ({cr(p.corpus_cr, 0)})</option>
              ))}
            </Select>
          </div>
          <Banner tone="info">
            Synthetic data only for now. Real family files wait for the privacy review. Imported holdings never change a profile unless you choose to use them below.
          </Banner>
          {notice && (
            <Banner tone="good" live title="Imported.">
              {notice.row_count} holdings, {cr(notice.total_cr, 1)}, from {notice.filename}.
            </Banner>
          )}
          <div className="stack-lg" key={profileId}>
            <ImportFlow profileId={profileId} onImported={setNotice} />
            <ImportsList profileId={profileId} />
            <ConsolidationView profileId={profileId} />
            <ApplyCard profileId={profileId} search={search} />
          </div>
        </>
      )}
    </div>
  );
}
