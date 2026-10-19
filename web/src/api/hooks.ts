import { keepPreviousData, useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import type { QueryClient } from "@tanstack/react-query";
import { markFreshSignup } from "../plan/draft";
import { api, ApiError, setCsrf } from "./client";
import type { Basis, DemoFamily, ModuleId, ProfileInput, ScenarioRequest, SessionInfo } from "./client";

export const keys = {
  session: ["session"] as const,
  meta: ["meta"] as const,
  profiles: ["profiles"] as const,
  analysis: (id: number, basis: Basis) => ["analysis", id, basis] as const,
  history: (id: number, basis: Basis) => ["history", id, basis] as const,
  scenario: (id: number, request: ScenarioRequest | null) => ["scenario", id, JSON.stringify(request)] as const,
  dashboard: ["dashboard"] as const,
  profile: (id: number) => ["profile", id] as const,
};

/** The signed-in session, or null when nobody is signed in. */
export function useSession() {
  return useQuery({
    queryKey: keys.session,
    queryFn: async (): Promise<SessionInfo | null> => {
      try {
        const session = await api.me();
        setCsrf(session.csrf_token);
        return session;
      } catch (error) {
        if (error instanceof ApiError && error.status === 401) return null;
        throw error;
      }
    },
    retry: false,
    staleTime: Infinity,
  });
}

export function useMeta() {
  return useQuery({ queryKey: keys.meta, queryFn: api.meta, staleTime: Infinity });
}

export function useProfiles(enabled: boolean) {
  return useQuery({ queryKey: keys.profiles, queryFn: api.profiles, enabled });
}

export function useAnalysis(profileId: number | null, basis: Basis) {
  return useQuery({
    queryKey: keys.analysis(profileId ?? 0, basis),
    queryFn: () => api.analysis(profileId as number, basis),
    enabled: profileId !== null,
    retry: false,
    staleTime: 5 * 60 * 1000,
  });
}

/** Value and drawdown curves for the current mix and the three options. Reuses the server's cached analysis. */
export function useHistory(profileId: number | null, basis: Basis) {
  return useQuery({
    queryKey: keys.history(profileId ?? 0, basis),
    queryFn: () => api.history(profileId as number, basis),
    enabled: profileId !== null,
    retry: false,
    staleTime: 5 * 60 * 1000,
  });
}

/** One scenario (a built-in one or the custom dials) applied to every option. Keeps the last answer on screen while a new one loads. */
export function useScenarioComparison(profileId: number | null, request: ScenarioRequest | null) {
  return useQuery({
    queryKey: keys.scenario(profileId ?? 0, request),
    queryFn: () => api.scenario(profileId as number, request as ScenarioRequest),
    enabled: profileId !== null && request !== null,
    retry: false,
    staleTime: 5 * 60 * 1000,
    placeholderData: keepPreviousData,
  });
}

/** The person's chosen dashboard modules (the default four until they save their own). */
export function useDashboard() {
  return useQuery({ queryKey: keys.dashboard, queryFn: api.dashboard, retry: false, staleTime: 5 * 60 * 1000 });
}

export function useSaveDashboard() {
  const client = useQueryClient();
  return useMutation({
    mutationFn: (modules: ModuleId[]) => api.saveDashboard(modules),
    onSuccess: (saved) => client.setQueryData(keys.dashboard, saved),
  });
}

export function useResetDashboard() {
  const client = useQueryClient();
  return useMutation({
    mutationFn: () => api.resetDashboard(),
    onSuccess: (saved) => client.setQueryData(keys.dashboard, saved),
  });
}

/** The full profile being edited. Never refetched in the background: a refetch would hand the form new data while someone is typing.
 * It changes only through the editor itself, which updates this cache when it saves. */
export function useProfile(profileId: number | null) {
  return useQuery({
    queryKey: keys.profile(profileId ?? 0),
    queryFn: () => api.profile(profileId as number),
    enabled: profileId !== null,
    retry: false,
    staleTime: Infinity,
  });
}

const RESULTS = ["analysis", "history", "scenario"];
const isResultOf = (profileId: number) => (q: { queryKey: readonly unknown[] }) =>
  RESULTS.includes(String(q.queryKey[0])) && q.queryKey[1] === profileId;

/** Saving a profile changes everything computed from it: reset those results so no old number lingers, and recompute what is on screen. */
function resetResultsFor(client: QueryClient, profileId: number): void {
  void client.resetQueries({ predicate: isResultOf(profileId) });
}

export function useSaveProfile() {
  const client = useQueryClient();
  return useMutation({
    mutationFn: ({ id, body }: { id: number; body: ProfileInput }) => api.updateProfile(id, body),
    onSuccess: (saved) => {
      resetResultsFor(client, saved.id);
      client.setQueryData(keys.profile(saved.id), saved);
      void client.invalidateQueries({ queryKey: keys.profiles });
    },
  });
}

export function useCreateProfile() {
  const client = useQueryClient();
  return useMutation({
    mutationFn: (body: ProfileInput) => api.createProfile(body),
    onSuccess: (created) => {
      client.setQueryData(keys.profile(created.id), created);
      void client.invalidateQueries({ queryKey: keys.profiles });
    },
  });
}

export function useDeleteProfile() {
  const client = useQueryClient();
  return useMutation({
    mutationFn: (id: number) => api.deleteProfile(id),
    onSuccess: (_, id) => {
      client.removeQueries({ predicate: isResultOf(id) });
      client.removeQueries({ queryKey: keys.profile(id) });
      void client.invalidateQueries({ queryKey: keys.profiles });
    },
  });
}

/** Forget everything that belongs to a person (profiles, analyses), but keep the session and public facts in place:
 * the screen is subscribed to them, and clearing the whole cache would orphan that subscription. */
function dropPrivateData(client: QueryClient): void {
  client.removeQueries({ predicate: (q) => q.queryKey[0] !== keys.session[0] && q.queryKey[0] !== keys.meta[0] });
}

function useStartSession<A extends unknown[]>(call: (...args: A) => Promise<SessionInfo>, afterSuccess?: () => void) {
  const client = useQueryClient();
  return useMutation({
    mutationFn: (args: A) => call(...args),
    onSuccess: (session) => {
      afterSuccess?.();
      setCsrf(session.csrf_token);
      dropPrivateData(client); // nothing from a previous sign-in may linger
      client.setQueryData(keys.session, session);
    },
  });
}

export const useLogin = () => {
  const m = useStartSession(api.login);
  return { ...m, run: (username: string, password: string) => m.mutate([username, password]) };
};
export const useSignup = () => {
  const m = useStartSession(api.signup, markFreshSignup); // a brand-new account lands on the guided plan
  return { ...m, run: (username: string, password: string) => m.mutate([username, password]) };
};
export const useDemo = () => {
  const m = useStartSession(api.demo);
  return { ...m, run: (family: DemoFamily) => m.mutate([family]) };
};

export function useLogout() {
  const client = useQueryClient();
  return useMutation({
    mutationFn: api.logout,
    onSettled: () => {
      setCsrf("");
      dropPrivateData(client);
      client.setQueryData(keys.session, null);
    },
  });
}
