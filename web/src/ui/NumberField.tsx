import { useEffect, useId, useState } from "react";

/** Parse what a person typed: commas and spaces are allowed, anything else that is not a number is "no value". */
export function parseNumber(text: string): number | null {
  const cleaned = text.replace(/[,\s]/g, "");
  if (cleaned === "") return null;
  const value = Number(cleaned);
  return Number.isFinite(value) ? value : null;
}

/**
 * A labelled number box that lets a person type freely (empty, half-typed, with commas) and reports a number, or null
 * while there is none. It shows its own range message at once and ties it to the input for screen readers.
 */
export function NumberField({
  label,
  value,
  onChange,
  min,
  max,
  integer = false,
  unit,
  hint,
  error,
}: {
  label: string;
  value: number;
  onChange: (value: number | null) => void;
  min?: number;
  max?: number;
  integer?: boolean;
  unit?: string;
  hint?: string;
  error?: string | null;
}) {
  const id = useId();
  const [text, setText] = useState(String(value));

  // Follow the value when it changes from outside (a preset, a reset, a restored draft) but not while typing.
  useEffect(() => {
    if (parseNumber(text) !== value) setText(String(value));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [value]);

  const parsed = parseNumber(text);
  let own: string | null = null;
  if (parsed === null) own = "Enter a number.";
  else if (integer && !Number.isInteger(parsed)) own = "Use a whole number.";
  else if (min !== undefined && parsed < min) own = `Must be at least ${min.toLocaleString("en-US")}.`;
  else if (max !== undefined && parsed > max) own = `Must be at most ${max.toLocaleString("en-US")}.`;
  const message = own ?? error ?? null;
  const describedBy = [hint ? `${id}-hint` : "", message ? `${id}-error` : ""].filter(Boolean).join(" ") || undefined;

  return (
    <div className="field">
      <label htmlFor={id} className="field-label">
        {label}
        {unit && <span className="muted"> ({unit})</span>}
      </label>
      <input
        id={id}
        className="input num-input"
        inputMode="decimal"
        autoComplete="off"
        value={text}
        aria-invalid={message ? true : undefined}
        aria-describedby={describedBy}
        onChange={(event) => {
          setText(event.target.value);
          onChange(parseNumber(event.target.value));
        }}
      />
      {hint && (
        <p id={`${id}-hint`} className="field-hint">
          {hint}
        </p>
      )}
      {message && (
        <p id={`${id}-error`} className="field-error">
          {message}
        </p>
      )}
    </div>
  );
}
