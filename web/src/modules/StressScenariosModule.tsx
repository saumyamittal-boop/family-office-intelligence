import { useMeta } from "../api/hooks";
import { Badge } from "../ui/Status";
import { QueryBlock } from "../ui/QueryBlock";
import { times } from "../format";
import { AllResultsTable, fromScenarioRow, PresetAssumptions, ScenarioLab, ScenarioResultCard } from "./ScenarioParts";
import { shownFor } from "./types";
import type { ModuleContext, ModuleMode } from "./types";

/** What a crash, an inflation spike, a large bill or a lost decade would do to the chosen mix. */
export function StressScenariosModule({ ctx, mode }: { ctx: ModuleContext; mode: ModuleMode }) {
  const meta = useMeta();
  const shown = shownFor(ctx.analysis, ctx.choice);
  const presets = meta.data?.scenario_presets ?? [];
  const description = new Map(presets.map((p) => [p.name, p.description]));
  const [baseline, ...results] = shown.scenarios;

  return (
    <>
      <div className="pills">
        {baseline && (
          <>
            <Badge>{`Baseline: real corpus ${baseline.real_corpus_multiple.toFixed(2)}x of today at the horizon`}</Badge>
            <Badge>{`Safety net ${times(baseline.cover_ratio)}`}</Badge>
          </>
        )}
        <Badge>{`Showing the ${shown.portfolio.label} mix`}</Badge>
      </div>
      <div className="scn-grid">
        {results.map((row) => (
          <ScenarioResultCard key={row.scenario} result={fromScenarioRow(row)} description={description.get(row.scenario)} />
        ))}
      </div>
      {mode === "page" && (
        <>
          <PresetAssumptions presets={presets} />
          <QueryBlock query={meta} label="The scenario settings" rows={3}>
            {(m) => (
              <ScenarioLab
                profileId={ctx.profileId} basis={ctx.basis} choice={ctx.choice} presets={m.scenario_presets}
                ranges={m.custom_scenario_ranges} defaultPreset={ctx.analysis.comparison_scenario}
              />
            )}
          </QueryBlock>
          <AllResultsTable rows={shown.scenarios} label={shown.portfolio.label} />
        </>
      )}
    </>
  );
}
