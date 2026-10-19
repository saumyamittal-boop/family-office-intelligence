import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { useState } from "react";
import { describe, expect, it, vi } from "vitest";
import { SegmentedControl, Select, TextField } from "./Controls";
import { DataTable } from "./DataTable";
import { IconButton, SidePanel, TooltipProvider } from "./Overlays";
import { StatTile } from "./StatTile";
import { Badge, Banner } from "./Status";
import { EmptyState, ErrorState, LoadingBlock } from "./States";

describe("status is never colour alone", () => {
  it.each([
    ["good", "OK"],
    ["warn", "Warning"],
    ["bad", "Problem"],
    ["info", "Note"],
  ] as const)("a %s badge says %s to screen readers and shows an icon", (tone, word) => {
    const { container } = render(<Badge tone={tone}>Label</Badge>);
    expect(screen.getByText(`${word}:`, { exact: false })).toHaveClass("sr-only");
    expect(container.querySelector("svg")).toBeInTheDocument();
  });

  it("a neutral badge adds nothing extra", () => {
    const { container } = render(<Badge>Plain</Badge>);
    expect(container.querySelector("svg")).not.toBeInTheDocument();
  });

  it("a stat tile in a warning tone shows an icon and the word, not just a coloured edge", () => {
    const { container } = render(<StatTile label="Drawdown" value="14.0%" tone="warn" />);
    expect(container.querySelector(".tile-status svg")).toBeInTheDocument();
    expect(screen.getByText("Warning")).toHaveClass("sr-only");
  });
});

describe("banners", () => {
  it("a critical banner is announced immediately; a live one politely; plain ones not at all", () => {
    render(
      <>
        <Banner tone="bad" critical title="Alert.">A</Banner>
        <Banner tone="info" live>B</Banner>
        <Banner tone="info">C</Banner>
      </>,
    );
    expect(screen.getAllByRole("alert")).toHaveLength(1);
    expect(screen.getAllByRole("status")).toHaveLength(1);
  });
});

describe("SegmentedControl", () => {
  function Harness() {
    const [value, setValue] = useState("b");
    return (
      <>
        <SegmentedControl label="Pick one" value={value} onChange={setValue} options={[{ value: "a", label: "Alpha" }, { value: "b", label: "Beta" }, { value: "c", label: "Gamma" }]} />
        <p data-testid="value">{value}</p>
      </>
    );
  }

  it("is a labelled group of radio buttons, so arrow keys and screen readers work natively", async () => {
    const user = userEvent.setup();
    render(<Harness />);
    expect(screen.getByRole("group", { name: "Pick one" })).toBeInTheDocument();
    expect(screen.getByRole("radio", { name: "Beta" })).toBeChecked();
    await user.click(screen.getByRole("radio", { name: "Beta" }));
    await user.keyboard("{ArrowRight}");
    expect(screen.getByTestId("value")).toHaveTextContent("c");
    await user.keyboard("{ArrowLeft}{ArrowLeft}");
    expect(screen.getByTestId("value")).toHaveTextContent("a");
  });
});

describe("form fields", () => {
  it("a select is labelled by its visible text", () => {
    render(
      <Select label="Family profile" defaultValue="2">
        <option value="1">One</option>
        <option value="2">Two</option>
      </Select>,
    );
    expect(screen.getByRole("combobox", { name: "Family profile" })).toHaveValue("2");
  });

  it("a text field ties its hint and its error to the input, and marks it invalid", () => {
    render(<TextField label="Password" hint="At least 8 characters." error="Too short." />);
    const input = screen.getByLabelText("Password");
    expect(input).toHaveAttribute("aria-invalid", "true");
    expect(input).toHaveAccessibleDescription("At least 8 characters. Too short.");
  });

  it("a valid field is not marked invalid", () => {
    render(<TextField label="Name" />);
    expect(screen.getByLabelText("Name")).not.toHaveAttribute("aria-invalid");
  });
});

describe("DataTable", () => {
  it("has a caption, column headers and row headers, so cells are announced with context", () => {
    render(
      <DataTable
        caption="Allocation"
        rows={[{ k: "Debt", v: "34.3%" }]}
        rowKey={(r) => r.k}
        columns={[
          { key: "k", header: "Asset class", rowHeader: true, cell: (r) => r.k },
          { key: "v", header: "Share", align: "right", cell: (r) => r.v },
        ]}
      />,
    );
    expect(screen.getByRole("table", { name: "Allocation" })).toBeInTheDocument();
    expect(screen.getByRole("columnheader", { name: "Share" })).toBeInTheDocument();
    expect(screen.getByRole("rowheader", { name: "Debt" })).toBeInTheDocument();
    expect(screen.getByRole("cell", { name: "34.3%" })).toHaveClass("num");
  });
});

describe("loading, empty and error states", () => {
  it("loading is announced politely and marked busy, with decorative placeholders", () => {
    const { container } = render(<LoadingBlock label="Running the allocation model" />);
    const region = screen.getByRole("status");
    expect(region).toHaveAttribute("aria-busy", "true");
    expect(region).toHaveTextContent("Running the allocation model");
    expect(container.querySelectorAll('.skeleton[aria-hidden="true"]').length).toBeGreaterThan(0);
  });

  it("an empty state explains itself and can offer the next step", () => {
    render(<EmptyState title="Nothing here yet" action={<button>Start</button>}>Because nothing has been added.</EmptyState>);
    expect(screen.getByRole("heading", { name: "Nothing here yet" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Start" })).toBeInTheDocument();
  });

  it("an error is announced at once and offers a retry that works", async () => {
    const retry = vi.fn();
    const user = userEvent.setup();
    render(<ErrorState message="The server said no." onRetry={retry} />);
    expect(screen.getByRole("alert")).toHaveTextContent("The server said no.");
    await user.click(screen.getByRole("button", { name: "Try again" }));
    expect(retry).toHaveBeenCalledOnce();
  });
});

describe("overlays", () => {
  it("a side panel is a titled dialog; Escape closes it and focus returns to what opened it", async () => {
    const user = userEvent.setup();
    function Harness() {
      const [open, setOpen] = useState(false);
      return (
        <>
          <button onClick={() => setOpen(true)}>Open details</button>
          <SidePanel open={open} onOpenChange={setOpen} title="Details" description="More about this.">
            <button>Inside</button>
          </SidePanel>
        </>
      );
    }
    render(<Harness />);
    const opener = screen.getByRole("button", { name: "Open details" });
    await user.click(opener);
    const dialog = await screen.findByRole("dialog", { name: "Details" });
    expect(dialog).toHaveAccessibleDescription("More about this.");
    expect(within(dialog).getByRole("button", { name: "Close panel" })).toBeInTheDocument();
    await user.keyboard("{Escape}");
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
    expect(opener).toHaveFocus();
  });

  it("an icon-only button has an accessible name", () => {
    render(
      <TooltipProvider>
        <IconButton label="Open navigation" icon="menu" />
      </TooltipProvider>,
    );
    expect(screen.getByRole("button", { name: "Open navigation" })).toBeInTheDocument();
  });
});
