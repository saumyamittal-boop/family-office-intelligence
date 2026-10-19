/** localStorage can be missing or throw (private windows, blocked site data), so every access is wrapped.
 * Only harmless per-viewer conveniences are kept here (theme, sidebar). Never tokens, never financial data. */
export function readStored(key: string): string | null {
  try {
    return window.localStorage.getItem(key);
  } catch {
    return null;
  }
}

export function writeStored(key: string, value: string): void {
  try {
    window.localStorage.setItem(key, value);
  } catch {
    /* the preference simply lasts until the page is closed */
  }
}
