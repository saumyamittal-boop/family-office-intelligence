import { useState } from "react";
import type { PlanAnswers, PlanConfig, RiskKey } from "../api/client";
import { Card } from "../ui/Card";
import { SegmentedControl } from "../ui/Controls";
import { NumberField } from "../ui/NumberField";

/**
 * Change an answer and watch the strategies follow. Switching comfort is instant (the three strategies do not depend on
 * it); changing spending or the safety net recalculates, and the previous result stays on screen, marked "Updating".
 */
export function WhatIf({
  answers,
  update,
  config,
  updating,
}: {
  answers: PlanAnswers;
  update: (patch: Partial<PlanAnswers>) => void;
  config: PlanConfig;
  updating: boolean;
}) {
  const [spendingOk, setSpendingOk] = useState(true);
  return (
    <Card
      title="Try a change"
      subtitle="The strategies above follow whatever you change here"
      actions={
        <span className="preview-status" role="status">
          {updating ? "Updating the strategies…" : "Up to date"}
        </span>
      }
    >
      <div className="whatif-grid">
        <div className="field">
          <span className="field-label" id="whatif-comfort">Comfort with a bad year</span>
          <SegmentedControl<RiskKey>
            label="Comfort with a bad year"
            value={answers.risk}
            onChange={(risk) => update({ risk })}
            options={config.comfort.map((c) => ({ value: c.key, label: `${c.letter} · ${c.key}` }))}
          />
        </div>
        <div className="field">
          <label htmlFor="whatif-months" className="field-label">
            Safety net: <b>{answers.months} months</b>
          </label>
          <input
            id="whatif-months"
            type="range"
            className="range"
            min={config.months.min}
            max={config.months.max}
            value={answers.months}
            aria-valuetext={`${answers.months} months`}
            onChange={(e) => update({ months: Number(e.target.value) })}
          />
        </div>
        <NumberField
          label="Yearly spending"
          unit={"₹ Cr"}
          min={config.spending.min}
          max={config.spending.max}
          value={answers.spending}
          onChange={(v) => {
            setSpendingOk(v !== null && v >= config.spending.min && v <= config.spending.max);
            if (v !== null && v >= config.spending.min && v <= config.spending.max) update({ spending: v });
          }}
          error={spendingOk ? null : undefined}
        />
      </div>
    </Card>
  );
}
