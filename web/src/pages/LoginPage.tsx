import { useState } from "react";
import type { FormEvent } from "react";
import { ApiError } from "../api/client";
import type { DemoFamily } from "../api/client";
import { useDemo, useLogin, useMeta, useSignup } from "../api/hooks";

const DEMO_LABELS: Record<DemoFamily, string> = {
  legacy: "Legacy-conservative family",
  business: "Business-heavy family",
  nextgen: "Next-gen growth family",
  gap: "₹1,000 Cr liquidity-gap example",
};

function message(error: unknown): string | null {
  if (!error) return null;
  return error instanceof ApiError ? error.message : "Something went wrong. Please try again.";
}

export function LoginPage() {
  const meta = useMeta();
  const login = useLogin();
  const signup = useSignup();
  const demo = useDemo();
  const [mode, setMode] = useState<"login" | "signup">("login");
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");

  const active = mode === "login" ? login : signup;
  const busy = login.isPending || signup.isPending || demo.isPending;

  function submit(event: FormEvent) {
    event.preventDefault();
    active.run(username, password);
  }

  const problem = message(active.error) ?? message(demo.error);
  const families = (meta.data?.demo_families ?? []) as DemoFamily[];

  return (
    <main className="login">
      <section className="login-intro">
        <p className="brand">
          Family Office <b>Intelligence</b>
        </p>
        <h1>
          Your family's wealth,
          <br />
          <span>in one place.</span>
        </h1>
        <p className="lead">
          Decide how to spread capital across asset classes, keep enough liquidity for what is coming, and stress-test
          the plan. Every recommendation comes with its reasons.
        </p>
      </section>

      <section className="card login-card" aria-label="Sign in">
        <div className="tabs" role="tablist">
          <button role="tab" aria-selected={mode === "login"} onClick={() => setMode("login")} type="button">
            Log in
          </button>
          <button role="tab" aria-selected={mode === "signup"} onClick={() => setMode("signup")} type="button">
            Create account
          </button>
        </div>

        <form onSubmit={submit} noValidate>
          <label>
            {mode === "login" ? "Username" : "Choose a username"}
            <input
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              autoComplete="username"
              maxLength={64}
              required
            />
          </label>
          <label>
            {mode === "login" ? "Password" : "Choose a password"}
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              autoComplete={mode === "login" ? "current-password" : "new-password"}
              maxLength={256}
              required
            />
          </label>
          {mode === "signup" && <p className="hint">At least 8 characters.</p>}
          <button className="primary" type="submit" disabled={busy || !username || !password}>
            {mode === "login" ? "Log in" : "Create account"}
          </button>
        </form>

        {problem && (
          <p role="alert" className="error">
            {problem}
          </p>
        )}

        {families.length > 0 && (
          <div className="demos">
            <p className="muted">Or explore a demo family</p>
            {families.map((family) => (
              <button key={family} type="button" disabled={busy} onClick={() => demo.run(family)}>
                {DEMO_LABELS[family]}
              </button>
            ))}
            <p className="hint">Each visit gets its own private copy, so nobody else sees your changes.</p>
          </div>
        )}

        <p className="hint">
          Prototype with synthetic data only. Do not reuse a real password, and do not enter real client data.
        </p>
      </section>
    </main>
  );
}
