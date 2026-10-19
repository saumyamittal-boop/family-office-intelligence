import type { SessionInfo } from "../api/client";
import { useLogout } from "../api/hooks";
import { useTheme } from "../theme/ThemeProvider";
import { displayName } from "../user";
import type { ThemePreference } from "../theme/theme";
import { Icon } from "../ui/Icon";
import type { IconName } from "../ui/Icon";
import { IconButton, Menu, MenuItem, MenuLabel, MenuRadioGroup, MenuSeparator } from "../ui/Overlays";
import { Brand } from "./Sidebar";

const THEME_OPTIONS: readonly { value: ThemePreference; label: string; icon: IconName }[] = [
  { value: "light", label: "Light", icon: "sun" },
  { value: "dark", label: "Dark", icon: "moon" },
  { value: "system", label: "Match my device", icon: "monitor" },
];

export function ThemeMenu() {
  const { preference, resolved, setPreference } = useTheme();
  const current = THEME_OPTIONS.find((o) => o.value === preference);
  return (
    <Menu
      label={`Theme: ${current?.label ?? "Match my device"}${preference === "system" ? ` (${resolved})` : ""}`}
      trigger={<Icon name={resolved === "dark" ? "moon" : "sun"} size={20} />}
    >
      <MenuLabel>Theme</MenuLabel>
      <MenuRadioGroup value={preference} onValueChange={setPreference} options={THEME_OPTIONS} />
    </Menu>
  );
}

export function UserMenu({ session }: { session: SessionInfo }) {
  const logout = useLogout();
  return (
    <Menu
      label={`Account: ${displayName(session.user)}`}
      trigger={
        <>
          <Icon name="profile" size={20} />
          <span className="user-name">{displayName(session.user)}</span>
        </>
      }
    >
      <MenuLabel>{session.user.is_demo ? "Demo copy: private to you, deleted after 24 hours" : "Signed in"}</MenuLabel>
      <MenuSeparator />
      <MenuItem icon="logout" onSelect={() => logout.mutate()}>
        Log out
      </MenuItem>
    </Menu>
  );
}

export function Topbar({ session, onOpenNav }: { session: SessionInfo; onOpenNav: () => void }) {
  return (
    <header className="topbar">
      <div className="topbar-nav-button">
        <IconButton label="Open navigation" icon="menu" onClick={onOpenNav} />
      </div>
      <div className="topbar-brand">
        <Brand />
      </div>
      <span className="spacer" />
      <span className="badge badge-info topbar-badge">Synthetic data</span>
      <ThemeMenu />
      <UserMenu session={session} />
    </header>
  );
}
