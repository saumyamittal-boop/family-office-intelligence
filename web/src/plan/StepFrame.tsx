import { useEffect, useRef } from "react";
import type { ReactNode } from "react";
import { Button } from "../ui/Button";
import { Card } from "../ui/Card";

/**
 * One question page. When the step changes, keyboard focus moves to its heading (and is announced), so a keyboard or
 * screen-reader user lands at the top of the new step instead of being left on a button that has disappeared.
 */
export function StepFrame({
  step,
  title,
  intro,
  children,
  canContinue,
  nextLabel = "Continue",
  focusOnMount,
  onBack,
  onNext,
}: {
  step: number;
  title: string;
  intro?: string;
  children: ReactNode;
  canContinue: boolean;
  nextLabel?: string;
  /** True once the person has moved between steps: the heading takes focus. False when the page first opens. */
  focusOnMount: boolean;
  onBack?: () => void;
  onNext: () => void;
}) {
  const heading = useRef<HTMLHeadingElement>(null);
  // Each step is mounted fresh (keyed by its number), so the decision comes from the caller rather than from "first render".
  useEffect(() => {
    if (focusOnMount) heading.current?.focus();
  }, [step, focusOnMount]);

  return (
    <div className="step-frame">
      <Card>
        <h2 ref={heading} tabIndex={-1} className="step-title">
          {title}
        </h2>
        {intro && <p className="muted step-intro">{intro}</p>}
        <div className="stack-lg">{children}</div>
        <div className="step-actions">
          {onBack ? (
            <Button icon="chevronLeft" onClick={onBack}>
              Back
            </Button>
          ) : (
            <span />
          )}
          <Button variant="primary" disabled={!canContinue} onClick={onNext}>
            {nextLabel}
          </Button>
        </div>
      </Card>
    </div>
  );
}
