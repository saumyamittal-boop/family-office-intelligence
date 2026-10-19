import { readStored, writeStored } from "./storage";

export type ThemePreference = "light" | "dark" | "system";
export type ResolvedTheme = "light" | "dark";

export const THEME_KEY = "foi.theme";
const PREFERENCES: readonly ThemePreference[] = ["light", "dark", "system"];

export function isPreference(value: unknown): value is ThemePreference {
  return typeof value === "string" && (PREFERENCES as readonly string[]).includes(value);
}

export function readPreference(): ThemePreference {
  const stored = readStored(THEME_KEY);
  return isPreference(stored) ? stored : "system";
}

export function savePreference(preference: ThemePreference): void {
  writeStored(THEME_KEY, preference);
}

export function systemPrefersDark(): boolean {
  return typeof window.matchMedia === "function" && window.matchMedia("(prefers-color-scheme: dark)").matches;
}

export function resolveTheme(preference: ThemePreference, systemDark: boolean): ResolvedTheme {
  if (preference === "system") return systemDark ? "dark" : "light";
  return preference;
}

/** Put the theme on <html>. The same attribute is set by the inline script in index.html before first paint. */
export function applyTheme(theme: ResolvedTheme): void {
  document.documentElement.setAttribute("data-theme", theme);
}
