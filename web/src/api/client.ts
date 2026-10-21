import type { components } from "./schema";

export type Schemas = components["schemas"];
export type Analysis = Schemas["AnalysisOut"];
export type PortfolioOut = Schemas["PortfolioOut"];
export type PortfolioDetail = Schemas["PortfolioDetail"];
export type SessionInfo = Schemas["SessionOut"];
export type ProfileSummary = Schemas["ProfileSummary"];
export type Meta = Schemas["MetaOut"];
export type Basis = Schemas["AnalysisOut"]["basis"];
export type DemoFamily = Schemas["DemoRequest"]["family"];
export type PlanAnswers = Schemas["PlanAnswersIn"];
export type PlanConfig = Schemas["PlanConfigOut"];
export type PlanPreview = Schemas["PlanPreviewOut"];
export type PlanStrategies = Schemas["PlanStrategiesOut"];
export type Strategy = Schemas["StrategyOut"];
export type RiskKey = PlanAnswers["risk"];
export type Commitment = Schemas["CommitmentIn"];
export type History = Schemas["HistoryOut"];
export type PortfolioHistory = Schemas["PortfolioHistory"];
export type ScenarioRequest = Schemas["ScenarioRequest"];
export type ScenarioComparison = Schemas["ScenarioComparison"];
export type ScenarioPreset = Schemas["ScenarioPreset"];
export type CustomScenario = Schemas["CustomScenario"];
export type Dashboard = Schemas["DashboardOut"];
export type ModuleId = Schemas["DashboardOut"]["modules"][number];
export type ProfileFull = Schemas["ProfileOut"];
export type ProfileInput = Schemas["ProfileIn"];
export type HoldingsFile = Schemas["FileIn"];
export type HoldingsPreview = Schemas["PreviewOut"];
export type HoldingsImport = Schemas["ImportOut"];
export type Consolidation = Schemas["ConsolidationOut"];
export type ApplyResult = Schemas["ApplyOut"];
export type AssetClass = Schemas["ClassTotal"]["asset_class"];
export type HoldingsUnit = Schemas["FileIn"]["unit"];
export type ExplainReply = Schemas["ReplyOut"];
export type ExplainAnswer = Schemas["AnswerOut"];
export type ExplainChip = Schemas["ChipOut"];
export type ExplainCatalog = Schemas["CatalogOut"];
export type ExplainAsk = Schemas["AskIn"];

/** What the server says went wrong, in words that can be shown to a person. */
export class ApiError extends Error {
  constructor(
    public readonly status: number,
    message: string,
    public readonly problems: string[] | null = null,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

// Kept in memory only (never in localStorage): it is re-issued by /api/auth/me after a reload.
let csrfToken = "";
export function setCsrf(token: string): void {
  csrfToken = token;
}

async function request<T>(method: "GET" | "POST" | "PUT" | "DELETE", path: string, body?: unknown): Promise<T> {
  const headers: Record<string, string> = {};
  if (body !== undefined) headers["Content-Type"] = "application/json";
  if (method !== "GET") headers["X-CSRF-Token"] = csrfToken;

  let response: Response;
  try {
    response = await fetch(path, {
      method,
      headers,
      body: body === undefined ? undefined : JSON.stringify(body),
      credentials: "same-origin",
    });
  } catch {
    throw new ApiError(0, "Can't reach the server. Check that the API is running, then try again.");
  }

  if (response.status === 204) return undefined as T;
  const data = (await response.json().catch(() => null)) as { detail?: string; problems?: string[] | null } | null;
  if (!response.ok) {
    throw new ApiError(response.status, data?.detail ?? "Something went wrong.", data?.problems ?? null);
  }
  return data as T;
}

export const api = {
  meta: () => request<Meta>("GET", "/api/meta"),
  me: () => request<SessionInfo>("GET", "/api/auth/me"),
  login: (username: string, password: string) => request<SessionInfo>("POST", "/api/auth/login", { username, password }),
  signup: (username: string, password: string) => request<SessionInfo>("POST", "/api/auth/signup", { username, password }),
  demo: (family: DemoFamily) => request<SessionInfo>("POST", "/api/auth/demo", { family }),
  logout: () => request<void>("POST", "/api/auth/logout"),
  profiles: () => request<ProfileSummary[]>("GET", "/api/profiles"),
  profile: (id: number) => request<ProfileFull>("GET", `/api/profiles/${id}`),
  createProfile: (body: ProfileInput) => request<ProfileFull>("POST", "/api/profiles", body),
  updateProfile: (id: number, body: ProfileInput) => request<ProfileFull>("PUT", `/api/profiles/${id}`, body),
  deleteProfile: (id: number) => request<void>("DELETE", `/api/profiles/${id}`),
  analysis: (profileId: number, basis: Basis) =>
    request<Analysis>("GET", `/api/profiles/${profileId}/analysis?basis=${basis}`),
  history: (profileId: number, basis: Basis) =>
    request<History>("GET", `/api/profiles/${profileId}/history?basis=${basis}`),
  scenario: (profileId: number, body: ScenarioRequest) =>
    request<ScenarioComparison>("POST", `/api/profiles/${profileId}/scenarios`, body),
  holdingsTemplate: () => request<Schemas["TemplateOut"]>("GET", "/api/holdings/template"),
  holdingsPreview: (profileId: number, body: HoldingsFile) =>
    request<HoldingsPreview>("POST", `/api/profiles/${profileId}/holdings/preview`, body),
  holdingsImport: (profileId: number, body: HoldingsFile & { label?: string | null }) =>
    request<HoldingsImport>("POST", `/api/profiles/${profileId}/holdings/imports`, body),
  holdingsImports: (profileId: number) => request<HoldingsImport[]>("GET", `/api/profiles/${profileId}/holdings/imports`),
  holdingsDeleteImport: (profileId: number, importId: number) =>
    request<void>("DELETE", `/api/profiles/${profileId}/holdings/imports/${importId}`),
  holdingsConsolidation: (profileId: number) => request<Consolidation>("GET", `/api/profiles/${profileId}/holdings/consolidation`),
  holdingsApplyPreview: (profileId: number, setCorpus: boolean) =>
    request<ApplyResult>("POST", `/api/profiles/${profileId}/holdings/apply/preview`, { set_corpus: setCorpus }),
  holdingsApply: (profileId: number, setCorpus: boolean) =>
    request<ApplyResult>("POST", `/api/profiles/${profileId}/holdings/apply`, { set_corpus: setCorpus }),
  explainCatalog: () => request<ExplainCatalog>("GET", "/api/explain/catalog"),
  explain: (profileId: number, body: ExplainAsk) =>
    request<ExplainReply>("POST", `/api/profiles/${profileId}/explain`, body),
  dashboard: () => request<Dashboard>("GET", "/api/dashboard"),
  saveDashboard: (modules: ModuleId[]) => request<Dashboard>("PUT", "/api/dashboard", { modules }),
  resetDashboard: () => request<Dashboard>("DELETE", "/api/dashboard"),
  planConfig: () => request<PlanConfig>("GET", "/api/plan/config"),
  planPreview: (answers: PlanAnswers) => request<PlanPreview>("POST", "/api/plan/preview", answers),
  planStrategies: (answers: PlanAnswers) => request<PlanStrategies>("POST", "/api/plan/strategies", answers),
  planSave: (answers: PlanAnswers, strategy: RiskKey) =>
    request<Schemas["SaveOut"]>("POST", "/api/plan/save", { answers, strategy }),
};
