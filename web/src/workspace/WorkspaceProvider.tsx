import { createContext, useCallback, useContext, useMemo } from "react";
import type { ReactNode } from "react";
import { useSearchParams } from "react-router-dom";
import type { Basis, ProfileSummary, SessionInfo } from "../api/client";
import { useAnalysis, useProfiles } from "../api/hooks";

type Workspace = {
  profiles: ReturnType<typeof useProfiles>;
  profile: ProfileSummary | null;
  profileId: number | null;
  setProfileId: (id: number) => void;
  basis: Basis;
  setBasis: (basis: Basis) => void;
  analysis: ReturnType<typeof useAnalysis>;
};

const WorkspaceContext = createContext<Workspace | null>(null);

function isBasis(value: string | null): value is Basis {
  return value === "all" || value === "strict";
}

/**
 * Which family profile and which cover basis the screens are showing.
 * Both live in the URL (?profile=5&basis=strict), so a reload or a shared link keeps your place, and nothing is
 * stored in the browser. An unknown profile id in the URL falls back to the first profile you own.
 */
export function WorkspaceProvider({ session, children }: { session: SessionInfo; children: ReactNode }) {
  const [params, setParams] = useSearchParams();
  const profiles = useProfiles(true);

  const requested = Number(params.get("profile"));
  const profile = profiles.data?.find((p) => p.id === requested) ?? profiles.data?.[0] ?? null;
  const profileId = profile?.id ?? null;
  const basisParam = params.get("basis");
  const basis: Basis = isBasis(basisParam) ? basisParam : session.default_basis;

  const update = useCallback(
    (key: string, value: string) => {
      setParams(
        (previous) => {
          const next = new URLSearchParams(previous);
          next.set(key, value);
          return next;
        },
        { replace: true },
      );
    },
    [setParams],
  );

  const analysis = useAnalysis(profileId, basis);
  const value = useMemo<Workspace>(
    () => ({
      profiles,
      profile,
      profileId,
      setProfileId: (id: number) => update("profile", String(id)),
      basis,
      setBasis: (next: Basis) => update("basis", next),
      analysis,
    }),
    [profiles, profile, profileId, basis, analysis, update],
  );

  return <WorkspaceContext.Provider value={value}>{children}</WorkspaceContext.Provider>;
}

export function useWorkspace(): Workspace {
  const context = useContext(WorkspaceContext);
  if (!context) throw new Error("useWorkspace must be used inside <WorkspaceProvider>");
  return context;
}
