---
name: engine-release
description: "Custom engine: cut an engine version for the game teams — semver plan from ADRs and API reviews, changelog, migration guide, integration test of game/, game-team sign-off, tag and LTS/hotfix branch plan as text."
argument-hint: "[version] [--from <tag>] [--lts] [--patch-of <release-branch>]"
user-invocable: true
disable-model-invocation: true
allowed-tools: Read, Glob, Grep, Write, Agent, AskUserQuestion, Bash(git log *), Bash(git rev-parse *), Bash(git tag --list*), Bash(git branch --list *), Bash(git status *), Bash(bash .claude/scripts/test-run.sh custom), Bash(bash "*/.claude/skills/engine-release/../../hooks/yaml-helper.sh" resolve_config *), Bash(bash .claude/scripts/adr-files.sh list), Bash(bash .claude/scripts/adr-files.sh where)
model: sonnet
---

!`bash "${CLAUDE_SKILL_DIR}/../../hooks/yaml-helper.sh" resolve_config --keys engine,review_mode,automation,workflow,project.stage`

Resolved above — use as-is. No block → defaults in
`.claude/docs/config-resolution.md`.

# Engine Release

> **Explicit invocation only**: this skill runs when the user types
> `/engine-release`. It is not started from context.

Every `AskUserQuestion` call follows `.claude/docs/automation-modes.md`
(collaborative asks always · guided major-only · autonomous logs and proceeds;
`automation_always_ask` categories always prompt).

An engine release is separate from a game release (`.claude/agents/release-manager.md`,
On a Custom Engine Project). This skill prepares one for the game teams that
consume the engine: the version number, the changelog, the migration guide, the
integration test of `game/`, each game team's sign-off, and the tag and branch
plan. `release-manager` owns the release; `chief-engine-architect` decides the
version bump from the ADRs; `engine-technical-writer` writes the migration
guide.

**This skill never creates a tag or a branch and never pushes.** It runs only
read-only `git` commands. The tag, branch and push commands are printed as text
in the release record for the user to run. This holds in every
`modes.automation`, `autonomous` included: a pushed tag is the one step game
teams act on, and it is not taken back cleanly.

## Phase 0: Engine Check

**First, before anything is read or spawned.** Read the `engine:` line above:

- `engine: Custom` → continue.
- Anything else, or unset → **refuse, and say so**:

  > `/engine-release did not run: it needs engine.name: Custom, and this project's engine is <value | unset>.`
  > `It versions an engine this project builds itself. <engine> is versioned by its vendor; this project pins a version of it.`
  > `For a game release, run /release-checklist or /team-release; to pin or upgrade <engine>, run /setup-engine.`

  Then stop. Verdict: **NOT ASSESSED — engine.name is not Custom**.

**Sign-offs and `review_mode`.** The agents this skill spawns are the
release's own roles, not director gates (`.claude/docs/director-gates.md` lists
none for it), so they run at every `review_mode`. Say so once:
`Release roles run at every review_mode — not director gates.`

## Insufficient input — check this before producing any record

1. List the inputs: the previous engine release tag, the commit range, the
   Accepted ADRs, the `/api-review` reports under
   `production/qa/api-reviews/`, the migration guide, the integration test
   result, and each game team's sign-off.
2. Record each `FOUND` or `ABSENT`.
3. Each release check whose input is ABSENT reads **`NOT ASSESSED — <reason>`**
   in the record. It is never left out and never read as met.
4. Resolve engine source roots and shared build inputs using
   `.claude/docs/custom-engine-layout.md`, Resolving source roots for workflows.
   Record them for the inventory and candidate checks below. Not a git
   repository, or no mapped engine source → stop:
   **`NOT ASSESSED — nothing to release`**, naming what was missing. A crate-only
   engine does not require an `engine/` folder.

---

## Phase 1: Previous Release, Range and Candidate

1. **Tag scheme.** `git tag --list`. Engine release tags follow the scheme the
   last engine release record names (`production/releases/engine/`); none →
   propose `engine-vX.Y.Z` and ask. Engine tags must not collide with the
   game's release tags (`/hotfix` tags the game's `vX.Y.Z`).
2. **Previous release.** `--from <tag>`, else the newest engine tag. None →
   `first engine release`: the range is the whole history of the resolved engine
   roots and shared build inputs, and
   the record says so.
3. **Candidate commit.** `HEAD` for a release from `main`; the head of
   `--patch-of <release-branch>` for a patch on a release branch
   (`git branch --list 'release/*'`). Record its full hash
   (`git rev-parse`). The tag is planned on this commit, never on whatever
   `main` holds when the user later runs the command.
4. **Candidate checkout.** Compare `git rev-parse HEAD` with the full candidate
   hash. If unequal, do not run Phase 4: `NOT ASSESSED — HEAD differs from candidate`.
   Ask the user to prepare a clean checkout of that candidate; this skill never
   switches branches. A clean checkout of another commit proves nothing about it.
5. **Clean tree.** `git status --porcelain`. Any tracked modification or untracked
   file that can affect compilation, tests or runtime (including root build files,
   lockfiles, presets, toolchain files and `project.yaml`, as well as
   the resolved engine roots, consumer roots or test roots) → the integration test (Phase 4) would run on
   files that are not in the candidate: say so, and that check is
   `NOT ASSESSED — working tree differs from the candidate` until the tree is
   clean.

---

## Phase 2: Inventory and Version

