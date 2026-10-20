# Development tooling

What was added to the owner's machine to help build and review this app, where it lives, and how to undo it.
None of it is part of the app: no third-party file is stored in this repository, and nothing here changes the financial model.
Recorded 2026-10-20. The fuller record, with licence texts, is kept beside the installed skills in `~/.claude/third-party-skills/README.md`.

## Design skills (instructions that shape how Claude builds screens)

| Skill | Source and pinned commit | Licence | Where it lives |
|---|---|---|---|
| 15 skills by Emil Kowalski (motion, animation review, edge-case breaking, mobile polish) | github.com/emilkowalski/skills `2d22863` | MIT | `~/.claude/skills/<name>/` |
| `design-taste-frontend` ("taste-skill") | github.com/Leonxlnx/taste-skill `63aba5f` | MIT | `~/.claude/skills/design-taste-frontend/`. Runs Node scripts that start a local headless Chrome and fetch images from public art and image sites |
| `impeccable` and 4 helper agents | github.com/pbakaus/impeccable `374a0e1` | Apache-2.0 | `~/.claude/skills/impeccable/`, `~/.claude/agents/impeccable-*.md` |

Each was read before installation and copied unchanged at the commit shown.

**Rule for this project:** the approved design system (`docs/design-system.md`, tokens in `web/src/styles/tokens.css`) comes first. The skills extend it; they do not restyle the app without the owner's approval.
This is a finance dashboard, so restraint beats flair.

## Impeccable's engine, hooks and telemetry

- The engine is a downloaded program, `~/.impeccable/bin/0.1.16/impeccable.exe` (19.8 MB). Its SHA-256 matches the release's published checksum and GitHub's digest, and it carries a valid code-signing certificate.
  It includes a web client and a local server, so it is not inert.
- Hooks in `D:\.claude\settings.local.json` run it at session start, after every file edit and at stop, for sessions whose project folder is `D:\`. After edits to `.ts`, `.tsx`, `.css`, `.html`, `.js` and similar files it can report design findings to Claude.
  That file is outside this repository.
- Its telemetry is on by default upstream and is **switched off** in `~/.impeccable/config.json`.
- **Undo:** delete `D:\.claude\settings.local.json` (hooks), `~/.impeccable` (engine and config), `~/.claude/skills/impeccable` and `~/.claude/agents/impeccable-*.md`.

## Tools

- **Figma** (official plugin): connected. The owner is on Figma Starter with a View seat, which allows only about 6 reads from Figma a month; use them on a specific file the owner names.
- **Playwright** (Anthropic's official plugin, which runs Microsoft's `@playwright/mcp`): chosen but installed by the owner from the plugin menu; not confirmed yet. It runs the newest version at each start. End-to-end tests for Phase 7 will use Playwright Test, which is separate and not yet a project dependency.

## Free-model gateway (kept apart from Claude)

- **FreeLLMAPI** v0.16.5 (commit `5540efa`, MIT) is built in `D:\tools\freellmapi`, started only by `D:\tools\start-freellmapi.cmd`, on http://127.0.0.1:3001, with its catalog sync and update check switched off. It has no provider keys until the owner adds some.
- Claude does not use it: `ANTHROPIC_BASE_URL` stays `https://api.anthropic.com`. Nothing private (dissertation, credentials, family data) goes through it, because prompts go to whichever free provider is next in line.
- **Do not** open a Claude session with `D:\tools\freellmapi` as the project folder: it ships settings that pre-approve commands such as `rm -rf client/.git`.
- **Undo:** delete `D:\tools\freellmapi` and `D:\tools\start-freellmapi.cmd`.
- Reviewed and **not** installed: OmniRoute (diegosouzapw), RTK (rtk-ai) and Caveman (JuliusBrussee). Reasons are in the owner's notes: size and account-routing risk for the first, command rewriting for the second, terse replies for the third.

## A finding worth keeping

SciPy's bundled linear-programming solver (HiGHS) hangs or crashes on this Windows machine when a thread that used it exits. The API therefore keeps its engine threads alive
(`api/analysis.py`). The evidence is in `docs/migration/phase-4-report.md`.
