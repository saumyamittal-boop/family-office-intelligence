import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { act } from "react";
import { describe, expect, it, vi } from "vitest";
import { ThemeMenu } from "../layout/Topbar";
import { TooltipProvider } from "../ui/Overlays";
import { ThemeProvider, useTheme } from "./ThemeProvider";
import { THEME_KEY, readPreference, resolveTheme, savePreference } from "./theme";

type Listener = (event: MediaQueryListEvent) => void;

/** A controllable stand-in for the device's colour-scheme setting. */
function fakeDevice(dark: boolean) {
  const listeners = new Set<Listener>();
  window.matchMedia = ((query: string) => ({
    matches: dark, media: query, onchange: null, dispatchEvent: () => false, addListener: () => {}, removeListener: () => {},
    addEventListener: (_: string, l: Listener) => listeners.add(l),
    removeEventListener: (_: string, l: Listener) => listeners.delete(l),
  })) as typeof window.matchMedia;
  return {
    switchTo(next: boolean) {
      dark = next;
      listeners.forEach((l) => l({ matches: next } as MediaQueryListEvent));
    },
  };
}

const theme = () => document.documentElement.getAttribute("data-theme");

function Probe() {
  const { preference, resolved } = useTheme();
  return <p data-testid="probe">{`${preference}/${resolved}`}</p>;
}

describe("resolving the theme", () => {
  it("follows the device only in system mode", () => {
    expect(resolveTheme("system", true)).toBe("dark");
    expect(resolveTheme("system", false)).toBe("light");
    expect(resolveTheme("light", true)).toBe("light");
    expect(resolveTheme("dark", false)).toBe("dark");
  });

  it("ignores junk in storage and defaults to the device", () => {
    for (const junk of ["", "purple", "DARK", "null", "{}"]) {
      window.localStorage.setItem(THEME_KEY, junk);
      expect(readPreference()).toBe("system");
    }
    window.localStorage.setItem(THEME_KEY, "dark");
    expect(readPreference()).toBe("dark");
  });

  it("still works when the browser blocks storage", () => {
    const blocked = () => {
      throw new Error("storage blocked");
    };
    vi.spyOn(Storage.prototype, "getItem").mockImplementation(blocked);
    vi.spyOn(Storage.prototype, "setItem").mockImplementation(blocked);
    expect(readPreference()).toBe("system");
    expect(() => savePreference("dark")).not.toThrow();
    vi.restoreAllMocks();
  });
});

describe("ThemeProvider", () => {
  it("applies the device theme on load and follows the device live in system mode", () => {
    const device = fakeDevice(true);
    render(
      <ThemeProvider>
        <Probe />
      </ThemeProvider>,
    );
    expect(theme()).toBe("dark");
    expect(screen.getByTestId("probe")).toHaveTextContent("system/dark");
    act(() => device.switchTo(false));
    expect(theme()).toBe("light");
    expect(screen.getByTestId("probe")).toHaveTextContent("system/light");
  });

  it("a saved choice wins over the device and is not moved by it", () => {
    const device = fakeDevice(false);
    window.localStorage.setItem(THEME_KEY, "dark");
    render(
      <ThemeProvider>
        <Probe />
      </ThemeProvider>,
    );
    expect(theme()).toBe("dark");
    act(() => device.switchTo(true));
    act(() => device.switchTo(false));
    expect(theme()).toBe("dark");
  });

  it("the theme menu switches the theme, remembers it, and labels the current choice", async () => {
    fakeDevice(false);
    const user = userEvent.setup();
    render(
      <ThemeProvider>
        <QueryClientProvider client={new QueryClient()}>
          <TooltipProvider>
            <ThemeMenu />
            <Probe />
          </TooltipProvider>
        </QueryClientProvider>
      </ThemeProvider>,
    );
    await user.click(screen.getByRole("button", { name: /Theme: Match my device \(light\)/ }));
    await user.click(await screen.findByRole("menuitemradio", { name: "Dark" }));
    expect(theme()).toBe("dark");
    expect(window.localStorage.getItem(THEME_KEY)).toBe("dark");
    expect(screen.getByRole("button", { name: "Theme: Dark" })).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "Theme: Dark" }));
    expect(await screen.findByRole("menuitemradio", { name: "Dark" })).toBeChecked();
    await user.click(screen.getByRole("menuitemradio", { name: "Light" }));
    expect(theme()).toBe("light");
  });
});
