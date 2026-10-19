/** One fixed colour per asset class, from the design tokens (so charts follow the theme). */
export const CLASS_COLOR: Record<string, string> = {
  "Large-cap equity": "var(--chart-large)",
  "Mid-cap equity": "var(--chart-mid)",
  Debt: "var(--chart-debt)",
  Gold: "var(--chart-gold)",
  "Cash & liquid": "var(--chart-cash)",
  Illiquid: "var(--chart-illiquid)",
};

export const FALLBACK_COLOR = "var(--chart-cash)";

export function classColor(name: string): string {
  return CLASS_COLOR[name] ?? FALLBACK_COLOR;
}

/** Illiquid holdings are also drawn hatched, so the "held fixed" bucket is not told apart by colour alone. */
export const HATCH_CSS =
  "repeating-linear-gradient(45deg, var(--chart-illiquid) 0 3px, var(--surface) 3px 5px)";
