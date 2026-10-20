import { screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";
import App from "../App";
import type { HoldingsFile } from "../api/client";
import { checkFile, MAX_FILE_BYTES, toBase64 } from "../holdings/files";
import { applyResult, consolidation, CSV_TEXT, emptyConsolidation, holdingsApp, IMPORTED, previewOk, previewWithProblems, withImports } from "../test/holdingsFixtures";
import { dashboard } from "../test/phase4Fixtures";
import { json, renderWithProviders, serve } from "../test/render";
import { analysis } from "../test/fixtures";
import { appRoutes } from "../test/phase4Fixtures";

afterEach(() => vi.unstubAllGlobals());

async function openHoldings(routes = holdingsApp()) {
  const calls = serve(routes);
  renderWithProviders(<App />, "/holdings");
  await screen.findByRole("heading", { level: 1, name: "Holdings" });
  await screen.findByRole("button", { name: "Download a template" });
  return calls;
}

const csvFile = (text = CSV_TEXT, name = "statement.csv") => new File([text], name, { type: "text/csv" });
const previews = (calls: ReturnType<typeof serve>) =>
  calls.filter((c) => c.method === "POST" && c.path === "/api/profiles/1/holdings/preview").map((c) => JSON.parse(c.body!) as HoldingsFile);
const choose = async (user: ReturnType<typeof userEvent.setup>, file = csvFile()) => user.upload(screen.getByLabelText("Holdings file"), file);
const section = async (title: string | RegExp) => within((await screen.findByRole("heading", { name: title })).closest("section") as HTMLElement);

describe("the Holdings page", () => {
  it("opens with the import card, an honest synthetic-data note and nothing imported", async () => {
    await openHoldings();
    expect(screen.getByText(/Synthetic data only for now/)).toBeInTheDocument();
    expect(screen.getByLabelText("Holdings file")).toBeInTheDocument();
    expect(screen.getByRole("combobox", { name: "Amounts are in" })).toHaveValue("cr");
    expect(await screen.findByText("Nothing imported for this family yet.")).toBeInTheDocument();
    expect(await screen.findByText("No holdings imported yet")).toBeInTheDocument();
    expect(screen.queryByText("Use these holdings in your profile")).not.toBeInTheDocument(); // nothing to apply yet
  });

  it("is a normal page in the menu now, not a placeholder", async () => {
    await openHoldings();
    const nav = screen.getByRole("navigation", { name: "Main" });
    expect(within(nav).getByRole("link", { name: "Holdings" })).toHaveAttribute("aria-current", "page");
    expect(screen.queryByText("Not built yet")).not.toBeInTheDocument();
  });

  it("downloads the template the server provides", async () => {
    const user = userEvent.setup();
    const created = vi.fn(() => "blob:template");
    vi.stubGlobal("URL", Object.assign(URL, { createObjectURL: created, revokeObjectURL: vi.fn() }));
    await openHoldings();
    await user.click(screen.getByRole("button", { name: "Download a template" }));
    await waitFor(() => expect(created).toHaveBeenCalledTimes(1));
    const blob = (created.mock.calls[0] as unknown as [Blob])[0];
    expect(blob.type).toContain("text/csv");
    expect(await blob.text()).toContain("Name,Asset class,Account,Value (Cr)");
  });
});

describe("choosing a file", () => {
  it("sends it to the server as JSON and shows exactly what was read", async () => {
    const user = userEvent.setup();
    const calls = await openHoldings();
    await choose(user);
    expect(await screen.findByText("Rows read")).toBeInTheDocument();
    const sent = previews(calls)[0]!;
    expect(sent).toMatchObject({ filename: "statement.csv", unit: "cr", class_overrides: {} });
    expect(atob(sent.content_base64)).toBe(CSV_TEXT);
    expect(screen.getByText(/Columns used: name ← “Name”, asset class ← “Asset class”, account ← “Account”, value ← “Value \(Cr\)”/)).toBeInTheDocument();
    expect(screen.getByText("Read as rupees crore")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Import 6 holdings \(₹100\.0 Cr\)/ })).toBeEnabled();
    expect(screen.getByLabelText("Name for this import")).toHaveValue("statement.csv");
  });

  it("shows how labels were read and the lines, on request", async () => {
    const user = userEvent.setup();
    await openHoldings();
    await choose(user);
    await user.click(await screen.findByText("How the asset classes in your file were read"));
    expect(screen.getByText(/“Real estate” → Illiquid \(held fixed\)/)).toBeInTheDocument();
    await user.click(screen.getByText(/Show the lines \(6\)/));
    const table = within(screen.getByRole("table", { name: "Lines read from the file" }));
    expect(table.getByRole("row", { name: /Fund A.*Large-cap equity.*Demat 1.*₹40\.00 Cr/ })).toBeInTheDocument();
    expect(table.getByRole("row", { name: /Office.*Illiquid \(held fixed\).*—/ })).toBeInTheDocument();
  });

  it("reads the file again when the unit changes", async () => {
    const user = userEvent.setup();
    const calls = await openHoldings();
    await choose(user);
    await screen.findByText("Rows read");
    await user.selectOptions(screen.getByRole("combobox", { name: "Amounts are in" }), "lakh");
    await waitFor(() => expect(previews(calls)).toHaveLength(2));
    expect(previews(calls)[1]).toMatchObject({ unit: "lakh" });
  });

  it("refuses an obviously wrong file before sending anything", async () => {
    const user = userEvent.setup({ applyAccept: false });
    const calls = await openHoldings();
    await user.upload(screen.getByLabelText("Holdings file"), new File(["x"], "report.pdf"));
    expect(await screen.findByText("Choose a .csv or .xlsx file.")).toBeInTheDocument();
    await user.upload(screen.getByLabelText("Holdings file"), new File(["x".repeat(MAX_FILE_BYTES + 1)], "huge.csv"));
    expect(await screen.findByText(/larger than 150 KB/)).toBeInTheDocument();
    expect(previews(calls)).toHaveLength(0);
  });

  it("explains a file the server refuses, in the server's own words", async () => {
    const user = userEvent.setup();
    await openHoldings(holdingsApp({ "POST /api/profiles/1/holdings/preview": json({ detail: "Excel files with macros are not accepted. Save a copy without macros (.xlsx) and upload that.", problems: null }, 422) }));
    await choose(user, new File(["x"], "macro.csv"));
    const alert = await screen.findByText("This file can't be used.");
    expect(alert.closest(".banner")).toHaveTextContent("Excel files with macros are not accepted");
    expect(screen.queryByRole("button", { name: /^Import/ })).not.toBeInTheDocument();
  });

  it("lists every problem, blocks the import, and lets the person assign a class to an unknown label", async () => {
    const user = userEvent.setup();
    let fixed = false;
    const calls = await openHoldings(
      holdingsApp({ "POST /api/profiles/1/holdings/preview": (init) => { fixed = JSON.parse(String(init?.body)).class_overrides?.Equity === "Large-cap equity"; return new Response(JSON.stringify(fixed ? previewOk() : previewWithProblems())); } }),
    );
    await choose(user);
    expect(await screen.findByText("2 problems to fix:")).toBeInTheDocument();
    expect(screen.getByText("Row 6: the value must be above zero.")).toBeInTheDocument();
    expect(screen.getByText(/Row 4 repeats row 3/)).toBeInTheDocument(); // a warning, shown but not blocking
    expect(screen.getByRole("button", { name: /^Import 4 holdings/ })).toBeDisabled();

    await user.selectOptions(screen.getByRole("combobox", { name: "Class for Equity" }), "Large-cap equity");
    await waitFor(() => expect(previews(calls)).toHaveLength(2));
    expect(previews(calls)[1]!.class_overrides).toEqual({ Equity: "Large-cap equity" });
    await waitFor(() => expect(screen.getByRole("button", { name: /^Import 6 holdings/ })).toBeEnabled());
    expect(screen.queryByText("Assign an asset class")).not.toBeInTheDocument();
  });

  it("does not offer to import a file with nothing usable in it", async () => {
    const user = userEvent.setup();
    await openHoldings(holdingsApp({ "POST /api/profiles/1/holdings/preview": json(previewOk({ ok: false, line_count: 0, total_cr: 0, lines: [], problems: [{ severity: "error", message: "Row 2: the value must be above zero.", row: 2, field: "value" }] })) }));
    await choose(user);
    expect(await screen.findByRole("button", { name: "Nothing to import yet" })).toBeDisabled();
    expect(screen.queryByText(/Show the lines/)).not.toBeInTheDocument();
  });

  it("says when the same data is already imported and will not import it twice", async () => {
    const user = userEvent.setup();
    await openHoldings(holdingsApp({ "POST /api/profiles/1/holdings/preview": json(previewOk({ already_imported: true })) }));
    await choose(user);
    expect(await screen.findByText("This data is already imported for this profile.")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /^Import 6 holdings/ })).toBeDisabled();
  });
});

