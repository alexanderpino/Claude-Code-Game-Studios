# Engine-support implementation audit

Date: 16 November 2026. Baseline: `abc0de79d6ceb0b5d7aa693945849b3937afbe6a`.
Status: **superseded by the fix plan.** This file records the pre-plan audit
(E01–E08, C01–C03, D01–D05). Its result, recorded at the time as converged
over the 63-path snapshot, no longer holds: a later harsh-critic review of the
whole change found six blocking defects (AAA-ENGINE-2026 F1–F6), and the fix
plan `fix-plan.md` replaced this audit. The current state is under "Final
state" below and in `CONTINUE-ENGINE-SUPPORT.md`. No completion claim for live
Claude behavior or production engine support.

## Final state (18 November 2026)

- Commit state: Phases 1–10 are committed on `feature/custom-engine-support`
  at `4b4aaea` and pushed; Phase 11 is committed as `7929b58` on
  `feature/content-xr-roles` (branched from `4b4aaea`), pushed, not merged.
  Phase 12 (part 2) is committed as `9e135e7` on
  `feature/custom-engine-xr-numerics-demo`. Phases 1–12 are merged into `main`
  through PR #1 (`22fbb13`). Phase 13 (agent models and effort) is
  implemented on `feature/agent-model-effort`, branched from `22fbb13`,
  uncommitted; its exit checks (6.1) passed after AM38(e), and its critic (AAA-ENGINE-2026-P13) blocked round 1 on F1-F6, which the fixes answer, and ended round 2 with Push: clear (F9, a follow-up, recorded and fixed).
- The fix plan (revision 4, amendments AM1–AM40, Phases 8, 9, 10, 11, 12 and 13 in its
  sections 10, 11, 12, 13, 14 and 15) is implemented through Phase 13. Phase 10
  included the main session's re-pin of the shared-file manifest (AM27); its
  critic, AAA-ENGINE-2026-P10, ended at round 2 with every finding resolved (F1, the
  phase note's hunk counts; F2, `/create-epics` selecting a module's TR entries
  by `system:`). Phases 1–9 were implemented in the order 1, 2, 3,
  4, 7, 6, 5, 8, 9. Phases 1–8 each passed their harsh-critic review: findings
  files AAA-ENGINE-2026-IMPL (Phases 1–2), -P3, -P4, -P7AB, -P7C, -P7D, -P6,
  -P5 and -P8, every finding resolved or recorded in the plan; the plan itself
  was reviewed as AAA-ENGINE-2026-PLAN (3 rounds, F21 left as a follow-up for
  the owner). `CONTINUE-ENGINE-SUPPORT.md` has the per-review table.
- An independent score at snapshot S11 was 8.7 / 10 (deductions D1–D9).
  Phase 8 (fixes 8.1–8.9) addressed them and passed its critic
  (AAA-ENGINE-2026-P8, 3 rounds: F1–F11 resolved in round 2; follow-ups F12,
  F13 fixed by the main session and confirmed in round 3).
- A second independent score at snapshot S15 was 9.2 / 10 (deductions N1–N5),
  a third at S16 was 9.4 / 10 (P1–P4, AM22), and a fourth at S23, after Phase
  10 and its critic, was 9.5 / 10. Phase 9 (fixes 9.1–9.4 and
  AM20 to AM26) addressed them. Its critic, AAA-ENGINE-2026-P9, ran 4 rounds:
  F1–F8 resolved in round 2, F9–F11 and F13–F15 in round 3; F12 (the
  diff-based shared-file test) was escalated at round 3 and stayed escalated
  at round 4. The owner decided on 2026-11-17 to replace that test with an
  approved-hunk guard (AM27); in round 5 the P9 critic re-ran every F12
  mutation against it and found F12 resolved. N3's first test (every glob added to a
  base-release rule is a Custom root) keeps one named exception,
  `shader-code.md`'s `**/*.slang`, with its reason (fix plan AM20).
- Phase 10 (section 12) is one exhaustive pass over the change at S20: 139 raw
  findings, of which triage found 128 real, 8 needing a decision (D1–D8,
  AM28), 1 already recorded and 2 refuted. Seven fix lanes worked them, red
  first. The main session then made the plan edits the lanes sent it (R65,
  R32 and the plan text for the D1–D8 decisions, AM31) and the cross-lane
  items R55 (its spec), R57, R129 and R135, which the lane notes marked
  partial or blocked.
  The guard-lane holes R20 and R22–R32 were not fixed: AM27 supersedes
  them.
