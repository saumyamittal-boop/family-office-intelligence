import { screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";
import App from "../App";
import type { PlanAnswers } from "../api/client";
import { analysis, META, session } from "../test/fixtures";
import { audit } from "../test/axe";
import { CONFIG, SAVED, previewFor, strategiesFor } from "../test/planFixtures";
import { json, jsonBy, renderWithProviders, serve } from "../test/render";

const SLOW = { timeout: 5000 };

function signedIn() {
  return serve({
    "GET /api/auth/me": json(session),
    "GET /api/meta": json(META),
    "GET /api/profiles": json([{ id: 1, name: "Gap family", corpus_cr: 1000 }]),
    "GET /api/profiles/1/analysis": json(analysis()),
    "GET /api/plan/config": json(CONFIG),
    "POST /api/plan/preview": jsonBy<PlanAnswers>(previewFor),
    "POST /api/plan/strategies": jsonBy<PlanAnswers>(strategiesFor),
    "POST /api/plan/save": json(SAVED, 201),
  });
}

async function next(user: ReturnType<typeof userEvent.setup>, label = "Continue") {
  const button = await screen.findByRole("button", { name: label });
  await waitFor(() => expect(button).toBeEnabled(), SLOW);
  await user.click(button);
}

afterEach(() => vi.unstubAllGlobals());

describe.each(["light", "dark"] as const)("the plan is accessible in the %s theme", (theme) => {
  it("every question step passes the automated audit, including with commitment rows and a validation problem", async () => {
    window.localStorage.setItem("foi.theme", theme);
    signedIn();
    const user = userEvent.setup();
    renderWithProviders(<App />, "/plan");
    expect(await screen.findByRole("heading", { name: "Tell us about the family" }, SLOW)).toBeInTheDocument();
    expect(document.documentElement).toHaveAttribute("data-theme", theme);
    expect((await audit()).join(" | ")).toBe("");

    await next(user);
    await screen.findByRole("heading", { name: "Anything big coming up?" });
    await user.click(screen.getByRole("button", { name: "Add a commitment" }));
    await user.click(screen.getByRole("button", { name: "Add your own expense" }));
    expect(screen.getByLabelText("Name this expense")).toBeInTheDocument();
    expect((await audit()).join(" | ")).toBe("");
    await user.click(screen.getByRole("button", { name: "Remove commitment 2" }));
    await user.click(screen.getByRole("button", { name: "Remove commitment 1" }));

    await next(user);
    await screen.findByRole("heading", { name: "How do you feel about a bad year?" });
    expect((await audit()).join(" | ")).toBe("");

    await next(user);
    await screen.findByRole("heading", { name: "Your safety net" });
    expect((await audit()).join(" | ")).toBe("");

    await next(user);
    await screen.findByRole("heading", { name: "What does the family own today?" });
    const illiquid = await screen.findByRole("textbox", { name: /Property, business and other holdings/ }, SLOW);
    expect((await audit()).join(" | ")).toBe("");
    await user.clear(illiquid);
    await user.type(illiquid, "5000");
    await within(screen.getByRole("complementary", { name: "Live read-out" })).findByText(/At least 5% of the wealth/, {}, SLOW);
    expect((await audit()).join(" | ")).toBe(""); // with the problem banner showing
  }, 40000);

  it("the results pass the audit as pictures, as tables, and after saving", async () => {
    window.localStorage.setItem("foi.theme", theme);
    signedIn();
    const user = userEvent.setup();
    renderWithProviders(<App />, "/plan");
    await screen.findByRole("heading", { name: "Tell us about the family" }, SLOW);
    for (const label of ["Continue", "Continue", "Continue", "Continue", "See my strategies"]) await next(user, label);
    await screen.findByRole("heading", { name: /Three ways to run/ }, { timeout: 8000 });
    expect((await audit()).join(" | ")).toBe("");

    for (const toggle of screen.getAllByRole("radio", { name: "Table" })) await user.click(toggle);
    expect((await audit()).join(" | ")).toBe("");

    await user.click(screen.getByRole("button", { name: /Save Strategy B to my profiles/ }));
    await screen.findByText("Saved.");
    expect((await audit()).join(" | ")).toBe("");
  }, 60000);
});
