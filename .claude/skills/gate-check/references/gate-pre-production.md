> Gate definition, loaded by `/gate-check` for the target stage only.
> Never load the other five — one gate applies per invocation.


# Gate: Technical Setup → Pre-Production


**Required Artifacts:**
- [ ] Engine chosen (CLAUDE.md Technology Stack is not `[CHOOSE]`)
- [ ] Project config populated (`project.yaml` has engine/naming/performance set, or legacy `.claude/docs/technical-preferences.md` populated)
- [ ] Art bible exists at `design/art/art-bible.md` with at least Sections 1–4 (Visual Identity Foundation)
- [ ] At least 3 Architecture Decision Records in `docs/architecture/` covering
      Foundation-layer systems (scene management, event architecture, save/load)
- [ ] Engine reference docs exist in `docs/engine-reference/[engine]/`
- [ ] Test framework initialized: the engine's test root exists — `tests/unit/` and `tests/integration/` (Godot, Web; Custom adds `tests/benchmarks/`), `Assets/Tests/EditMode/` and `Assets/Tests/PlayMode/` (Unity), or `Source/<Module>/Private/Tests/` (Unreal); see `.claude/docs/directory-structure.md`
- [ ] CI/CD test workflow exists at `.github/workflows/tests.yml` (or equivalent)
- [ ] At least one example test file exists to confirm the framework is functional
- [ ] Master architecture document exists at `docs/architecture/architecture.md`
- [ ] Architecture traceability index exists at `docs/architecture/requirements-traceability.md`
- [ ] `/architecture-review` has been run (a review report file exists in `docs/architecture/`)
- [ ] `design/accessibility-requirements.md` exists with accessibility tier committed
- [ ] `design/ux/interaction-patterns.md` exists (pattern library initialized, even if minimal)

**Which `/architecture-review` report counts.** Read the `Mode:` line of each
`docs/architecture/architecture-review-*.md`, and for each item below use the
newest report whose mode checked it:

| Item | Modes that check it |
|---|---|
| `/architecture-review` has been run | `full` |
| Traceability matrix has zero Foundation layer gaps | `full`, `coverage`, `rtm` |
| Engine audit shows no deprecated API usage | `full`, `engine` |

A `single-gdd` report saw one system and a `consistency` report only compared
ADRs, so neither counts here. When no report's mode checked an item,
that item is NOT ASSESSED, never passed on a narrower report: name the newest report's
mode and the run that closes it (run `/architecture-review full`, or the mode
the table names). A report with no `Mode:` line was written before 1.2.0 and
does not say what it checked, so it counts for none of the three, as
`/architecture-review` itself rules.

**Quality Checks:**
- [ ] Architecture decisions cover core systems (rendering, input, state management)
- [ ] Technical preferences have naming conventions and performance budgets set
- [ ] Accessibility tier is defined and documented (even "Basic" is acceptable — undefined is not)
- [ ] At least one screen's UX spec started (often the main menu or core HUD is designed during Technical Setup)
- [ ] All ADRs have an **Engine Compatibility section** with engine version stamped
- [ ] All ADRs have a **GDD Requirements Addressed section** with explicit GDD linkage
- [ ] No ADR references APIs listed in `docs/engine-reference/[engine]/deprecated-apis.md`
- [ ] All HIGH RISK engine domains (per VERSION.md) have been explicitly addressed
      in the architecture document or flagged as open questions
- [ ] Architecture traceability matrix has **zero Foundation layer gaps**
      (all Foundation requirements must have ADR coverage before Pre-Production)

**ADR Circular Dependency Check**: run the deterministic graph builder rather than
reading every ADR to trace the graph by hand — a manual trace across a dozen ADRs
eventually misses an edge; the script cannot:
```
Bash: bash .claude/scripts/adr-dep-graph.sh
```
It prints `ADRS`, `EDGES` (one `adr-A -> adr-B` per Depends-On reference),
`NO_DEPS_SECTION` (ADRs with no Depends On), `UNFILLED_DEPS` (a Depends On row
still the template's placeholder), a `CYCLE:` line per ADR on a dependency cycle
with its edges into that cycle, `BLOCKED_BY_CYCLE` (ADRs on no cycle that depend
on one) and `ORDER` (the rest, dependencies first).
- **Any `CYCLE:` lines → FAIL**: "Circular ADR dependency: [the nodes on the
  `CYCLE:` lines]. Neither can reach Accepted while the cycle exists. Remove one
  'Depends On' edge shown on a `CYCLE:` line to break the cycle." Name the
  `BLOCKED_BY_CYCLE` ADRs as waiting on the cycle, not as part of it: none of
  their own edges is the one to remove.
