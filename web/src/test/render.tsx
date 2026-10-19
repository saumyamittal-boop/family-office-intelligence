import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render } from "@testing-library/react";
import type { ReactElement } from "react";
import { MemoryRouter } from "react-router-dom";
import { vi } from "vitest";
import { ThemeProvider } from "../theme/ThemeProvider";
import { TooltipProvider } from "../ui/Overlays";

export function renderWithProviders(ui: ReactElement, route = "/") {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <ThemeProvider>
      <QueryClientProvider client={client}>
        <MemoryRouter initialEntries={[route]}>
          <TooltipProvider>{ui}</TooltipProvider>
        </MemoryRouter>
      </QueryClientProvider>
    </ThemeProvider>,
  );
}

export type Route = (init: RequestInit | undefined) => Response | Promise<Response>;

/** Replace fetch with canned answers, keyed "METHOD /path" (query strings are ignored). Returns the recorded calls. */
export function serve(routes: Record<string, Route>) {
  const calls: { path: string; method: string; body?: string; headers: Record<string, string> }[] = [];
  vi.stubGlobal("fetch", (path: string, init?: RequestInit) => {
    const method = init?.method ?? "GET";
    calls.push({ path, method, body: typeof init?.body === "string" ? init.body : undefined, headers: { ...(init?.headers as Record<string, string> | undefined) } });
    const route = routes[`${method} ${path.split("?")[0]}`];
    return Promise.resolve(route ? route(init) : new Response(JSON.stringify({ detail: "Not found." }), { status: 404 }));
  });
  return calls;
}

export const json =
  (body: unknown, status = 200) =>
  () =>
    new Response(JSON.stringify(body), { status });

/** A canned answer that depends on the JSON the app sent, for testing things that must follow what was typed. */
export const jsonBy =
  <T,>(make: (body: T) => unknown, status = 200): Route =>
  (init) =>
    new Response(JSON.stringify(make(JSON.parse(String(init?.body ?? "null")) as T)), { status });
