import { useLocation } from "react-router-dom";
import { ConsolidationView } from "../holdings/ConsolidationView";
import { ButtonLink } from "../ui/Button";
import type { ModuleContext, ModuleMode } from "./types";

/** Everything imported from statements, added up by asset class. The Holdings page has the import and the detail. */
export function HoldingsConsolidationModule({ ctx, mode }: { ctx: ModuleContext; mode: ModuleMode }) {
  const { search } = useLocation();
  return (
    <ConsolidationView
      profileId={ctx.profileId}
      compact={mode === "card"}
      empty={<ButtonLink to={{ pathname: "/holdings", search }} variant="primary" icon="holdings">Import holdings</ButtonLink>}
    />
  );
}
