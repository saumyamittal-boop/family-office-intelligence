import { NavLink, useLocation } from "react-router-dom";
import { Icon } from "../ui/Icon";
import { IconButton } from "../ui/Overlays";
import { Badge } from "../ui/Status";
import { NAV } from "./nav";

export function Brand({ compact = false }: { compact?: boolean }) {
  return (
    <div className="brand">
      <span className="brand-mark" aria-hidden="true">
        FOI
      </span>
      {!compact && (
        <span className="brand-name">
          Family Office <b>Intelligence</b>
        </span>
      )}
    </div>
  );
}

/** The main navigation. `collapsed` shows icons only (names stay available to screen readers and as tooltips). */
export function NavList({ collapsed = false, onNavigate }: { collapsed?: boolean; onNavigate?: () => void }) {
  const { search } = useLocation(); // keep ?profile= and ?basis= when moving between pages
  return (
    <nav aria-label="Main">
      <ul className="nav-list">
        {NAV.map((item) => (
          <li key={item.to}>
            <NavLink
              to={{ pathname: item.to, search }}
              end={item.to === "/"}
              className="nav-link"
              title={collapsed ? item.label : undefined}
              onClick={onNavigate}
            >
              <Icon name={item.icon} />
              <span className={collapsed ? "sr-only" : "nav-label"}>{item.label}</span>
              {item.arrivesInPhase && !collapsed && <Badge tone="neutral">Soon</Badge>}
              {item.arrivesInPhase && collapsed && <span className="sr-only">(coming soon)</span>}
            </NavLink>
          </li>
        ))}
      </ul>
    </nav>
  );
}

export function Sidebar({ collapsed, onToggle }: { collapsed: boolean; onToggle: () => void }) {
  return (
    <aside className="sidebar" aria-label="Sidebar">
      <Brand compact={collapsed} />
      <NavList collapsed={collapsed} />
      <div className="sidebar-foot">
        <IconButton
          label={collapsed ? "Expand sidebar" : "Collapse sidebar"}
          icon={collapsed ? "chevronRight" : "chevronLeft"}
          onClick={onToggle}
          aria-expanded={!collapsed}
        />
      </div>
    </aside>
  );
}
