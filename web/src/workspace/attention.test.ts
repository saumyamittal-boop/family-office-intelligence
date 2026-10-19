import { describe, expect, it } from "vitest";
import { analysis, portfolio } from "../test/fixtures";
import { attentionItems } from "./AttentionBar";

const clean = () => analysis({ current: portfolio("Current", { lam_base: null, lam_used: null }) });

describe("warnings that must always show, whatever else is on screen", () => {
  it("a clean analysis raises none", () => {
    expect(attentionItems(clean())).toEqual([]);
  });

  it("flags a liquidity shortfall in the current mix with the actual cover", () => {
    const items = attentionItems(analysis()); // the fixture's current mix holds 50 of 120 Cr
    expect(items.map((i) => i.id)).toEqual(["liquidity"]);
    expect(items[0]).toMatchObject({ tone: "bad" });
    expect(items[0]?.body).toContain("₹50 Cr");
    expect(items[0]?.body).toContain("₹120 Cr");
    expect(items[0]?.body).toContain("0.4x");
  });

  it("flags a solver that did not converge, naming each affected portfolio", () => {
    const data = clean();
    data.options[0] = { ...data.options[0]!, portfolio: portfolio("Growth", { optimiser_converged: false }) };
    data.options[2] = { ...data.options[2]!, portfolio: portfolio("Defensive", { optimiser_converged: false }) };
    const [item] = attentionItems(data);
    expect(item?.id).toBe("optimiser");
    expect(item?.body).toContain("Growth, Defensive");
  });

  it("flags a current mix whose history fell further than the person's limit", () => {
    const data = analysis({ current: portfolio("Current", { dd_ok: false, lam_base: null, lam_used: null }) });
    expect(attentionItems(data).map((i) => i.id)).toEqual(["drawdown"]);
  });

  it("does not depend on any choice of which portfolio is displayed", () => {
    const data = analysis();
    expect(attentionItems(data)).toEqual(attentionItems(structuredClone(data)));
  });
});
