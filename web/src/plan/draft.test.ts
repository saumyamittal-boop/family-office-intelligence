import { describe, expect, it, vi } from "vitest";
import { CONFIG } from "../test/planFixtures";
import {
  clearDraft, clearFreshSignup, defaultAnswers, isFreshSignup, markFreshSignup, readDraft, writeDraft,
} from "./draft";

const KEY = "foi.plan.draft";
const good = {
  answers: { name: "Sharma family", wealth: 250, spending: 6, risk: "Grow", months: 24, commitments: [{ kind: "Wedding", year: 2, amount_cr: 8 }], amounts: { Debt: 50 } },
  furthest: 4,
};

describe("the plan draft (kept in this tab only)", () => {
  it("starts from the form's defaults when nothing is saved", () => {
    expect(readDraft(CONFIG)).toEqual({ answers: defaultAnswers(CONFIG), furthest: 1 });
    expect(defaultAnswers(CONFIG)).toMatchObject({ name: "My family", wealth: 100, spending: 3, risk: "Balance", months: 12, commitments: [], amounts: null });
  });

  it("restores exactly what was written", () => {
    writeDraft(good as never);
    expect(readDraft(CONFIG)).toEqual(good);
  });

  it("is kept in session storage, so it is gone when the tab closes and never in local storage", () => {
    writeDraft(good as never);
    expect(window.sessionStorage.getItem(KEY)).not.toBeNull();
    expect(window.localStorage.getItem(KEY)).toBeNull();
  });

  it.each([
    ["text that is not JSON", "not json"],
    ["null", "null"],
    ["an array", "[]"],
    ["an empty object", "{}"],
    ["answers with the wrong types", JSON.stringify({ answers: { name: 5, wealth: "x", spending: 1, months: 12, risk: "Balance" }, furthest: 2 })],
    ["an unknown comfort level", JSON.stringify({ ...good, answers: { ...good.answers, risk: "Reckless" } })],
    ["too many commitments", JSON.stringify({ ...good, answers: { ...good.answers, commitments: Array(4).fill(good.answers.commitments[0]) } })],
    ["a malformed commitment", JSON.stringify({ ...good, answers: { ...good.answers, commitments: [{ kind: "Wedding", year: "soon" }] } })],
    ["amounts that are not numbers", JSON.stringify({ ...good, answers: { ...good.answers, amounts: { Debt: "lots" } } })],
  ])("falls back to a clean form for %s instead of restoring something broken", (_name, stored) => {
    window.sessionStorage.setItem(KEY, stored);
    expect(readDraft(CONFIG)).toEqual({ answers: defaultAnswers(CONFIG), furthest: 1 });
  });

  it("keeps the furthest step inside the real range", () => {
    window.sessionStorage.setItem(KEY, JSON.stringify({ ...good, furthest: 99 }));
    expect(readDraft(CONFIG).furthest).toBe(6);
    window.sessionStorage.setItem(KEY, JSON.stringify({ ...good, furthest: -3 }));
    expect(readDraft(CONFIG).furthest).toBe(1);
    window.sessionStorage.setItem(KEY, JSON.stringify({ ...good, furthest: "far" }));
    expect(readDraft(CONFIG).furthest).toBe(1);
  });

  it("clearing removes it", () => {
    writeDraft(good as never);
    clearDraft();
    expect(readDraft(CONFIG).furthest).toBe(1);
  });

  it("works when the browser blocks storage: reads give a clean form and writes never throw", () => {
    const blocked = () => {
      throw new Error("blocked");
    };
    vi.spyOn(Storage.prototype, "getItem").mockImplementation(blocked);
    vi.spyOn(Storage.prototype, "setItem").mockImplementation(blocked);
    vi.spyOn(Storage.prototype, "removeItem").mockImplementation(blocked);
    expect(readDraft(CONFIG).furthest).toBe(1);
    expect(() => writeDraft(good as never)).not.toThrow();
    expect(() => clearDraft()).not.toThrow();
    expect(isFreshSignup()).toBe(false);
    expect(() => markFreshSignup()).not.toThrow();
    expect(() => clearFreshSignup()).not.toThrow();
    vi.restoreAllMocks();
  });
});

describe("landing a brand-new account on the plan", () => {
  it("is marked once and cleared once", () => {
    expect(isFreshSignup()).toBe(false);
    markFreshSignup();
    expect(isFreshSignup()).toBe(true);
    expect(isFreshSignup()).toBe(true); // reading does not consume it, so a re-render cannot lose it
    clearFreshSignup();
    expect(isFreshSignup()).toBe(false);
  });
});
