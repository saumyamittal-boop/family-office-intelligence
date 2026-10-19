import type { ReactNode } from "react";
import { Icon } from "./Icon";
import type { IconName } from "./Icon";

export type Tone = "good" | "warn" | "bad" | "info" | "neutral";

const ICON: Record<Exclude<Tone, "neutral">, IconName> = { good: "success", warn: "warning", bad: "error", info: "info" };
/** Said aloud by screen readers. Colour is never the only way a status is shown. */
const WORD: Record<Exclude<Tone, "neutral">, string> = { good: "OK", warn: "Warning", bad: "Problem", info: "Note" };

export function toneIcon(tone: Tone): IconName | null {
  return tone === "neutral" ? null : ICON[tone];
}

/** A compact status label: icon + words, in the tone's colours. */
export function Badge({ tone = "neutral", children }: { tone?: Tone; children: ReactNode }) {
  return (
    <span className={`badge badge-${tone}`}>
      {tone !== "neutral" && <Icon name={ICON[tone]} size={14} />}
      {tone !== "neutral" && <span className="sr-only">{WORD[tone]}: </span>}
      {children}
    </span>
  );
}

/**
 * A message that fills the width. `critical` uses role="alert" so it is announced at once; `live` uses role="status"
 * for a message that appears after an action; otherwise it is plain content and adds no announcements.
 */
export function Banner({
  tone = "info",
  title,
  children,
  action,
  critical = false,
  live = false,
}: {
  tone?: Exclude<Tone, "neutral">;
  title?: string;
  children?: ReactNode;
  action?: ReactNode;
  critical?: boolean;
  live?: boolean;
}) {
  return (
    <div className={`banner banner-${tone}`} role={critical ? "alert" : live ? "status" : undefined}>
      <span className="banner-icon">
        <Icon name={ICON[tone]} size={20} />
      </span>
      <div className="banner-body">
        <span className="sr-only">{WORD[tone]}: </span>
        {title && <strong>{title} </strong>}
        {children}
      </div>
      {action && <div className="banner-action">{action}</div>}
    </div>
  );
}
