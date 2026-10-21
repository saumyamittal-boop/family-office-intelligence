import { GLOSSARY } from "../content/glossary";
import type { GlossaryKey } from "../content/glossary";
import { Button } from "../ui/Button";
import { SidePanel } from "../ui/Overlays";

/** The assistant question that goes with each number, where there is one. */
const ASK: Partial<Record<GlossaryKey, { intent: string; label: string }>> = {
  expectedReturn: { intent: "expected_return", label: "Ask the assistant about my expected return" },
  volatility: { intent: "compare_mixes", label: "Ask the assistant how the mixes compare" },
  worstDrawdown: { intent: "drawdown_meaning", label: "Ask the assistant about my drawdown" },
  cvar: { intent: "cvar_meaning", label: "Ask the assistant about CVaR" },
  liquidityCover: { intent: "liquidity_enough", label: "Ask the assistant about my liquidity" },
};

/** The detail behind a headline number: what it means, how it is worked out, and what it does not tell you. */
export function GlossaryPanel({ term, onClose, onAsk }: { term: GlossaryKey | null; onClose: () => void; onAsk?: (intent: string) => void }) {
  const entry = term ? GLOSSARY[term] : null;
  const ask = term ? ASK[term] : undefined;
  return (
    <SidePanel
      open={entry !== null}
      onOpenChange={(open) => !open && onClose()}
      title={entry?.title ?? ""}
      description={entry?.summary}
    >
      {entry && (
        <>
          <section>
            <h3>How it is worked out</h3>
            <ul>
              {entry.how.map((line) => (
                <li key={line}>{line}</li>
              ))}
            </ul>
          </section>
          <section>
            <h3>What it does not tell you</h3>
            <ul>
              {entry.limits.map((line) => (
                <li key={line}>{line}</li>
              ))}
            </ul>
          </section>
          {ask && onAsk && <Button variant="secondary" icon="assistant" onClick={() => onAsk(ask.intent)}>{ask.label}</Button>}
          <p className="hint">Illustrative simulation on synthetic data, not investment advice.</p>
        </>
      )}
    </SidePanel>
  );
}