- No `CYCLE:` lines → this check passes. But the acyclic result is only as
  trustworthy as the dependency sections are complete: if `NO_DEPS_SECTION` or
  `UNFILLED_DEPS` lists many ADRs, surface that as a CONCERNS note rather than a
  clean pass, naming each `UNFILLED_DEPS` ADR as unfilled (what it depends on is
  unknown, not none).

**Engine Validation** (read `docs/engine-reference/[engine]/VERSION.md` first):
- [ ] ADRs that touch post-cutoff engine APIs are flagged with Knowledge Risk: HIGH/MEDIUM
- [ ] `/architecture-review` engine audit shows no deprecated API usage
- [ ] All ADRs agree on the same engine version (no stale version references)

## Workflow tier reductions

The checklist above is the **`full` baseline**. At lower tiers apply the
reduction for the resolved tier; items not named keep their status above.
Reductions only ever *relax* a requirement — `workflow_overrides` is the
only thing that adds one.

- **`full`** — engine + art bible §1–4+ + 3+ ADRs + architecture + UX specs started + accessibility doc + traceability index all required
- **`standard`** — art bible required **only if visual-asset stories exist**; ADRs reduced to **critical (Foundation-layer) only**; UX-specs-started, accessibility doc, interaction-patterns, traceability index → recommended
- **`minimal`** — only **engine configured** required (the minimal floor); everything else **drops**

## Custom engine additions

**Applies only when the resolved `engine` line reads `Custom`** (any case) — a
project that builds its own engine. On any other engine, or with no engine
set, skip this block and print one line in the report's checklist:
`Custom engine additions: skipped — engine is <name | unset>`. On Custom these
items are added to the checklist above; none of them replaces an item there.
Reviewer for this block: `chief-engine-architect`, through gate **CEA-ADR**
(Section 4b, "Custom engine: chief-engine-architect").

**Required Artifacts (Custom):**
- [ ] **Engine module map.** A module spec at `docs/architecture/modules/<module>.md`
      (template `.claude/docs/templates/engine-module-spec.md`) for every **MVP
      engine module**. Derive the MVP set from the master architecture document
      or the module-layout ADR — whichever names the engine modules for the MVP —
      never from a fixed list. When neither names them, the item is NOT ASSESSED:
      "MVP engine modules not named in `docs/architecture/architecture.md` or a
      module-layout ADR". A spec still holding only the template's `[...]`
      placeholders is present-but-empty (Section 5).
- [ ] **Core engine ADRs Accepted.** ADRs (`bash .claude/scripts/adr-files.sh list`) with status
      `Accepted`, written in `/architecture-decision`'s engine mode (they carry
      the `## Memory`, `## Threading`, `## Latency & Frame Budget`,
      `## ABI / API Stability`, `## Determinism` and
      `## Platform / Graphics-API Matrix` sections), that together cover:
      memory ownership and allocators · threading model · job system · ECS and
      data layout · RHI and graphics API(s) · render graph · platform layer ·
      editor UI framework (or an ADR recording that the MVP ships no editor).
      One ADR may cover several. Name each domain with no Accepted ADR; a
      `Proposed` ADR does not cover its domain.
- [ ] **CEA-ADR reviewed.** Each of those ADRs carries the line
      `CEA-ADR: <verdict> (<date>[, CONCERNS accepted])` under `## Status`
      (`/architecture-decision` writes it with the ADR at `review_mode: full`),
      with APPROVE, or CONCERNS followed by `CONCERNS accepted`. An ADR with no
      such line (written at `review_mode` `lean` or `solo`, where
      `/architecture-decision` skips CEA-ADR) is reviewed by this gate's panel
      at `review_mode: full` — Section 4b. At `solo` and `lean` the CEA gates do
      not run (Section 4b): mark the item `CEA-ADR not run — [Solo | Lean] mode`
      for each such ADR, by name, and leave it out of the verdict, as the
      panel's own skip is.
