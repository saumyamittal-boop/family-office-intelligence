import { screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import axe from "axe-core";
import { afterEach, describe, expect, it, vi } from "vitest";
import App from "./App";
import { analysis, META, session } from "./test/fixtures";
import { json, renderWithProviders, serve } from "./test/render";

/**
 * Automated WCAG checks (axe-core) on the screens a person actually sees. Colour contrast cannot be computed
 * without a real layout engine, so it is checked separately: tokens in styles/contrast.test.ts, and in a real browser.
 */
async function audit(root: Element = document.body): Promise<string[]> {
  const result = await axe.run(root, {
    runOnly: { type: "tag", values: ["wcag2a", "wcag2aa", "wcag21a", "wcag21aa", "wcag22aa", "best-practice"] },
    rules: { "color-contrast": { enabled: false } },
  });
  return result.violations.map((v) => `${v.id}: ${v.help} -> ${v.nodes.map((n) => n.target.join(" ")).join(" | ")}`);
}

describe("the audit itself", () => {
  it("catches real problems, so a clean result means something", async () => {
    const { container } = renderWithProviders(
      <main>
        <h1>Page</h1>
        <button />
        <img src="chart.png" />
        <input />
        <div role="img" />
      </main>,
    );
    const found = (await audit(container)).join("\n");
    for (const rule of ["button-name", "image-alt", "label", "role-img-alt"]) expect(found).toContain(rule);
  });
});

const PROFILES = [{ id: 1, name: "Gap family", corpus_cr: 1000 }];
const signedIn = () =>
  serve({
    "GET /api/auth/me": json(session),
    "GET /api/meta": json(META),
    "GET /api/profiles": json(PROFILES),
    "GET /api/profiles/1/analysis": json(analysis()),
  });

afterEach(() => vi.unstubAllGlobals());

describe.each(["light", "dark"] as const)("accessibility in the %s theme", (theme) => {
  const setTheme = () => {
    window.localStorage.setItem("foi.theme", theme);
  };

  it("sign-in screen", async () => {
    setTheme();
    serve({ "GET /api/auth/me": json({ detail: "Please sign in." }, 401), "GET /api/meta": json(META) });
    renderWithProviders(<App />);
    await screen.findByRole("button", { name: "Log in" });
    expect(document.documentElement).toHaveAttribute("data-theme", theme);
    expect(await audit()).toEqual([]);
  });

  it("sign-in screen showing a server error", async () => {
    setTheme();
    const user = userEvent.setup();
    serve({
      "GET /api/auth/me": json({ detail: "Please sign in." }, 401),
      "GET /api/meta": json(META),
      "POST /api/auth/login": json({ detail: "Wrong username or password.", problems: null }, 401),
    });
    renderWithProviders(<App />);
    await user.type(await screen.findByLabelText("Username"), "asha");
    await user.type(screen.getByLabelText("Password"), "whatever-it-is");
    await user.click(screen.getByRole("button", { name: "Log in" }));
    await screen.findByRole("alert");
    expect(await audit()).toEqual([]);
  });

  it("overview with every chart as a picture", async () => {
    setTheme();
    signedIn();
    renderWithProviders(<App />);
    await screen.findByText("8.8%");
    expect(await audit()).toEqual([]);
  });

  it("overview with every chart as a table", async () => {
    setTheme();
    const user = userEvent.setup();
    signedIn();
    renderWithProviders(<App />);
    await screen.findByText("8.8%");
    for (const toggle of screen.getAllByRole("radio", { name: "Table" })) await user.click(toggle);
    expect(screen.queryByRole("img")).not.toBeInTheDocument();
    expect(await audit()).toEqual([]);
  });

  it("overview with the explanation panel open", async () => {
    setTheme();
    const user = userEvent.setup();
    signedIn();
    renderWithProviders(<App />);
    await user.click(await screen.findByRole("button", { name: "About Expected return" }));
    await screen.findByRole("dialog", { name: "Expected return" });
    expect(await audit()).toEqual([]);
  });

  it("navigation drawer", async () => {
    setTheme();
    const user = userEvent.setup();
    signedIn();
    renderWithProviders(<App />);
    await user.click(await screen.findByRole("button", { name: "Open navigation" }));
    const drawer = await screen.findByRole("dialog", { name: "Navigation" });
    expect(within(drawer).getByRole("navigation", { name: "Main" })).toBeInTheDocument();
    expect(await audit()).toEqual([]);
  });

  it("loading, failure and placeholder pages", async () => {
    setTheme();
    serve({
      "GET /api/auth/me": json(session),
      "GET /api/meta": json(META),
      "GET /api/profiles": json(PROFILES),
      "GET /api/profiles/1/analysis": json({ detail: "This profile can't be analysed yet.", problems: null }, 422),
    });
    const { unmount } = renderWithProviders(<App />);
    await screen.findByRole("alert");
    expect(await audit()).toEqual([]);
    unmount();

    signedIn();
    renderWithProviders(<App />, "/holdings");
    await waitFor(() => expect(screen.getByText("Not built yet")).toBeInTheDocument());
    expect(await audit()).toEqual([]);
  });
});
