---
name: api-review
description: "Custom engine: review a change to the engine's public surface — C++ headers, Rust pub API, C ABI. Classifies breaking, additive and deprecation; checks the deprecation window, migration note and sign-off."
argument-hint: "[<base>..<head> | --working-tree] [--next <version>]"
user-invocable: true
allowed-tools: Read, Glob, Grep, Write, Agent, AskUserQuestion, Bash(git diff *), Bash(git log *), Bash(git show *), Bash(git merge-base *), Bash(git rev-parse *), Bash(git tag --list*), Bash(git status *), Bash(bash "*/.claude/skills/api-review/../../hooks/yaml-helper.sh" resolve_config *), Bash(bash .claude/scripts/adr-files.sh list), Bash(bash .claude/scripts/adr-files.sh where)
model: sonnet
---

!`bash "${CLAUDE_SKILL_DIR}/../../hooks/yaml-helper.sh" resolve_config --keys engine,review_mode,automation,workflow`

Resolved above — use as-is. No block → defaults in
`.claude/docs/config-resolution.md`.

# API Review

Every `AskUserQuestion` call follows `.claude/docs/automation-modes.md`
(collaborative asks always · guided major-only · autonomous logs and proceeds;
`automation_always_ask` categories always prompt).

A change to a public header, a `pub` item or a C ABI struct goes through this
review before merge (`.claude/agents/chief-engine-architect.md`, API and ABI
Standards). Every breaking or deprecating change needs a deprecation window, a
migration note written with `engine-technical-writer`, and sign-off from
`chief-engine-architect` (`.claude/rules/engine-api-code.md`, Public API and
deprecation). This skill checks each of those against the diff and reports what
it could not check.

It reviews and drafts. It never edits engine code or headers, never moves an
ADR's status, and runs only read-only `git` commands.

## Phase 0: Engine Check

**First, before anything is read or spawned.** Read the `engine:` line above:

- `engine: Custom` → continue.
- Anything else, or unset → **refuse, and say so** — never run a reduced review:

  > `/api-review did not run: it needs engine.name: Custom, and this project's engine is <value | unset>.`
  > `It reviews the public surface of an engine this project builds itself (engine/<module>/include/, the engine's crates). <engine> ships its own API, which this project does not version.`
  > `For a native plugin or engine module on <engine> (a GDExtension, a Unity native plugin, an Unreal module), run /code-review on the change; to change the engine, run /setup-engine.`

  Then stop. Verdict: **NOT ASSESSED — engine.name is not Custom**.

## Insufficient input — check this before producing any report

**If the inputs this review needs do not exist, the answer is "could not
review" — not an approval.**

1. List the inputs: the diff range, the public surface it touches (Phase 2),
   the ADRs (`bash .claude/scripts/adr-files.sh list`), any existing migration note under
   `docs/engine/migration/`, and the engine release tags.
2. Record each `FOUND` or `ABSENT` — not "assumed present".
3. A check whose input is ABSENT reads **`NOT ASSESSED — <reason>`**. It is
   never left out and never read as a pass.
4. Not a git repository, or the range resolves to nothing → stop:
   **`NOT ASSESSED — no change to review`**, naming the range tried.

**A diff that touches no public file is not the same as a diff that was not
read.** "No public surface change" is reported only when Phase 2 derived the
surface and found the range outside it.

---

## Phase 1: Find the Change

Read the argument:

- `<base>..<head>` → that range. Check both ends with `git rev-parse --verify`.
- `--working-tree` → uncommitted changes against `HEAD` (`git diff HEAD`), and
  `git status --short` to list untracked public files, which `git diff` does
  not show.
- No argument → propose `$(git merge-base main HEAD)..HEAD` (the branch's
  changes against the trunk) and ask; offer `--working-tree` as the other
  option. Never pick one silently.

**Pin the range before reading it.** A branch name or `HEAD` moves, so the
review records what it reviewed, and `/engine-release` matches against that
record, never against the range re-resolved later:

- `Base:` and `Head:` — the full hashes, `git rev-parse <base>` and
  `git rev-parse <head>`. Every later step uses the hashes, not the names.
- `Reviewed commits:` — `git log --format=%H <base-hash>..<head-hash>`, every
  full hash.
- `--working-tree`: `Base:` is `git rev-parse HEAD`, `Head:` is `working tree`,
  and `Reviewed commits: none — working tree` (it reviews no commit).

`--next <version>` names the engine release the change will ship in. Without
it, the review writes `next release` and the deprecation messages are checked
for a removal release only by their form (Phase 2).

Find the engine release tags: `git tag --list` and keep those the project uses
for engine releases (`engine-v*` when `/engine-release` set the scheme, or
whatever scheme its record names). None → `Engine releases: none tagged`; every
removal is then `NOT ASSESSED — no engine release tags to count a deprecation
window against`.

---

## Phase 2: Derive the Public Surface and Classify Each Change

**Read `references/surface.md` now and follow it** — how the C++ and Rust
public surface is derived, the classification table, and the deprecation,
removal and boundary checks are in that file, not here. Read it again if the
conversation was compacted or resumed during this phase.

