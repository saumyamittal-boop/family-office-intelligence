import { createContext, useCallback, useContext, useMemo, useState } from "react";
import type { ReactNode } from "react";
import { useLocation } from "react-router-dom";
import { ApiError } from "../api/client";
import type { ExplainChip } from "../api/client";
import { useAsk } from "../api/hooks";
import { ButtonLink } from "../ui/Button";
import { SidePanel } from "../ui/Overlays";
import { LoadingBlock } from "../ui/States";
import { Banner } from "../ui/Status";
import { useWorkspace } from "../workspace/WorkspaceProvider";
import { ReplyView } from "./ReplyView";

type Ask = { intent: string; slots?: Record<string, string> };
type Explain = { open: (ask: Ask) => void };

const ExplainContext = createContext<Explain | null>(null);

/**
 * One "Why?" panel for the whole signed-in app: any warning or number can open it with a question type, and it is drawn once.
 * The answer is the same one the Assistant page gives, written from the model's own results.
 */
export function ExplainProvider({ children }: { children: ReactNode }) {
  const { profileId, basis } = useWorkspace();
  const { search } = useLocation();
  const ask = useAsk(profileId);
  const { mutate, reset } = ask;
  const [shown, setShown] = useState(false);

  const run = useCallback((chip: Ask) => mutate({ intent: chip.intent, slots: chip.slots ?? {}, basis }), [mutate, basis]);
  const open = useCallback((next: Ask) => {
    if (profileId === null) return;
    setShown(true);
    run(next);
  }, [profileId, run]);
  const value = useMemo(() => ({ open }), [open]);

  const reply = ask.data;
  const title = reply?.answer?.title ?? "Ask the assistant";
  return (
    <ExplainContext.Provider value={value}>
      {children}
      <SidePanel
        open={shown}
        onOpenChange={(next) => {
          setShown(next);
          if (!next) reset();
        }}
        title={title}
        description="Written from the model's own results. It never predicts or advises."
      >
        {ask.isPending && <LoadingBlock label="Working it out" />}
        {ask.isError && (
          <Banner tone="bad" title="Couldn’t answer." critical>
            {ask.error instanceof ApiError ? ask.error.message : "Something went wrong. Please try again."}
          </Banner>
        )}
        {reply && <ReplyView reply={reply} title={false} busy={ask.isPending} onAsk={(chip: ExplainChip) => run(chip)} />}
        <div className="answer-links">
          <ButtonLink to={{ pathname: "/assistant", search }} variant="secondary" icon="assistant">Ask something else</ButtonLink>
        </div>
      </SidePanel>
    </ExplainContext.Provider>
  );
}

export function useExplain(): Explain {
  const context = useContext(ExplainContext);
  if (!context) throw new Error("useExplain must be used inside <ExplainProvider>");
  return context;
}
