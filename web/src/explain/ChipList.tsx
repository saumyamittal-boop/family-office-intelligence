import type { ExplainChip } from "../api/client";

/** Questions as buttons. Choosing one asks it exactly as written here: nothing the person typed is involved. */
export function ChipList({
  chips, onPick, label, disabled = false,
}: {
  chips: readonly ExplainChip[];
  onPick: (chip: ExplainChip) => void;
  label: string;
  disabled?: boolean;
}) {
  if (chips.length === 0) return null;
  return (
    <div className="chips" role="group" aria-label={label}>
      {chips.map((chip) => (
        <button key={`${chip.intent}:${chip.label}`} type="button" className="chip" disabled={disabled} onClick={() => onPick(chip)}>
          {chip.label}
        </button>
      ))}
    </div>
  );
}
