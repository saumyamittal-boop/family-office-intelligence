import type { Basis } from "../api/client";
import { useMeta } from "../api/hooks";
import { cr } from "../format";
import { Select } from "../ui/Controls";
import { useWorkspace } from "./WorkspaceProvider";

/** Which family and which liquidity-cover basis every analysis page is showing. */
export function WorkspaceBar() {
  const { profiles, profileId, setProfileId, basis, setBasis } = useWorkspace();
  const meta = useMeta();
  const bases = Object.entries(meta.data?.cover_bases ?? {});

  return (
    <div className="workspace-bar">
      <Select
        label="Family profile"
        value={profileId ?? ""}
        onChange={(e) => setProfileId(Number(e.target.value))}
        disabled={!profiles.data?.length}
      >
        {(profiles.data ?? []).map((p) => (
          <option key={p.id} value={p.id}>
            {p.name} ({cr(p.corpus_cr, 0)})
          </option>
        ))}
      </Select>
      <Select label="What counts towards the safety net" value={basis} onChange={(e) => setBasis(e.target.value as Basis)}>
        {bases.map(([key, text]) => (
          <option key={key} value={key}>
            {text}
          </option>
        ))}
      </Select>
    </div>
  );
}
