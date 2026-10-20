import { useId, useState } from "react";
import { api, ApiError } from "../api/client";
import type { AssetClass, HoldingsImport, HoldingsUnit, HoldingsPreview } from "../api/client";
import { useImportHoldings, usePreviewHoldings } from "../api/hooks";
import { cr } from "../format";
import { Button } from "../ui/Button";
import { Card } from "../ui/Card";
import { Select, TextField } from "../ui/Controls";
import { DataTable } from "../ui/DataTable";
import type { Column } from "../ui/DataTable";
import { StatTile } from "../ui/StatTile";
import { Badge, Banner } from "../ui/Status";
import { checkFile, className, download, HOLDING_CLASSES, toBase64, UNITS } from "./files";

type Picked = { name: string; base64: string };

const problemsOf = (error: unknown): string[] =>
  error instanceof ApiError ? (error.problems?.length ? error.problems : [error.message]) : error ? ["Something went wrong. Please try again."] : [];

/** Choose a file, see exactly what the server read from it, fix what blocks it, then confirm. Nothing is stored before the last click. */
export function ImportFlow({ profileId, onImported }: { profileId: number; onImported: (imported: HoldingsImport) => void }) {
  const fileId = useId();
  const preview = usePreviewHoldings(profileId);
  const importer = useImportHoldings(profileId);
  const [picked, setPicked] = useState<Picked | null>(null);
  const [unit, setUnit] = useState<HoldingsUnit>("cr");
  const [overrides, setOverrides] = useState<Record<string, AssetClass>>({});
  const [label, setLabel] = useState("");
  const [local, setLocal] = useState<string | null>(null);
  const [inputKey, setInputKey] = useState(0);

  // The mutation shows only its newest call, so a slow earlier preview can never overwrite a later one.
  const read = (file: Picked, nextUnit: HoldingsUnit, nextOverrides: Record<string, AssetClass>) =>
    preview.mutate({ filename: file.name, content_base64: file.base64, unit: nextUnit, class_overrides: nextOverrides });

  const onFile = async (file: File | undefined) => {
    setLocal(null);
    importer.reset();
    if (!file) return;
    const problem = checkFile(file);
    if (problem) {
      setLocal(problem);
      setPicked(null);
      preview.reset();
      return;
    }
    const next = { name: file.name, base64: await toBase64(file) };
    setPicked(next);
    setOverrides({});
    setLabel(file.name);
    read(next, unit, {});
  };

  const reset = () => {
    setPicked(null);
    setOverrides({});
    setLabel("");
    setLocal(null);
    preview.reset();
    importer.reset();
    setInputKey((k) => k + 1);
  };

  const confirm = () => {
    if (!picked) return;
    importer.mutate(
      { filename: picked.name, content_base64: picked.base64, unit, class_overrides: overrides, label: label.trim() || null },
      { onSuccess: (imported) => { reset(); onImported(imported); } },
    );
  };

  const data = preview.data;
  const refusal = preview.error ? problemsOf(preview.error) : [];

  return (
    <Card title="Import a statement" subtitle="A CSV or Excel (.xlsx) file, up to 150 KB and 1,000 rows. Use synthetic data only for now.">
      <div className="stack-lg">
        <div className="import-pick">
          <div className="field">
            <label htmlFor={fileId} className="field-label">Holdings file</label>
            <input key={inputKey} id={fileId} type="file" className="file-input" accept=".csv,.xlsx,.txt,.tsv" onChange={(e) => void onFile(e.target.files?.[0])} />
          </div>
          <Select
            label="Amounts are in" value={unit}
            onChange={(e) => { const next = e.target.value as HoldingsUnit; setUnit(next); if (picked) read(picked, next, overrides); }}
          >
            {UNITS.map((u) => <option key={u.value} value={u.value}>{u.label}</option>)}
          </Select>
          <Button
            icon="table"
            onClick={() => void api.holdingsTemplate().then((t) => download(t.filename, t.content)).catch(() => setLocal("The template could not be downloaded."))}
          >
            Download a template
          </Button>
        </div>
        <p className="hint">The unit applies unless the value column's heading names one, such as &ldquo;Value (Lakh)&rdquo;. The file is read on the server and never sent anywhere else.</p>

        {local && <Banner tone="bad" critical>{local}</Banner>}
        {refusal.length > 0 && (
          <Banner tone="bad" title="This file can't be used." critical>
            {refusal.join(" ")}
          </Banner>
        )}
        {data && picked && (
          <div className={preview.isPending ? "is-updating" : undefined}>
            <PreviewPanel data={data} overrides={overrides} onAssign={(labelText, cls) => {
              const next = { ...overrides, [labelText]: cls };
              setOverrides(next);
              read(picked, unit, next);
            }} />
            <div className="import-confirm">
              <TextField label="Name for this import" value={label} maxLength={60} onChange={(e) => setLabel(e.target.value)} />
              <div className="form-actions">
                <Button variant="primary" disabled={!data.ok || data.already_imported || importer.isPending || preview.isPending} onClick={confirm}>
                  {importer.isPending ? "Importing…" : data.line_count === 0 ? "Nothing to import yet" : `Import ${data.line_count} holdings (${cr(data.total_cr, 1)})`}
                </Button>
                <Button variant="ghost" onClick={reset} disabled={importer.isPending}>Choose another file</Button>
              </div>
              {data.already_imported && <Banner tone="info">This data is already imported for this profile.</Banner>}
              {importer.isError && (
                <Banner tone="bad" title="Couldn't import." critical>{problemsOf(importer.error).join(" ")}</Banner>
              )}
            </div>
          </div>
        )}
      </div>
    </Card>
  );
}