At the end of this phase there is one row per changed public item, each with a
class (`breaking-abi`, `breaking-source`, `removal`, `deprecation`, `additive`,
`compatible`) or `NOT ASSESSED — <reason>`, its findings, and the module it
belongs to.

---

## Phase 3: Migration Note

Needed for every row classed `breaking-abi`, `breaking-source`, `removal` or
`deprecation`. None of those → `Migration note: not needed — additive or
compatible changes only`, and go to Phase 4.

1. Find what exists: a note in the diff itself, or under
   `docs/engine/migration/` (`<last-release>-to-<next>.md`, or the layout the
   project already uses — follow it and say so).
2. Spawn `engine-technical-writer` via Agent with: the classified rows, the
   public-surface diff, and the ADRs the change cites with their Status. Ask it
   to review the existing note, or draft one in its migration-guide structure
   (Summary → Who is affected → Changes table → Before/After → Steps → How to
   verify → Known gaps), and to return the text — not to write it.
3. A note drafted from a **Proposed** ADR comes back labelled DRAFT. Record
   `Migration note: DRAFT — ADR-NNNN is Proposed`; it counts as not yet written
   in the verdict (`NOT ASSESSED`), because the decision it documents is not
   made.
4. The agent cannot run or returns no note → `Migration note: NOT ASSESSED —
   engine-technical-writer returned no note`.

Show the note, then ask: *"May I write this migration note to
`docs/engine/migration/[last-release]-to-[next].md`?"* — appending a section when
the file exists. On no, the note stays in the report and the migration row says
`drafted, not written — the user declined`, which counts as missing in the
verdict.

---

## Phase 4: Sign-off

**Which reviewers.** `chief-engine-architect` always, plus the owning lead for
every changed module. Resolve paths and aliases through the project's module map
and `.claude/docs/custom-engine-layout.md`; resolve each owner's lead from its
Custom-engine coordination section and `.claude/docs/agent-roster.md`. An owner
that is itself a lead reviews directly. Deduplicate reviewers and record the
path → owner → lead mapping before spawning.

This includes `sim` → simulation-systems-lead, and `cinematics`, `camera` and
legacy `sequencer` → cinematics-sequencer-engineer → editor-architect, with the
same chain for registered crate aliases. The owning lead coordinates additional
runtime handoff review with affected leads. Unmapped ownership or a missing
lead is `NOT ASSESSED — reviewer ownership unresolved (<paths>)`; ask CEA to
resolve it before sign-off rather than treating CEA alone as complete coverage.

**When.** For a change with any `breaking-*`, `deprecation` or `removal` row,
the sign-off runs at **every** `review_mode`: `.claude/rules/engine-api-code.md`
requires it, and it is not a director gate (`.claude/docs/director-gates.md`
lists none for this skill), so `review_mode` does not waive it. For a change
whose rows are all `additive` or `compatible`, it runs at `full`; at
`lean` or `solo` print `Sign-off skipped — additive-only change, review_mode:
<value>`.

Spawn every reviewer in one message (independent), each with: the classified
rows for its modules (CEA gets all), the public-surface diff, the migration
note or its status, the ADRs cited, and this instruction: *"Return APPROVE,
CONCERNS or REJECT on the first line, then the reason. If an input you need is
missing, return NOT ASSESSED naming it. A problem you did find still takes
CONCERNS or REJECT."* Collect every result before Phase 5.

A reviewer that returns nothing, or cannot be spawned, is
`<agent>: NOT ASSESSED — no sign-off returned`. Never write a sign-off the agent
did not give.

---

## Phase 5: Verdict and Report

**Read `references/report.md` now and follow it** — the verdict order and the
report template are in that file. Read it again if the conversation was
compacted or resumed during this phase.

Show the verdict, the change table and every `NOT ASSESSED` line, then ask:
*"May I write this API review to
`production/qa/api-reviews/api-review-[date]-[short-name].md`?"* Write only after
a yes, creating the folder if it is absent. On no, the review stays in the
conversation and the closing line says it was not written.

---

## Phase 6: Next Steps

- **APPROVED** → merge as normal; `/engine-release` reads this report when it
  cuts the release that contains the change.
- **NEEDS REVISION** → fix what the findings name (deprecate before removing,
  add the replacement beside the old API, a `_v2` interface beside a C ABI
  struct, a migration note), then run `/api-review` again on the new range.
- **REJECTED** → take the reviewer's reason to `/architecture-decision` when the
  change needs a decision first, or revert the public part of the change.
- **NOT ASSESSED** → supply what is missing (a Rust public-API listing, the
  ADR that sets the deprecation window, engine release tags, a reviewer's
  sign-off), then run `/api-review` again.

### Rules
- Every row cites the file and line of the diff it comes from.
- A class is decided from the diff, never from a commit message.
- A breaking change is not made acceptable by a migration note alone; it also
  needs its deprecation window (`.claude/rules/engine-api-code.md`).
- This skill never edits engine code, headers, ADRs or tests, and never runs a
  `git` command that changes the repository.
