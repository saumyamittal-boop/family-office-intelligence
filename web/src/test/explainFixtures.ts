import type { ExplainAnswer, ExplainCatalog, ExplainReply } from "../api/client";
import { analysis } from "./fixtures";
import { appRoutes } from "./phase4Fixtures";
import { json } from "./render";
import type { Route } from "./render";

export const CATALOG: ExplainCatalog = {
  max_question_length: 300,
  options: ["Current", "Growth", "Balanced", "Defensive"],
  scenarios: ["Baseline (no shock)", "Equities fall 25%", "Market crash", "Inflation and rate spike", "Large unexpected expense", "Lost decade"],
  groups: [
    { title: "My mix", chips: [{ intent: "why_mix", label: "Why the Balanced mix?", slots: { option: "Balanced" } }, { intent: "compare_mixes", label: "How do the mixes compare?", slots: {} }] },
    { title: "Liquidity", chips: [{ intent: "liquidity_enough", label: "Is my liquidity enough?", slots: {} }] },
    { title: "Risk", chips: [{ intent: "scenario_loss", label: "How would a market crash affect me?", slots: { scenario: "Market crash" } }, { intent: "drawdown_meaning", label: "What is a drawdown limit?", slots: {} }] },
    { title: "About the model", chips: [{ intent: "help", label: "What can I ask?", slots: {} }] },
  ],
};

const fig = (key: string, label: string, shown: string, value: number | null, unit: ExplainAnswer["figures"][number]["unit"], field: string, extra: Partial<ExplainAnswer["figures"][number]> = {}) =>
  ({ key, label, shown, value, unit, field, page: "Risk and liquidity", derived: false, in_table: false, ...extra });

export function liquidityAnswer(over: Partial<ExplainAnswer> = {}): ExplainAnswer {
  return {
    intent: "liquidity_enough",
    title: "Is my liquidity enough?",
    lead: "Over the next 24 months your planned outflows come to ₹120 Cr. Your liquid assets count for ₹469 Cr, which is 3.9x the amount needed.",
    sections: [
      { heading: "What this means", lines: ["That is a comfortable margin: the liquid assets cover the planned outflows with room to spare."], from_engine: false },
      { heading: "The basis used", lines: ["All liquid tiers, haircut-adjusted (as specified)"], from_engine: true },
    ],
    tables: [{ caption: "Liquidity ladder: the first years", columns: ["Year", "Outflows", "Liquid assets"], rows: [["1", "₹3.0 Cr", "₹129.0 Cr"], ["2", "₹3.1 Cr", "₹139.1 Cr"]] }],
    figures: [
      fig("need", "Outflows to be covered", "₹120 Cr", 120, "cr", "current.required_cover_cr"),
      fig("have", "Liquid assets counted", "₹469 Cr", 469, "cr", "current.available_cover_cr"),
      fig("ratio", "Cover", "3.9x", 3.9, "ratio", "current.available_cover_cr / current.required_cover_cr", { derived: true }),
      fig("lad.y1", "Year", "1", 1, "count", "current_ladder[0].year", { in_table: true }),
    ],
    caveats: ["This is an illustrative simulation on synthetic data. It is not investment advice."],
    notes: [],
    links: [{ label: "Risk and liquidity", to: "/risk" }],
    follow_ups: [{ intent: "cover_basis", label: "What counts towards the cover?", slots: {} }],
    ...over,
  };
}

export const answerReply = (over: Partial<ExplainReply> = {}, answer: Partial<ExplainAnswer> = {}): ExplainReply => ({
  kind: "answer", intent: "liquidity_enough", confidence: null, message: null, answer: liquidityAnswer(answer), suggestions: [], ...over,
});
export const refusalReply: ExplainReply = {
  kind: "refusal", intent: null, confidence: null, answer: null,
  message: "I can't tell you what to buy, sell or choose. I can show what the model's mixes imply for your family, how they compare, and what they assume. The choice stays yours.",
  suggestions: [{ intent: "compare_mixes", label: "How do the mixes compare?", slots: {} }, { intent: "why_mix", label: "Why the Balanced mix?", slots: { option: "Balanced" } }],
};
export const clarifyReply: ExplainReply = {
  kind: "clarify", intent: null, confidence: 0.41, answer: null, message: "I wasn't sure which of these you meant. Choose one, or ask in other words.",
  suggestions: [{ intent: "liquidity_enough", label: "Is my liquidity enough?", slots: {} }, { intent: "cover_basis", label: "What counts towards the cover?", slots: {} }],
};
export const outOfScopeReply: ExplainReply = {
  kind: "out_of_scope", intent: null, confidence: null, answer: null, message: "I couldn't match that to a question I can answer. Here are some I can.",
  suggestions: [{ intent: "help", label: "What can I ask?", slots: {} }],
};

type Body = { question?: string | null; intent?: string | null };

/** The canned server with the assistant added. `reply` decides what each question gets. */
export function assistantApp(reply: (body: Body) => ExplainReply | Response = () => answerReply(), extra: Record<string, Route> = {}): Record<string, Route> {
  return appRoutes(analysis(), {
    "GET /api/explain/catalog": json(CATALOG),
    "POST /api/profiles/1/explain": (init) => {
      const made = reply(JSON.parse(String(init?.body ?? "{}")) as Body);
      return made instanceof Response ? made : new Response(JSON.stringify(made));
    },
    ...extra,
  });
}
