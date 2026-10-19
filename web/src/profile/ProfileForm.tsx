import { useState } from "react";
import type { ReactNode } from "react";
import { Button } from "../ui/Button";
import { Card } from "../ui/Card";
import { TextField } from "../ui/Controls";
import { NumberField } from "../ui/NumberField";
import { Banner } from "../ui/Status";
import { check, holdingsTotal, ILLIQUID, MAX_ONE_OFFS, newRowId, sameForm, toInput } from "./form";
import type { Check, FormState, Num } from "./form";
import type { ProfileInput } from "../api/client";

function Section({ title, hint, children }: { title: string; hint?: string; children: ReactNode }) {
  return (
    <Card title={title} subtitle={hint}>
      <div className="form-section">{children}</div>
    </Card>
  );
}

const messageFor = (checks: readonly Check[], field: string): string | null => checks.find((c) => c.field === field)?.message ?? null;

export type Outcome = { kind: "saved" | "created"; message: string };

/**
 * Every input of a family profile, in the units people use. Changes are checked as they are typed; nothing is sent until
 * "Save". `initial` seeds the form; give the component a new `key` to start it afresh for another profile.
 */
export function ProfileForm({
  initial,
  classes,
  isNew,
  saving,
  serverProblems,
  onSave,
  onSaveAsNew,
}: {
  initial: FormState;
  classes: readonly string[];
  isNew: boolean;
  saving: boolean;
  serverProblems: readonly string[];
  onSave: (input: ProfileInput) => void;
  onSaveAsNew: (input: ProfileInput) => void;
}) {
  const [form, setForm] = useState<FormState>(initial);
  const checks = check(form);
  const changed = !sameForm(form, initial);
  const input = toInput(form);

  const set = <K extends keyof FormState>(key: K, value: FormState[K]) => setForm((f) => ({ ...f, [key]: value }));
  const setHolding = (name: string, value: Num) => setForm((f) => ({ ...f, holdings: { ...f.holdings, [name]: value } }));
  const setIlliquid = <K extends keyof FormState["illiquid"]>(key: K, value: FormState["illiquid"][K]) =>
    setForm((f) => ({ ...f, illiquid: { ...f.illiquid, [key]: value } }));
  const setLimit = (name: string, side: "min" | "max", value: Num) =>
    setForm((f) => ({ ...f, limits: { ...f.limits, [name]: { ...f.limits[name]!, [side]: value } } }));

  const total = holdingsTotal(form);
  const marketClasses = classes.filter((c) => c !== ILLIQUID);

  return (
    <form
      className="stack-lg"
      noValidate
      onSubmit={(event) => {
        event.preventDefault();
        if (input) onSave(input);
      }}
    >
      <Section title="Basics">
        <div className="form-grid">
          <TextField label="Profile name" value={form.name} maxLength={60} onChange={(e) => set("name", e.target.value)} error={form.name.trim() === "" ? messageFor(checks, "name") : null} />
          <NumberField label="Total corpus" unit="₹ Cr" value={form.corpus} min={1} max={1_000_000} onChange={(v) => set("corpus", v)} />
          <NumberField label="Annual spending" unit="₹ Cr" value={form.spending} min={0} max={100_000} onChange={(v) => set("spending", v)} />
          <NumberField label="Investment horizon" unit="years" value={form.horizon} min={1} max={60} integer onChange={(v) => set("horizon", v)} />
          <NumberField label="Largest fall you can sit through" unit="%" value={form.maxDrawdown} min={1} max={80} onChange={(v) => set("maxDrawdown", v)} />
          <NumberField label="Safety net" unit="months of outflows" value={form.coverMonths} min={1} max={240} integer onChange={(v) => set("coverMonths", v)} />
          <NumberField label="Target real return" unit="% a year" value={form.target} min={-5} max={25} onChange={(v) => set("target", v)} />
        </div>
      </Section>

      <Section title="Current holdings" hint="Share of the whole corpus. They need to add up to 100%.">
        <div className="form-grid">
          {classes.map((name) => (
            <NumberField
              key={name} label={name === ILLIQUID ? "Illiquid (held fixed)" : name} unit="%" value={form.holdings[name] ?? null}
              min={0} max={100} onChange={(v) => setHolding(name, v)}
            />
          ))}
        </div>
        <p className={`sum-note ${Math.abs(total - 100) > 0.5 ? "field-error" : "muted"}`} role="status">
          Total: {total.toFixed(1)}% {Math.abs(total - 100) > 0.5 ? "(needs to be 100%)" : ""}
        </p>
        {messageFor(checks, "holdings") && Math.abs(total - 100) <= 0.5 && <p className="field-error">{messageFor(checks, "holdings")}</p>}
      </Section>

      <Section title="Illiquid holdings" hint="Held fixed by the model: it never buys or sells them, and they never count towards the safety net.">
        <div className="form-grid">
          <TextField label="What is it?" value={form.illiquid.description} maxLength={60} onChange={(e) => setIlliquid("description", e.target.value)} />
          <NumberField label="Assumed return" unit="% a year" value={form.illiquid.expectedReturn} min={-10} max={40} onChange={(v) => setIlliquid("expectedReturn", v)} />
          <NumberField
            label="Assumed volatility" unit="%" value={form.illiquid.volatility} min={0} max={80} onChange={(v) => setIlliquid("volatility", v)}
            hint="Appraisal-based values look calmer than the true risk. Treat this as a floor."
          />
          <NumberField label="Lock-in" unit="years" value={form.illiquid.lockIn} min={0} max={30} integer onChange={(v) => setIlliquid("lockIn", v)} />
          <NumberField label="Correlation with listed equities" value={form.illiquid.corr} min={0} max={1} onChange={(v) => setIlliquid("corr", v)} hint="0 to 1" />
        </div>
      </Section>

      <Section title="Planned one-off outflows" hint={`Up to ${MAX_ONE_OFFS}, in rupees crore, by year from today.`}>
        {form.oneOffs.length === 0 ? (
          <p className="empty-note">No one-off outflows planned.</p>
        ) : (
          <ul className="row-list">
            {form.oneOffs.map((row, i) => (
              <li key={row.id} className="row-item">
                <NumberField
                  label={`Outflow ${i + 1}: year`} value={row.year} min={1} max={form.horizon ?? 60} integer
                  onChange={(v) => setForm((f) => ({ ...f, oneOffs: f.oneOffs.map((o) => (o.id === row.id ? { ...o, year: v } : o)) }))}
                />
                <NumberField
                  label={`Outflow ${i + 1}: amount`} unit="₹ Cr" value={row.amount} min={0.01}
                  onChange={(v) => setForm((f) => ({ ...f, oneOffs: f.oneOffs.map((o) => (o.id === row.id ? { ...o, amount: v } : o)) }))}
                />
                <Button
                  variant="ghost" icon="minus" aria-label={`Remove outflow ${i + 1}`}
                  onClick={() => setForm((f) => ({ ...f, oneOffs: f.oneOffs.filter((o) => o.id !== row.id) }))}
                />
              </li>
            ))}
          </ul>
        )}
        <div>
          <Button
            icon="plus" disabled={form.oneOffs.length >= MAX_ONE_OFFS}
            onClick={() => setForm((f) => ({ ...f, oneOffs: [...f.oneOffs, { id: newRowId(), year: 1, amount: 1 }] }))}
          >
            Add an outflow
          </Button>
          {form.oneOffs.length >= MAX_ONE_OFFS && <span className="muted"> That is the most the model takes.</span>}
        </div>
      </Section>

      <Section title="Limits for each asset class" hint="The smallest and largest share of the liquid part the model may use. Illiquid holdings are not included.">
        <ul className="row-list">
          {marketClasses.map((name) => {
            const lim = form.limits[name];
            if (!lim) return null;
            return (
              <li key={name} className="row-item">
                <NumberField label={`${name}: minimum`} unit="%" value={lim.min} min={0} max={100} onChange={(v) => setLimit(name, "min", v)} error={lim.min !== null && lim.max !== null && lim.min > lim.max ? "The minimum can't be above the maximum." : null} />
                <NumberField label={`${name}: maximum`} unit="%" value={lim.max} min={0} max={100} onChange={(v) => setLimit(name, "max", v)} />
              </li>
            );
          })}
        </ul>
        {messageFor(checks, "limits") && <p className="field-error">{messageFor(checks, "limits")}</p>}
      </Section>

      {serverProblems.length > 0 && (
        <Banner tone="bad" title="The server could not accept this profile." critical>
          <ul className="reasons">
            {serverProblems.map((p) => (
              <li key={p}>{p}</li>
            ))}
          </ul>
        </Banner>
      )}

      {checks.length > 0 && changed && (
        <Banner tone="warn" title={`${checks.length === 1 ? "One thing" : `${checks.length} things`} to fix before saving:`} live>
          <ul className="reasons">
            {checks.map((c) => (
              <li key={`${c.field}-${c.message}`}>{c.message}</li>
            ))}
          </ul>
        </Banner>
      )}

      <div className="form-actions">
        <Button type="submit" variant="primary" disabled={!input || saving || (!isNew && !changed)}>
          {saving ? "Saving…" : isNew ? "Create profile" : "Save changes"}
        </Button>
        {!isNew && (
          <Button disabled={!input || saving} onClick={() => input && onSaveAsNew(input)}>
            Save as new profile
          </Button>
        )}
      </div>
    </form>
  );
}
