import { screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";
import { analysis, LADDER } from "../test/fixtures";
import { history } from "../test/phase4Fixtures";
import { renderWithProviders } from "../test/render";
import { AnnualReturnsChart, DrawdownChart, HistoryValueChart, yearRows, yearTicks } from "./HistoryCharts";
import { LadderChart, ladderRunsOut } from "./LadderChart";

const h = history();
const mix = (label: string) => h.portfolios.find((p) => p.label === label)!;

describe("year helpers", () => {
  it("yearTicks keeps the first date of each calendar year, so no label repeats", () => {
    expect(yearTicks(["2016-01-04", "2016-06-30", "2017-01-02", "2017-12-29", "2019-03-01"])).toEqual(["2016-01-04", "2017-01-02", "2019-03-01"]);
    expect(yearTicks([])).toEqual([]);
  });

  it("yearRows reports where each series ended the year and the deepest fall inside it", () => {
    const dates = ["2016-06-30", "2016-12-30", "2017-06-30", "2017-12-29"];
    const rows = yearRows(dates, [[100, 110, 120, 90], [100, 100, 100, 100]], [0, 0, -0.05, -0.2]);
    expect(rows).toEqual([
      { year: "2016", end: [110, 100], deepest: 0 },
      { year: "2017", end: [90, 100], deepest: -0.2 },
    ]);
  });
});

describe("liquidity ladder chart", () => {
  it("states the span, the totals and the first and last liquid assets in its text alternative", () => {
    renderWithProviders(<LadderChart rows={analysis().options[1]!.ladder} label="Balanced" />);
    expect(screen.getByRole("img")).toHaveAccessibleName(/Balanced: over 4 years the liquid assets go from ₹350 Cr in year 1 to ₹260 Cr in year 4, against ₹189 Cr of outflows\./);
  });

  it("says when the liquid assets run out, and where", () => {
    const rows = LADDER.map((r, i) => (i >= 2 ? { ...r, liquid_value_cr: -10 * (i - 1) } : r));
    expect(ladderRunsOut(rows)).toBe(3);
    renderWithProviders(<LadderChart rows={rows} label="Growth" />);
    expect(screen.getByRole("img")).toHaveAccessibleName(/They run out in year 3\./);
  });

  it("ladderRunsOut is null while the assets last", () => {
    expect(ladderRunsOut(LADDER)).toBeNull();
    expect(ladderRunsOut([])).toBeNull();
  });

  it("has a table with the months of spending covered", async () => {
    const user = userEvent.setup();
    renderWithProviders(<LadderChart rows={LADDER} label="Balanced" />);
    await user.click(screen.getByRole("radio", { name: "Table" }));
    const table = screen.getByRole("table", { name: "Liquidity ladder, Balanced" });
    expect(within(table).getByRole("columnheader", { name: "Months of spending covered" })).toBeInTheDocument();
    expect(within(table).getByRole("row", { name: /^1 .*₹120\.0 Cr.*₹350\.0 Cr.*132$/ })).toBeInTheDocument();
  });
});

describe("value history chart", () => {
  it("names each mix and where it ends, and warns that the past is not a forecast", () => {
    renderWithProviders(<HistoryValueChart dates={h.dates} lines={[mix("Current"), mix("Balanced")]} />);
    const label = screen.getByRole("img").getAttribute("aria-label") ?? "";
    expect(label).toContain("Growth of 100 invested on 2015-12-31, to 2019-06-28");
    expect(label).toContain("Current ends at 131.2"); // 100 + 24 * 1.3
    expect(label).toContain("Balanced ends at 124.0");
    expect(label).toContain("Past sample returns do not predict future ones.");
  });

  it("offers year-end values as a table, one column per mix", async () => {
    const user = userEvent.setup();
    renderWithProviders(<HistoryValueChart dates={h.dates} lines={[mix("Current"), mix("Balanced"), mix("Defensive")]} />);
    await user.click(screen.getByRole("radio", { name: "Table" }));
    const table = screen.getByRole("table", { name: "Value of 100 invested, at the end of each year" });
    expect(within(table).getAllByRole("columnheader").map((c) => c.textContent)).toEqual(["Year end", "Current", "Balanced", "Defensive"]);
    expect(within(table).getByRole("row", { name: /^2015 100\.0 100\.0 100\.0$/ })).toBeInTheDocument();
    expect(within(table).getByRole("row", { name: /^2019 / })).toBeInTheDocument();
  });
});

describe("drawdown chart", () => {
  it("says the fall is within the limit, with the date of the trough", () => {
    renderWithProviders(<DrawdownChart dates={h.dates} history={mix("Balanced")} limit={0.15} />);
    expect(screen.getByRole("img")).toHaveAccessibleName(/Balanced: the worst fall from a previous peak was 7\.4%, around 2018-06-29\. Your limit is 15%, so this is within it\./);
  });

  it("says the fall is above the limit when it is", () => {
    renderWithProviders(<DrawdownChart dates={h.dates} history={mix("Current")} limit={0.05} />);
    expect(screen.getByRole("img")).toHaveAccessibleName(/Your limit is 5%, so this is above it\./);
  });

  it("tabulates the deepest fall in each year, and says None where there was none", async () => {
    const user = userEvent.setup();
    renderWithProviders(<DrawdownChart dates={h.dates} history={mix("Balanced")} limit={0.15} />);
    await user.click(screen.getByRole("radio", { name: "Table" }));
    const table = screen.getByRole("table", { name: "Deepest fall in each year, Balanced" });
    expect(within(table).getByRole("row", { name: /^2016 None$/ })).toBeInTheDocument();
    expect(within(table).getByRole("row", { name: /^2018 −7\.4%$/ })).toBeInTheDocument();
  });
});

describe("calendar-year returns chart", () => {
  it("counts the losing years and names the best and worst", () => {
    renderWithProviders(<AnnualReturnsChart history={mix("Balanced")} />);
    expect(screen.getByRole("img")).toHaveAccessibleName(
      "Balanced: 1 of 4 calendar years lost money. The best was 2017 at +11.0%; the worst was 2018 at −4.0%.",
    );
  });

  it("marks a part year in the description and the table", async () => {
    const user = userEvent.setup();
    renderWithProviders(<AnnualReturnsChart history={mix("Balanced")} />);
    expect(screen.getByText(/A \* marks a year with only part of its days in the sample\./)).toBeInTheDocument();
    await user.click(screen.getByRole("radio", { name: "Table" }));
    expect(screen.getByRole("row", { name: /2019 \(part year\)/ })).toBeInTheDocument();
    expect(screen.getByRole("row", { name: /^2018 −4\.0% 261$/ })).toBeInTheDocument();
  });

  it("copes with no years at all", () => {
    renderWithProviders(<AnnualReturnsChart history={{ ...mix("Balanced"), annual: [] }} />);
    expect(screen.getByRole("img")).toHaveAccessibleName("No calendar years available.");
  });
});
