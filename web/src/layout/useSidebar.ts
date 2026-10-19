import { useCallback, useState } from "react";
import { readStored, writeStored } from "../theme/storage";

const KEY = "foi.sidebar";

/** Whether the desktop sidebar is collapsed to icons. A per-viewer convenience, remembered in this browser. */
export function useSidebarCollapsed(): [boolean, () => void] {
  const [collapsed, setCollapsed] = useState(() => readStored(KEY) === "collapsed");
  const toggle = useCallback(() => {
    const next = !collapsed;
    setCollapsed(next);
    writeStored(KEY, next ? "collapsed" : "expanded");
  }, [collapsed]);
  return [collapsed, toggle];
}