- Phase 11 (section 13, AM32 (a)–(g); the OpenSpec change
  `add-content-and-xr-roles`) adds, on every engine where it is valid,
  `lighting-artist`, `cinematic-designer` and `xr-experience-designer`
  (`model: inherit`, reporting to `art-director`, `narrative-director` and
  `game-designer`); "DCC Interchange" and "Character Technology" in
  `technical-artist`, and the VR sections of `qa-lead`, `release-manager` and
  `performance-analyst`, which apply only when `platform.targets` contains
  `XR`; the `/setup-engine` XR option and the `platform` block it writes; the
  Custom seams; the reworded one-shot VR card (AM32(g)); the agent lists and
  counts; and `studio-tests/test_engine_phase11.py`. Each shared-file hunk is
  pinned under AM32, AM33, AM34 or AM35. The ledger gained S149–S176, E386–E468 and
  C168–C218. The integration checks (tasks 9.1, 9.2) passed at snapshot S24.
  The Phase 11 critic blocked round 1 on F1–F9; AM33 and the fixes answer
  them. Round 2 found them met and one new defect, F10, answered by AM34;
  round 3 ended "Push: clear". The re-score (task 9.4, score report 5) gave
  9.4 at S27 with N1–N3, D1 and D2; AM35 answers them, and the re-check at
  S28 scored 9.6 / 10 (D2 is left open for C134–C167).
