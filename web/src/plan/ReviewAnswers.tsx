import type { PlanAnswers, PlanConfig } from "../api/client";
import { cr } from "../format";
import { Button } from "../ui/Button";
import { Card } from "../ui/Card";
import { commitmentPhrase } from "./names";

/** Every answer in one place, each with an Edit button that jumps to its step and comes straight back to the strategies. */
export function ReviewAnswers({ answers, config, onEdit }: { answers: PlanAnswers; config: PlanConfig; onEdit: (step: number) => void }) {
  const comfort = config.comfort.find((c) => c.key === answers.risk);
  const owned = answers.amounts ? cr(Object.values(answers.amounts).reduce((a, b) => a + b, 0), 0) : `a typical split of ${cr(answers.wealth, 0)}`;
  const commitments = answers.commitments.length
    ? answers.commitments.map(commitmentPhrase).join(", ")
    : "Nothing planned";

  const rows: { label: string; value: string; step: number }[] = [
    { label: "Plan name", value: answers.name, step: 1 },
    { label: "Total wealth", value: cr(answers.wealth, 0), step: 1 },
    { label: "Yearly spending", value: cr(answers.spending), step: 1 },
    { label: "Upcoming commitments", value: commitments, step: 2 },
    { label: "Comfort with a bad year", value: comfort?.headline ?? answers.risk, step: 3 },
    { label: "Safety net", value: `${answers.months} months`, step: 4 },
    { label: "What the family owns", value: owned, step: 5 },
  ];

  return (
    <Card title="Your answers" subtitle="Change any of them and the strategies update">
      <ul className="review-list">
        {rows.map((row) => (
          <li key={row.label} className="review-row">
            <span className="review-label">{row.label}</span>
            <span className="review-value">{row.value}</span>
            <Button variant="ghost" onClick={() => onEdit(row.step)} aria-label={`Edit ${row.label.toLowerCase()}`}>
              Edit
            </Button>
          </li>
        ))}
      </ul>
    </Card>
  );
}
