# /engine-release — Phase 2: Inventory and Version

> Part of `/engine-release`. `SKILL.md` names when to read this file; the settings it
> resolved and the rules under its later headings still apply here.

## Phase 2: Inventory and Version

**In this file:**

- 2a Commits in range
- 2b Public-surface changes and their `/api-review` coverage
- 2c ADRs in range
- 2d The version number
- 2e The changelog draft

`<range>` below is `<previous tag>..<candidate hash>` from Phase 1, or the
candidate's whole history on a first release.

### 2a. Commits in range

`git log --no-merges --format='%H %s' <range> -- <engine roots> <shared build inputs>`
lists the engine's commits, using the paths resolved in SKILL.md (quote each
path separately). Include private implementation and dependency/build changes,
not only public API paths. The same over consumer and test roots is context
unless a test/build file is itself a shared engine build input. Record the count.
No engine commit in range → stop: `NOT ASSESSED — no engine change since
<previous tag>`.

### 2b. Public-surface changes and their `/api-review` coverage

1. Derive the public surface the way `/api-review` does
   (`.claude/skills/api-review/references/surface.md`, 2a) — from the
   repository, not from a list. Its C++ part is every module's `include/`
   folder at any depth (`engine/**/include/**`, nested modules such as
   `engine/renderer/features/` included), not only the top-level modules.
2. `git log --format=%H <range> -- <each public path>` gives the commits that
   touched it (pathspec `':(glob)engine/**/include/**'` for the C++ headers).
3. Read every report in `production/qa/api-reviews/`. A report covers a commit
   only when the commit's full hash is on its `Reviewed commits:` line — the
   list `/api-review` pinned when it ran. Never re-run the report's `Range:`: a
   range that names a branch or `HEAD` resolves today to commits made after the
   review, which nobody reviewed. A report with no full `Base:` and `Head:`
   hashes or no `Reviewed commits:` line covers nothing:
   `NOT ASSESSED — report range not pinned (<path>)`. A squash merge, rebase or
   cherry-pick gives the change a new hash, so the new commit is not covered
   until `/api-review <hash>^..<hash>` reviews it. A report of a working tree
   covers no commit — say so.
4. One row per public-surface commit:

| Coverage | Result |
|---|---|
| Newest covering report is APPROVED | covered |
| Newest covering report is NEEDS REVISION or REJECTED | release blocker — `NOT READY` |
| Newest covering report is NOT ASSESSED | `NOT ASSESSED — /api-review <path> NOT ASSESSED` |
| No covering report | `NOT ASSESSED — no /api-review for <hash>` (and each unpinned report's `NOT ASSESSED — report range not pinned` line) |

Collect the breaking, deprecating and removal rows of the covering reports:
they are the release's breaking-change list.

### 2c. ADRs in range

`git log --name-only --format= <range> -- [adr_dir]/` (the `dir` row of
`bash .claude/scripts/adr-files.sh where`) lists the ADRs added or changed. Read each one's Status:

- **Accepted** → part of this release. Its `## ABI / API Stability` section
  names API and ABI breaks; a change to an asset or file format it records is a
  format break.
- **Proposed** → inspect whether implementation in the candidate depends on
  this unaccepted ADR. If so, `NOT READY — candidate implements unaccepted ADR
  <path>`: a document status cannot exclude code already in the candidate.
  Only a proposal with no dependent implementation in the candidate belongs
  under `Not in this release`. Unclear dependency → NOT ASSESSED, naming the
  files and decision that need confirmation. Apply this check to every ADR
  governing changed code, including ADRs unchanged during the release range.
- **Superseded** → cite the superseding ADR.

### 2d. The version number

The rule (`release-manager`, On a Custom Engine Project): **major** for a public
API or ABI break or an asset-format break, **minor** for features, **patch** for
fixes only.

- On a release branch (`--patch-of`): the range holds fixes only. An additive,
  deprecating or breaking change in it → `NOT READY — <change> is not a fix;
  it ships in the next minor` (the next major if it breaks, as above).
- Before 1.0 (`0.y.z`): what a bump means is the project's rule. Grep
  `docs/architecture/` for it; none → ask the user and record the answer. Never
  assume one.

Spawn `chief-engine-architect` via Agent with the commit list, the
breaking-change list from 2b, the ADRs from 2c and the previous version. Ask it
to return the bump (major, minor or patch) and its reason on the first lines,
then `APPROVE`, `CONCERNS` or `REJECT` for releasing this range at all — or
`NOT ASSESSED` naming a missing input.

- No version argument → propose CEA's version and ask the user to confirm.
- A version argument that differs from CEA's → show both with CEA's reason
  and ask. Never pick one silently. Unresolved → `Version: NOT ASSESSED —
  <argument> vs <CEA's>`.
- CEA returns nothing → `chief-engine-architect: NOT ASSESSED — no sign-off
  returned`; the user may still name a version, and the record says the bump
  was not reviewed.

### 2e. The changelog draft

Engine-facing, for game programmers — not player-facing (that is
`/patch-notes`). Sections, each line citing a commit hash or an ADR:

```markdown
## Engine [version] — [date]
### Breaking        (from 2b and the Accepted ADRs; each with its migration-guide anchor)
### Deprecated      (each with its replacement and removal release)
### Removed
### Added
### Fixed
### Performance     (only numbers from a /benchmark-report in production/qa/benchmarks/, cited by path)
### Not in this release   (Proposed ADRs and their dependent changes)
```

Sort commits by their Conventional Commits prefix (`feat:` → Added, `fix:` →
Fixed, `perf:` → Performance); a commit with none goes under **Other** with its
subject. A breaking or deprecating change is listed from its `/api-review` row,
never from a commit subject alone. No `/benchmark-report` in range →
`Performance: no measurement in this range` — never a claim that nothing got
slower.

---
