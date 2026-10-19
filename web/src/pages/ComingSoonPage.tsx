import { useLocation } from "react-router-dom";
import { NAV } from "../layout/nav";
import { ButtonLink } from "../ui/Button";
import { Badge } from "../ui/Status";
import { EmptyState } from "../ui/States";

/** Honest placeholder for a page that is planned but not built yet. It shows no invented numbers. */
export function ComingSoonPage() {
  const { pathname, search } = useLocation();
  const item = NAV.find((n) => n.to === pathname);

  if (!item) {
    return (
      <EmptyState icon="info" title="This page does not exist" action={<ButtonLink to={{ pathname: "/", search }} variant="primary">Go to the overview</ButtonLink>}>
        Check the address, or use the navigation on the left.
      </EmptyState>
    );
  }

  return (
    <div className="page">
      <h1>{item.label}</h1>
      <EmptyState
        icon={item.icon}
        title="Not built yet"
        action={
          <ButtonLink to={{ pathname: "/", search }} variant="primary">
            Back to the overview
          </ButtonLink>
        }
      >
        {item.description}
      </EmptyState>
      {item.arrivesInPhase && (
        <p className="muted center-text">
          <Badge tone="info">Planned for phase {item.arrivesInPhase} of 8</Badge>
        </p>
      )}
    </div>
  );
}
