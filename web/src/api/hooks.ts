import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import type { QueryClient } from "@tanstack/react-query";
import { markFreshSignup } from "../plan/draft";
import { api, ApiError, setCsrf } from "./client";
import type { Basis, DemoFamily, SessionInfo } from "./client";

export const keys = {
  session: ["session"] as const,
  meta: ["meta"] as const,
  profiles: ["profiles"] as const,
  analysis: (id: number, basis: Basis) => ["analysis", id, basis] as const,
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
