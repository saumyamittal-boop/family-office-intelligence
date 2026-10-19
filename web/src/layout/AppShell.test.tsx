import { screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { Route, Routes } from "react-router-dom";
import { afterEach, describe, expect, it, vi } from "vitest";
import { ComingSoonPage } from "../pages/ComingSoonPage";
import { renderWithProviders, serve } from "../test/render";
import { session } from "../test/fixtures";
import { AppShell } from "./AppShell";
import { NAV } from "./nav";

function shell(route = "/") {
  return renderWithProviders(
    <Routes>
      <Route element={<AppShell session={session} />}>
        <Route index element={<h1>Home page</h1>} />
        <Route path="*" element={<ComingSoonPage />} />
      </Route>
    </Routes>,
    route,
  );
}

afterEach(() => vi.unstubAllGlobals());

describe("navigation", () => {
  it("lists every page and marks the current one", () => {
    shell();
    const nav = screen.getByRole("navigation", { name: "Main" });
    for (const item of NAV) expect(within(nav).getByRole("link", { name: new RegExp(item.label) })).toBeInTheDocument();
    expect(within(nav).getByRole("link", { name: /Overview/ })).toHaveAttribute("aria-current", "page");
    expect(within(nav).getByRole("link", { name: /Plan my money/ })).not.toHaveAttribute("aria-current");
  });

  it("says which pages are not built yet", () => {
    shell();
    const nav = screen.getByRole("navigation", { name: "Main" });
    expect(within(nav).getAllByText("Soon")).toHaveLength(NAV.filter((n) => n.arrivesInPhase).length);
  });

  it("an unbuilt page is an honest placeholder with its phase, not invented numbers", async () => {
    const user = userEvent.setup();
    shell();
    await user.click(screen.getByRole("link", { name: /Holdings/ }));
    expect(screen.getByRole("heading", { name: "Holdings" })).toBeInTheDocument();
    expect(screen.getByText("Not built yet")).toBeInTheDocument();
    expect(screen.getByText(/Planned for phase 5 of 8/)).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /Holdings/ })).toHaveAttribute("aria-current", "page");
    expect(screen.queryByText(/₹/)).not.toBeInTheDocument();
  });

  it("keeps the chosen profile and basis when moving between pages", () => {
    shell("/?profile=2&basis=strict");
    const link = screen.getByRole("link", { name: /Risk and liquidity/ });
    expect(link).toHaveAttribute("href", "/risk?profile=2&basis=strict");
  });

  it("an address that does not exist says so and offers a way back", () => {
    shell("/nope");
    expect(screen.getByText("This page does not exist")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Go to the overview" })).toBeInTheDocument();
  });
});

describe("landmarks and keyboard", () => {
  it("has a skip link that targets the focusable main region", () => {
    shell();
    const skip = screen.getByRole("link", { name: "Skip to main content" });
    expect(skip).toHaveAttribute("href", "#main");
    const main = screen.getByRole("main");
    expect(main).toHaveAttribute("id", "main");
    expect(main).toHaveAttribute("tabindex", "-1");
  });

  it("is the first thing a keyboard user reaches", async () => {
    const user = userEvent.setup();
    shell();
    await user.tab();
    expect(screen.getByRole("link", { name: "Skip to main content" })).toHaveFocus();
  });
});

describe("collapsible sidebar", () => {
  it("collapses to icons, keeps every link's name, and remembers the choice", async () => {
    const user = userEvent.setup();
    const { unmount } = shell();
    const toggle = screen.getByRole("button", { name: "Collapse sidebar" });
    expect(toggle).toHaveAttribute("aria-expanded", "true");

    await user.click(toggle);
    expect(screen.getByRole("button", { name: "Expand sidebar" })).toHaveAttribute("aria-expanded", "false");
    expect(document.querySelector(".shell")).toHaveClass("is-collapsed");
    expect(screen.getByRole("link", { name: /Recommendation.*coming soon/ })).toBeInTheDocument();
    expect(window.localStorage.getItem("foi.sidebar")).toBe("collapsed");

    unmount();
    shell(); // a fresh page load
    expect(screen.getByRole("button", { name: "Expand sidebar" })).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Expand sidebar" }));
    expect(window.localStorage.getItem("foi.sidebar")).toBe("expanded");
  });

  it("works without storage: the choice simply lasts until the page closes", async () => {
    vi.spyOn(Storage.prototype, "setItem").mockImplementation(() => {
      throw new Error("blocked");
    });
    const user = userEvent.setup();
    shell();
    await user.click(screen.getByRole("button", { name: "Collapse sidebar" }));
    expect(document.querySelector(".shell")).toHaveClass("is-collapsed");
    vi.restoreAllMocks();
  });
});

describe("navigation drawer (small screens)", () => {
  it("opens as a dialog, and choosing a page closes it", async () => {
    const user = userEvent.setup();
    shell();
    await user.click(screen.getByRole("button", { name: "Open navigation" }));
    const drawer = await screen.findByRole("dialog", { name: "Navigation" });
    await user.click(within(drawer).getByRole("link", { name: /Scenarios/ }));
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Scenarios" })).toBeInTheDocument();
  });
});

describe("account menu", () => {
  it("shows who is signed in, says a demo copy is private, and logs out", async () => {
    const calls = serve({ "POST /api/auth/logout": () => new Response(null, { status: 204 }) });
    const user = userEvent.setup();
    shell();
    await user.click(screen.getByRole("button", { name: "Account: Demo family" }));
    expect(await screen.findByText(/Demo copy: private to you/)).toBeInTheDocument();
    await user.click(screen.getByRole("menuitem", { name: "Log out" }));
    await vi.waitFor(() => expect(calls.some((c) => c.method === "POST" && c.path === "/api/auth/logout")).toBe(true));
  });
});
