import { describe, expect, it } from "vitest";
import rawTokens from "./tokens.css?raw";

const tokens = rawTokens.replace(/\r\n/g, "\n"); // the file may have Windows line endings on this machine

/** Colour tokens of one theme, read from the real stylesheet. */
function themeTokens(selector: string): Record<string, string> {
  const start = tokens.indexOf(selector);
  expect(start, `${selector} block not found`).toBeGreaterThanOrEqual(0);
  const body = tokens.slice(tokens.indexOf("{", start) + 1, tokens.indexOf("}", start));
  const found: Record<string, string> = {};
  for (const match of body.matchAll(/--([a-z0-9-]+):\s*(#[0-9a-fA-F]{6})\s*;/g)) found[match[1] as string] = match[2] as string;
  return found;
}

function luminance(hex: string): number {
  const channel = (offset: number) => {
    const c = parseInt(hex.slice(offset, offset + 2), 16) / 255;
    return c <= 0.03928 ? c / 12.92 : ((c + 0.055) / 1.055) ** 2.4;
  }; // WCAG 2.x relative luminance
  return 0.2126 * channel(1) + 0.7152 * channel(3) + 0.0722 * channel(5);
}

export function contrast(a: string, b: string): number {
  const [hi, lo] = [luminance(a), luminance(b)].sort((x, y) => y - x) as [number, number];
  return (hi + 0.05) / (lo + 0.05);
}

const TEXT: [string, string][] = [
  ["ink", "bg"], ["ink", "surface"], ["ink", "surface-2"], ["ink", "brand-soft"],
  ["ink-2", "bg"], ["ink-2", "surface"], ["ink-2", "surface-2"],
  ["brand-ink", "brand"], ["brand-ink", "brand-hover"],
  ["brand-text", "surface"], ["brand-text", "brand-soft"], ["brand-text", "bg"],
  ["good-ink", "good-bg"], ["warn-ink", "warn-bg"], ["bad-ink", "bad-bg"], ["info-ink", "info-bg"],
  // Scenario headlines are drawn straight on the card surface (phase 4).
  ["good-ink", "surface"], ["bad-ink", "surface"],
];

const NON_TEXT: [string, string][] = [
  ["line-strong", "surface"], ["line-strong", "bg"], ["focus", "surface"], ["focus", "bg"],
  ["brand", "surface"], ["brand", "bg"],
  ["chart-large", "surface"], ["chart-mid", "surface"], ["chart-debt", "surface"], ["chart-gold", "surface"],
  ["chart-cash", "surface"], ["chart-illiquid", "surface"], ["chart-a", "surface"], ["chart-b", "surface"],
];

describe.each([
  ["light", ':root,\n:root[data-theme="light"]'],
  ["dark", ':root[data-theme="dark"]'],
])("%s theme", (_name, selector) => {
  const t = themeTokens(selector);

  it("defines every token the pairs below need", () => {
    for (const [a, b] of [...TEXT, ...NON_TEXT]) {
      expect(t[a], `--${a}`).toMatch(/^#/);
      expect(t[b], `--${b}`).toMatch(/^#/);
    }
  });

  it.each(TEXT)("text: --%s on --%s is at least 4.5:1", (a, b) => {
    expect(contrast(t[a] as string, t[b] as string)).toBeGreaterThanOrEqual(4.5);
  });

  it.each(NON_TEXT)("non-text: --%s against --%s is at least 3:1", (a, b) => {
    expect(contrast(t[a] as string, t[b] as string)).toBeGreaterThanOrEqual(3);
  });
});

describe("the contrast calculator", () => {
  it("matches known WCAG values", () => {
    expect(contrast("#000000", "#ffffff")).toBeCloseTo(21, 5);
    expect(contrast("#777777", "#ffffff")).toBeCloseTo(4.48, 1); // the classic just-failing grey
    expect(contrast("#767676", "#ffffff")).toBeGreaterThanOrEqual(4.5); // and the darkest grey that passes
  });
});

describe("the two themes", () => {
  it("define the same set of tokens, so nothing is missing in one of them", () => {
    const light = Object.keys(themeTokens(':root,\n:root[data-theme="light"]')).sort();
    const dark = Object.keys(themeTokens(':root[data-theme="dark"]')).sort();
    expect(dark).toEqual(light);
  });
});
