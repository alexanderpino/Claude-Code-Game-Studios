# /api-review — Phase 2: Public Surface and Classification

> Part of `/api-review`. `SKILL.md` names when to read this file; the settings it
> resolved and the rules under its later headings still apply here.

## Phase 2: Derive the Public Surface and Classify Each Change

**In this file:**

- 2a Derive the public surface — never from a list
- 2b Classify each changed public item
- 2c Deprecation, removal and ADR checks
- 2d Boundary checks from `engine-api-code.md`

### 2a. Derive the public surface — never from a list

The surface is derived from what the repository holds, so a module added
yesterday is covered without anyone extending this file.

**Read the reviewed revision, not the checkout.** For a `<base>..<head>` range
the code under review is the commit `<head>`. The working tree can be another
checkout, or hold uncommitted edits, so it is not read. Read each file with
`git show <head>:<path>` instead of Read, and list a folder with
`git show <head>:<dir>/` instead of Glob; read the old side of a removed or
changed declaration with `git show <base>:<path>`. Every check in 2a–2d (the
include folders, `extern "C"`, `[[deprecated]]`, `pub mod` and `pub use`
reachability) runs on those contents. Only `--working-tree` reads the working
tree.

**C++.**
- Every file under a module's `include/` folder (Glob `engine/**/include/**`)
  is public, at any depth, so a nested module such as `engine/renderer/features/`
  (`engine/renderer/features/include/renderer/features/*.h`) is covered — the
  layout is `<module row>include/…` for each `engine/` row of
  `.claude/docs/custom-engine-layout.md`. Leave out a path with a `src/`
  segment above its `include/` (a backend's private headers). Each folder that
  holds an `include/` is a module; the most specific layout row decides which.
- C++ module interface units (`engine/**/*.cppm`, `engine/**/*.ixx`): their
  `export` declarations are public.
- C ABI: any `extern "C"` block or struct in a public file is **ABI surface**,
  and so is every versioned interface struct (`…_v1`, `…V1`, a struct with a
  `version` or `struct_size` first field).
- Files under `engine/*/src/` are not public.

**Rust.**
- The engine's crates: resolve the module map and workspace members using
  `.claude/docs/custom-engine-layout.md`, Resolving source roots for workflows.
  Keep the mapped engine members, including `crates/` aliases; record the layout
  and keep game members separate. No workspace file → Glob `Cargo.toml` and
  nested `Cargo.toml` files in the mapped engine roots, skipping `target/`.
- The public API is every item reachable from the crate root through public
  paths: `pub` items in `lib.rs`, in `pub mod` submodules at any depth, and
  `pub use` re-exports. A `pub` item in a private module that nothing
  re-exports is not public; neither is `pub(crate)`.
- `#[repr(C)]` types and `extern "C"` functions that the plugin or hot-reload
  boundary uses are **ABI surface**.

**How the Rust surface is read.** Two ways, best first:

1. **A public-API listing for both ends**, which the user supplies — rustdoc
   JSON output, or a tool such as `cargo-public-api` built on it. Compare the
   two listings item by item. This skill does not run them. Their command
   lines are `NOT SOURCEABLE — <tool> flags are not covered by
   docs/engine-reference/custom/` unless that folder documents them; never
   write one from memory.
2. **Reading the source.** For each changed `.rs` file, follow `pub mod` and
   `pub use` from `lib.rs` to decide whether each changed item is reachable.
   A file whose reachability cannot be decided — a glob re-export
   (`pub use x::*`), items made by a macro, a `#[cfg(...)]` that changes what
   is exported — is `NOT ASSESSED — reachability of <file> not decidable from
   source`. Ask for a listing (way 1) rather than guess.

**Changed files.** `git diff --name-status <range>` (or `git diff HEAD
--name-status` plus `git status --short` for the working tree). Keep the files
in the surface above. Report the count of changed files outside it as
`not public`, by name when there are ten or fewer.

### 2b. Classify each changed public item

Read the diff of each public file (`git diff <range> -- <file>`) and give every
changed declaration one class. When a declaration fits two, take the first in
this table.

| Class | C++ | Rust |
|---|---|---|
| `breaking-abi` | a change to a C ABI struct's fields, order or types, or to an `extern "C"` signature, **in place**; a member added to or reordered in a class an ADR records as crossing a binary boundary | a change to a `#[repr(C)]` type or `extern "C"` fn on the plugin or hot-reload boundary, in place |
| `breaking-source` | a declaration removed or renamed with no prior deprecation; a parameter or return type changed with no overload kept; a public header moved or removed; a pure virtual added to a class callers derive from; an enumerator removed or renamed; a template constraint tightened | a reachable item removed, renamed or made non-public; a fn signature changed (a parameter added or removed, a parameter or return type changed, any change to a trait item's signature) other than the `compatible` forms; a generic bound tightened; a trait item added with no default; a trait item added that makes the trait not dyn-compatible (the Rust Reference's Dyn compatibility rules: an associated const; an associated type with generic parameters; or, unless it has `where Self: Sized`, an associated function with no `self` receiver, or a method with a type parameter, with `Self` outside its receiver, with a receiver other than `&self`, `&mut self`, `Box<Self>`, `Rc<Self>`, `Arc<Self>` or a `Pin` of one of those, or returning `impl Trait` or `async`; a by-value `self` receiver counts as `where Self: Sized`); a type parameter without a default added to a trait or a public type; a field added to a struct whose fields are all `pub` and that is not `#[non_exhaustive]`; a variant added to an enum that is not `#[non_exhaustive]`; `#[non_exhaustive]` added to an enum, a variant, or a struct with no private fields; a trait impl removed; a type that was `Send` or `Sync` no longer is |
| `removal` | a declaration removed that carried `[[deprecated]]` or the engine's deprecation macro | an item removed that carried `#[deprecated]` |
| `deprecation` | `[[deprecated("…")]]` or the engine's deprecation macro (`ENGINE_DEPRECATED(version, msg)`) added | `#[deprecated(since = "…", note = "…")]` added |
| `additive` | a new declaration, header, overload or versioned interface (`…_v2` beside `…_v1`) | a new reachable item; a defaulted trait method that keeps the trait dyn-compatible (or one on a trait that was not dyn-compatible already); a defaulted type parameter added; a new field or variant on a `#[non_exhaustive]` type |
| `compatible` | a layout change in a C++ type that is not ABI surface and that no ADR records as crossing a binary boundary — shipping links statically unless an ADR says otherwise (`chief-engine-architect`, API and ABI Standards); a doc-comment-only change | a doc-comment-only change; a private field change on a struct with private fields; on a free fn, an inherent method or a type (never a trait item): a generic bound loosened, or a parameter generalised to a generic that still accepts the original type, or the fn made safe from `unsafe` |

Notes the row carries, not separate classes:

- An **added overload** in C++ can make an existing call ambiguous; an
  **added inherent method or defaulted trait method** in Rust can conflict
  with a method callers already import. Write `additive — name-conflict risk`
  and name the existing name it could collide with.
- A **doc-comment-only** change goes to `engine-technical-writer` in the
  report, not to the sign-off.

A declaration whose change you cannot read — a generated header that is not in
the diff, a macro whose expansion decides the signature — is
`NOT ASSESSED — <why>`. Never class it from its name.

### 2c. Deprecation, removal and ADR checks

Run each check on the rows it names. A failed check is a **finding** on that
row; a check that could not run is `NOT ASSESSED — <reason>` on that row.

1. **Breaking with no deprecation** (`breaking-source`, `breaking-abi`): the
   API is removed or changed incompatibly only after a deprecation window
   (`engine-api-code.md`). Finding: *deprecate the old API and add the replacement
   beside it*. A C ABI struct or versioned interface edited in place is a
   finding the reviewers are told to treat as REJECT: versioned interfaces are
   added beside the old one, never edited in place
   (`chief-engine-architect.md`).
2. **Deprecation message** (`deprecation`): it names the replacement — or says
   there is none — and the release that removes it (`removed in N+2`, or the
   macro's version argument; in Rust, `since` plus a note naming the
   replacement and the removal release). Either missing → finding.
3. **Removal window** (`removal`):
   - Find the commit that added the deprecation: `git log -S'<deprecation
     attribute line>' --oneline -- <file>`.
   - Find the window: Grep the ADRs (`glob=` the `match` row of
     `bash .claude/scripts/adr-files.sh where`) for the one that sets the
     deprecation window (an `## ABI / API Stability` section's
     **Versioning** line, or a line naming the deprecation window). No ADR sets
     one → `NOT ASSESSED — no deprecation window recorded`, as
     `chief-engine-architect` rules for removals. Read the window's unit: a
     number of minor releases (the default reading of "N releases") or of major
     releases. An ADR whose wording leaves the unit open ("two versions", "a
     while") → `NOT ASSESSED — window unit not stated`.
   - List the engine release tags that contain the deprecation:
     `git tag --list --contains <commit>`, kept to the engine release tags
     (Phase 1). None → the deprecation never shipped → finding.
   - Count releases in the window's unit, never raw tags: with the minor unit,
     the number of distinct minor versions (`X.Y`) among those tags, so the
     patch tags `engine-v0.7.1` and `engine-v0.7.2` add nothing beyond
     `engine-v0.7.0`; with the major unit, distinct major versions. A tag the
     scheme does not let you read as a version → `NOT ASSESSED — <tag> not a
     version`.
   - Releases shipped deprecated ≥ window → met. Fewer → finding, naming both
     numbers and the unit.
4. **ADR** (`breaking-*`, `removal`): an **Accepted** ADR records the break
   and its removal version (its `## ABI / API Stability` section). None →
   finding. Only a Proposed one → `NOT ASSESSED — ADR-NNNN is Proposed`.

### 2d. Boundary checks from `engine-api-code.md`

On every added or changed public declaration:

- **OS or SDK type in a public header or public crate API outside
  `engine/platform/`** (`HWND`, `ID3D12Device*`, `MTLDevice`, a console SDK
  handle, and the like) → finding. Backend-private files under `src/` are not
  public and are not checked here.
- **A public header or crate that includes or uses anything from `game/`** →
  finding: `engine/` never depends on `game/`.

A finding here is the module lead's to fix; the report routes it there.

---
