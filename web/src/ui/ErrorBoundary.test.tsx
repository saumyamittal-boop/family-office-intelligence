import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { useState } from "react";
import { describe, expect, it, vi } from "vitest";
import { ChartFrame } from "../charts/ChartFrame";
import { renderWithProviders } from "../test/render";
import { ErrorBoundary } from "./ErrorBoundary";

function Broken(): never {
  throw new Error("boom");
}

// React logs caught render errors to the console; keep the test output readable.
const quiet = () => vi.spyOn(console, "error").mockImplementation(() => {});

describe("error boundary", () => {
  it("shows a message instead of a blank page, and the rest of the page keeps working", () => {
    quiet();
    renderWithProviders(
      <>
        <p>Neighbouring content</p>
        <ErrorBoundary>
          <Broken />
        </ErrorBoundary>
      </>,
    );
    expect(screen.getByRole("alert")).toHaveTextContent("couldn't be shown");
    expect(screen.getByText("Neighbouring content")).toBeInTheDocument();
    vi.restoreAllMocks();
  });

  it("offers a retry that recovers once the problem is gone", async () => {
    quiet();
    const user = userEvent.setup();
    function Flaky() {
      const [fixed, setFixed] = useState(false);
      return (
        <>
          <button onClick={() => setFixed(true)}>Fix it</button>
          <ErrorBoundary>{fixed ? <p>All good</p> : <Broken />}</ErrorBoundary>
        </>
      );
    }
    renderWithProviders(<Flaky />);
    await user.click(screen.getByRole("button", { name: "Fix it" }));
    await user.click(screen.getByRole("button", { name: "Try again" }));
    expect(screen.getByText("All good")).toBeInTheDocument();
    vi.restoreAllMocks();
  });

  it("clears the failure when the page address changes", () => {
    quiet();
    const { rerender } = renderWithProviders(
      <ErrorBoundary resetKey="/a">
        <Broken />
      </ErrorBoundary>,
    );
    expect(screen.getByRole("alert")).toBeInTheDocument();
    rerender(
      <ErrorBoundary resetKey="/b">
        <p>Another page</p>
      </ErrorBoundary>,
    );
    expect(screen.getByText("Another page")).toBeInTheDocument();
    expect(screen.queryByRole("alert")).not.toBeInTheDocument();
    vi.restoreAllMocks();
  });

  it("a chart that fails to draw says so, points to the table, and does not take its card down", () => {
    quiet();
    renderWithProviders(
      <ChartFrame title="Broken chart" summary="Numbers in words." chart={<Broken />} table={<p>table</p>} />,
    );
    expect(screen.getByRole("heading", { name: "Broken chart" })).toBeInTheDocument();
    expect(screen.getByRole("alert")).toHaveTextContent("This chart couldn't be drawn");
    expect(screen.getByRole("alert")).toHaveTextContent("Table view");
    expect(screen.getByText("Numbers in words.")).toBeInTheDocument();
    vi.restoreAllMocks();
  });
});
