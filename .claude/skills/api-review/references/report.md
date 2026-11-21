# /api-review — Phase 5: Verdict and Report

> Part of `/api-review`. `SKILL.md` names when to read this file; the settings it
> resolved and the rules under its later headings still apply here.

## Phase 5: Verdict and Report

**In this file:**

- The verdict, first match wins
- The report template

### The verdict

First match wins:

1. **REJECTED** — a reviewer returned REJECT, or a row has a C ABI struct or
   versioned interface edited in place (`references/surface.md` 2c.1).
2. **NEEDS REVISION** — any other finding on any row (2c, 2d); a reviewer
   returned CONCERNS; or a migration note that Phase 3 required is not in the
   repository (none exists and none was drafted, or the user declined to write
   the draft).
3. **NOT ASSESSED** — no failure above, and any of these: a row is
   `NOT ASSESSED`; a check on a row could not run (no deprecation window
   recorded, the window unit not stated, no engine release tags to count a
   deprecation window against, a Proposed ADR); the Rust surface could not be
   read; the migration note is DRAFT or `engine-technical-writer returned no
   note`; a required reviewer returned `no sign-off returned`; a reviewer
   returned NOT ASSESSED; `reviewer ownership unresolved` for a changed path.
   Any other `NOT ASSESSED` line of this review lands here too. Name each
   reason.
4. **APPROVED** — every changed public item is classed, no row has a finding,
   every required migration note is written, and every required reviewer
   returned APPROVE. `APPROVED — no public surface change` is reachable only
   when Phase 2 derived the whole surface (C++ and Rust) and the range touched
   none of it.

**NOT ASSESSED ranks below REJECTED and NEEDS REVISION and above APPROVED.** A
known problem is more actionable than an unknown, and a review that could not
check part of the change has not shown that part is safe to merge.

**Every verdict line names what did not run**, including a skipped sign-off:

> `Verdict: APPROVED — additive only; sign-off skipped (additive-only change, review_mode: solo)`
> `Verdict: NOT ASSESSED — removal of engine::jobs::submit_legacy: no deprecation window recorded in docs/architecture/; core-systems-lead: no sign-off returned`

### The report template

```markdown
# API Review — [short name]
Generated: [date]   Range: [<base>..<head> as given | working tree vs HEAD]   Ships in: [--next version | next release]
Base: [full hash]   Head: [full hash | working tree]
Reviewed commits: [every full hash of git log --format=%H <base-hash>..<head-hash>, space-separated | none — working tree]

## Verdict
[REJECTED | NEEDS REVISION | NOT ASSESSED | APPROVED] — [every NOT ASSESSED item and every skip, with its reason]

## Inputs
| Input | Status | Source |
|-------|--------|--------|
| Diff range | FOUND / ABSENT | [range] |
| C++ public surface | FOUND [n modules] / ABSENT | engine/**/include/, *.cppm/*.ixx |
| Rust public surface | FOUND [n crates, read by: listing / source] / ABSENT / NOT ASSESSED — reason | [workspace Cargo.toml] |
| Engine release tags | FOUND [list] / none tagged | git tag --list |
| ADRs cited | [ADR ids with Status] / none | adr-files.sh list |
| Migration note | FOUND / ABSENT / DRAFT / not needed | [path] |

Changed files not public: [n] [names when ≤ 10]

## Changes
| # | Item | File:line | Module | Class | Findings | Status |
|---|------|-----------|--------|-------|----------|--------|
| 1 | [symbol] | [path:line] | [module] | [breaking-abi / breaking-source / removal / deprecation / additive / compatible] | [finding, or none] | [OK / FINDING / NOT ASSESSED — reason] |

## Deprecation and Removal
| Item | Deprecated in (commit, first release) | Releases shipped deprecated | Window (ADR) | Met? |
|------|---------------------------------------|-----------------------------|--------------|------|
[or: none in this change]

## Migration Note
[path written | drafted, not written — the user declined | DRAFT — ADR-NNNN is Proposed | NOT ASSESSED — reason | not needed — additive or compatible changes only]

## Sign-off
| Reviewer | Modules | Result | Reason |
|----------|---------|--------|--------|
| chief-engine-architect | all | [APPROVE / CONCERNS / REJECT / NOT ASSESSED — reason] | |
| [lead] | [modules] | | |
[or: Sign-off skipped — additive-only change, review_mode: <value>]

## Routed
- [each finding → the owning lead or specialist; doc-comment-only changes → engine-technical-writer]

## Not Assessed
- [every item that could not be checked, its reason, and what would let it be checked]
```

Close the run with the verdict line, the report path (or `not written — the user
declined`), and Phase 6's next step for that verdict, then:
Run status: **COMPLETE** — API review produced. That word says the review was
produced; the verdict line above is what it found. The other outcomes are the
two stops in SKILL.md: `NOT ASSESSED — engine.name is not Custom` and
`NOT ASSESSED — no change to review`.

---
