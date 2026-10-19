import { useState } from "react";
import type { FormEvent } from "react";
import { ApiError } from "../api/client";
import type { DemoFamily } from "../api/client";
import { useDemo, useLogin, useMeta, useSignup } from "../api/hooks";
import { Brand } from "../layout/Sidebar";
import { ThemeMenu } from "../layout/Topbar";
import { Button } from "../ui/Button";
import { Card } from "../ui/Card";
import { TextField } from "../ui/Controls";
import { Banner } from "../ui/Status";

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
  const problem = message(active.error) ?? message(demo.error);
  const families = (meta.data?.demo_families ?? []) as DemoFamily[];

  function submit(event: FormEvent) {
    event.preventDefault();
    active.run(username, password);
  }

  return (
    <main className="login" id="main">
      <section>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
          <Brand />
          <ThemeMenu />
        </div>
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

      <Card className="login-card">
        <div className="tabs" role="tablist" aria-label="Sign in or create an account">
          <button
            role="tab" id="tab-login" aria-selected={mode === "login"} className="btn tab" type="button"
            onClick={() => setMode("login")}
          >
            Log in
          </button>
          <button
            role="tab" id="tab-signup" aria-selected={mode === "signup"} className="btn tab" type="button"
            onClick={() => setMode("signup")}
          >
            Create account
          </button>
        </div>

        <form className="form" onSubmit={submit} noValidate aria-labelledby={mode === "login" ? "tab-login" : "tab-signup"}>
          <TextField
            label={mode === "login" ? "Username" : "Choose a username"}
            value={username}
            onChange={(e) => setUsername(e.target.value)}
            autoComplete="username"
            maxLength={64}
            required
          />
          <TextField
            label={mode === "login" ? "Password" : "Choose a password"}
            hint={mode === "signup" ? "At least 8 characters." : undefined}
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            autoComplete={mode === "login" ? "current-password" : "new-password"}
            maxLength={256}
            required
          />
          <Button variant="primary" type="submit" disabled={busy || !username || !password}>
            {mode === "login" ? "Log in" : "Create account"}
          </Button>
        </form>

        {problem && (
          <div style={{ marginTop: "var(--space-3)" }}>
            <Banner tone="bad" critical>
              {problem}
            </Banner>
          </div>
        )}

        {families.length > 0 && (
          <div className="demos">
            <p className="hint">Or explore a demo family</p>
            {families.map((family) => (
              <Button key={family} disabled={busy} onClick={() => demo.run(family)}>
                {DEMO_LABELS[family]}
              </Button>
            ))}
            <p className="hint">Each visit gets its own private copy, so nobody else sees your changes.</p>
          </div>
        )}

        <p className="hint" style={{ marginTop: "var(--space-4)" }}>
          Prototype with synthetic data only. Do not reuse a real password, and do not enter real client data.
        </p>
      </Card>
    </main>
  );
}
