import type { Analysis } from "../api/client";
import { cr, tidyText, times } from "../format";
import { Banner } from "../ui/Status";

/**
 * Warnings that matter whatever else is on screen. They are worked out from the analysis alone, never from which
 * modules a person has chosen to show, so customising the dashboard can never hide one (requirement for Phase 4).
 */
export function attentionItems(analysis: Analysis): { id: string; tone: "warn" | "bad"; title: string; body: string }[] {
  const items: { id: string; tone: "warn" | "bad"; title: string; body: string }[] = [];

  const unconverged = [analysis.current, ...analysis.options.map((o) => o.portfolio)].filter((p) => !p.optimiser_converged);
  if (unconverged.length > 0) {
    items.push({
      id: "optimiser",
      tone: "bad",
      title: "Approximate result.",
      body: `The optimiser did not report a clean solution for ${unconverged.map((p) => p.label).join(", ")}. Treat those weights as approximate.`,
    });
  }

  const { available_cover_cr: have, required_cover_cr: need } = analysis.current;
  if (need > 0 && have < need) {
    items.push({
      id: "liquidity",
      tone: "bad",
      title: "Liquidity shortfall.",
      body: `Your current mix counts ${cr(have, 0)} of easily reached assets against ${cr(need, 0)} needed: ${times(have / need)} the safety net.`,
    });
  }

  if (!analysis.current.dd_ok) {
    items.push({
      id: "drawdown",
      tone: "warn",
      title: "Drawdown above your limit.",
      body: "In the sample history your current mix fell further than the fall you said you could sit through.",
    });
  }
  return items;
}

export function AttentionBar({ analysis }: { analysis: Analysis }) {
  const items = attentionItems(analysis);
  if (items.length === 0) return null;
  return (
    <div className="stack" aria-label="Needs your attention" role="region">
      {items.map((item) => (
        <Banner key={item.id} tone={item.tone} title={item.title} critical={item.tone === "bad"}>
          {tidyText(item.body)}
        </Banner>
      ))}
    </div>
  );
}
