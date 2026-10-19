import { screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";
import App from "../App";
import type { ProfileFull, ProfileInput } from "../api/client";
import { analysis } from "../test/fixtures";
import { appRoutes, PROFILE } from "../test/phase4Fixtures";
import { json, jsonBy, renderWithProviders, serve } from "../test/render";

afterEach(() => vi.unstubAllGlobals());

type Summary = { id: number; name: string; corpus_cr: number };

/** A server that remembers: the list of profiles changes as the page creates, saves and deletes them. */
function profileServer(initial: Summary[] = [{ id: 1, name: "Gap family", corpus_cr: 1000 }]) {
  let list = [...initial];
  let nextId = 10;
  const full = new Map<number, ProfileFull>([[1, PROFILE]]);
  const routes = appRoutes(analysis(), {
    "GET /api/profiles": () => new Response(JSON.stringify(list)),
    "GET /api/profiles/1": () => new Response(JSON.stringify(full.get(1))),
    "PUT /api/profiles/1": jsonBy<ProfileInput>((body) => {
      const saved = { ...body, id: 1 } as ProfileFull;
      full.set(1, saved);
      list = list.map((p) => (p.id === 1 ? { id: 1, name: body.name, corpus_cr: body.corpus_cr } : p));
      return saved;
    }),
    "POST /api/profiles": (init) => {
      const body = JSON.parse(String(init?.body)) as ProfileInput;
      const created = { ...body, id: nextId++ } as ProfileFull;
      full.set(created.id, created);
      list = [...list, { id: created.id, name: body.name, corpus_cr: body.corpus_cr }];
      return new Response(JSON.stringify(created), { status: 201 });
    },
    "DELETE /api/profiles/1": () => {
      list = list.filter((p) => p.id !== 1);
      return new Response(null, { status: 204 });
    },
  });
  for (const id of [10, 11]) routes[`GET /api/profiles/${id}`] = () => new Response(JSON.stringify(full.get(id)));
  return routes;
}

async function openProfile(routes = profileServer(), path = "/profile") {
  const calls = serve(routes);
  renderWithProviders(<App />, path);
  await screen.findByRole("heading", { level: 1, name: "Family profile" });
  await screen.findByLabelText("Profile name");
  return calls;
}

const numberBox = (label: RegExp | string) => screen.getByRole("textbox", { name: label }) as HTMLInputElement;
const saveButton = () => screen.getByRole("button", { name: /Save changes|Saving…/ });
const puts = (calls: ReturnType<typeof serve>) => calls.filter((c) => c.method === "PUT");

async function replace(user: ReturnType<typeof userEvent.setup>, label: RegExp | string, text: string) {
  const box = numberBox(label);
  await user.clear(box);
  if (text) await user.type(box, text);
}

describe("the Family profile page", () => {
  it("lists the account's profiles and fills the form from the chosen one, in the units people use", async () => {
    await openProfile();
    expect(within(screen.getByRole("navigation", { name: "Your family profiles" })).getByRole("button", { name: /Gap family/ })).toHaveAttribute("aria-current", "true");
    expect((screen.getByLabelText("Profile name") as HTMLInputElement).value).toBe("Gap family");
    expect(numberBox(/Total corpus/).value).toBe("1000");
    expect(numberBox(/Largest fall you can sit through/).value).toBe("15"); // 0.15 shown as a percent
    expect(numberBox(/^Large-cap equity \(%\)$/).value).toBe("55");
    expect(numberBox(/Illiquid \(held fixed\)/).value).toBe("40");
    expect(screen.getByText(/Total: 100\.0%/)).toBeInTheDocument();
    expect(numberBox(/Outflow 1: amount/).value).toBe("100");
  });

  it("tells a demo family's visitor the changes stay in their private copy", async () => {
    await openProfile();
    expect(screen.getByText(/private copy of a demo family/)).toBeInTheDocument();
  });

  it("keeps Save off until something changes, then saves the edit with the CSRF token", async () => {
    const user = userEvent.setup();
    const calls = await openProfile();
    expect(saveButton()).toBeDisabled();
    await replace(user, /Total corpus/, "1200");
    expect(saveButton()).toBeEnabled();
    await user.click(saveButton());

    await waitFor(() => expect(puts(calls)).toHaveLength(1));
    const put = puts(calls)[0]!;
    expect(put.path).toBe("/api/profiles/1");
    expect(put.headers["X-CSRF-Token"]).toBe("csrf-abc");
    const sent = JSON.parse(put.body!) as ProfileInput;
    expect(sent.corpus_cr).toBe(1200);
    expect(sent.max_drawdown).toBe(0.15); // back to fractions
    expect(sent.holdings["Large-cap equity"]).toBe(0.55);
    expect(sent.limits["Debt"]).toEqual({ min: 0.1, max: 0.6 });
    expect(sent.one_offs).toEqual([{ year: 1, amount_cr: 100 }]);

    expect(await screen.findByText(/Profile saved\. The dashboard and analysis pages now use these numbers\./)).toBeInTheDocument();
    await waitFor(() => expect(saveButton()).toBeDisabled()); // the saved values are the new starting point
    expect(numberBox(/Total corpus/).value).toBe("1200");
    expect(within(screen.getByRole("navigation", { name: "Your family profiles" })).getByText("₹1,200 Cr")).toBeInTheDocument();
  });

  it("keeps unsaved edits when the window regains focus (a background refetch must not wipe them)", async () => {
    const user = userEvent.setup();
    const calls = await openProfile();
    await replace(user, /Total corpus/, "1200");
    const loads = () => calls.filter((c) => c.method === "GET" && c.path === "/api/profiles/1").length;
    const before = loads();
    window.dispatchEvent(new Event("visibilitychange")); // what returning to the tab does (the query library listens on window)
    await new Promise((resolve) => setTimeout(resolve, 150));
    expect(loads()).toBe(before); // the profile is not re-fetched behind the person's back
    expect(numberBox(/Total corpus/).value).toBe("1200");
    expect(saveButton()).toBeEnabled();
  });

  it("recalculates what depends on the profile after a save", async () => {
    const user = userEvent.setup();
    const calls = await openProfile();
    const analyses = () => calls.filter((c) => c.path.startsWith("/api/profiles/1/analysis")).length;
    await waitFor(() => expect(analyses()).toBeGreaterThan(0)); // fetched when the page opened
    const before = analyses();
    await replace(user, /Total corpus/, "1200");
    await user.click(saveButton());
    await waitFor(() => expect(analyses()).toBeGreaterThan(before)); // the old results were dropped and recomputed
  });

  it("refuses holdings that do not add up, says by how much, and sends nothing", async () => {
    const user = userEvent.setup();
    const calls = await openProfile();
    await replace(user, /^Debt \(%\)$/, "10");
    expect(screen.getByText(/Total: 110\.0% \(needs to be 100%\)/)).toBeInTheDocument();
    const banner = await screen.findByText("One thing to fix before saving:");
    expect(banner.closest(".banner")).toHaveTextContent("Holdings add up to 110.0%. They need to add up to 100%.");
    expect(saveButton()).toBeDisabled();
    expect(puts(calls)).toHaveLength(0);
  });

  it("shows each rule's own message at the box, and lists every problem together", async () => {
    const user = userEvent.setup();
    await openProfile();
    await replace(user, /Total corpus/, "0");
    await replace(user, /Safety net/, "2.5");
    expect(screen.getByText("Must be at least 1.")).toBeInTheDocument();
    expect(screen.getByText("Use a whole number.")).toBeInTheDocument();
    const banner = (await screen.findByText(/things to fix before saving:/)).closest(".banner") as HTMLElement;
    expect(within(banner).getAllByRole("listitem")).toHaveLength(2);
    expect(saveButton()).toBeDisabled();
  });

  it("shows what the server refused if it still says no", async () => {
    const user = userEvent.setup();
    const routes = profileServer();
    routes["PUT /api/profiles/1"] = json({ detail: "Please fix the highlighted problems.", problems: ["Holdings add up to 100.5%. They need to add up to 100%.", "A second problem."] }, 422);
    await openProfile(routes);
    await replace(user, /Total corpus/, "1200");
    await user.click(saveButton());
    const alert = await screen.findByText("The server could not accept this profile.");
    expect(alert.closest(".banner")).toHaveTextContent("A second problem.");
    expect(saveButton()).toBeEnabled(); // the edits are still there to correct
    expect(numberBox(/Total corpus/).value).toBe("1200");
  });

  it("saves the edited form as a separate new profile and switches to it", async () => {
    const user = userEvent.setup();
    const calls = await openProfile();
    await replace(user, /Total corpus/, "800");
    await user.click(screen.getByRole("button", { name: "Save as new profile" }));
    expect(await screen.findByText("Saved as a new profile: Gap family.")).toBeInTheDocument();
    const post = calls.find((c) => c.method === "POST" && c.path === "/api/profiles")!;
    expect(JSON.parse(post.body!).corpus_cr).toBe(800);
    expect(puts(calls)).toHaveLength(0); // the original is untouched
    const list = within(screen.getByRole("navigation", { name: "Your family profiles" }));
    await waitFor(() => expect(list.getAllByRole("button")).toHaveLength(2));
    expect(list.getByText("₹800 Cr")).toBeInTheDocument();
  });

  it("starts a new profile from a neutral template and creates it", async () => {
    const user = userEvent.setup();
    const calls = await openProfile();
    await user.click(screen.getByRole("button", { name: "New profile" }));
    expect(await screen.findByRole("button", { name: "Create profile" })).toBeEnabled();
    expect((screen.getByLabelText("Profile name") as HTMLInputElement).value).toBe("New profile");
    expect(numberBox(/Total corpus/).value).toBe("100");
    expect(screen.getByText("Not saved yet")).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Create profile" }));
    expect(await screen.findByText("Saved as a new profile: New profile.")).toBeInTheDocument();
    const post = calls.find((c) => c.method === "POST" && c.path === "/api/profiles")!;
    expect(JSON.parse(post.body!)).toMatchObject({ name: "New profile", corpus_cr: 100, holdings: expect.objectContaining({ Illiquid: 0.25 }) });
  });

  it("adds and removes planned outflows, up to three", async () => {
    const user = userEvent.setup();
    await openProfile();
    const add = screen.getByRole("button", { name: "Add an outflow" });
    await user.click(add);
    await user.click(add);
    expect(numberBox(/Outflow 3: year/)).toBeInTheDocument();
    expect(add).toBeDisabled();
    expect(screen.getByText(/That is the most the model takes/)).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Remove outflow 2" }));
    expect(screen.queryByRole("textbox", { name: /Outflow 3: year/ })).not.toBeInTheDocument();
    expect(add).toBeEnabled();
  });

  it("catches an outflow outside the horizon", async () => {
    const user = userEvent.setup();
    await openProfile();
    await replace(user, /Outflow 1: year/, "40");
    expect(screen.getByText("Must be at most 15.")).toBeInTheDocument();
    expect(saveButton()).toBeDisabled();
  });

  it("will not delete the only profile", async () => {
    await openProfile();
    expect(screen.getByRole("button", { name: "Delete profile" })).toBeDisabled();
    expect(screen.getByText("This is your only profile.")).toBeInTheDocument();
  });

  it("asks before deleting, and deleting switches to what is left", async () => {
    const user = userEvent.setup();
    const routes = profileServer([{ id: 1, name: "Gap family", corpus_cr: 1000 }, { id: 11, name: "Second family", corpus_cr: 400 }]);
    routes["GET /api/profiles/11"] = json({ ...PROFILE, id: 11, name: "Second family", corpus_cr: 400 });
    const calls = await openProfile(routes);
    await user.click(screen.getByRole("button", { name: "Delete profile" }));
    expect(screen.getByText("Delete “Gap family”?")).toBeInTheDocument();
    expect(calls.some((c) => c.method === "DELETE")).toBe(false); // nothing happens until confirmed
    await user.click(screen.getByRole("button", { name: "Keep it" }));
    expect(screen.queryByText("Delete “Gap family”?")).not.toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "Delete profile" }));
    await user.click(screen.getByRole("button", { name: "Yes, delete it" }));
    expect(await screen.findByText("Profile deleted.")).toBeInTheDocument();
    const del = calls.find((c) => c.method === "DELETE")!;
    expect(del.path).toBe("/api/profiles/1");
    expect(del.headers["X-CSRF-Token"]).toBe("csrf-abc");
    await waitFor(() => expect((screen.getByLabelText("Profile name") as HTMLInputElement).value).toBe("Second family"));
  });

  it("says so, with a retry, when a profile cannot be loaded", async () => {
    const routes = profileServer();
    routes["GET /api/profiles/1"] = json({ detail: "Profile not found.", problems: null }, 404);
    serve(routes);
    renderWithProviders(<App />, "/profile");
    expect(await screen.findByText("Can't load this profile")).toBeInTheDocument();
    expect(screen.getByText("Profile not found.")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Try again" })).toBeInTheDocument();
  });
});
