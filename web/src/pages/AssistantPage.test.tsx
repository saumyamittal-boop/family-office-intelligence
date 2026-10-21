import { screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";
import App from "../App";
import { answerReply, assistantApp, clarifyReply, liquidityAnswer, outOfScopeReply, refusalReply } from "../test/explainFixtures";
import { json, renderWithProviders, serve } from "../test/render";

type Calls = ReturnType<typeof serve>;
const asks = (calls: Calls) => calls.filter((c) => c.method === "POST" && c.path === "/api/profiles/1/explain").map((c) => JSON.parse(c.body!) as Record<string, unknown>);

async function openAssistant(reply?: Parameters<typeof assistantApp>[0], route = "/assistant") {
  const calls = serve(assistantApp(reply));
  renderWithProviders(<App />, route);
  await screen.findByRole("heading", { level: 1, name: "Assistant" });
  await screen.findByRole("button", { name: "Is my liquidity enough?" });
  return calls;
}

describe("the Assistant page", () => {
  it("opens with a plain statement of what it does and does not do, the question box and the starter questions", async () => {
    await openAssistant();
    expect(screen.getByText(/I don.t predict markets, pick investments or tell you what to buy or sell/)).toBeInTheDocument();
    expect(screen.getByRole("textbox", { name: "Your question" })).toHaveAttribute("maxlength", "300");
    expect(screen.getByText(/Your question is not stored/)).toBeInTheDocument();
    for (const group of ["My mix", "Liquidity", "Risk", "About the model"]) expect(screen.getByRole("group", { name: group })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Ask" })).toBeDisabled(); // nothing typed yet
  });

  it("is a normal page in the menu now, with no 'Soon' tag", async () => {
    await openAssistant();
    const nav = screen.getByRole("navigation", { name: "Main" });
    const link = within(nav).getByRole("link", { name: /Assistant/ });
    expect(link).toHaveAttribute("aria-current", "page");
    expect(link.textContent).not.toMatch(/Soon/);
    expect(screen.queryByText("Not built yet")).not.toBeInTheDocument();
  });
});

describe("asking a question from the list", () => {
  it("sends the chosen question type, not text, and shows the layered answer", async () => {
    const user = userEvent.setup();
    const calls = await openAssistant();
    await user.click(screen.getByRole("button", { name: "Is my liquidity enough?" }));

    const answer = await screen.findByRole("article", { name: "Is my liquidity enough?" });
    expect(asks(calls)).toEqual([{ intent: "liquidity_enough", slots: {}, basis: "strict" }]);
    const sent = calls.find((c) => c.path.endsWith("/explain") && c.method === "POST")!;
    expect(sent.headers["X-CSRF-Token"]).toBe("csrf-abc");
    expect(within(answer).getByText(/Over the next 24 months your planned outflows come to ₹120 Cr/)).toBeInTheDocument();
    expect(within(answer).getByRole("heading", { name: "What this means" })).toBeInTheDocument();
    expect(within(answer).getByText("In the model’s own words, unchanged.")).toBeInTheDocument();
    expect(within(answer).getByRole("table", { name: "Liquidity ladder: the first years" })).toBeInTheDocument();
    expect(within(answer).getByText("This is an illustrative simulation on synthetic data. It is not investment advice.")).toBeInTheDocument();
    expect(within(answer).getByRole("link", { name: "See it on Risk and liquidity" })).toHaveAttribute("href", "/risk");
  });

  it("passes a chip's parameters along", async () => {
    const user = userEvent.setup();
    const calls = await openAssistant();
    await user.click(screen.getByRole("button", { name: "How would a market crash affect me?" }));
    await waitFor(() => expect(asks(calls)).toHaveLength(1));
    expect(asks(calls)[0]).toEqual({ intent: "scenario_loss", slots: { scenario: "Market crash" }, basis: "strict" });
  });

  it("lists every figure with where it comes from, and says which were worked out", async () => {
    const user = userEvent.setup();
    await openAssistant();
    await user.click(screen.getByRole("button", { name: "Is my liquidity enough?" }));
    const answer = await screen.findByRole("article", { name: "Is my liquidity enough?" });
    await user.click(within(answer).getByText(/Show the evidence \(4 figures\)/));
    const table = within(within(answer).getByRole("table", { name: "Figures used in this answer and where each comes from" }));
    expect(table.getByRole("row", { name: /Outflows to be covered.*₹120 Cr.*Risk and liquidity.*current\.required_cover_cr/ })).toBeInTheDocument();
    expect(table.getByRole("row", { name: /Cover.*3\.9x.*Worked out from.*current\.available_cover_cr/ })).toBeInTheDocument();
  });

  it("offers the next questions, and asking one replaces the answer", async () => {
    const user = userEvent.setup();
    const calls = await openAssistant((body) =>
      body.intent === "cover_basis" ? answerReply({ intent: "cover_basis" }, { intent: "cover_basis", title: "What counts towards the liquidity cover", lead: "The safety-net check counts the assets that can be turned into cash in time.", follow_ups: [], tables: [], figures: [] }) : answerReply(),
    );
    await user.click(screen.getByRole("button", { name: "Is my liquidity enough?" }));
    const first = await screen.findByRole("article", { name: "Is my liquidity enough?" });
    await user.click(within(first).getByRole("button", { name: "What counts towards the cover?" }));
    expect(await screen.findByRole("article", { name: "What counts towards the liquidity cover" })).toBeInTheDocument();
    expect(screen.queryByRole("article", { name: "Is my liquidity enough?" })).not.toBeInTheDocument();
    expect(asks(calls).map((a) => a.intent)).toEqual(["liquidity_enough", "cover_basis"]);
  });
});

describe("asking in your own words", () => {
  it("sends the question in the request body only, never in the address", async () => {
    const user = userEvent.setup();
    const calls = await openAssistant();
    const box = screen.getByRole("textbox", { name: "Your question" });
    await user.type(box, "is my liquidity enough?");
    await user.click(screen.getByRole("button", { name: "Ask" }));

    await screen.findByRole("article", { name: "Is my liquidity enough?" });
    expect(asks(calls)).toEqual([{ question: "is my liquidity enough?", slots: {}, basis: "strict" }]);
    expect(calls.every((c) => !c.path.includes("liquidity"))).toBe(true); // no request carries the question in its address
    expect(window.location.href).not.toContain("liquidity");
  });

  it("submits with the Enter key and ignores a question that is only spaces", async () => {
    const user = userEvent.setup();
    const calls = await openAssistant();
    const box = screen.getByRole("textbox", { name: "Your question" });
    await user.type(box, "   {Enter}");
    expect(asks(calls)).toHaveLength(0);
    await user.clear(box);
    await user.type(box, "what is cvar{Enter}");
    await screen.findByRole("article");
    expect(asks(calls)).toHaveLength(1);
  });

  it("offers the nearest other questions in case the answer was not what was meant", async () => {
    const user = userEvent.setup();
    const calls = await openAssistant((body) => (body.question ? answerReply({ confidence: 0.6, suggestions: [{ intent: "cover_basis", label: "What counts towards the cover?", slots: {} }] }) : answerReply({ intent: "cover_basis" }, { title: "What counts towards the liquidity cover", follow_ups: [] })));
    await user.type(screen.getByRole("textbox", { name: "Your question" }), "liquidity please");
    await user.click(screen.getByRole("button", { name: "Ask" }));
    const group = await screen.findByRole("group", { name: "Not what you meant? Try one of these" });
    await user.click(within(group).getByRole("button", { name: "What counts towards the cover?" }));
    await waitFor(() => expect(asks(calls)).toHaveLength(2));
    expect(asks(calls)[1]).toMatchObject({ intent: "cover_basis" });
  });

  it("says plainly that it will not give advice, and points to what it can do", async () => {
    const user = userEvent.setup();
    const calls = await openAssistant(() => refusalReply);
    await user.type(screen.getByRole("textbox", { name: "Your question" }), "which fund should I buy");
    await user.click(screen.getByRole("button", { name: "Ask" }));
    const banner = (await screen.findByText("Outside what I do.")).closest(".banner") as HTMLElement;
    expect(banner).toHaveTextContent("I can't tell you what to buy, sell or choose");
    expect(screen.queryByRole("article")).not.toBeInTheDocument();
    const chips = screen.getByRole("group", { name: "Questions you can ask" });
    await userEvent.setup().click(within(chips).getByRole("button", { name: "How do the mixes compare?" }));
    await waitFor(() => expect(asks(calls)).toHaveLength(2));
  });

  it("asks which one was meant when it is not sure", async () => {
    const user = userEvent.setup();
    await openAssistant(() => clarifyReply);
    await user.type(screen.getByRole("textbox", { name: "Your question" }), "liquid");
    await user.click(screen.getByRole("button", { name: "Ask" }));
    expect(await screen.findByText("Which did you mean?")).toBeInTheDocument();
    const chips = screen.getByRole("group", { name: "Questions you can ask" });
    expect(within(chips).getAllByRole("button").map((b) => b.textContent)).toEqual(["Is my liquidity enough?", "What counts towards the cover?"]);
  });

  it("admits when it cannot match the question", async () => {
    const user = userEvent.setup();
    await openAssistant(() => outOfScopeReply);
    await user.type(screen.getByRole("textbox", { name: "Your question" }), "who won the match");
    await user.click(screen.getByRole("button", { name: "Ask" }));
    expect(await screen.findByText("No match.")).toBeInTheDocument();
  });

  it("shows the server's reason when it cannot answer, and keeps the list usable", async () => {
    const user = userEvent.setup();
    await openAssistant(() => new Response(JSON.stringify({ detail: "This profile can't be analysed yet: it needs some yearly spending.", problems: null }), { status: 422 }));
    await user.click(screen.getByRole("button", { name: "Is my liquidity enough?" }));
    const alert = await screen.findByRole("alert");
    expect(alert).toHaveTextContent("can't be analysed yet");
    expect(screen.getByRole("button", { name: "What can I ask?" })).toBeEnabled();
  });

  it("disables the buttons while an answer is on its way", async () => {
    const user = userEvent.setup();
    let release: () => void = () => {};
    const gate = new Promise<void>((resolve) => (release = resolve));
    const calls = serve({
      ...assistantApp(),
      "POST /api/profiles/1/explain": async () => {
        await gate;
        return new Response(JSON.stringify(answerReply()));
      },
    });
    renderWithProviders(<App />, "/assistant");
    await screen.findByRole("button", { name: "Is my liquidity enough?" });
    await user.click(screen.getByRole("button", { name: "Is my liquidity enough?" }));
    expect(await screen.findByText("Working it out")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "What can I ask?" })).toBeDisabled();
    release();
    await screen.findByRole("article");
    expect(asks(calls)).toHaveLength(1);
  });
});

