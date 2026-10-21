import { useEffect, useRef, useState } from "react";
import type { FormEvent } from "react";
import { useSearchParams } from "react-router-dom";
import { ApiError } from "../api/client";
import type { ExplainChip } from "../api/client";
import { useAsk, useExplainCatalog } from "../api/hooks";
import { cr } from "../format";
import { ChipList } from "../explain/ChipList";
import { ReplyView } from "../explain/ReplyView";
import { Button } from "../ui/Button";
import { Select, TextField } from "../ui/Controls";
import { ErrorState, LoadingBlock } from "../ui/States";
import { Banner } from "../ui/Status";
import { useWorkspace } from "../workspace/WorkspaceProvider";

const SLOT_KEYS = ["option", "scenario"] as const;

/**
 * Ask about your family's results. Every answer is written from the model's own numbers; nothing is predicted, nothing is advised,
 * and the question is not stored (it is sent in the request, not in the address, and forgotten once answered).
 */
export function AssistantPage() {
  const { profiles, profile, profileId, setProfileId, basis } = useWorkspace();
  const catalog = useExplainCatalog();
  const ask = useAsk(profileId);
  const [question, setQuestion] = useState("");
  const [params, setParams] = useSearchParams();
  const asked = useRef<string | null>(null);

  const run = (body: { question?: string; intent?: string; slots?: Record<string, string> }) => ask.mutate({ ...body, slots: body.slots ?? {}, basis });
  const pick = (chip: ExplainChip) => {
    setQuestion("");
    run({ intent: chip.intent, slots: chip.slots });
  };
  const submit = (event: FormEvent) => {
    event.preventDefault();
    if (question.trim()) run({ question: question.trim() });
  };

  // A link from another page can carry a question type (?intent=liquidity_enough): ask it once, then drop it from the address.
  const linked = params.get("intent");
  useEffect(() => {
    if (!linked) {
      asked.current = null; // the link was used up: the same link can be followed again
      return;
    }
    if (profileId === null || asked.current === linked) return;
    asked.current = linked;
    const slots: Record<string, string> = {};
    for (const key of SLOT_KEYS) {
      const value = params.get(key);
      if (value) slots[key] = value;
    }
    ask.mutate({ intent: linked, slots, basis });
    setParams((previous) => {
      const next = new URLSearchParams(previous);
      ["intent", ...SLOT_KEYS].forEach((k) => next.delete(k));
      return next;
    }, { replace: true });
  }, [linked, profileId, basis, params, ask, setParams]);

  return (
    <div className="page">
      <div className="page-head">
        <div>
          <h1>Assistant</h1>
          <p>Ask what the model shows for your family, and why.</p>
        </div>
      </div>

      {profiles.isPending && <LoadingBlock label="Loading your family profiles" />}
      {profiles.isError && (
        <ErrorState
          title="Can't load your profiles" onRetry={() => profiles.refetch()}
          message={profiles.error instanceof ApiError ? profiles.error.message : "Something went wrong."}
        />
      )}
      {profiles.isSuccess && !profile && <ErrorState title="No family profile yet" message="Create a plan first, then ask about it here." />}

      {profile && profileId !== null && (
        <>
          <div className="workspace-bar">
            <Select
              label="Asking about this family" value={profileId}
              onChange={(e) => { setProfileId(Number(e.target.value)); ask.reset(); }}
            >
              {(profiles.data ?? []).map((p) => <option key={p.id} value={p.id}>{p.name} ({cr(p.corpus_cr, 0)})</option>)}
            </Select>
          </div>

          <Banner tone="info" title="What I do and don&rsquo;t do.">
            I explain results the model has already worked out. I don&rsquo;t predict markets, pick investments or tell you what to buy or sell,
            and I never calculate a number myself. Synthetic data only; an illustrative simulation, not investment advice.
          </Banner>

          <form className="ask-form" onSubmit={submit}>
            <TextField
              label="Your question" value={question} maxLength={catalog.data?.max_question_length ?? 300} autoComplete="off"
              hint="For example: is my liquidity enough? Your question is not stored."
              onChange={(e) => setQuestion(e.target.value)}
            />
            <Button type="submit" variant="primary" icon="assistant" disabled={ask.isPending || !question.trim()}>
              {ask.isPending ? "Working it out…" : "Ask"}
            </Button>
          </form>

          <div className="stack" aria-live="polite" aria-busy={ask.isPending}>
            {ask.isPending && <LoadingBlock label="Working it out" />}
            {ask.isError && (
              <Banner tone="bad" title="Couldn&rsquo;t answer." critical>
                {ask.error instanceof ApiError ? ask.error.message : "Something went wrong. Please try again."}
              </Banner>
            )}
            {ask.data && !ask.isPending && <ReplyView reply={ask.data} onAsk={pick} busy={ask.isPending} />}
          </div>

          <section aria-labelledby="starters">
            <h2 id="starters">Or choose a question</h2>
            {catalog.isPending && <LoadingBlock label="Loading the questions" />}
            {catalog.isError && <Banner tone="warn">The list of questions couldn&rsquo;t be loaded. You can still type one above.</Banner>}
            <div className="stack-lg">
              {catalog.data?.groups.map((group) => (
                <div key={group.title}>
                  <h3>{group.title}</h3>
                  <ChipList label={group.title} chips={group.chips} onPick={pick} disabled={ask.isPending} />
                </div>
              ))}
            </div>
          </section>
        </>
      )}
    </div>
  );
}
