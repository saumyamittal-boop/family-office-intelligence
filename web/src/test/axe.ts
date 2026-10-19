import axe from "axe-core";

/**
 * Automated WCAG 2.2 AA checks on whatever is on screen. Colour contrast cannot be computed without a layout engine, so it is
 * checked separately (tokens in styles/contrast.test.ts, and in a real browser).
 */
export async function audit(root: Element = document.body): Promise<string[]> {
  const result = await axe.run(root, {
    runOnly: { type: "tag", values: ["wcag2a", "wcag2aa", "wcag21a", "wcag21aa", "wcag22aa", "best-practice"] },
    rules: { "color-contrast": { enabled: false } },
  });
  return result.violations.map((v) => `${v.id}: ${v.help} -> ${v.nodes.map((n) => n.target.join(" ")).join(" | ")}`);
}
