import { Icon } from "./Icon";
import { toneIcon } from "./Status";
import type { Tone } from "./Status";

const WORD: Partial<Record<Tone, string>> = { good: "OK", warn: "Warning", bad: "Problem", info: "Note" };

/** One headline number with its plain-language meaning, and an optional "About this" button. */
export function StatTile({
  label,
  value,
  sub,
  tone = "neutral",
  onInfo,
}: {
  label: string;
  value: string;
  sub?: string;
  tone?: Tone;
  onInfo?: () => void;
}) {
  const icon = toneIcon(tone);
  return (
    <div className={`tile tile-${tone}`}>
      <div className="tile-top">
        <span className="tile-label">{label}</span>
        {onInfo && (
          <button type="button" className="tile-info" onClick={onInfo} aria-label={`About ${label}`}>
            <Icon name="info" size={16} />
          </button>
        )}
      </div>
      <div className="tile-value">
        {value}
        {icon && (
          <span className="tile-status">
            <Icon name={icon} size={18} />
            <span className="sr-only">{WORD[tone]}</span>
          </span>
        )}
      </div>
      {sub && <div className="tile-sub">{sub}</div>}
    </div>
  );
}
