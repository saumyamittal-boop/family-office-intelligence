import { useEffect, useRef, useState } from "react";
import type { Commitment, PlanAnswers, PlanConfig, PlanPreview } from "../api/client";
import { classColor, HATCH_CSS } from "../charts/colors";
import { cr, pct } from "../format";
import { Button } from "../ui/Button";
import { Select, SegmentedControl, TextField } from "../ui/Controls";
import { NumberField } from "../ui/NumberField";
import { Banner } from "../ui/Status";

export type StepProps = {
  answers: PlanAnswers;
  update: (patch: Partial<PlanAnswers>) => void;
  config: PlanConfig;
  preview: PlanPreview | undefined;
  onValid: (valid: boolean) => void;
};

const inRange = (v: number | null, min: number, max: number): v is number => v !== null && v >= min && v <= max;

// ---- 1. About you ----------------------------------------------------------------------------------------------------------
export function AboutStep({ answers, update, config, onValid }: StepProps) {
  const [name, setName] = useState(answers.name);
  const [wealth, setWealth] = useState<number | null>(answers.wealth);
  const [spending, setSpending] = useState<number | null>(answers.spending);

  const nameOk = name.trim().length > 0 && name.length <= 60;
  const wealthOk = inRange(wealth, config.wealth.min, config.wealth.max);
  const spendingOk = inRange(spending, config.spending.min, config.spending.max);
  useEffect(() => onValid(nameOk && wealthOk && spendingOk), [nameOk, wealthOk, spendingOk, onValid]);

  return (
    <>
      <TextField
        label="What should we call this plan?"
        value={name}
        maxLength={60}
        error={nameOk ? null : "Give the plan a name."}
        onChange={(e) => {
          setName(e.target.value);
          if (e.target.value.trim()) update({ name: e.target.value });
        }}
      />
      <NumberField
        label="About how much is the family's total wealth?"
        unit="₹ Cr"
        hint="A rough number is fine."
        value={answers.wealth}
        min={config.wealth.min}
        max={config.wealth.max}
        onChange={(v) => {
          setWealth(v);
          // A new total suggests a fresh split of what the family owns, as the Streamlit plan does.
          if (inRange(v, config.wealth.min, config.wealth.max) && v !== answers.wealth) update({ wealth: v, amounts: null });
        }}
      />
      <NumberField
        label="About how much does the family spend in a typical year?"
        unit="₹ Cr"
        value={answers.spending}
        min={config.spending.min}
        max={config.spending.max}
        onChange={(v) => {
          setSpending(v);
          if (inRange(v, config.spending.min, config.spending.max)) update({ spending: v });
        }}
      />
    </>
  );
}

// ---- 2. What's coming -------------------------------------------------------------------------------------------------------
type Row = { id: number; kind: string; year: number | null; amount: number | null };

export function ComingStep({ answers, update, config, onValid }: StepProps) {
  const nextId = useRef(answers.commitments.length);
  const [rows, setRows] = useState<Row[]>(() =>
    answers.commitments.map((c, i) => ({ id: i, kind: c.kind, year: c.year, amount: c.amount_cr })),
  );

  const rowOk = (r: Row) => inRange(r.year, 1, config.horizon_years) && Number.isInteger(r.year) && r.amount !== null && r.amount > 0;
  const valid = rows.length <= config.max_commitments && rows.every(rowOk);
  useEffect(() => onValid(valid), [valid, onValid]);

  function commit(next: Row[]) {
    setRows(next);
    if (next.every(rowOk)) {
      const commitments: Commitment[] = next.map((r) => ({ kind: r.kind, year: r.year as number, amount_cr: r.amount as number }));
      update({ commitments });
    }
  }

  const change = (id: number, patch: Partial<Row>) => commit(rows.map((r) => (r.id === id ? { ...r, ...patch } : r)));
  const add = () =>
    commit([
      ...rows,
      { id: nextId.current++, kind: config.commitment_kinds[0] ?? "Other", year: 3, amount: Math.max(0.1, Math.round(answers.wealth * 0.05 * 10) / 10) },
    ]);

  return (
    <>
      <p className="muted">
        For example a child's education, a wedding, buying a property or investing in a business. Add up to {config.max_commitments}. Leave it empty if
        nothing is planned.
      </p>
      {rows.length === 0 && <p className="empty-note">Nothing planned. That is fine; you can add something at any time.</p>}
      <ul className="commitment-list">
        {rows.map((row, index) => (
          <li key={row.id} className="commitment-row" aria-label={`Commitment ${index + 1}`}>
            <Select label="What" value={row.kind} onChange={(e) => change(row.id, { kind: e.target.value })}>
              {config.commitment_kinds.map((k) => (
                <option key={k} value={k}>
                  {k}
                </option>
              ))}
            </Select>
            <NumberField label="In how many years" integer min={1} max={config.horizon_years} value={row.year ?? 0} onChange={(v) => change(row.id, { year: v })} />
            <NumberField label="Amount" unit={"₹ Cr"} min={0.01} value={row.amount ?? 0} onChange={(v) => change(row.id, { amount: v })} />
            <Button variant="ghost" icon="close" aria-label={`Remove commitment ${index + 1}`} onClick={() => commit(rows.filter((r) => r.id !== row.id))} />
          </li>
        ))}
      </ul>
      <div>
        <Button icon="plus" onClick={add} disabled={rows.length >= config.max_commitments}>
          Add a commitment
        </Button>
        {rows.length >= config.max_commitments && <span className="hint"> You can add up to {config.max_commitments}.</span>}
      </div>
    </>
  );
}

