import type { ApplyResult, AssetClass, Consolidation, HoldingsImport, HoldingsPreview } from "../api/client";
import { analysis } from "./fixtures";
import { appRoutes } from "./phase4Fixtures";
import { json, jsonBy } from "./render";
import type { Route } from "./render";

const CLASSES: AssetClass[] = ["Large-cap equity", "Mid-cap equity", "Debt", "Gold", "Cash & liquid", "Illiquid"];
const TOTALS: Record<AssetClass, [number, number]> = {
  "Large-cap equity": [40, 1], "Mid-cap equity": [10, 1], Debt: [30, 1], Gold: [5, 1], "Cash & liquid": [5, 1], Illiquid: [10, 1],
};

const byClass = (): HoldingsPreview["by_class"] => CLASSES.map((c) => ({ asset_class: c, total_cr: TOTALS[c][0], share: TOTALS[c][0] / 100, lines: TOTALS[c][1] }));
const line = (row: number, name: string, asset_class: AssetClass, account: string, value_cr: number) => ({ row, name, asset_class, account, value_cr });

export const CSV_TEXT = "Name,Asset class,Account,Value (Cr)\nFund A,Large-cap equity,Demat 1,40\n";

export function previewOk(overrides: Partial<HoldingsPreview> = {}): HoldingsPreview {
  return {
    ok: true, filename: "statement.csv", file_kind: "csv", unit: "cr", unit_label: "rupees crore",
    columns: { name: "Name", asset_class: "Asset class", account: "Account", value: "Value (Cr)" }, ignored_columns: [], rows_read: 6, line_count: 6, total_cr: 100,
    lines: [
      line(2, "Fund A", "Large-cap equity", "Demat 1", 40), line(3, "Fund B", "Mid-cap equity", "Demat 1", 10), line(4, "Bonds C", "Debt", "Bank 2", 30),
      line(5, "Gold ETF", "Gold", "Demat 1", 5), line(6, "Savings", "Cash & liquid", "Bank 2", 5), line(7, "Office", "Illiquid", "", 10),
    ],
    by_class: byClass(), mapped: [{ label: "Real estate", asset_class: "Illiquid", rows: 1 }], unrecognised: [], problems: [], already_imported: false, ...overrides,
  };
}

export function previewWithProblems(): HoldingsPreview {
  return previewOk({
    ok: false, line_count: 4, rows_read: 6, total_cr: 85,
    unrecognised: [{ label: "Equity", rows: 2 }],
    problems: [
      { severity: "error", message: "“Equity” (2 rows, first at row 5) is not an asset class the model knows. Assign one below.", row: 5, field: "asset_class" },
      { severity: "error", message: "Row 6: the value must be above zero.", row: 6, field: "value" },
      { severity: "warning", message: "Row 4 repeats row 3 (same name, class, account and value). Both are counted.", row: 4, field: null },
    ],
  });
}

export const IMPORTED: HoldingsImport = {
  id: 7, label: "statement.csv", filename: "statement.csv", file_kind: "csv", unit: "cr", row_count: 6, total_cr: 100, created: "2026-10-20T09:00:00+00:00",
};

export function consolidation(overrides: Partial<Consolidation> = {}): Consolidation {
  return {
    profile_id: 1, imports: 1, lines: 6, total_cr: 100, by_class: byClass(),
    by_account: [
      { account: "Demat 1", total_cr: 55, share: 0.55, lines: 3 }, { account: "Bank 2", total_cr: 35, share: 0.35, lines: 2 }, { account: "", total_cr: 10, share: 0.1, lines: 1 },
    ],
    top_positions: [
      { name: "Fund A", asset_class: "Large-cap equity", accounts: 2, value_cr: 40, share: 0.4 }, { name: "Bonds C", asset_class: "Debt", accounts: 1, value_cr: 30, share: 0.3 },
    ],
    profile_corpus_cr: 1000, difference_cr: -900,
    compare: CLASSES.map((c) => ({ asset_class: c, imported_share: TOTALS[c][0] / 100, profile_share: c === "Large-cap equity" ? 0.55 : c === "Cash & liquid" ? 0.05 : c === "Illiquid" ? 0.4 : 0, difference: 0 })),
    ...overrides,
  };
}

export function emptyConsolidation(): Consolidation {
  return consolidation({
    imports: 0, lines: 0, total_cr: 0, difference_cr: 0, by_account: [], top_positions: [], compare: [],
    by_class: CLASSES.map((c) => ({ asset_class: c, total_cr: 0, share: 0, lines: 0 })),
  });
}

export function applyResult(overrides: Partial<ApplyResult> = {}): ApplyResult {
  const shares = (m: Record<string, number>) => Object.fromEntries(CLASSES.map((c) => [c, m[c] ?? 0]));
  return {
    before: { corpus_cr: 1000, shares: shares({ "Large-cap equity": 0.55, "Cash & liquid": 0.05, Illiquid: 0.4 }) },
    after: { corpus_cr: 1000, shares: shares({ "Large-cap equity": 0.4, "Mid-cap equity": 0.1, Debt: 0.3, Gold: 0.05, "Cash & liquid": 0.05, Illiquid: 0.1 }) },
    changed: true, saved: false,
    notes: ["The imported total (₹100.0 Cr) differs from the profile's corpus (₹1,000.0 Cr). The imported shares are applied to the profile's corpus. Tick the box to set the corpus to the imported total as well."],
    ...overrides,
  };
}

/** The canned server with the holdings endpoints added. Pass routes to replace any of them. */
export function holdingsApp(extra: Record<string, Route> = {}): Record<string, Route> {
  return appRoutes(analysis(), {
    "GET /api/holdings/template": json({ filename: "holdings-template.csv", content: CSV_TEXT }),
    "GET /api/profiles/1/holdings/imports": json([]),
    "GET /api/profiles/1/holdings/consolidation": json(emptyConsolidation()),
    "POST /api/profiles/1/holdings/preview": json(previewOk()),
    "POST /api/profiles/1/holdings/imports": json(IMPORTED, 201),
    "POST /api/profiles/1/holdings/apply/preview": jsonBy<{ set_corpus: boolean }>((b) => applyResult({ after: { ...applyResult().after, corpus_cr: b.set_corpus ? 100 : 1000 } })),
    "POST /api/profiles/1/holdings/apply": json(applyResult({ saved: true })),
    "DELETE /api/profiles/1/holdings/imports/7": () => new Response(null, { status: 204 }),
    ...extra,
  });
}

export const withImports = (extra: Record<string, Route> = {}) =>
  holdingsApp({
    "GET /api/profiles/1/holdings/imports": json([IMPORTED]),
    "GET /api/profiles/1/holdings/consolidation": json(consolidation()),
    ...extra,
  });
