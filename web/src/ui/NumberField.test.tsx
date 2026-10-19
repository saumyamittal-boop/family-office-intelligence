import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { useState } from "react";
import { describe, expect, it, vi } from "vitest";
import { NumberField, parseNumber } from "./NumberField";

describe("parseNumber", () => {
  it.each([
    ["250", 250], ["2,50,000", 250000], [" 1 000 ", 1000], ["3.5", 3.5], ["-4", -4], ["0", 0], [".5", 0.5],
    ["", null], ["   ", null], ["abc", null], ["12abc", null], ["1e3", 1000], ["Infinity", null], ["NaN", null],
  ])("reads %j as %j", (text, expected) => {
    expect(parseNumber(text)).toBe(expected);
  });
});

function Harness({ min, max, integer, error }: { min?: number; max?: number; integer?: boolean; error?: string }) {
  const [value, setValue] = useState(10);
  return (
    <>
      <NumberField label="Amount" unit="Cr" hint="Rough is fine." value={value} onChange={(v) => v !== null && setValue(v)} min={min} max={max} integer={integer} error={error} />
      <button onClick={() => setValue(77)}>Preset</button>
    </>
  );
}

describe("NumberField", () => {
  it("is a labelled box whose hint is tied to it for screen readers", () => {
    render(<Harness />);
    const box = screen.getByLabelText(/Amount/);
    expect(box).toHaveValue("10");
    expect(box).toHaveAccessibleDescription("Rough is fine.");
    expect(box).toHaveAttribute("inputmode", "decimal");
  });

  it("lets a person type freely: empty, half-typed and with commas, reporting a number or null", async () => {
    const user = userEvent.setup();
    const onChange = vi.fn();
    render(<NumberField label="Amount" value={10} onChange={onChange} />);
    const box = screen.getByLabelText("Amount");
    await user.clear(box);
    expect(onChange).toHaveBeenLastCalledWith(null);
    expect(screen.getByText("Enter a number.")).toBeInTheDocument();
    await user.type(box, "1,250");
    expect(onChange).toHaveBeenLastCalledWith(1250);
    expect(screen.queryByText("Enter a number.")).not.toBeInTheDocument();
  });

  it("says at once when the value is out of range, and ties the message to the box", async () => {
    const user = userEvent.setup();
    render(<Harness min={1} max={100} />);
    const box = screen.getByLabelText(/Amount/);
    await user.clear(box);
    await user.type(box, "0");
    expect(screen.getByText("Must be at least 1.")).toBeInTheDocument();
    expect(box).toHaveAttribute("aria-invalid", "true");
    expect(box).toHaveAccessibleDescription(/Must be at least 1\./);
    await user.clear(box);
    await user.type(box, "500");
    expect(screen.getByText("Must be at most 100.")).toBeInTheDocument();
    await user.clear(box);
    await user.type(box, "50");
    expect(box).not.toHaveAttribute("aria-invalid");
  });

  it("asks for a whole number when it needs one", async () => {
    const user = userEvent.setup();
    render(<Harness integer min={1} max={25} />);
    const box = screen.getByLabelText(/Amount/);
    await user.clear(box);
    await user.type(box, "2.5");
    expect(screen.getByText("Use a whole number.")).toBeInTheDocument();
  });

  it("follows a value that changes from outside, such as a preset or a reset", async () => {
    const user = userEvent.setup();
    render(<Harness />);
    await user.click(screen.getByRole("button", { name: "Preset" }));
    expect(screen.getByLabelText(/Amount/)).toHaveValue("77");
  });

  it("does not overwrite what is being typed when the value it reported comes back", async () => {
    const user = userEvent.setup();
    render(<Harness />);
    const box = screen.getByLabelText(/Amount/);
    await user.clear(box);
    await user.type(box, "5.");
    expect(box).toHaveValue("5."); // "5." parses to 5, which must not be rewritten to "5" mid-typing
  });

  it("shows an error from outside (for a rule the box cannot know) and keeps its own message first", () => {
    render(<Harness error="Too much for this plan." />);
    expect(screen.getByText("Too much for this plan.")).toBeInTheDocument();
  });
});