**Read `references/inventory.md` now and follow it** — the commit, ADR and
`/api-review` inventory, the changelog draft and the version decision are in
that file, not here. Read it again if the conversation was compacted or resumed
during this phase.

---

## Phase 3: Migration Guide

Required when Phase 2 found any breaking or deprecating change
(`release-manager`: no notes, no release). None → `Migration guide: not
needed — no breaking or deprecating change`.

1. Spawn `engine-technical-writer` via Agent with: the previous tag, the
   planned tag, the Accepted ADRs in range, the `/api-review` reports and any
   notes already under `docs/engine/migration/` (for example a
   `<previous>-to-next.md` that `/api-review` appended to). Ask it to return
   one guide between the two named tags, built from the public-API difference
   and the ADRs, every changes-table row pointing at one or the other — and not
   to write it.
2. The Rust part of the guide reads `NOT ASSESSED` when no public-API diff
   could be made for it (`engine-technical-writer`, Migration guides) — carry
   that line into the record.
3. Show the guide, then ask: *"May I write the migration guide to
   `docs/engine/migration/[previous]-to-[new].md`?"*

No guide where one is required — none drafted, or the user declined — is a
release blocker (`NOT READY`). A guide built on a Proposed ADR is DRAFT and the
check is `NOT ASSESSED`.

---

## Phase 4: Integration Test of `game/`

Only run in the clean candidate checkout verified in Phase 1. Recheck HEAD and
the working tree immediately before the run; any mismatch makes integration
NOT ASSESSED. Record the tested hash with the result. Run as one plain command:

```bash
bash .claude/scripts/test-run.sh custom
```

It builds with `commands.build` and runs `commands.test`. Read its `rule` row:

| `rule` | Integration result |
|---|---|
| `custom:ctest-pass`, `custom:cargo-pass` | PASS — cite the test count |
| `custom:ctest-failed`, `custom:cargo-failed`, `custom:build-failed`, `custom:cargo-compile-failed`, `custom:nonzero` | FAIL — release blocker (`custom:nonzero`: the test command failed with no runner count to read) |
| `custom:ctest-zero`, `custom:cargo-zero` | NOT ASSESSED — zero tests is never a pass |
| `custom:no-test-command` | NOT ASSESSED — `commands.test` unset |
| `custom:0`, a timeout, `runner-unavailable`, `-`, or any other row | NOT ASSESSED — name the row |

**Affirmative candidate-build evidence is required for PASS.** Record
`build_exit 0` with `build_timed_out no`. With no separate build command, only
a Cargo test run that compiled the workspace (`runner cargo` and
`custom:cargo-pass`) supplies that evidence. A passing CTest row with a skipped
build can be an old binary: integration is
`NOT ASSESSED — no affirmative candidate-build evidence`. Set `commands.build`
and rerun against the clean candidate. A failed build remains FAIL.

**Consumer coverage comes from targets and execution evidence.** Resolve each
in-repo consumer and its test targets from the module map and build manifests.
For Cargo, inspect workspace members, package/target names, default-members and
the command's package selections/exclusions; consumer integration tests may live
at `game/tests/` and the command may simply be `cargo test --workspace`. For
CMake, follow registered test targets and their consumer links, not a directory
name or a literal `game` in the command.

Read the helper's run log or an equivalent candidate-bound execution receipt.
Record which consumer targets were built and which tests actually ran, with
nonzero counts and results for each required consumer. Aggregate engine-test
success, selecting a package without executing its consumer tests, or a path
name alone does not prove integration. Missing, excluded or zero-test consumers
make integration `NOT ASSESSED — consumer targets not verified (<targets>)`,
whatever the aggregate row; an executed failing consumer test is FAIL. A dirty
tree or candidate mismatch (Phase 1) makes any result NOT ASSESSED.

---

## Phase 5: Game-Team Sign-off

Ask which game teams consume this release — the in-repo `game/` and any other
project the user names. For each, ask whether its integration build against
the candidate commit passes, and record the answer as the user gives it, with
the build it names. A team that has not answered is **`NOT ASSESSED — no
confirmation`**, never signed off (`release-manager`). A team that reports a
failure is a release blocker.

In `autonomous` mode no question is asked: every team is `NOT ASSESSED — no
confirmation`, and the record says the mode is why.

---

## Phase 6: Release Roles, Branch Plan, Verdict and Record

**Read `references/record.md` now and follow it** — the release-role
sign-offs, the tag, branch, LTS and hotfix plan, the verdict order and the
record template are in that file. Read it again if the conversation was
compacted or resumed during this phase.

---

## Phase 7: Next Steps

- **READY TO TAG** → the user runs the printed commands, in order, then
  tells the game teams; `producer` schedules each team's integration
  milestone.
- **NOT READY** → fix each blocker the record names (a FAIL, a failed game
  team, an `/api-review` that is not APPROVED, a missing migration guide), then
  run `/engine-release` again.
- **NOT ASSESSED** → supply each missing input — run `/api-review` on the
  uncovered changes, make the test command build and test `game/`, collect the
  game teams' confirmations, set the deprecation window or LTS support window
  in an ADR — then run `/engine-release` again.

### Rules
- Every changelog line cites a commit or an ADR.
- A team that did not confirm is `NOT ASSESSED`, never signed off.
- The version bump is `chief-engine-architect`'s call from the ADRs; the user
  confirms it.
- No `git tag`, `git branch`, `git checkout`, `git cherry-pick`, `git merge` or
  `git push` is run by this skill — they are printed for the user.
