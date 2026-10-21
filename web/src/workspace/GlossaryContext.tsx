import { createContext, useCallback, useContext, useMemo, useState } from "react";
import type { ReactNode } from "react";
import type { GlossaryKey } from "../content/glossary";
import { useExplain } from "../explain/ExplainContext";
import { GlossaryPanel } from "./GlossaryPanel";

type Glossary = { open: (term: GlossaryKey) => void };

const GlossaryContext = createContext<Glossary | null>(null);

/** One "About this number" panel for a whole page: any module can open it, and it is drawn once. */
export function GlossaryProvider({ children }: { children: ReactNode }) {
  const [term, setTerm] = useState<GlossaryKey | null>(null);
  const explain = useExplain();
  const open = useCallback((next: GlossaryKey) => setTerm(next), []);
  const value = useMemo(() => ({ open }), [open]);
  return (
    <GlossaryContext.Provider value={value}>
      {children}
      <GlossaryPanel term={term} onClose={() => setTerm(null)} onAsk={(intent) => { setTerm(null); explain.open({ intent }); }} />
    </GlossaryContext.Provider>
  );
}

export function useGlossary(): Glossary {
  const context = useContext(GlossaryContext);
  if (!context) throw new Error("useGlossary must be used inside <GlossaryProvider>");
  return context;
}