describe("confirming an import", () => {
  it("stores it with the chosen name and CSRF token, tells the person, and clears the form", async () => {
    const user = userEvent.setup();
    let stored = false;
    const calls = await openHoldings(
      holdingsApp({
        "POST /api/profiles/1/holdings/imports": () => { stored = true; return new Response(JSON.stringify(IMPORTED), { status: 201 }); },
        "GET /api/profiles/1/holdings/imports": () => new Response(JSON.stringify(stored ? [IMPORTED] : [])),
        "GET /api/profiles/1/holdings/consolidation": () => new Response(JSON.stringify(stored ? consolidation() : emptyConsolidation())),
      }),
    );
    await choose(user);
    await screen.findByText("Rows read");
    const name = screen.getByLabelText("Name for this import");
    await user.clear(name);
    await user.type(name, "March statement");
    await user.click(screen.getByRole("button", { name: /^Import 6 holdings/ }));

    const post = calls.find((c) => c.method === "POST" && c.path === "/api/profiles/1/holdings/imports")!;
    expect(JSON.parse(post.body!)).toMatchObject({ filename: "statement.csv", label: "March statement", unit: "cr", class_overrides: {} });
    expect(post.headers["X-CSRF-Token"]).toBe("csrf-abc");
    expect(await screen.findByText("Imported.")).toBeInTheDocument();
    expect(screen.queryByText("Rows read")).not.toBeInTheDocument(); // the preview is gone
    expect((screen.getByLabelText("Holdings file") as HTMLInputElement).value).toBe("");
    expect(await within(screen.getByRole("table", { name: "Imports for this profile" })).findByText("statement.csv (CSV)")).toBeInTheDocument();
    expect(await screen.findByText("Consolidated holdings")).toBeInTheDocument();
  });

  it("shows why the server declined at the last step", async () => {
    const user = userEvent.setup();
    await openHoldings(holdingsApp({ "POST /api/profiles/1/holdings/imports": json({ detail: "A profile can hold at most 20 imports. Delete one first.", problems: null }, 409) }));
    await choose(user);
    await user.click(await screen.findByRole("button", { name: /^Import 6 holdings/ }));
    expect(await screen.findByText("Couldn't import.")).toBeInTheDocument();
    expect(screen.getByText(/at most 20 imports/)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /^Import 6 holdings/ })).toBeEnabled(); // the file is still there to try again
  });

  it("lets the person drop the file and start over", async () => {
    const user = userEvent.setup();
    await openHoldings();
    await choose(user);
    await screen.findByText("Rows read");
    await user.click(screen.getByRole("button", { name: "Choose another file" }));
    expect(screen.queryByText("Rows read")).not.toBeInTheDocument();
  });
});

