import type { AssetClass, HoldingsUnit } from "../api/client";

/** The model's six asset classes, in the order everything on screen lists them. Typed against the API, so a rename fails the build. */
export const HOLDING_CLASSES: readonly AssetClass[] = ["Large-cap equity", "Mid-cap equity", "Debt", "Gold", "Cash & liquid", "Illiquid"];

export const className = (c: string): string => (c === "Illiquid" ? "Illiquid (held fixed)" : c);
export const accountName = (a: string): string => (a === "" ? "No account named" : a);

export const UNITS: { value: HoldingsUnit; label: string }[] = [
  { value: "cr", label: "Rupees crore" },
  { value: "lakh", label: "Rupees lakh" },
  { value: "inr", label: "Rupees" },
];

/** The same limits the server enforces, checked first so an obviously unusable file is not sent at all. */
export const MAX_FILE_BYTES = 150 * 1024;
const ALLOWED = [".csv", ".xlsx", ".txt", ".tsv"];

export function checkFile(file: { name: string; size: number }): string | null {
  const lower = file.name.toLowerCase();
  if (!ALLOWED.some((ext) => lower.endsWith(ext))) return "Choose a .csv or .xlsx file.";
  if (file.size === 0) return "That file is empty.";
  if (file.size > MAX_FILE_BYTES) return `That file is larger than ${MAX_FILE_BYTES / 1024} KB. A holdings list should be much smaller.`;
  return null;
}

/** The file's bytes as base64, which is how the API takes a file (inside JSON, so its size and type guards still apply). */
export async function toBase64(file: Blob): Promise<string> {
  const bytes = new Uint8Array(await file.arrayBuffer());
  let binary = "";
  for (let i = 0; i < bytes.length; i += 0x8000) binary += String.fromCharCode(...bytes.subarray(i, i + 0x8000));
  return btoa(binary);
}

/** Saves text as a file. A byte-order mark is added so Excel opens a CSV with the rupee sign intact. */
export function download(filename: string, content: string): void {
  const url = URL.createObjectURL(new Blob(["﻿", content], { type: "text/csv;charset=utf-8" }));
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(url);
}
