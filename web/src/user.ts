import type { SessionInfo } from "./api/client";

/** What to call the signed-in person on screen. A demo copy has a machine-made username, so it is shown as "Demo family". */
export function displayName(user: SessionInfo["user"]): string {
  return user.is_demo ? "Demo family" : user.username;
}
