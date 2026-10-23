# Documentation index

> Illustrative simulation, not investment advice. Results depend on the data, assumptions, and methodology used. Historical outcomes do not
> guarantee future performance. All data in this project is synthetic.

## Start here

| If you want to… | Read |
|---|---|
| Understand what this is and how it is built | [architecture.md](architecture.md) |
| Get it running on a clean machine | [setup.md](setup.md) |
| Take over the project, or fix something that broke | [handover.md](handover.md) |
| Know what is built, what is partly done and what is missing | [limitations.md](limitations.md) |
| Decide whether it could ever hold real data | [production-readiness.md](production-readiness.md) |

## Reference

| Topic | Document |
|---|---|
| Settings (environment variables) | [configuration.md](configuration.md) |
| Database tables, migrations, backup | [database.md](database.md) |
| HTTP API (generated from the code) | [api.md](api.md) |
| Financial method, assumptions and what they cannot tell you | [methodology.md](methodology.md), [protected-assumptions.md](protected-assumptions.md), [personas-and-assumptions.md](personas-and-assumptions.md) |
| Importing a holdings statement (CSV / Excel) | [holdings-import.md](holdings-import.md) |
| Running and extending the tests | [testing.md](testing.md) |
| Hosting the React + FastAPI version | [deployment-react.md](deployment-react.md) |
| Hosting the Streamlit version (`main`) | [deployment.md](deployment.md) |
| Audit of the React version for a shareable link, with scores and evidence | [audit-shared-link.md](audit-shared-link.md) |
| The plan for sharing the React version, hosting it, and the sign-in question (a proposal) | [plan-sharing-and-deployment.md](plan-sharing-and-deployment.md), [ADR-0022](adr/0022-authentication-own-or-managed.md) |

## Background and history

| Topic | Where |
|---|---|
| Requirements and scope | [requirements.md](requirements.md) |
| Why each decision was made | [adr/](adr/README.md) (0001 to 0021) |
| What each migration phase did, tested and left open | [migration/](migration/phase-8-report.md) (`phase-1-report.md` … `phase-8-report.md`) |
| Mentor feedback and what came of it | [backlog-from-mentor-feedback.md](backlog-from-mentor-feedback.md) |
| Look and feel | [design-system.md](design-system.md), [dev-tooling.md](dev-tooling.md) |
| Demo script (Streamlit version, 3 minutes) | [demo-script.md](demo-script.md) |
| Demo script (React version, in person, with a one-click launcher in `demo/`) | [demo-script-react.md](demo-script-react.md) |
| Change log | [../CHANGELOG.md](../CHANGELOG.md) |

## Which documents are generated

`api.md` is written by `python tools/export_api_docs.py` from the running application and `tests/test_api_docs.py` fails when it is stale.
`tests/test_docs.py` checks that links resolve, that every setting the code reads is documented, that documented defaults and assumption
values equal the code's, and that no document claims compliance, validation or security assurance the project does not have.
