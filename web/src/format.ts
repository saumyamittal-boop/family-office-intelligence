/**
 * Number formatting that matches the Python app (fo/ui.py) exactly.
 *
 * Percentages round half up on the decimal text, so 13.75% shows as 13.8%. Plain float formatting
 * would print 13.7 because 13.75 is not exactly representable. src/test/format_vectors.json holds
 * 1,350 cases recorded from the Python formatter; format.test.ts checks every one.
 */

const MINUS = "−"; // the typographic minus used throughout the app
const RUPEE = "₹";

/** Round `value` half-up (away from zero on ties) to `digits` decimals, working on the decimal text. */
export function halfUp(value: number, digits: number): string {
  if (!Number.isFinite(value)) return "n/a";
  // Like Python's Decimal(str(round(value, 9))): settle float noise at 9 decimals first.
  const [whole = "0", fraction = ""] = Math.abs(value).toFixed(9).split(".");
  const kept = BigInt(whole + fraction.slice(0, digits));
  const roundUp = fraction.charCodeAt(digits) - 48 >= 5;
  const digitsText = (kept + (roundUp ? 1n : 0n)).toString().padStart(digits + 1, "0");
  const integerPart = digits === 0 ? digitsText : digitsText.slice(0, -digits);
  const decimalPart = digits === 0 ? "" : "." + digitsText.slice(-digits);
  const negative = value < 0 || Object.is(value, -0);
  return (negative ? "-" : "") + integerPart + decimalPart;
}

function withThousands(text: string): string {
  const negative = text.startsWith("-");
  const [integer = "0", decimal] = (negative ? text.slice(1) : text).split(".");
  const grouped = integer.replace(/\B(?=(\d{3})+(?!\d))/g, ",");
  return (negative ? "-" : "") + grouped + (decimal === undefined ? "" : "." + decimal);
}

/** 0.1375 -> "13.8%" */
export function pct(value: number, digits = 1): string {
  const text = halfUp(value * 100, digits);
  return text === "n/a" ? text : `${text}%`;
}

/** -0.1375 -> "−13.8%", 0.05 -> "+5.0%" */
export function signedPct(value: number, digits = 1): string {
  const text = halfUp(Math.abs(value) * 100, digits);
  return text === "n/a" ? text : `${value >= 0 ? "+" : MINUS}${text}%`;
}

/** 1000 -> "₹1,000.0 Cr" */
export function cr(value: number, digits = 1): string {
  const text = halfUp(value, digits);
  return text === "n/a" ? text : `${RUPEE}${withThousands(text)} Cr`;
}

/** -137.5 -> "−₹137.5 Cr" */
export function signedCr(value: number, digits = 1): string {
  const text = halfUp(Math.abs(value), digits);
  return text === "n/a" ? text : `${value >= 0 ? "+" : MINUS}${RUPEE}${withThousands(text)} Cr`;
}

/** 3.14159 -> "3.1x" (cover ratios) */
export function times(value: number, digits = 1): string {
  const text = halfUp(value, digits);
  return text === "n/a" ? text : `${text}x`;
}
