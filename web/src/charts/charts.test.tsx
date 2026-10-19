import { screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";
import { analysis } from "../test/fixtures";
import { renderWithProviders } from "../test/render";
import { AllocationChart } from "./AllocationChart";
import { OutflowsChart } from "./OutflowsChart";
import { ProjectionChart } from "./ProjectionChart";
import { ScenarioChart } from "./ScenarioChart";

const data = analysis();
const balanced = data.options[1]!;

describe("every chart offers a text alternative and a table", () => {
  it("allocation: the summary names every class and share; the table gives the rupee amounts", async () => {
    const user = userEvent.setup();
    renderWithProviders(<AllocationChart title="Balanced mix" weights={balanced.portfolio.weights_total} corpusCr={1000} />);
    const picture = screen.getByRole("img");
    expect(picture).toHaveAccessibleName(/Balanced mix: .*Debt 20\.0%.*Illiquid \(fixed\) 40\.0%.*of ₹1,000 Cr\./);

    await user.click(screen.getByRole("radio", { name: "Table" }));
    const table = screen.getByRole("table", { name: "Balanced mix" });
    expect(within(table).getByRole("row", { name: /Large-cap equity.*13\.8%.*₹137\.5 Cr/ })).toBeInTheDocument();
    expect(within(table).getAllByRole("row")).toHaveLength(7); // header + six classes
  });

  it("the donut legend marks the illiquid bucket as hatched, not only coloured", () => {
    renderWithProviders(<AllocationChart title="Mix" weights={balanced.portfolio.weights_total} corpusCr={1000} />);
    const swatches = document.querySelectorAll<HTMLElement>(".legend .swatch");
    expect(swatches).toHaveLength(6);
    const hatched = [...swatches].filter((s) => s.style.background.includes("repeating-linear-gradient"));
    expect(hatched).toHaveLength(1);
  });

  it("allocation hides zero-share classes from the donut but still lists them", () => {
    renderWithProviders(<AllocationChart title="Mix" weights={{ Debt: 0.6, Gold: 0, Illiquid: 0.4 }} corpusCr={500} />);
    expect(screen.getByRole("img")).toHaveAccessibleName(/Debt 60\.0%, Illiquid \(fixed\) 40\.0%/);
    expect(screen.getByRole("img")).not.toHaveAccessibleName(/Gold/);
    expect(screen.getAllByText("Gold").length).toBeGreaterThan(0); // still in the legend
  });

  it("projection: states the start and end values, and the switch changes today's rupees to nominal", async () => {
    const user = userEvent.setup();
    renderWithProviders(<ProjectionChart current={data.current_projection} selected={balanced.projection} selectedLabel="Balanced" />);
    expect(screen.getByRole("img")).toHaveAccessibleName(/Over 3 years, in today's rupees, the current mix goes from ₹1,000 Cr to/);

    await user.click(screen.getByRole("radio", { name: "Nominal" }));
    expect(screen.getByRole("img")).toHaveAccessibleName(/in nominal rupees/);
    await user.click(screen.getByRole("radio", { name: "Table" }));
    const table = screen.getByRole("table", { name: "Projected corpus by year" });
    expect(within(table).getAllByRole("row")).toHaveLength(5); // header + years 0 to 3
    expect(within(table).getByRole("row", { name: /^3 / })).toHaveTextContent("₹1,");
  });

  it("outflows: totals the rupees and separates one-off amounts", async () => {
    const user = userEvent.setup();
    renderWithProviders(<OutflowsChart rows={data.upcoming_outflows} />);
    expect(screen.getByRole("img")).toHaveAccessibleName(/over the next 3 years total ₹163 Cr, of which ₹100 Cr are one-off/); // 120 + 20.9 + 21.8 = 162.7, rounded half up
    await user.click(screen.getByRole("radio", { name: "Table" }));
    expect(screen.getByRole("row", { name: /^1 .*₹100\.0 Cr.*₹120\.0 Cr/ })).toBeInTheDocument();
  });

  it("scenario: states each option's loss in words and flags the short safety net", async () => {
    const user = userEvent.setup();
    renderWithProviders(<ScenarioChart scenario="Equities fall 25%" rows={data.comparison} />);
    const summary = screen.getByRole("img").getAttribute("aria-label") ?? "";
    expect(summary).toContain("Current −₹137.5 Cr (−13.8%), safety net short at 0.4x");
    expect(summary).toContain("Defensive −₹39.7 Cr (−4.0%), safety net held at 3.4x");

    await user.click(screen.getByRole("radio", { name: "Table" }));
    expect(within(screen.getByRole("row", { name: /Current/ })).getByText("Short")).toBeInTheDocument();
    expect(within(screen.getByRole("row", { name: /Defensive/ })).getByText("Held")).toBeInTheDocument();
  });

  it("switching to the table and back keeps the chart", async () => {
    const user = userEvent.setup();
    renderWithProviders(<OutflowsChart rows={data.upcoming_outflows} />);
    await user.click(screen.getByRole("radio", { name: "Table" }));
    expect(screen.queryByRole("img")).not.toBeInTheDocument();
    await user.click(screen.getByRole("radio", { name: "Chart" }));
    expect(screen.getByRole("img")).toBeInTheDocument();
  });
});
