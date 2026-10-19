import type { Commitment } from "../api/client";
import { cr } from "../format";

export const CUSTOM_KIND = "Custom";
export const LABEL_MAX = 40;

/** How a commitment is named in a sentence: a preset in lower case, a custom expense by the name the family gave it. */
export function commitmentName(c: Pick<Commitment, "kind" | "label">): string {
  if (c.kind === CUSTOM_KIND) return c.label?.trim() || "Custom expense";
  return c.kind.toLowerCase();
}

/** "wedding in 2 years (₹8.0 Cr)" or "Aarav's school fees in 3 years (₹9.0 Cr)". */
export function commitmentPhrase(c: Commitment): string {
  return `${commitmentName(c)} in ${c.year} ${c.year === 1 ? "year" : "years"} (${cr(c.amount_cr)})`;
}
