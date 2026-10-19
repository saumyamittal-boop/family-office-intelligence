import { GLOSSARY } from "../content/glossary";
import type { GlossaryKey } from "../content/glossary";
import { SidePanel } from "../ui/Overlays";

/** The detail behind a headline number: what it means, how it is worked out, and what it does not tell you. */
export function GlossaryPanel({ term, onClose }: { term: GlossaryKey | null; onClose: () => void }) {
  const entry = term ? GLOSSARY[term] : null;
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
          <p className="hint">Illustrative simulation on synthetic data, not investment advice.</p>
        </>
      )}
    </SidePanel>
  );
}
