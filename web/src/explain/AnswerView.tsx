import { useLocation } from "react-router-dom";
import type { ExplainAnswer, ExplainChip } from "../api/client";
import { ButtonLink } from "../ui/Button";
import { DataTable } from "../ui/DataTable";
import type { Column } from "../ui/DataTable";
import { ChipList } from "./ChipList";

type Row = { id: number; cells: string[] };
type Figure = ExplainAnswer["figures"][number];

function AnswerTable({ table }: { table: ExplainAnswer["tables"][number] }) {
  const columns: Column<Row>[] = table.columns.map((header, i) => ({
    key: String(i), header, rowHeader: i === 0, align: i === 0 ? undefined : "right", cell: (row: Row) => row.cells[i] ?? "",
  }));
  const rows: Row[] = table.rows.map((cells, id) => ({ id, cells }));
  return <DataTable caption={table.caption} columns={columns} rows={rows} rowKey={(r) => String(r.id)} />;
}

const evidenceColumns: Column<Figure>[] = [
  { key: "label", header: "Figure", rowHeader: true, cell: (f) => f.label },
  { key: "shown", header: "Shown as", align: "right", cell: (f) => f.shown },
  { key: "page", header: "Also on", cell: (f) => f.page },
  { key: "field", header: "Where it comes from", cell: (f) => <>{f.derived ? "Worked out from " : ""}<code>{f.field}</code></> },
];

/** One answer: the result in a sentence, then the reasons, the comparison, the limits, the evidence and where to go next. */
export function AnswerView({
  answer, onAsk, title = true, busy = false,
}: {
  answer: ExplainAnswer;
  onAsk: (chip: ExplainChip) => void;
  title?: boolean;
  busy?: boolean;
}) {
  const { search } = useLocation();
  return (
    <article className="answer" aria-label={answer.title}>
      {title && <h2 className="answer-title">{answer.title}</h2>}
      <p className="answer-lead">{answer.lead}</p>
      {answer.notes.map((note) => <p key={note} className="hint">{note}</p>)}

      {answer.tables.map((t) => <AnswerTable key={t.caption} table={t} />)}

      {answer.sections.map((s) => (
        <section key={s.heading} className="answer-section">
          <h3>{s.heading}</h3>
          {s.from_engine && <p className="hint">In the model&rsquo;s own words, unchanged.</p>}
          <ul>{s.lines.map((line) => <li key={line}>{line}</li>)}</ul>
        </section>
      ))}

      <section className="answer-section">
        <h3>Keep in mind</h3>
        <ul>{answer.caveats.map((c) => <li key={c}>{c}</li>)}</ul>
      </section>

      {answer.figures.length > 0 && (
        <details className="disclosure">
          <summary>Show the evidence ({answer.figures.length} figure{answer.figures.length === 1 ? "" : "s"})</summary>
          <p className="hint">Every number above came from the model&rsquo;s own results. This is where each one comes from.</p>
          <DataTable caption="Figures used in this answer and where each comes from" columns={evidenceColumns} rows={answer.figures} rowKey={(f) => f.key} />
        </details>
      )}

      {answer.links.length > 0 && (
        <div className="answer-links">
          {answer.links.map((l) => <ButtonLink key={l.to} to={{ pathname: l.to, search }} variant="ghost">See it on {l.label}</ButtonLink>)}
        </div>
      )}
      {answer.follow_ups.length > 0 && <ChipList label="Ask next" chips={answer.follow_ups} onPick={onAsk} disabled={busy} />}
    </article>
  );
}