describe("links into the Assistant", () => {
  it("asks a question named in the address once, then removes it from the address", async () => {
    const calls = await openAssistant(undefined, "/assistant?intent=liquidity_enough&option=Growth&profile=1");
    await screen.findByRole("article", { name: "Is my liquidity enough?" });
    expect(asks(calls)).toEqual([{ intent: "liquidity_enough", slots: { option: "Growth" }, basis: "strict" }]);
    await new Promise((r) => setTimeout(r, 50));
    expect(asks(calls)).toHaveLength(1); // not asked again on the next render
  });

  it("keeps the family and basis in its own links", async () => {
    const user = userEvent.setup();
    await openAssistant(undefined, "/assistant?profile=1&basis=strict");
    await user.click(screen.getByRole("button", { name: "Is my liquidity enough?" }));
    const answer = await screen.findByRole("article");
    expect(within(answer).getByRole("link", { name: "See it on Risk and liquidity" }).getAttribute("href")).toBe("/risk?profile=1&basis=strict");
  });

  it("answers for the basis in the address, and the app's default when there is none", async () => {
    const user = userEvent.setup();
    const calls = await openAssistant(undefined, "/assistant?basis=all");
    await user.click(screen.getByRole("button", { name: "Is my liquidity enough?" }));
    await screen.findByRole("article");
    expect(asks(calls)[0]!.basis).toBe("all");
  });
});

