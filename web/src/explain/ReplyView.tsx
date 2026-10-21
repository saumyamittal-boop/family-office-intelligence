import type { ExplainChip, ExplainReply } from "../api/client";
import { Banner } from "../ui/Status";
import { AnswerView } from "./AnswerView";
import { ChipList } from "./ChipList";

const TITLE: Record<string, string> = {
  refusal: "Outside what I do.",
  clarify: "Which did you mean?",
  out_of_scope: "No match.",
  empty: "Ask a question.",
};

/** What came back: an answer, or an honest "I can't", "which did you mean?" or "that is not something I know", with ways forward. */
export function ReplyView({
  reply, onAsk, title = true, busy = false,
}: {
  reply: ExplainReply;
  onAsk: (chip: ExplainChip) => void;
  title?: boolean;
  busy?: boolean;
}) {
  const suggestions = reply.suggestions ?? [];
  if (reply.kind === "answer" && reply.answer) {
    return (
      <>
        <AnswerView answer={reply.answer} onAsk={onAsk} title={title} busy={busy} />
        {suggestions.length > 0 && <ChipList label="Not what you meant? Try one of these" chips={suggestions} onPick={onAsk} disabled={busy} />}
      </>
    );
  }
  return (
    <div className="stack">
      <Banner tone={reply.kind === "refusal" ? "warn" : "info"} title={TITLE[reply.kind]} live>
        {reply.message}
      </Banner>
      <ChipList label="Questions you can ask" chips={suggestions} onPick={onAsk} disabled={busy} />
    </div>
  );
}