function PreviewPanel({ data, overrides, onAssign }: { data: HoldingsPreview; overrides: Record<string, AssetClass>; onAssign: (label: string, cls: AssetClass) => void }) {
  const errors = data.problems.filter((p) => p.severity === "error");
  const warnings = data.problems.filter((p) => p.severity === "warning");
  const lineCols: Column<HoldingsPreview["lines"][number]>[] = [
    { key: "r", header: "Row", align: "right", cell: (l) => String(l.row) },
    { key: "n", header: "Name", rowHeader: true, cell: (l) => l.name },
    { key: "c", header: "Asset class", cell: (l) => className(l.asset_class) },
    { key: "a", header: "Account", cell: (l) => l.account || "—" },
    { key: "v", header: "Value", align: "right", cell: (l) => cr(l.value_cr, 2) },
  ];
  const classCols: Column<HoldingsPreview["by_class"][number]>[] = [
    { key: "c", header: "Asset class", rowHeader: true, cell: (r) => className(r.asset_class) },
    { key: "t", header: "Total", align: "right", cell: (r) => cr(r.total_cr) },
    { key: "l", header: "Lines", align: "right", cell: (r) => String(r.lines) },
  ];
  return (
    <div className="stack-lg">
      <div className="grid-tiles tiles-3">
        <StatTile label="Rows read" value={String(data.rows_read)} sub={`${data.line_count} usable`} />
        <StatTile label="Total" value={cr(data.total_cr, 1)} sub={`Read as ${data.unit_label}`} />
        <StatTile
          label="Problems" value={String(errors.length)} tone={errors.length ? "bad" : "good"}
          sub={errors.length ? "Fix these before importing" : warnings.length ? `${warnings.length} to look at` : "None"}
        />
      </div>
      <p className="hint">
        Columns used: {Object.entries(data.columns).map(([role, header]) => `${role.replace("_", " ")} ← “${header}”`).join(", ")}.
      </p>

      {errors.length > 0 && (
        <Banner tone="bad" title={`${errors.length} problem${errors.length === 1 ? "" : "s"} to fix:`} live>
          <ul className="reasons">{errors.slice(0, 25).map((p, i) => <li key={`${p.message}-${i}`}>{p.message}</li>)}</ul>
          {errors.length > 25 && <p className="hint">&hellip;and {errors.length - 25} more. Fix the file and choose it again.</p>}
        </Banner>
      )}
      {warnings.length > 0 && (
        <Banner tone="warn" title="Worth a look (these don't block the import):">
          <ul className="reasons">{warnings.map((p, i) => <li key={`${p.message}-${i}`}>{p.message}</li>)}</ul>
        </Banner>
      )}

      {data.unrecognised.length > 0 && (
        <Card title="Assign an asset class" subtitle="The model has six classes. These labels aren't on its list, and nothing is guessed.">
          <ul className="row-list">
            {data.unrecognised.map((u) => (
              <li key={u.label} className="row-item">
                <span><strong>&ldquo;{u.label}&rdquo;</strong> <span className="muted">({u.rows} row{u.rows === 1 ? "" : "s"})</span></span>
                <Select
                  label={`Class for ${u.label}`} hideLabel value={overrides[u.label] ?? ""}
                  onChange={(e) => e.target.value && onAssign(u.label, e.target.value as AssetClass)}
                >
                  <option value="">Choose a class&hellip;</option>
                  {HOLDING_CLASSES.map((c) => <option key={c} value={c}>{className(c)}</option>)}
                </Select>
              </li>
            ))}
          </ul>
        </Card>
      )}

      {data.line_count > 0 && (
        <>
          <DataTable caption="Total by asset class in this file" columns={classCols} rows={data.by_class} rowKey={(r) => r.asset_class} />
          {data.mapped.length > 0 && (
            <details className="disclosure">
              <summary>How the asset classes in your file were read</summary>
              <ul className="reasons">
                {data.mapped.map((m) => (
                  <li key={m.label}>&ldquo;{m.label}&rdquo; &rarr; {className(m.asset_class)} <Badge>{`${m.rows} row${m.rows === 1 ? "" : "s"}`}</Badge></li>
                ))}
              </ul>
            </details>
          )}
          <details className="disclosure">
            <summary>Show the lines ({data.line_count})</summary>
            <DataTable caption="Lines read from the file" columns={lineCols} rows={data.lines} rowKey={(l) => String(l.row)} />
            {data.line_count > data.lines.length && <p className="hint">The first {data.lines.length} are shown.</p>}
          </details>
        </>
      )}
    </div>
  );
}