describe("the Why? buttons", () => {
  it("open the same answer beside a warning, without leaving the page", async () => {
    const user = userEvent.setup();
    const calls = serve(assistantApp());
    renderWithProviders(<App />, "/");
    const warnings = await screen.findByRole("region", { name: "Needs your attention" });
    await user.click(within(warnings).getByRole("button", { name: /^Why\? Liquidity shortfall/ }));

    const panel = await screen.findByRole("dialog");
    expect(await within(panel).findByText(/Over the next 24 months your planned outflows come to ₹120 Cr/)).toBeInTheDocument();
    expect(asks(calls)).toEqual([{ intent: "liquidity_enough", slots: {}, basis: "strict" }]);
    expect(within(panel).getByRole("link", { name: "Ask something else" })).toHaveAttribute("href", "/assistant");
    expect(screen.getByRole("region", { name: "Needs your attention", hidden: true })).toBeInTheDocument(); // the page behind is unchanged (and inert while the panel is open)
  });

  it("let you carry on asking inside the panel", async () => {
    const user = userEvent.setup();
    const calls = serve(assistantApp());
    renderWithProviders(<App />, "/");
    const warnings = await screen.findByRole("region", { name: "Needs your attention" });
    await user.click(within(warnings).getByRole("button", { name: /^Why\? Liquidity shortfall/ }));
    const panel = await screen.findByRole("dialog");
    await user.click(await within(panel).findByRole("button", { name: "What counts towards the cover?" }));
    await waitFor(() => expect(asks(calls).map((a) => a.intent)).toEqual(["liquidity_enough", "cover_basis"]));
  });

  it("are also offered under 'About this number'", async () => {
    const user = userEvent.setup();
    const calls = serve(assistantApp());
    renderWithProviders(<App />, "/");
    await screen.findByRole("region", { name: "Needs your attention" });
    await user.click(screen.getAllByRole("button", { name: /^About Liquidity cover/ })[0]!);
    const panel = await screen.findByRole("dialog");
    await user.click(within(panel).getByRole("button", { name: "Ask the assistant about my liquidity" }));
    await waitFor(() => expect(asks(calls)).toEqual([{ intent: "liquidity_enough", slots: {}, basis: "strict" }]));
    expect(await screen.findByText(/Over the next 24 months/)).toBeInTheDocument();
  });

  it("show the server's reason in the panel if it cannot answer", async () => {
    const user = userEvent.setup();
    serve(assistantApp(() => new Response(json({ detail: "The allocation model is busy. Please try again in a minute.", problems: null }) ().body, { status: 503 })));
    renderWithProviders(<App />, "/");
    const warnings = await screen.findByRole("region", { name: "Needs your attention" });
    await user.click(within(warnings).getByRole("button", { name: /^Why\? Liquidity shortfall/ }));
    const panel = await screen.findByRole("dialog");
    expect(await within(panel).findByText(/allocation model is busy/)).toBeInTheDocument();
  });
});

describe("the answer view with nothing special", () => {
  it("copes with an answer that has no tables, figures, links or follow-ups", async () => {
    const user = userEvent.setup();
    await openAssistant(() => answerReply({}, liquidityAnswer({ tables: [], figures: [], links: [], follow_ups: [], sections: [], notes: ["Showing the Balanced mix because the question did not name one."] })));
    await user.click(screen.getByRole("button", { name: "Is my liquidity enough?" }));
    const answer = await screen.findByRole("article");
    expect(within(answer).queryByText(/Show the evidence/)).not.toBeInTheDocument();
    expect(within(answer).getByText("Showing the Balanced mix because the question did not name one.")).toBeInTheDocument();
  });
});