- Phase 12 (section 14, AM36 (a)–(g) and AM37; the OpenSpec change
  `add-custom-engine-xr-numerics-demo`) adds, on Custom only, the XR
  contracts of `platform-engineer`, `audio-engine-engineer`, the
  `frame-budget.md` template and `cea-frame-budget.md` (each applying only
  when `platform.targets` contains `XR`); the Numerics section of
  `ecs-dod-architect` and the ULP-bound-or-tolerance rule of
  `ecs-math-code.md`; the research route of `chief-engine-architect` with the
  `/prototype` engine spike; the `/vertical-slice` tech-demo path;
  `.claude/docs/engine-industry-lessons.md` with its pointer lines; and
  `studio-tests/test_engine_phase12.py`. Its shared-file hunks are each pinned
  `custom-addition` (the `/vertical-slice` Phase 6 block re-pinned under
  AM37). The ledger gained S177–S205, E469–E578 and C219–C265. The
  integration checks passed (tasks 8.1, 8.2): `propose` found no new hunk,
  `check` reports 0 problems, and the full suite passed on the Phase 12 tree
  at S29, none skipped. The Phase 12 critic (task 8.3) blocked its round 1
  on F1–F5 and its round 2 on F6 (the fix plan's Status line), with F7 a
  follow-up; AM37 and the fixes answer them, and its round 3 ended "Push:
  clear". F7 is carried into AM36(g): a lesson's problem line, like its cost
  line, may read `NOT SOURCEABLE` with its reason. The independent re-score
  (task 8.4) gave 9.4/10 at S32 (score report 6); its N1 (three lesson
  labels: I1's and MC2's problem, M1's cost, now `NOT SOURCEABLE`) and N2
  (tighter checks in `test_engine_phase12.py`) were addressed; the re-check gave
  9.6/10 at S33.
- Suite: Phase 10's lanes ran only their own tests while other lanes were
  editing; the full suite then passed on the finished tree after the re-pin,
  none skipped, and `shared_hunks.py check` reports 0 problems. Phase 11's
  task groups ran only the test modules each task lists; the full suite then
  passed on the Phase 11 tree at S24, none skipped (task 9.2). Phase 12's
  task groups did the same, and the full suite then passed on the Phase 12
  tree at S29, none skipped (task 8.2). No count is stated
  here; the command's `Ran` line is the count, and
  `studio-tests/test_engine_phase8b.py` fails a stated count that differs from
  the suite.
- Not converged: the fix plan's open points O1–O6, O8, O10–O15 and O17–O19 are open
  (section 8; O9 is closed by fix 8.6, O16 by AM27, confirmed by the P9 and
  Phase 10 critics); O17 (AM28) records that
  the AM27 manifest does not cover files new outside base skill directories.
- Ledger: 206 sources, 586 evidence records and 269 claims
  (`run_manifest.json`, last `ledger_` entry). The P9 critic checked C124–C133
  in round 1 (C126's rewrite in round 2); the Phase 10 critic reported a
  re-fetch of 19 quotes from 13 sources of the claims Phase 10 added
  (C134–C167) in its round-1 hand-back, but its findings file does not list
  them by evidence id (O12). The Phase 12 critic (AAA-ENGINE-2026-P12)
  re-fetched every quote E469–E572 and the reused E31, E89, E331 and E332 in
  round 1 and E573–E574 in round 2, and found each verbatim; the statuses of
  C219–C265 record this. After the review, C248, C259 and C262 were rewritten
  for score report 6 N1 and E575–E578 added; their statuses record the curl
  re-fetch of their quotes, and no critic has reviewed the new wording.

## Scope and result

Continued the existing A1/A2/A3/B/C1 audit without resetting or replacing the
pre-existing Copilot changes. This pass inspected the ownership/coverage map,
setup, implementation/helper/frame workflows, API and memory audit scope,
release candidate and inventory checks, benchmark timing definitions,
security evidence requirements, and critical memory/queue/audio/graph/cooking
examples. The research report and its earlier source-validation record remain
separate evidence. No new external research claim was added in this pass.

The current pass found and repaired these concrete integration defects:

| ID | Finding and repair | Evidence and limits |
|---|---|---|
| E01 | Setup assigned runtime `engine/assets/` to tooling, contrary to the module map. Setup now uses world-streaming-engineer. | Cross-table ownership test failed on this exact row, then passed. |
| E02 | Release required `engine/` and inventoried only that directory; memory audit defaulted to it. Supported crate-only engines could be rejected or omitted. Shared root resolution now covers mapped engine modules and shared build inputs; release, memory/API audits and frame workflows use it. | Source inspection and crate-only behavioral scenarios; live Claude scenarios unrun. |
| E03 | Both audio path-rule examples mixed into stale output, although the agent examples had already been fixed. Both now clear output first. | Actual Rust rule snippet compiled with offline stubs: silence and waveform tests failed before repair; `3 passed; 0 failed` afterward. C++ edit inspected, not compiled. |
| E04 | Documented `crates/sequencer/` alias bypassed the simulation rule. Added its glob. | Exhaustive module-table/rule test failed only on that alias, then passed. |
| E05 | Helper workflow read game GDDs before reaching the Custom module branch; frame implementation/test paths still named only the older layout. Module-contract discovery and mapped crate/test paths are now explicit. | Static instruction review and behavioral scenarios; no live helper generation claimed. |
| E06 | Release could read a passing CTest row without an affirmative build, admitting a previously built test binary. PASS now requires successful candidate-build evidence or successful Cargo test compilation. | Disposable actual-helper probe produced `build - skipped: no commands.build`, `tests total=3 passed=3 failed=0`, then `custom:ctest-pass`. Release regression scenario now rejects that as NOT ASSESSED; live release-skill execution unrun. |

Setup's coverage pointer is intentionally inside the emitted Engine Specialists
template. Its Markdown fence/table placement was inspected. The direct-check
commands and their limits are documented in `studio-tests/README.md`.

## Independent critic findings

The independent read-only critic (`/root/engine_support_critic`) completed one
bounded review of the scope in `review-snapshot.json` and reported three
findings. The parent confirmed each in the cited source before repairing it.
Regression scenarios were added to the specs before each repair; they are
static specifications, not executed live runs. The critic then ran one targeted
closure check over only these findings and their changed sites: all three closed
in the instructions, no residual at those sites. It edited no files.

| ID | Severity | Finding and repair | Evidence and limits |
|---|---|---|---|
| C01 | Serious | Memory-audit §2d accepted clean-tree sanitizer logs by timestamp and dirty receipts by commit plus filenames, so another branch's newer log or a second edit to the same dirty file could count as current. §2d now binds a log to the full tested revision and the contents of relevant source/build inputs (dirty, untracked and active ignored); dates only reject stale logs; a missing binding needs explicit current-contents/build-settings confirmation or reads `NOT ASSESSED — tested source/build identity not established`. SKILL.md records identity/binding and allows read-only `git hash-object` (without `-w`). Security-audit's fuzz receipts inherit the rule. | Memory-audit spec Cases 10/11 and the Case 8 receipt variant added before the repair. Closure check: closed. Live skill runs unrun. |
| C02 | Moderate | Engine-release Phase 4 found consumer tests by grepping `tests/integration/` and a literal `game` in the command, a C++-layout assumption. It now resolves consumer packages/targets from manifests and the module map and requires candidate-bound, nonzero executed consumer tests, including Rust `game/tests/` under `cargo test --workspace`; excluded, zero-test or aggregate-only evidence is `NOT ASSESSED — consumer targets not verified`. | Engine-release spec Case 10 added before the repair. Closure check: closed. Live skill runs unrun. |
| C03 | Moderate | API-review Phase 4 used an incomplete static lead table that omitted registered module leads. It now resolves path → owner → lead through the module map, coordination sections and roster, covering sim, cinematics, camera, sequencer and crate aliases; reviewers are deduplicated, unresolved ownership is `NOT ASSESSED — reviewer ownership unresolved`, and breaking-change sign-off still runs at `solo`. | API-review spec Case 8 added before the repair. Closure check: closed. Live skill runs unrun. |

Parent findings in the closing pass, both spec-only:

| ID | Finding and repair | Evidence and limits |
|---|---|---|
| E07 | The memory-audit spec still described the pre-C01 rule: its Summary, the Static Assertion (`git status --porcelain` on the scope, `git log -1`), and Case 8's command, question and reason (`scope has uncommitted changes the run may not include`). Updated to §2d: `--untracked-files=all` over source roots and build inputs, read-only `git hash-object`, the `identity not established` reason, and unbound logs in Protocol Compliance. The stricter requirement is kept, not weakened. | A repository-wide search finds no remaining copy of the old reason or question text. |
| E08 | The five cases added in this audit (memory-audit 10/11, engine-release 9/10, api-review 8) had no `**Assertions:**` block, the checklist `/skill-test spec` grades, so they checked nothing. Added assertions taken from each case's Expected behaviour, using the skills' own reason strings. | Round-2 read of the E07/E08 deltas found D01–D05 below. |

Round 2: an independent reader reviewed only the E07/E08 spec deltas against
the skill text. It found five spec defects, each confirmed by the parent in the
source and repaired; api-review Case 8 and engine-release Case 9 had none. The
same reader then ran a targeted closure check over only D01–D05 at their changed
sites: all five closed. It noted one ambiguity, not a defect: Case 8's
weak-receipt clause was not tied to the no-confirmation path. That clause now
reads "without that confirmation".

| ID | Severity | Finding and repair | Evidence and limits |
|---|---|---|---|
| D01 | Moderate | Memory-audit Case 11 did not pin the user's answer, so a correct run that accepted an explicit confirmation and reached CLEAN failed the assertion. The fixture now pins HEAD = revision A and a no/don't-know answer; the assertion reads NOT ASSESSED while unconfirmed. | Spec-only. |
| D02 | Minor | Case 11's untracked parser file had no path, so it could fall outside the `memory` scope, and H1's hash scheme was unstated. Now `crates/memory/src/parser.rs`, with H1 a git blob hash. | Spec-only. |
| D03 | Moderate | Case 8 left NOT ASSESSED after a no/don't-know answer, and the explicit-confirmation variant, unasserted; its fixture did not pin "no read risk". A skill ignoring every confirmation passed every case. Added the fixture line and both assertions. | Spec-only. |
| D04 | Moderate | The Static Assertion required `Bash(git hash-object *)`, which also pre-approves `git hash-object -w` (writes to `.git`) in a read-only skill. Memory-audit `allowed-tools` is now `Bash(git hash-object -- *)`, the form §2d documents; the assertion requires a rule that cannot match `-w`. | Command check on the frontmatter: RED (permissive rule present) before, GREEN after. `skill-lint.sh memory-audit`: 1 of 1, frontmatter ok. |
| D05 | Minor | Engine-release Case 10 pinned package `(sample-client)` although the skill's reason names targets. It now accepts the package or its `boot` target. | Spec-only. |

Observed outside this scope, not changed: security-audit applies memory-audit's
freshness checks to fuzz receipts, but its `allowed-tools` grants no git
command. That path fails safe (unconfirmed working-tree evidence is NOT
ASSESSED), so it is a usability gap, not a false pass.

## Verification observed after the critic repairs

Python commands used
`C:/Users/AlexanderPino/AppData/Local/Python/pythoncore-3.14-64/python.exe`;
shell commands used `C:/Program Files/Git/bin/bash.exe`. No global PATH change.

| Check | Observed result |
|---|---|
| `python -m unittest discover -s studio-tests -p 'test_*.py' -v` | `OK` after the C01–C03 repairs and again after the D01–D05 repairs, over the pre-plan suite (registry/path/ownership checks and generated-CI fixture tests). The suite has grown since; the current count is under "Final state". |
| `python studio-tests/check_audio_examples.py` | `3 passed; 0 failed`: silence, additive waveform across callbacks, bounded command consumption. Uses actual rule callback; deterministic surrounding stubs. |
| Compiler used for the offline example | `rustc 1.93.0 (254b59607 2026-01-19)`. This is the installed verifier, not a project toolchain pin. |
| `bash -n` on `.claude/scripts/*.sh` and `.claude/hooks/*.sh` | 67 shell files checked, failure flag 0. |
| `bash .claude/scripts/skill-lint.sh all` | `checked 84 of 84`, exit 0; 84 `check1` rows read `frontmatter=ok missing=- name=match`, none otherwise. Rows for memory-audit, engine-release and api-review inspected. After D04, `skill-lint.sh memory-audit`: `checked 1 of 1`, frontmatter ok. These are structural observations, not behavioral verdicts. |
| `bash .claude/scripts/agent-check.sh --agent cinematics-sequencer-engineer` | Not rerun: no agent file changed after the pre-critic run. That run exited 0 with real Python on process PATH; 74 agents, valid cinematics frontmatter; three asks-user notes are routed through its caller by the agent's collaboration protocol. |
| `git -c core.whitespace=blank-at-eol,blank-at-eof diff --check` | Exit 0 on the tracked diff; only LF/CRLF conversion warnings. |
| Same check, `git diff --no-index --check /dev/null <file>` per untracked file | 102 untracked files, 0 with whitespace errors; the five files edited after that scan rechecked clean. The pre-critic run covered only the tracked diff. |

A pre-critic run observed the same Python, Rust, shell and lint counts; it is
superseded by this run, not relabelled as it.

The Python registry checks match 81 public skills plus three old-name aliases,
74 agents, and their catalog/spec registration. The module check exercises each
documented engine module and its crate alias against the published path globs.
It uses Python fnmatch as a structural approximation, not Claude's live matcher.

No engine runtime exists here. No complete C++ engine build, target-hardware
run, console certification, GPU capture, sanitizer campaign or live Claude
behavioral scenario was performed. A passing offline callback test establishes
only the exercised buffer and command-count behavior. New release, helper and
crate-only scenarios remain specifications awaiting live execution.

## Requested independent critic

Called the refreshed Gemini MCP `ask_gemini` with
`model: gemini-3.1-pro-preview`, review-only and no writes. It failed before a
critique with `ProjectIdRequiredError`: this account requires
`GOOGLE_CLOUD_PROJECT` or `GOOGLE_CLOUD_PROJECT_ID`. The user was asked for the
project ID. No fallback-model output or successful critique is recorded.

The subsequent direct CLI attempt was cancelled at the user's instruction:
"stop using gemini, ask a critic". The CLI returned cancellation code 130, with
no final critique. Gemini is no longer a required reviewer; no Gemini critique
exists, and earlier stalled CLI attempts are not reviews. The independent
critic's review and closure check are recorded under "Independent critic
findings". No commit, push, PR, message, deployment or publication was performed.

## Review convergence record

```yaml
scope_id: 1b274cb404e2d87236256f8f8105df2637d916d47c73a7250945901a91a10d6a
previous_scope_id: 2652d0cab02c7adcb37c76b72d400416a776603e4c073cde47a929beacdda22d  # same scope; roster corrected, C03 paths added
origin: CONTINUE-ENGINE-SUPPORT.md original A1/A2/A3/B/C1 task
baseline: abc0de79d6ceb0b5d7aa693945849b3937afbe6a
snapshot: review-snapshot.json, content_hash b9bd5126bbb22f0e7852949fdc70280bfd46992ebb748d49cb484af240081a27
paths: review-snapshot.json paths (63)
reviewers:
  - parent: bounded integration and critical-example audit
  - independent critic: round 1 bounded review and C01-C03 closure check (replaced Gemini at user instruction)
  - independent spec-delta reader: round 2, E07/E08 spec deltas only, then D01-D05 closure check
round: 2
findings:
  - E01: closed, ownership regression green
  - E02: closed in instructions, live scenarios unrun
  - E03: closed, Rust example regression green, C++ inspected
  - E04: closed, path regression green
  - E05: closed in instructions, live scenarios unrun
  - E06: closed in instructions, helper observation reproduced, live scenario unrun
  - C01 (Serious), C02, C03 (Moderate): closed in instructions; critic closure check passed; live unrun
  - E07, E08: closed by parent; reviewed in round 2
  - D01, D03, D04 (Moderate), D02, D05 (Minor): closed; reader's closure check passed at the changed sites; Case 8 clause clarified after it (not a defect)
coverage: round-1 critic coverage for unchanged paths; round-2 reader coverage and closure check for the spec deltas and memory-audit allowed-tools; hashes in review-snapshot.json; no agent summary accepted as execution proof
closure_check: passed  # for the pre-plan scope only
result: superseded  # recorded at the time as converged for this 63-path scope; replaced by fix-plan.md after AAA-ENGINE-2026 F1-F6
next_action: see "Final state" above and CONTINUE-ENGINE-SUPPORT.md. Instruction coverage only; live Claude skill runs, engine builds and hardware tests remain unrun. No commit is authorized.
```
