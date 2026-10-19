import type { ReactNode } from "react";
import type { ModuleMode } from "./types";

/** Two related cards: side by side on a full page, stacked inside a dashboard card. */
export function Pair({ mode, children }: { mode: ModuleMode; children: ReactNode }) {
  return mode === "page" ? <div className="grid-2">{children}</div> : <>{children}</>;
}
