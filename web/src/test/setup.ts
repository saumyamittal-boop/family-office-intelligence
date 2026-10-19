import "@testing-library/jest-dom/vitest";
import { cleanup } from "@testing-library/react";
import { Children, cloneElement, createElement, isValidElement } from "react";
import type { ReactElement, ReactNode } from "react";
import { afterEach, beforeEach, vi } from "vitest";

// jsdom has no layout, so Recharts' ResponsiveContainer would measure 0x0 and draw nothing. Give it a fixed size.
vi.mock("recharts", async (importOriginal) => {
  const actual = await importOriginal<typeof import("recharts")>();
  return {
    ...actual,
    ResponsiveContainer: ({ children }: { children: ReactNode }) =>
      createElement(
        "div",
        { style: { width: 640, height: 300 } },
        Children.map(children, (child) =>
          isValidElement(child) ? cloneElement(child as ReactElement<{ width?: number; height?: number }>, { width: 640, height: 300 }) : child,
        ),
      ),
  };
});

// Browser APIs that jsdom lacks and Radix UI uses.
class ResizeObserverStub {
  observe() {}
  unobserve() {}
  disconnect() {}
}
vi.stubGlobal("ResizeObserver", ResizeObserverStub);

beforeEach(() => {
  window.localStorage.clear();
  document.documentElement.setAttribute("data-theme", "light");
  Element.prototype.hasPointerCapture = () => false;
  Element.prototype.setPointerCapture = () => {};
  Element.prototype.releasePointerCapture = () => {};
  Element.prototype.scrollIntoView = () => {};
  // Default: a light-mode device. Individual tests replace this to simulate dark mode.
  window.matchMedia = ((query: string) => ({
    matches: false, media: query, onchange: null,
    addEventListener: () => {}, removeEventListener: () => {}, addListener: () => {}, removeListener: () => {}, dispatchEvent: () => false,
  })) as typeof window.matchMedia;
});

afterEach(() => cleanup());