describe("imports and the consolidated view", () => {
  it("lists imports and deletes one only after a second click", async () => {
    const user = userEvent.setup();
    let removed = false;
    const calls = await openHoldings(
      withImports({
        "DELETE /api/profiles/1/holdings/imports/7": () => { removed = true; return new Response(null, { status: 204 }); },
        "GET /api/profiles/1/holdings/imports": () => new Response(JSON.stringify(removed ? [] : [IMPORTED])),
      }),
    );
    const list = await section("Your imports");
    expect(await list.findByRole("row", { name: /statement\.csv \(CSV\).*6.*₹100\.0 Cr.*2026-10-20/ })).toBeInTheDocument();
    await user.click(list.getByRole("button", { name: "Delete statement.csv" }));
    expect(calls.some((c) => c.method === "DELETE")).toBe(false); // asked first
    await user.click(list.getByRole("button", { name: "Keep" }));
    await user.click(list.getByRole("button", { name: "Delete statement.csv" }));
    await user.click(list.getByRole("button", { name: "Yes, delete statement.csv" }));
    const del = calls.find((c) => c.method === "DELETE")!;
    expect(del.path).toBe("/api/profiles/1/holdings/imports/7");
    expect(del.headers["X-CSRF-Token"]).toBe("csrf-abc");
    expect(await list.findByText("Nothing imported for this family yet.")).toBeInTheDocument();
  });

  it("adds everything up by class, account and name, and compares it with the profile", async () => {
    await openHoldings(withImports());
    expect(await screen.findByText("Total imported")).toBeInTheDocument();
    expect(screen.getByText("1 import")).toBeInTheDocument();
    expect(screen.getByRole("img", { name: /Consolidated holdings: Large-cap equity 40\.0%.*Illiquid \(fixed\) 10\.0%, of ₹100 Cr\./ })).toBeInTheDocument();
    const accounts = within(screen.getByRole("table", { name: "Imported holdings by account" }));
    expect(accounts.getByRole("row", { name: /Demat 1.*₹55\.0 Cr.*55\.0%.*3/ })).toBeInTheDocument();
    expect(accounts.getByRole("row", { name: /No account named.*₹10\.0 Cr/ })).toBeInTheDocument();
    const top = within(screen.getByRole("table", { name: "The five largest holdings across all accounts" }));
    expect(top.getByRole("row", { name: /Fund A.*Large-cap equity.*2.*₹40\.0 Cr.*40\.0%/ })).toBeInTheDocument();
    const compare = within(screen.getByRole("table", { name: /imported against the profile/ }));
    expect(compare.getByRole("row", { name: /Large-cap equity.*40\.0%.*55\.0%/ })).toBeInTheDocument();
    expect(screen.getByText(/Imported total ₹100\.0 Cr against a profile corpus of ₹1,000\.0 Cr \(−₹900\.0 Cr\)/)).toBeInTheDocument();
  });
});

