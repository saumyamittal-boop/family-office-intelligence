import { useEffect, useMemo, useState } from "react";
import { ApiError } from "../api/client";
import type { Analysis, Basis, PortfolioOut, SessionInfo } from "../api/client";
import { useAnalysis, useLogout, useMeta, useProfiles } from "../api/hooks";
import { cr, pct, signedCr, signedPct, times } from "../format";

const ILLIQUID = "Illiquid";

function Tile({ label, value, sub, tone }: { label: string; value: string; sub?: string; tone?: "good" | "warn" }) {
  return (
    <div className={`tile ${tone ?? ""}`}>
      <div className="tile-label">{label}</div>
      <div className="tile-value">{value}</div>
      {sub && <div className="tile-sub">{sub}</div>}
    </div>
  );
}

function OptimiserWarning({ analysis }: { analysis: Analysis }) {
  const unconverged = [analysis.current, ...analysis.options.map((o) => o.portfolio)].filter(
    (p) => !p.optimiser_converged,
  );
  if (unconverged.length === 0) return null;
  return (
    <p role="alert" className="banner warn">
      The optimiser did not report a clean solution for: {unconverged.map((p) => p.label).join(", ")}. Treat those
      weights as approximate.
    </p>
  );
}

function Allocation({ analysis, option }: { analysis: Analysis; option: PortfolioOut }) {
  const order = [...Object.keys(analysis.current.weights_total).filter((c) => c !== ILLIQUID), ILLIQUID];
  return (
    <table>
      <caption className="sr-only">Share of the whole corpus by asset class</caption>
      <thead>
        <tr>
          <th scope="col">Asset class</th>
          <th scope="col" className="num">
            Now
          </th>
          <th scope="col" className="num">
            {option.label}
          </th>
        </tr>
      </thead>
      <tbody>
        {order.map((name) => (
          <tr key={name}>
            <th scope="row">{name === ILLIQUID ? "Illiquid (fixed)" : name}</th>
            <td className="num">{pct(analysis.current.weights_total[name] ?? 0)}</td>
            <td className="num">{pct(option.weights_total[name] ?? 0)}</td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}

function Comparison({ analysis }: { analysis: Analysis }) {
  return (
    <>
      <table>
        <caption className="sr-only">Options compared under: {analysis.comparison_scenario}</caption>
        <thead>
          <tr>
            <th scope="col">Option</th>
            <th scope="col" className="num">
              Value change
            </th>
            <th scope="col" className="num">
              Expected return
            </th>
            <th scope="col" className="num">
              Safety net after
            </th>
          </tr>
        </thead>
        <tbody>
          {analysis.comparison.map((row) => (
            <tr key={row.option}>
              <th scope="row">{row.option}</th>
              <td className="num">
                {signedCr(row.value_change_cr)} ({signedPct(row.value_change)})
              </td>
              <td className="num">{pct(row.exp_return)}</td>
              <td className="num">
                {times(row.cover_ratio_after)} {row.cover_held ? "held" : "short"}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
      <ul className="notes">
        {analysis.comparison_insights.map((note) => (
          <li key={note.body} className={note.tone}>
            {note.body}
          </li>
        ))}
      </ul>
    </>
  );
}

export function AnalysisView({ analysis }: { analysis: Analysis }) {
  const labels = ["Current", ...analysis.options.map((o) => o.portfolio.label)];
  const [choice, setChoice] = useState("Balanced");
  const detail = analysis.options.find((o) => o.portfolio.label === choice);
  const option = detail?.portfolio ?? analysis.options[1]?.portfolio ?? analysis.current;
  const shown = choice === "Current" ? analysis.current : option;
  const ratio = shown.available_cover_cr / shown.required_cover_cr;

  return (
    <div className="stack">
      <OptimiserWarning analysis={analysis} />

      <div className="segmented" role="group" aria-label="Portfolio">
        {labels.map((label) => (
          <button key={label} type="button" aria-pressed={label === choice} onClick={() => setChoice(label)}>
            {label}
          </button>
        ))}
      </div>

      <div className="tiles">
        <Tile
          label="Expected return"
          value={pct(shown.exp_return)}
          sub={`${pct(shown.exp_real)} after inflation`}
          tone={shown.meets_target ? "good" : "warn"}
        />
        <Tile label="Volatility" value={pct(shown.vol)} sub="Annual, including illiquid holdings" />
        <Tile
          label="Worst drawdown"
          value={pct(shown.max_dd)}
          sub="Peak to trough in the sample history"
          tone={shown.dd_ok ? "good" : "warn"}
        />
        <Tile
          label="Liquidity cover"
          value={times(ratio)}
          sub={`${cr(shown.available_cover_cr, 0)} counted vs ${cr(shown.required_cover_cr, 0)} needed`}
          tone={ratio >= 1.5 ? "good" : "warn"}
        />
      </div>

      <div className="grid-2">
        <section className="card">
          <h2>Allocation</h2>
          <Allocation analysis={analysis} option={shown} />
        </section>
        <section className="card">
          <h2>{choice === "Current" ? "Where you are now" : `Why the ${choice} mix`}</h2>
          {choice === "Current" ? (
            <ul className="notes">
              {(detail?.insights ?? analysis.options[1]?.insights ?? []).map((i) => (
                <li key={i.body} className={i.tone}>
                  <b>{i.title}.</b> {i.body}
                </li>
              ))}
            </ul>
          ) : (
            <ul className="notes">
              {shown.explanation.map((line) => (
                <li key={line}>{line}</li>
              ))}
            </ul>
          )}
        </section>
      </div>

      <section className="card">
        <h2>Compare under: {analysis.comparison_scenario}</h2>
        <Comparison analysis={analysis} />
      </section>

      <p className="hint">
        Cover basis in force: {analysis.basis_label}. Data: {analysis.data_source}. Illustrative simulation, not
        investment advice.
      </p>
    </div>
  );
}

export function HomePage({ session }: { session: SessionInfo }) {
  const meta = useMeta();
  const profiles = useProfiles(true);
  const logout = useLogout();
  const [profileId, setProfileId] = useState<number | null>(null);
  const [basis, setBasis] = useState<Basis>(session.default_basis);

  useEffect(() => {
    if (profileId === null && profiles.data?.length) setProfileId(profiles.data[0]?.id ?? null);
  }, [profiles.data, profileId]);

  const analysis = useAnalysis(profileId, basis);
  const bases = useMemo(() => Object.entries(meta.data?.cover_bases ?? {}), [meta.data]);

  return (
    <div className="shell">
      <header className="topbar">
        <p className="brand">
          Family Office <b>Intelligence</b>
        </p>
        <span className="pill">Foundation build</span>
        <span className="spacer" />
        <span className="muted">
          {session.user.username}
          {session.user.is_demo ? " (demo copy)" : ""}
        </span>
        <button type="button" onClick={() => logout.mutate()}>
          Log out
        </button>
      </header>

      <main className="content">
        <div className="controls">
          <label>
            Family profile
            <select value={profileId ?? ""} onChange={(e) => setProfileId(Number(e.target.value))}>
              {(profiles.data ?? []).map((p) => (
                <option key={p.id} value={p.id}>
                  {p.name} ({cr(p.corpus_cr, 0)})
                </option>
              ))}
            </select>
          </label>
          <label>
            What counts towards the safety net
            <select value={basis} onChange={(e) => setBasis(e.target.value as Basis)}>
              {bases.map(([key, label]) => (
                <option key={key} value={key}>
                  {label}
                </option>
              ))}
            </select>
          </label>
        </div>

        {analysis.isPending && analysis.fetchStatus !== "idle" && <p className="muted">Running the allocation model…</p>}
        {analysis.isError && (
          <p role="alert" className="banner bad">
            {analysis.error instanceof ApiError ? analysis.error.message : "Something went wrong."}{" "}
            <button type="button" onClick={() => analysis.refetch()}>
              Try again
            </button>
          </p>
        )}
        {analysis.data && <AnalysisView key={`${profileId}-${basis}`} analysis={analysis.data} />}
      </main>
    </div>
  );
}
