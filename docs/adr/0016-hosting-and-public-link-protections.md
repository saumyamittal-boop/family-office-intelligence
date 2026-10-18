# ADR-0016: Hosting approach and public-link protections

**Date**: 2026-10-18
**Status**: accepted
**Deciders**: Project owner (asked to prepare deployment), facilitated by Claude
**Builds on**: [ADR-0010](0010-multi-user-local-accounts.md) and [ADR-0014](0014-app-structure-and-visual-direction.md)

## Context

The mentor asked for a link he can open on any day, and the team said it would try to deploy itself by the end of
October. ADR-0010 deferred online hosting because free Streamlit hosting does not guarantee local files, which would wipe a
SQLite database. A public link can also reach strangers, and the demo families have no password. Docker is not installed on
the development machine, and nothing has been published.

## Decision

Prepare the app so it can be hosted in either of two ways, and recommend Streamlit Community Cloud for the first link:
it is free, takes minutes, and the mentor only needs the demo families, which are re-created on every start. Keep the
Docker setup ready for a persistent host later. Protect any public link with three optional settings, all off by default:
an access code (`FO_ACCESS_CODE`) that hides everything, including the demo buttons; a sign-up cap (`FO_MAX_ACCOUNTS`,
default 200); and in-memory throttling of wrong passwords and access codes. The database location is configurable
(`FO_DB_PATH`) for a persistent volume. A `.gitignore` keeps the user database, licensed market data and secrets out of any
repository. Publishing (GitHub, hosting accounts) stays the owner's action.

## Alternatives Considered

### Alternative 1: Host straight away on a VM with Docker
- **Pros**: Always on; accounts persist.
- **Cons**: Hours of setup and a monthly cost; the image is not yet build-tested.
- **Why not**: Disproportionate for a mentor preview; kept as the next step.

### Alternative 2: Run on the owner's PC through a tunnel
- **Pros**: Free; accounts persist.
- **Cons**: Works only while the PC is on; exposes a personal machine to the internet.
- **Why not**: Unreliable for "open it any day", and a security exposure.

### Alternative 3: Move to an external database now
- **Pros**: Accounts survive on any host.
- **Cons**: A bigger change, a new service to run, and credentials to manage.
- **Why not**: Not needed for a demo that uses the always-available demo families.

## Consequences

### Positive
- A shareable link is a short checklist away, with protections that stop casual misuse.
- Local use is unchanged: with no settings, nothing new appears.

### Negative
- On Community Cloud, accounts created live can disappear, and the app sleeps after 12 idle hours.
- The throttle resets on restart and can briefly lock out a real user whose name is being guessed.

### Risks
- The Docker image is untested. Mitigation: build and run it once on a machine with Docker before relying on it.
- A shared access code is a weak secret. Mitigation: use it only for a synthetic-data preview, and rotate it afterwards.