- [ ] **`performance.frame_budget_ms` is set.** Read it and
      `performance.target_framerate` from `project.yaml` (else
      `technical-preferences.md`), as the performance check in
      `3-run-gate-check.md` reads the budgets. Unset in both → this item is **NOT ASSESSED**, never PASS: a budget
      nobody set is not one the engine can be held to. Set alongside a
      `target_framerate` it disagrees with (1000 / framerate differs by more than
      0.1 ms) → CONCERNS, naming both values.
- [ ] **`docs/architecture/frame-budget.md` exists** (template
      `.claude/docs/templates/frame-budget.md`) with whole-frame CPU and GPU
      budgets each equal to `performance.frame_budget_ms`, affected subsystem
      slices, and independent-thread deadlines. Check parallel CPU work by
      critical-path wall time and overlapping GPU queues by measured frame span;
      never sum subsystem percentiles or queue busy times into a frame total.
      A whole-frame budget that differs is CONCERNS; absent slices are NOT
      ASSESSED; a file of template placeholders is present-but-empty.
- [ ] **`docs/architecture/memory-invariants.md` exists** (template
      `.claude/docs/templates/memory-invariants.md`) with real content.
- [ ] **Engine tests run and pass.** Run `bash .claude/scripts/test-run.sh custom`
      and read its `rule` row:
      - `custom:ctest-pass` or `custom:cargo-pass` → passes, with the count
      - `custom:ctest-zero`, `custom:cargo-zero`, `custom:no-test-command`, or
        `custom:0` (read by exit code only — a run of zero tests looks the same)
        → **NOT ASSESSED**, naming the rule. Zero tests are never a pass
      - `custom:build-failed` or `custom:cargo-compile-failed` → **Blocker**: the
        engine does not build
      - `custom:ctest-failed`, `custom:cargo-failed`, `custom:nonzero` → test
        failures, Blocker or CONCERNS by `testing.strict` (Section 3)
      - `timeout`, `runner-unavailable`, or `-` (no row of the ladder fits) →
        **NOT ASSESSED**, naming the rule: the run did not finish or did not
        start, so nothing was verified
- [ ] **CI builds every target platform × graphics API.** Derive the set from
      the `## Platform / Graphics-API Matrix` rows marked supported in the
      Accepted ADRs; each needs a CI job or matrix entry in `.github/workflows/`
      (or the project's CI) that builds it. Name each row with no job. A row CI
      cannot build (no runner, a console SDK the CI cannot hold) is NOT ASSESSED
      for that row with the reason — never PASS. No ADR with a matrix → NOT
      ASSESSED: "no Platform / Graphics-API Matrix in any Accepted ADR".

**Tier reductions (Custom).** Same rules as above — reductions only relax:
- **`full`** — every item above required
- **`standard`** — core engine ADRs required for memory, threading, job system,
  RHI and platform layer (the Foundation layer); the ECS, render-graph and
  editor-UI ADRs → recommended; module specs, `memory-invariants.md` and the CI
  matrix → recommended; `frame_budget_ms`, `frame-budget.md`, CEA-ADR and the
  engine tests stay required
- **`minimal`** — **`performance.frame_budget_ms` set** and **the engine builds**
  stay required; everything else drops

**"The engine builds" needs affirmative evidence** from the same
`test-run.sh custom` output — a rule that is merely not a build failure is not
evidence, because `custom:no-test-command` stops before `commands.build` runs and
`timeout` or `runner-unavailable` never finish it. It passes only on one of:
- a `build_exit 0` row with `build_timed_out no` — `commands.build` ran and
  succeeded; or
- no `build` command ran (the `build` row reads `-`), the `runner` row reads
  `cargo`, and the rule is `custom:cargo-pass`, `custom:cargo-failed` or
  `custom:cargo-zero` — `cargo test` compiled the workspace before it ran.

`custom:build-failed` or `custom:cargo-compile-failed` → **Blocker**. Anything
else → **NOT ASSESSED**: "no affirmative build evidence — <the `build` row and
the rule>"; name the fix — set `commands.build` (and `commands.test`, which a
CMake project needs before the build step runs) with `/setup-engine custom` or
`/project-settings`, then re-run the gate.

At `qa.level: minimal` the test half of the engine-tests item is non-required
(Section 2b), but the build half is not: a build that fails is a Blocker at
every `qa.level`, as the smoke check is the floor for the game.