describe("using the holdings in the profile", () => {
  it("shows the change first, then makes it only when asked, and recalculates", async () => {
    const user = userEvent.setup();
    const calls = await openHoldings(withImports());
    const card = await section("Use these holdings in your profile");
    const table = within(await screen.findByRole("table", { name: "Profile holdings now and after using the imported holdings" }));
    expect(table.getByRole("row", { name: /Large-cap equity.*55\.0%.*40\.0%.*−15\.0%/ })).toBeInTheDocument();
    expect(table.getByRole("row", { name: /Debt.*0\.0%.*30\.0%.*\+30\.0%/ })).toBeInTheDocument();
    expect(card.getByText(/differs from the profile's corpus/)).toBeInTheDocument();
    expect(calls.some((c) => c.path === "/api/profiles/1/holdings/apply" && c.method === "POST")).toBe(false); // looking changes nothing

    await user.click(card.getByRole("button", { name: "Use these holdings in my profile" }));
    const post = calls.find((c) => c.method === "POST" && c.path === "/api/profiles/1/holdings/apply")!;
    expect(JSON.parse(post.body!)).toEqual({ set_corpus: false });
    expect(post.headers["X-CSRF-Token"]).toBe("csrf-abc");
    expect(await card.findByText("Your profile now uses these holdings.")).toBeInTheDocument();
    expect(card.getByRole("link", { name: "Open the dashboard" })).toHaveAttribute("href", expect.stringMatching(/^\/(\?|$)/));
    await waitFor(() => expect(calls.filter((c) => c.path.startsWith("/api/profiles/1/analysis")).length).toBeGreaterThan(1)); // old results dropped, recomputed
  });

  it("can also set the corpus, when the box is ticked", async () => {
    const user = userEvent.setup();
    const calls = await openHoldings(withImports());
    const card = await section("Use these holdings in your profile");
    await user.click(await card.findByRole("checkbox", { name: /set the profile's corpus to the imported total \(₹100\.0 Cr\)/ }));
    await waitFor(() => expect(calls.some((c) => c.path === "/api/profiles/1/holdings/apply/preview" && c.body === JSON.stringify({ set_corpus: true }))).toBe(true));
    expect(await card.findByText(/Corpus: ₹1,000\.0 Cr now, ₹100\.0 Cr after/)).toBeInTheDocument();
    await user.click(card.getByRole("button", { name: "Use these holdings in my profile" }));
    await waitFor(() => expect(JSON.parse(calls.filter((c) => c.path === "/api/profiles/1/holdings/apply").at(-1)!.body!)).toEqual({ set_corpus: true }));
  });

  it("explains a refusal and keeps the button off", async () => {
    await openHoldings(withImports({ "POST /api/profiles/1/holdings/apply/preview": json({ detail: "These holdings can't be applied to the profile.", problems: ["Illiquid holdings can be at most 95% of the corpus; the model needs a liquid part to allocate."] }, 422) }));
    const card = await section("Use these holdings in your profile");
    expect(await card.findByText("These holdings can't be used in the profile:")).toBeInTheDocument();
    expect(card.getByText(/at most 95%/)).toBeInTheDocument();
    expect(card.getByRole("button", { name: "Use these holdings in my profile" })).toBeDisabled();
  });

  it("says so when the profile already matches", async () => {
    await openHoldings(withImports({ "POST /api/profiles/1/holdings/apply/preview": json(applyResult({ changed: false, notes: [] })) }));
    const card = await section("Use these holdings in your profile");
    expect(await card.findByText("Your profile already matches these holdings.")).toBeInTheDocument();
    expect(card.getByRole("button", { name: "Use these holdings in my profile" })).toBeDisabled();
  });
});

describe("the dashboard module", () => {
  const withModule = (extra = {}) =>
    appRoutes(analysis(), {
      ...holdingsApp(),
      "GET /api/dashboard": json(dashboard(["holdings_consolidation", "allocation_actions", "risk_exposure", "stress_scenarios"], false)),
      ...extra,
    });

  it("shows the consolidated holdings in brief, linking to the Holdings page", async () => {
    serve(withModule({ "GET /api/profiles/1/holdings/consolidation": json(consolidation()) }));
    renderWithProviders(<App />);
    const card = within((await screen.findByRole("heading", { level: 2, name: "Holdings consolidation" })).closest("section") as HTMLElement);
    expect(await card.findByText("Total imported")).toBeInTheDocument();
    expect(card.getByRole("img", { name: /Consolidated holdings/ })).toBeInTheDocument();
    expect(card.queryByText("By account")).not.toBeInTheDocument(); // the detail lives on the Holdings page
    expect(card.getByRole("link", { name: /Holdings consolidation: open the full Holdings page/ })).toHaveAttribute("href", expect.stringMatching(/^\/holdings/));
  });

  it("invites the person to import when there is nothing yet", async () => {
    serve(withModule());
    renderWithProviders(<App />);
    const card = within((await screen.findByRole("heading", { level: 2, name: "Holdings consolidation" })).closest("section") as HTMLElement);
    expect(await card.findByText("No holdings imported yet")).toBeInTheDocument();
    expect(card.getByRole("link", { name: "Import holdings" })).toHaveAttribute("href", expect.stringMatching(/^\/holdings/));
  });

  it("fails on its own: the rest of the dashboard still draws", async () => {
    serve(withModule({ "GET /api/profiles/1/holdings/consolidation": json({ detail: "Down.", problems: null }, 500) }));
    renderWithProviders(<App />);
    const card = within((await screen.findByRole("heading", { level: 2, name: "Holdings consolidation" })).closest("section") as HTMLElement);
    expect(await card.findByText("Your holdings could not be loaded")).toBeInTheDocument();
    expect(await screen.findByRole("heading", { name: "Allocation and actions" })).toBeInTheDocument();
  });
});

describe("file helpers", () => {
  it("checkFile accepts the right types and sizes only", () => {
    expect(checkFile({ name: "a.CSV", size: 10 })).toBeNull();
    expect(checkFile({ name: "a.xlsx", size: 10 })).toBeNull();
    expect(checkFile({ name: "a.xls", size: 10 })).toMatch(/\.csv or \.xlsx/);
    expect(checkFile({ name: "a.csv", size: 0 })).toMatch(/empty/);
    expect(checkFile({ name: "a.csv", size: MAX_FILE_BYTES + 1 })).toMatch(/larger than 150 KB/);
    expect(checkFile({ name: "a.csv", size: MAX_FILE_BYTES })).toBeNull();
  });

  it("toBase64 round-trips bytes, including ones that are not text", async () => {
    const bytes = Uint8Array.from({ length: 70_000 }, (_, i) => i % 256); // longer than one encoding chunk
    const decoded = Uint8Array.from(atob(await toBase64(new Blob([bytes]))), (c) => c.charCodeAt(0));
    expect(decoded).toEqual(bytes);
  });
});
