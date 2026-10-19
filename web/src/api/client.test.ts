import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { api, ApiError, setCsrf } from "./client";

function reply(status: number, body: unknown) {
  return Promise.resolve(new Response(body === undefined ? null : JSON.stringify(body), { status }));
}

describe("api client", () => {
  const fetchMock = vi.fn();
  beforeEach(() => {
    vi.stubGlobal("fetch", fetchMock);
    setCsrf("token-123");
  });
  afterEach(() => {
    fetchMock.mockReset();
    vi.unstubAllGlobals();
  });

  it("sends the CSRF header on writes but not on reads", async () => {
    fetchMock.mockImplementation(() => reply(200, {}));
    await api.profiles();
    await api.login("asha", "pass-pass");
    const [read = {}, write = {}] = fetchMock.mock.calls.map(([, init]) => init.headers as Record<string, string>);
    expect(read).not.toHaveProperty("X-CSRF-Token");
    expect(write["X-CSRF-Token"]).toBe("token-123");
    expect(write["Content-Type"]).toBe("application/json");
  });

  it("sends cookies only to its own origin and never puts credentials in the URL", async () => {
    fetchMock.mockImplementation(() => reply(200, {}));
    await api.login("asha", "s3cret-pass");
    const [url, init] = fetchMock.mock.calls[0] ?? [];
    expect(url).toBe("/api/auth/login");
    expect(init.credentials).toBe("same-origin");
    expect(String(url)).not.toContain("s3cret");
  });

  it("turns server problems into an ApiError with the server's words", async () => {
    fetchMock.mockImplementation(() => reply(422, { detail: "Please fix the highlighted problems.", problems: ["Holdings add up to 90.0%."] }));
    await expect(api.signup("x", "y")).rejects.toMatchObject({
      name: "ApiError", status: 422, message: "Please fix the highlighted problems.", problems: ["Holdings add up to 90.0%."],
    });
  });

  it("reports an unreachable server in plain words", async () => {
    fetchMock.mockImplementation(() => Promise.reject(new TypeError("fetch failed")));
    const error = await api.profiles().catch((e) => e);
    expect(error).toBeInstanceOf(ApiError);
    expect(error.status).toBe(0);
    expect(error.message).toMatch(/Can't reach the server/);
  });

  it("copes with an empty 204 and with a non-JSON error body", async () => {
    fetchMock.mockImplementationOnce(() => reply(204, undefined));
    await expect(api.logout()).resolves.toBeUndefined();
    fetchMock.mockImplementationOnce(() => Promise.resolve(new Response("<html>bad gateway</html>", { status: 502 })));
    await expect(api.profiles()).rejects.toMatchObject({ status: 502, message: "Something went wrong." });
  });

  it("asks for the analysis with the cover basis spelled out", async () => {
    fetchMock.mockImplementation(() => reply(200, {}));
    await api.analysis(42, "strict");
    expect(fetchMock.mock.calls[0]?.[0]).toBe("/api/profiles/42/analysis?basis=strict");
  });
});
