import { useState } from "react";
import { ApiError } from "../api/client";
import type { Dashboard, ModuleId } from "../api/client";
import { useResetDashboard, useSaveDashboard } from "../api/hooks";
import { MODULE_ORDER, MODULES } from "../modules/catalog";
import { Button } from "../ui/Button";
import { Select } from "../ui/Controls";
import { Icon } from "../ui/Icon";
import { SidePanel } from "../ui/Overlays";
import { Badge, Banner } from "../ui/Status";

const SLOTS = 4;

const same = (a: readonly ModuleId[], b: readonly ModuleId[]) => a.length === b.length && a.every((id, i) => id === b[i]);

/** Put `id` in slot `index`. If it already sits in another slot the two swap, so there are always four different modules. */
export function place(draft: readonly ModuleId[], index: number, id: ModuleId): ModuleId[] {
  const next = [...draft];
  const current = next[index];
  const elsewhere = next.indexOf(id);
  if (elsewhere !== -1 && current !== undefined) next[elsewhere] = current;
  next[index] = id;
  return next;
}

/** Move the module in slot `from` to slot `to`, shifting the others. */
export function move(draft: readonly ModuleId[], from: number, to: number): ModuleId[] {
  const next = [...draft];
  const [taken] = next.splice(from, 1);
  if (taken !== undefined) next.splice(to, 0, taken);
  return next;
}

function CustomiseForm({ saved, onDone }: { saved: Dashboard; onDone: (message: string) => void }) {
  const [draft, setDraft] = useState<ModuleId[]>(saved.modules);
  const save = useSaveDashboard();
  const reset = useResetDashboard();
  const available = new Set(saved.catalog.filter((m) => m.available).map((m) => m.id));
  const changed = !same(draft, saved.modules);
  const busy = save.isPending || reset.isPending;
  const failure = save.error ?? reset.error;

  return (
    <div className="stack-lg">
      <p>
        Choose the four modules that matter most to you and put them in the order you want. The others stay one click away on the
        Recommendation, Risk and liquidity and Scenarios pages.
      </p>

      <ol className="slots" aria-label="Your four modules, in order">
        {draft.map((id, index) => (
          <li key={index} className="slot">
            <span className="slot-number" aria-hidden="true">{index + 1}</span>
            <div className="slot-pick">
              <Select
                label={`Slot ${index + 1}`}
                value={id}
                onChange={(event) => setDraft((d) => place(d, index, event.target.value as ModuleId))}
              >
                {MODULE_ORDER.map((m) => (
                  <option key={m} value={m} disabled={!available.has(m)}>
                    {MODULES[m].title}
                    {available.has(m) ? "" : " (arrives in phase 5)"}
                  </option>
                ))}
              </Select>
            </div>
            <div className="slot-moves">
              <Button
                variant="ghost" icon="chevronUp" aria-label={`Move ${MODULES[id].title} up`} disabled={index === 0}
                onClick={() => setDraft((d) => move(d, index, index - 1))}
              />
              <Button
                variant="ghost" icon="chevronDown" aria-label={`Move ${MODULES[id].title} down`} disabled={index === SLOTS - 1}
                onClick={() => setDraft((d) => move(d, index, index + 1))}
              />
            </div>
          </li>
        ))}
      </ol>

      <section aria-labelledby="layout-preview-title">
        <h3 id="layout-preview-title">Preview</h3>
        <ol className="layout-preview" aria-label="Layout preview">
          {draft.map((id, index) => (
            <li key={index}>
              <Icon name={MODULES[id].icon} size={16} />
              <span><span className="sr-only">Position {index + 1}: </span>{MODULES[id].title}</span>
            </li>
          ))}
        </ol>
        <p className="hint">Read left to right, then down. Your warnings stay above the modules whatever you choose.</p>
      </section>

      <section aria-labelledby="all-modules-title">
        <h3 id="all-modules-title">All modules</h3>
        <ul className="module-list">
          {MODULE_ORDER.map((id) => {
            const slot = draft.indexOf(id);
            return (
              <li key={id}>
                <div>
                  <strong>{MODULES[id].title}</strong>
                  <p className="muted">{MODULES[id].summary}</p>
                </div>
                {!available.has(id) ? <Badge>Arrives in phase 5</Badge> : slot >= 0 ? <Badge tone="info">{`On your dashboard: ${slot + 1}`}</Badge> : <Badge>{`On the ${MODULES[id].pageLabel} page`}</Badge>}
              </li>
            );
          })}
        </ul>
      </section>

      {failure && (
        <Banner tone="bad" title="Couldn't save." critical>
          {failure instanceof ApiError ? failure.message : "Something went wrong. Please try again."}
        </Banner>
      )}

      <div className="panel-actions">
        <Button
          variant="primary" disabled={!changed || busy}
          onClick={() => save.mutate(draft, { onSuccess: () => onDone("Your dashboard is saved.") })}
        >
          {save.isPending ? "Saving…" : "Save dashboard"}
        </Button>
        <Button variant="ghost" onClick={() => onDone("")} disabled={busy}>
          Cancel
        </Button>
        <Button
          variant="ghost" disabled={busy || (saved.is_default && !changed)}
          onClick={() => reset.mutate(undefined, { onSuccess: () => onDone("Your dashboard is back to the default four.") })}
        >
          Restore default
        </Button>
      </div>
    </div>
  );
}

/** The side panel where a person picks exactly four modules, orders them, and saves the choice to their account. */
export function CustomisePanel({
  open,
  onOpenChange,
  saved,
  onDone,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  saved: Dashboard;
  onDone: (message: string) => void;
}) {
  return (
    <SidePanel
      open={open}
      onOpenChange={onOpenChange}
      title="Customise your dashboard"
      description="Pick exactly four modules. Your choice is saved to your account."
    >
      <CustomiseForm saved={saved} onDone={onDone} />
    </SidePanel>
  );
}