// ---- 3. Comfort -------------------------------------------------------------------------------------------------------------
export function ComfortStep({ answers, update, config, preview, onValid }: StepProps) {
  useEffect(() => onValid(true), [onValid]);
  return (
    <fieldset className="choice-group">
      <legend className="field-label">Which sounds most like the family?</legend>
      {config.comfort.map((option) => {
        const loss = preview?.comfort.find((c) => c.key === option.key)?.loss_cr;
        return (
          <label key={option.key} className={`choice-card ${answers.risk === option.key ? "is-chosen" : ""}`}>
            <input type="radio" name="comfort" value={option.key} checked={answers.risk === option.key} onChange={() => update({ risk: option.key })} />
            <span className="choice-body">
              <b>{option.headline}</b>
              <span className="muted">
                {option.blurb} We would plan for a fall of up to {loss !== null && loss !== undefined ? `${cr(loss)} (${pct(option.max_drawdown, 0)})` : pct(option.max_drawdown, 0)} in a bad year.
              </span>
            </span>
          </label>
        );
      })}
    </fieldset>
  );
}

// ---- 4. Safety net ---------------------------------------------------------------------------------------------------------
const QUICK_MONTHS = ["6", "12", "18", "24", "36"] as const;

export function SafetyStep({ answers, update, config, preview, onValid }: StepProps) {
  useEffect(() => onValid(true), [onValid]);
  const net = preview?.safety_net;
  return (
    <>
      <div className="field">
        <label htmlFor="months" className="field-label">
          How many months of spending should always be within easy reach? <b className="months-readout">{answers.months} months</b>
        </label>
        <input
          id="months"
          type="range"
          className="range"
          min={config.months.min}
          max={config.months.max}
          step={1}
          value={answers.months}
          aria-valuetext={`${answers.months} months`}
          onChange={(e) => update({ months: Number(e.target.value) })}
        />
        <p className="field-hint">
          Counted: cash, liquid funds, bonds and gold. Shares are not counted, because they can be down exactly when the money is needed.
        </p>
      </div>
      <SegmentedControl<string>
        label="Quick choices"
        value={QUICK_MONTHS.includes(String(answers.months) as (typeof QUICK_MONTHS)[number]) ? String(answers.months) : ""}
        onChange={(v) => update({ months: Number(v) })}
        options={QUICK_MONTHS.map((m) => ({ value: m, label: `${m} months` }))}
      />
      <p className="muted">Planned commitments in that window are added on top of ordinary spending.</p>
      {net && (
        <Banner tone="info" live>
          Over {net.months} months the family needs about <b>{cr(net.required_cr)}</b> within easy reach: {cr(net.spending_cr)} of spending
          {net.commitments_cr > 0 ? ` plus ${cr(net.commitments_cr)} of planned commitments` : ""}.
        </Banner>
      )}
    </>
  );
}

// ---- 5. What you own --------------------------------------------------------------------------------------------------------
export function OwnStep({ answers, update, config, preview, onValid }: StepProps) {
  const typical = preview?.typical_amounts;
  const current: Record<string, number> | null = typical ? { ...typical, ...(answers.amounts ?? {}) } : (answers.amounts ?? null);
  const problems = preview?.problems ?? [];
  useEffect(() => onValid(current !== null && problems.length === 0), [current, problems.length, onValid]);

  if (!current) return <p className="muted">Working out a typical split to start from…</p>;

  const total = Object.values(current).reduce((sum, v) => sum + v, 0);
  const shares = config.classes.map((c) => ({ ...c, amount: current[c.name] ?? 0 }));
  const summary = shares.filter((s) => s.amount > 0 && total > 0).map((s) => `${s.label} ${pct(s.amount / total, 0)}`).join(", ");

  return (
    <>
      <p className="muted">
        We started with a typical split of {cr(answers.wealth, 0)}. Change anything that is different. A rough picture is enough.
      </p>
      <div className="own-grid">
        {shares.map((s) => (
          <NumberField
            key={s.name}
            label={s.label}
            unit={"₹ Cr"}
            hint={s.description}
            min={0}
            max={1_000_000}
            value={s.amount}
            onChange={(v) => v !== null && v >= 0 && v <= 1_000_000 && update({ amounts: { ...current, [s.name]: v } })}
          />
        ))}
      </div>
      <figure className="own-split" style={{ margin: 0 }}>
        <div className="own-bar" role="img" aria-label={summary ? `Your mix: ${summary}` : "No holdings entered yet"}>
          {shares.map((s) => (
            <span
              key={s.name}
              className="own-seg"
              style={{ width: total > 0 ? `${(s.amount / total) * 100}%` : 0, background: s.name === "Illiquid" ? HATCH_CSS : classColor(s.name) }}
            />
          ))}
        </div>
        <figcaption className="hint">
          Total {cr(total)}
          {answers.amounts && (
            <>
              {" "}
              ·{" "}
              <button type="button" className="link-button" onClick={() => update({ amounts: null })}>
                Reset to a typical split
              </button>
            </>
          )}
        </figcaption>
      </figure>
      {preview?.amounts_differ_from_wealth && preview.amounts_total_cr != null && (
        <Banner tone="info" live>
          These add up to {cr(preview.amounts_total_cr)}, so the plan uses that as the total (you said {cr(answers.wealth)} earlier).
        </Banner>
      )}
    </>
  );
}

