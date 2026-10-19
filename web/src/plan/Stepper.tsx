import { Icon } from "../ui/Icon";

/**
 * Progress through the plan. A real ordered list: the current step is announced as "current step", finished steps show
 * a tick, and any step already reached can be revisited by clicking it.
 */
export function Stepper({
  steps,
  current,
  furthest,
  onSelect,
}: {
  steps: string[];
  current: number;
  furthest: number;
  onSelect: (step: number) => void;
}) {
  return (
    <nav aria-label="Plan progress">
      <ol className="stepper">
        {steps.map((label, index) => {
          const number = index + 1;
          const state = number < current ? "done" : number === current ? "current" : "todo";
          const reachable = number <= furthest;
          return (
            <li key={label} className={`step step-${state}`}>
              <button
                type="button"
                className="step-button"
                aria-label={`Step ${number} of ${steps.length}: ${label}${state === "done" ? " (done)" : ""}`}
                aria-current={number === current ? "step" : undefined}
                disabled={!reachable}
                onClick={() => onSelect(number)}
              >
                <span className="step-badge" aria-hidden="true">
                  {state === "done" ? <Icon name="success" size={16} /> : number}
                </span>
                <span className="step-label">{label}</span>
              </button>
            </li>
          );
        })}
      </ol>
    </nav>
  );
}
