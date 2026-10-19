import { useState } from "react";
import { ApiError } from "../api/client";
import { useDeleteProfile, useCreateProfile, useMeta, useProfile, useSaveProfile, useSession } from "../api/hooks";
import { cr } from "../format";
import { ProfileForm } from "../profile/ProfileForm";
import { starterForm, toForm } from "../profile/form";
import { Button } from "../ui/Button";
import { ErrorState, LoadingBlock } from "../ui/States";
import { Banner } from "../ui/Status";
import { useWorkspace } from "../workspace/WorkspaceProvider";

const problemsOf = (error: unknown): string[] =>
  error instanceof ApiError ? (error.problems && error.problems.length > 0 ? error.problems : [error.message]) : error ? ["Something went wrong. Please try again."] : [];

export function ProfilePage() {
  const { profiles, profileId, setProfileId } = useWorkspace();
  const session = useSession();
  const meta = useMeta();
  const detail = useProfile(profileId);
  const save = useSaveProfile();
  const create = useCreateProfile();
  const remove = useDeleteProfile();

  const [creating, setCreating] = useState(false);
  const [confirmDelete, setConfirmDelete] = useState(false);
  const [notice, setNotice] = useState("");
  const [saves, setSaves] = useState(0); // bumped by each save, so the form starts again from what the server stored

  const classes = meta.data ? [...meta.data.asset_classes, "Illiquid"] : null;
  const list = profiles.data ?? [];
  const isDemo = session.data?.user.is_demo ?? false;
  const problems = problemsOf(save.error ?? create.error);
  const failedToDelete = remove.error instanceof ApiError ? remove.error.message : null;

  const choose = (id: number) => {
    setCreating(false);
    setConfirmDelete(false);
    setNotice("");
    save.reset();
    create.reset();
    remove.reset();
    setProfileId(id);
  };

  const created = (id: number, name: string) => {
    setCreating(false);
    setNotice(`Saved as a new profile: ${name}.`);
    setProfileId(id);
  };

  return (
    <div className="page">
      <div className="page-head">
        <div>
          <h1>Family profile</h1>
          <p>What you own, what you need, and the limits you want respected.</p>
        </div>
        <Button
          variant="primary" icon="plus" disabled={!classes || creating}
          onClick={() => { setCreating(true); setNotice(""); save.reset(); create.reset(); }}
        >
          New profile
        </Button>
      </div>

      {isDemo && (
        <Banner tone="info">This is your private copy of a demo family. Changes stay in this copy and disappear when it expires.</Banner>
      )}
      {notice && <Banner tone="good" live>{notice}</Banner>}

      {profiles.isPending || !classes ? (
        <LoadingBlock label="Loading your family profiles" rows={5} />
      ) : (
        <div className="profile-layout">
          <nav aria-label="Your family profiles">
            <ul className="profile-list">
              {list.map((p) => (
                <li key={p.id}>
                  <button type="button" className="profile-item" aria-current={!creating && p.id === profileId ? "true" : undefined} onClick={() => choose(p.id)}>
                    <strong>{p.name}</strong>{" "}
                    <small>{cr(p.corpus_cr, 0)}</small>
                  </button>
                </li>
              ))}
              {creating && (
                <li>
                  <span className="profile-item" aria-current="true">
                    <strong>New profile</strong>{" "}
                    <small>Not saved yet</small>
                  </span>
                </li>
              )}
            </ul>
          </nav>

          <div className="stack-lg">
            {creating ? (
              <ProfileForm
                key="new" initial={starterForm(classes.filter((c) => c !== "Illiquid"))} classes={classes} isNew saving={create.isPending}
                serverProblems={problems} onSave={(input) => create.mutate(input, { onSuccess: (p) => created(p.id, p.name) })}
                onSaveAsNew={() => undefined}
              />
            ) : detail.isPending ? (
              <LoadingBlock label="Loading the profile" rows={6} />
            ) : detail.isError || !detail.data ? (
              <ErrorState
                title="Can't load this profile"
                message={detail.error instanceof ApiError ? detail.error.message : "Something went wrong."}
                onRetry={() => void detail.refetch()}
              />
            ) : (
              <>
                <ProfileForm
                  key={`${detail.data.id}-${saves}`} initial={toForm(detail.data)} classes={classes} isNew={false}
                  saving={save.isPending || create.isPending} serverProblems={problems}
                  onSave={(input) =>
                    save.mutate({ id: detail.data.id, body: input }, {
                      onSuccess: () => {
                        setSaves((n) => n + 1);
                        setNotice("Profile saved. The dashboard and analysis pages now use these numbers.");
                      },
                    })
                  }
                  onSaveAsNew={(input) => create.mutate(input, { onSuccess: (p) => created(p.id, p.name) })}
                />
                <section aria-labelledby="delete-title" className="stack">
                  <h2 id="delete-title">Delete this profile</h2>
                  <p className="muted">You always keep at least one profile.</p>
                  {!confirmDelete ? (
                    <div>
                      <Button onClick={() => setConfirmDelete(true)} disabled={list.length <= 1}>Delete profile</Button>
                      {list.length <= 1 && <span className="muted"> This is your only profile.</span>}
                    </div>
                  ) : (
                    <Banner
                      tone="warn" title={`Delete “${detail.data.name}”?`}
                      action={
                        <>
                          <Button
                            variant="primary" disabled={remove.isPending}
                            onClick={() =>
                              remove.mutate(detail.data.id, {
                                onSuccess: () => {
                                  setConfirmDelete(false);
                                  const next = list.find((p) => p.id !== detail.data.id);
                                  if (next) setProfileId(next.id);
                                  setNotice("Profile deleted.");
                                },
                              })
                            }
                          >
                            Yes, delete it
                          </Button>
                          <Button variant="ghost" onClick={() => setConfirmDelete(false)}>Keep it</Button>
                        </>
                      }
                    >
                      This can't be undone.
                    </Banner>
                  )}
                  {failedToDelete && <Banner tone="bad" critical>{failedToDelete}</Banner>}
                </section>
              </>
            )}
          </div>
        </div>
      )}
      <p className="hint">Illustrative simulation, not investment advice. Use synthetic data only.</p>
    </div>
  );
}
