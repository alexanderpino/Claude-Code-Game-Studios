# /setup-engine — Custom (a project that builds its own engine)

> Part of `/setup-engine`. `SKILL.md` names when to read this file; the settings it
> resolved and the rules under its later headings still apply here.

Read when the engine is **Custom** (`/setup-engine custom`): the project writes
its own engine and its game in one repo. For Custom this file replaces
Sections 3, 6, 7 and 7.5 and gives the values Sections 4, 5 and 5.5 write;
Sections 8, 8.5 and 12 still apply, and C7 is Section 9. Never load
`godot-language-config.md`.

**In this file:** C1 An existing engine repo · C2 The questions · C3 The values
to write · C4 The reference docs · C5 No scaffold · C6 Build and test · C7 The
engine agents

Claude Code Game Studios ships **no engine code** for Custom: no sample engine,
no CMake or Cargo files, no starter. It supports writing one: the agents, the
path rules (`.claude/rules/engine-code.md`, `rhi-renderer-code.md`,
`ecs-math-code.md`, `simulation-code.md`, `audio-code.md`,
`streaming-io-code.md`, `scripting-code.md`, `editor-code.md`,
`shader-code.md` and others), `test-run.sh custom` and `test-scaffold.sh
custom`. The layout it expects, one repo (the full module list, with the rule
each module name matches, is `.claude/docs/custom-engine-layout.md`):

```
engine/   core/ memory/ jobs/ ecs/ math/ platform/ io/ streaming/ assets/ rhi/ renderer/
          vfx/ shaders/ physics/ animation/ scripting/ audio/ net/ online/ ui/ ai/
          editor/ tools/        (only the modules the project builds)
game/     src/ scripts/ data/
tests/    unit/ integration/ benchmarks/
docs/architecture/                ADRs
docs/engine-reference/custom/     the project's own pinned toolchain facts (C4)
```

The engine table row (`.claude/engines/engines.tsv`) gives Custom code root
`.`, test root `tests` and asset root `assets`, and no default commands: every
`commands.*` value comes from this file or the person, never from a fallback.

## C1. An existing engine repo

A `CMakeLists.txt` or a `Cargo.toml` at the project root, with no
`project.godot`, `*.uproject` or `ProjectSettings/ProjectVersion.txt`, means an
engine is already here: record it as it is and **change no file of it**. C1
replaces C2's language question and C5; C2's other questions, C3, C4, C6 and C7
still apply.

1. **Read, do not run.** With Glob and Read only:
   - **CMake:** `CMakeLists.txt` (`project(<name> VERSION <x> LANGUAGES …)`,
     `CMAKE_CXX_STANDARD`), `CMakePresets.json` (its configure, build and test
     preset names), and whether any `enable_testing()` / `add_test(` /
     `gtest_discover_tests(` line exists.
   - **Cargo:** `Cargo.toml` (`[workspace] members`, or `[package] name` and
     `version`), `rust-toolchain.toml` when present.
   - Both at once: ask which one builds the engine; the other is recorded in
     technical-preferences.md as a secondary build.
2. **Commands from what is there**, never from C3's defaults when the files say
   otherwise:
   - CMake with presets: `cmake --preset <configure> && cmake --build --preset <build>`
     and `ctest --preset <test> --output-on-failure`, with the names read in step 1.
   - CMake without presets: `cmake -S . -B build && cmake --build build` and
     `ctest --test-dir build --output-on-failure`.
   - Cargo: `cargo build --workspace` and `cargo test --workspace` (without
     `--workspace` for a single crate).
   - No test registration found: say `commands.test` is written but the checks
     that run tests will read zero tests, which `test-run.sh` never counts as a
     pass (`custom:ctest-zero`, `custom:cargo-zero`).
3. **Show the record and confirm it** in one block before writing: the build
   system and where it was read, each command, the language and standard, the
   project's own engine version (or `NOT DETERMINED`), and the folders found
   against the expected layout above. A layout that differs is recorded as it
   is; say which path rules will not load for it (a rule loads only for files
   under its globs, `.claude/docs/rules-reference.md`).

## C2. The questions (one round)

Ask once, all together, each with its default first and marked recommended.
Take an answer the person's own words already gave and say so in one line.

1. **Language and build:** `C++23 with CMake and CTest (Recommended)` /
   `Rust with Cargo` (`no_std` for the core crates where they need no OS).
   Skipped when C1 found one.
2. **C++ only — exceptions and RTTI:** `Both off (Recommended for engine code)`
   / `Exceptions off, RTTI on` / `Both on`. The answer is **not** written as a
   compiler flag here (no build file is written, C5). It becomes an **ADR
   candidate**: listed in the summary for `/architecture-decision` to decide,
   with its trade-off (error handling by return value; no `dynamic_cast` /
   `typeid`; third-party libraries that throw).
3. **Graphics API(s):** `Vulkan 1.4 (Recommended)` / `Direct3D 12` / `Metal` —
   more than one may be picked; each is a backend of the one RHI.
4. **Shader language:** `HLSL via DXC (Recommended)` / `Slang via slangc`.
5. **Platforms:** `Windows` / `Linux` / `macOS` / `Console` (several allowed);
   a typed `XR headset` is an answer too (the question tool takes four options;
   without it, list this as option 5). Metal without macOS, or Direct3D 12
   without Windows or console, is a mismatch: name it and ask again. For
   `platform.targets` (Section 5.5.4), `Windows`, `Linux` and `macOS` are `PC`,
   `Console` is `Console` and `XR headset` is `XR`.
6. **Target framerate:** `120 fps — 8.33 ms frame budget (Recommended for a
   AAA target)` / `60 fps — 16.6 ms frame budget`.
7. **C++ only — naming:** `snake_case, like the standard library
   (Recommended)` / `PascalCase types, camelCase members`. Rust has no question:
   it uses rustc's own lint conventions.

## C3. The values to write (Sections 4, 5 and 5.5)

Ask before each file, as Sections 4, 5 and 5.5 do; show every value first.

**CLAUDE.md** (Section 4), the import line under the `ENGINE-REFERENCE-IMPORT`
marker set to `@docs/engine-reference/custom/VERSION.md`:

```markdown
- **Engine**: Custom (in-house; <graphics APIs>; shaders <HLSL via DXC | Slang via slangc>)
- **Language**: <C++23 | Rust>
- **Build System**: <CMake + CTest — `<commands.build>` | Cargo — `cargo build --workspace`>
- **Asset Pipeline**: in-house cookers under `engine/tools/` (runtime loading in `engine/assets/`; none written yet)
```

**technical-preferences.md** (Section 5): Engine Custom and the language; the
naming below in prose; Performance Budgets from C2 question 6; Testing
`CTest` or `cargo test`, with benchmarks under `tests/benchmarks/`; the
exceptions/RTTI answer under a line `ADR candidates (not yet decided):`.
Forbidden Patterns and Allowed Libraries stay placeholders (Section 5's rule).
The Engine Specialists section:

```markdown
## Engine Specialists

Read `.claude/docs/engine-development-coverage.md` when planning modules and
handoffs. The same specification, implementation, review and evidence standards
apply to engine and game development.

- **Primary**: chief-engine-architect
- **Language/Code Specialist**: core-systems-lead (memory, jobs, platform; routes to its specialists)
- **Shader Specialist**: shader-pipeline-engineer
- **UI Specialist**: ui-programmer (no engine UI specialist; UI rendering goes through rendering-lead)
- **Additional Specialists**: rendering-lead, simulation-systems-lead, editor-architect, memory-allocator-specialist, concurrency-job-system-engineer, ecs-dod-architect, platform-engineer, world-streaming-engineer, online-services-engineer, asset-build-tooling-engineer, rhi-backend-engineer, render-graph-specialist, graphics-features-engineer, vfx-runtime-engineer, physics-simulation-engineer, animation-systems-engineer, scripting-runtime-engineer, audio-engine-engineer, level-editor-engineer, editor-ui-framework-engineer, cinematics-sequencer-engineer, engine-technical-writer
- **Routing Notes**: chief-engine-architect owns subsystem boundaries, API/ABI stability and frame budgets; technical-director keeps the whole-project technical call. Specialists report to their lead, leads to chief-engine-architect.

### File Extension Routing

| File / folder | Specialist to Spawn |
|---|---|
| `engine/core/` | core-systems-lead |
| `engine/platform/` | platform-engineer |
| `engine/streaming/`, `engine/io/`, `engine/assets/` | world-streaming-engineer |
| `engine/online/` | online-services-engineer |
| `engine/memory/` | memory-allocator-specialist |
| `engine/jobs/` | concurrency-job-system-engineer |
| `engine/ecs/`, `engine/math/` | ecs-dod-architect |
| `engine/rhi/` | rhi-backend-engineer |
| `engine/renderer/` | render-graph-specialist (frame pipeline: rendering-lead; lighting, shadows, post: graphics-features-engineer) |
| `engine/vfx/` | vfx-runtime-engineer |
| `engine/shaders/`, `.hlsl`, `.slang` | shader-pipeline-engineer |
| `engine/physics/` | physics-simulation-engineer |
| `engine/animation/` | animation-systems-engineer |
| `engine/cinematics/`, `engine/camera/`, `engine/sequencer/` | cinematics-sequencer-engineer |
| `engine/sim/` | simulation-systems-lead |
| `engine/input/`, `engine/media/`, `engine/xr/` | platform-engineer |
| `engine/net/`, `game/src/net/` | network-programmer |
| `engine/ai/`, `game/src/ai/` | ai-programmer |
| `engine/ui/`, `game/src/ui/` | ui-programmer |
| `engine/scripting/` | scripting-runtime-engineer |
| `game/scripts/` | gameplay-programmer |
| `engine/audio/` | audio-engine-engineer |
| `engine/editor/`, `tools/editor/` | editor-architect |
| `engine/tools/`, `CMakeLists.txt`, `Cargo.toml` | asset-build-tooling-engineer |
| `game/src/` | gameplay-programmer |
| General architecture review | chief-engine-architect |

Mapped `crates/<module>/` paths use the same owners. Resolve other layouts
through the project's module map and `.claude/docs/custom-engine-layout.md`
before delegation; unknown ownership blocks implementation.
```

**`project.yaml`** (Section 5.5), these blocks plus `performance`:

```yaml
engine:
  name: "Custom"
  language: "<C++ | Rust>"
  rendering: "<Vulkan 1.4 | Direct3D 12 | Metal, comma-separated when several>"
  physics: "in-house"

specialists:
  code: "core-systems-lead"
  shader: "shader-pipeline-engineer"
  ui: "ui-programmer"
  additional: ["chief-engine-architect", "rendering-lead", "simulation-systems-lead", "editor-architect", "memory-allocator-specialist", "concurrency-job-system-engineer", "ecs-dod-architect", "platform-engineer", "world-streaming-engineer", "online-services-engineer", "asset-build-tooling-engineer", "rhi-backend-engineer", "render-graph-specialist", "graphics-features-engineer", "vfx-runtime-engineer", "physics-simulation-engineer", "animation-systems-engineer", "scripting-runtime-engineer", "audio-engine-engineer", "level-editor-engineer", "editor-ui-framework-engineer", "cinematics-sequencer-engineer", "engine-technical-writer"]

naming:            # see the table below
  classes: <...>
  variables: <...>
  constants: <...>
  signals: on_event_name
  files: <...>
  scenes: snake_case

commands:
  build: "<see below>"
  test: "<see below>"
  smoke: "<see below>"
  # run: unset until a game executable exists

performance:
  target_framerate: <120 | 60>
  frame_budget_ms: <8.33 | 16.6>
```

- `Custom` with the capital: the check is case-sensitive, and `custom` reads as
  unset. No `engine.code_root` or `engine.test_root`: the engine table gives
  `.` and `tests`.
- `engine.version` is the project's **own** engine version: written only when
  C1 read one (`project(… VERSION x)` or Cargo's `version`); otherwise left out
  and said so. Never invent `0.1.0`.
- `specialists.*` uses only the four keys the schema has (`code`, `shader`,
  `ui`, `additional`; `.claude/docs/effects-map.md`, "engine.name and
  specialists"). The primary is technical-preferences.md's **Primary** line
  (`chief-engine-architect`), the same agent `yaml-helper.sh` derives from
  `engine.name: Custom`; the line keeps the legacy mirror in step.

**Naming** (enum values from `effects-map.md` § naming; a C++ prefix like `k`
or `m_` cannot be expressed in the enum and goes in technical-preferences.md
prose):

| Field | C++ snake_case | C++ PascalCase | Rust (rustc conventions) |
|---|---|---|---|
| `classes` | snake_case | PascalCase | PascalCase |
| `variables` | snake_case | camelCase | snake_case |
| `constants` | SCREAMING_SNAKE | PascalCase (`kMaxLights` in prose) | SCREAMING_SNAKE |
| `signals` | on_event_name | on_event_name | on_event_name |
| `files` | snake_case | PascalCase | snake_case |
| `scenes` | snake_case | snake_case | snake_case |

**Commands** (C1's, when it ran):

| | C++ / CMake | Rust / Cargo |
|---|---|---|
| `build` | `cmake --preset debug && cmake --build --preset debug` | `cargo build --workspace` |
| `test` | `ctest --preset debug --output-on-failure` | `cargo test --workspace` |
| `smoke` | `ctest --preset debug -L smoke --output-on-failure` | `cargo test --workspace smoke` |
| `run` | unset | unset |

- The C++ commands name a `debug` preset in `CMakePresets.json`, which the
  project writes with its first ADRs (C5). Until it exists, the build fails
  and C6 says so; the command is not changed to hide that.
- `smoke` runs the tests labelled or named `smoke`. With none yet, it reads
  zero tests, which is not a pass.
- `run` launches the **game** windowed (`.claude/docs/run-and-observe.md`). There is
  no game executable at setup, so it is left unset and the summary says
  `/dev-story`'s run-and-observe step is NOT ASSESSED until it is set with
  `/project-settings`. Never write a guessed path.
- Every value takes a double-quoted YAML scalar (none contains a quote; Section
  5.5.1's quoting rule).

## C4. The reference docs (Sections 6 and 7)

**Knowledge risk:** the engine is the project's own, so no model knows its API:
its source, its ADRs and `docs/engine-reference/custom/` are the reference.
Report `HIGH — in-house engine; agents read its source, ADRs and
docs/engine-reference/custom/`. Toolchain and graphics-API facts are pinned in
`VERSION.md` and nowhere else; an agent that needs one not recorded there
writes `NOT SOURCEABLE — <what> is not covered by docs/engine-reference/custom/`.

Create `docs/engine-reference/custom/VERSION.md` **for this project, now**,
from probes. Nothing ships in that folder. If it already exists, show the rows
that would change and ask before editing; never drop a row.

1. **Probe** (each read-only; a probe that fails or is not installed is
   `NOT DETERMINED`, never "absent"):
   - C++: `cmake --version`, `ctest --version`, then the compiler —
     `clang++ --version`, `g++ --version`; on Windows ask whether MSVC is used
     and take the version the person reads from a Developer prompt.
   - Rust: `cargo --version`, `rustc --version`.
   - Vulkan SDK: ask first — "May I run `vulkaninfo --summary` to record the
     Vulkan SDK and driver version?" It reads the GPU and driver. Declined:
     `NOT DETERMINED — not probed (declined)`.
   - DXC, slangc, Windows SDK (Direct3D 12), Xcode (Metal): ask the person for
     the version they use; not given is `NOT DETERMINED`.
2. **Write**, after "May I create `docs/engine-reference/custom/VERSION.md`?":

```markdown
# Custom engine — Version Reference

| Field | Value |
|-------|-------|
| **Engine Version** | <the project's own engine version from C1, or NOT DETERMINED — no version declared yet> |
| **Project Pinned** | <today's date> |
| **Installed at pin time** | <the toolchain line from the probes, e.g. CMake <x>, CTest <x>, <compiler> <x> — or NOT DETERMINED> |
| **LLM Knowledge Cutoff** | <the cutoff from Section 6's coverage table> |
| **Risk Level** | HIGH — in-house engine; its source and ADRs are the reference |

## Toolchain (probed <today's date>)

| Tool | Version | Source |
|------|---------|--------|
| <each probe or answer> | <its output, or NOT DETERMINED> | <the command, or "the person"> |

## Graphics and shaders

| Item | Value | Source |
|------|-------|--------|
| Graphics API(s) | <C2 answer> | /setup-engine custom |
| Vulkan SDK / driver | <vulkaninfo result, or NOT DETERMINED> | <command or "not probed"> |
| Shader compiler | <DXC or slangc version, or NOT DETERMINED> | <the person, or NOT DETERMINED> |

## Third-party libraries

None recorded. Add a row (name, version, licence, source URL) when one is
integrated — never speculatively.
```

Only probed or person-confirmed values go in a row. A version remembered from
training is not a source.

## C5. No scaffold (Section 7.5)

Say it plainly: "Claude Code Game Studios ships no engine code. There is no
starter, no `CMakeLists.txt`, no `Cargo.toml` and no `CMakePresets.json`; the
first engine files are yours to write." Write none of them, and no folder.

Recommend, in this order:
1. The first ADRs, with `/architecture-decision` in its engine mode (written to
   the path on `adr-files.sh`'s `new` row, default
   `docs/architecture/adr-NNNN-<slug>.md`, each reviewed by CEA-ADR): the
   module layout under `engine/` and the dependency direction between modules
   (engine never depends on `game/`), memory ownership and allocators, the job
   system and threading model, the RHI shape and frame pacing (frames in
   flight against the C2 budget), the C2 exceptions/RTTI candidate, and on
   C++ the test framework (record it with `/project-settings
   testing.framework=<name>`; `/test-helpers` covers the choice). The
   Technical Setup → Pre-Production gate also asks for ADRs on the ECS, the
   render graph, the platform layer and the editor UI framework.
2. Three documents from the framework's templates — no skill writes them; the
   owning agent fills each one, and the gate checks they exist:
   - `docs/architecture/frame-budget.md` from
     `.claude/docs/templates/frame-budget.md` — splits the C2 budget
     (`performance.frame_budget_ms`) across CPU phases and GPU passes; owner
     `chief-engine-architect`.
   - `docs/architecture/memory-invariants.md` from
     `.claude/docs/templates/memory-invariants.md` — the engine's memory rules;
     filled by `memory-allocator-specialist`, reviewed by `core-systems-lead`.
   - `docs/architecture/modules/<module>.md`, one per MVP module, from
     `.claude/docs/templates/engine-module-spec.md` — the module map; filled by
     each module's specialist.
3. The module layout from the first ADR, built through the story route once
   that ADR is accepted. The route starts from the game's design, even on an
   engine-first project: a game concept (`/brainstorm`), a systems index
   (`/map-systems`) and the architecture (`/create-architecture`) come first;
   then `/create-epics` (one epic per module spec, slugged `engine-<module>`)
   and `/create-stories`; then `/dev-story` builds each story. The module
   specs reach epics and stories only at `workflow: standard` or `full`: at
   `workflow: minimal`, the default, `/create-epics` and `/create-stories`
   stop on them and point to `/project-settings modes.workflow=standard`.
4. `/test-setup` for the test folders and CI (C6).

## C6. Build and test

- **No engine code yet** (no `CMakeLists.txt` and no `Cargo.toml`): run
  nothing. Report `Build/Test: NOT ASSESSED — no engine code yet (no
  CMakeLists.txt or Cargo.toml)`.
- **Engine code present:** run `commands.build` and report its command, exit
  code and last error line. Then `bash .claude/scripts/test-run.sh custom
  --no-build` (the build already ran) and report the `runner` and `rule` rows:
  - `custom:ctest-pass` / `custom:cargo-pass` — tests ran and passed, with the
    count.
  - `custom:ctest-zero` / `custom:cargo-zero` — `NOT ASSESSED — zero tests`;
    never a pass.
  - `custom:0` / `custom:nonzero` with runner `other` — read by exit code only;
    say a run of zero tests looks the same, and that the generated CI fails on
    it with `runner not recognised: CI cannot show that tests ran; use ctest or
    cargo test in commands.test`.
  - `custom:no-test-command` — `NOT ASSESSED — no test command`.
  - `custom:build-failed`, `custom:ctest-failed`, `custom:cargo-failed`,
    `custom:cargo-compile-failed` — report as failures, with the evidence row.

  A failure is reported, not fixed here: this skill changes no engine file.
- **Then offer `/test-setup`.** Show `bash .claude/scripts/test-scaffold.sh
  custom --dry-run` (it never overwrites a file): `tests/unit/`,
  `tests/integration/`, `tests/benchmarks/`, the tests README and the CI
  workflow. `/test-setup` creates them on a yes.

Section 8.5's `project-coherence.sh` still runs; its `[NOT CHECKED]` lines
for Custom (no engine binary to compare) are reported by name, never as
agreement.

## C7. The engine agents (Section 9)

Custom uses the 25 custom-engine agents: `chief-engine-architect`, `core-systems-lead`, `rendering-lead`, `simulation-systems-lead`, `editor-architect`, `memory-allocator-specialist`, `concurrency-job-system-engineer`, `ecs-dod-architect`, `platform-engineer`, `world-streaming-engineer`, `online-services-engineer`, `asset-build-tooling-engineer`, `rhi-backend-engineer`, `render-graph-specialist`, `shader-pipeline-engineer`, `graphics-features-engineer`, `vfx-runtime-engineer`, `physics-simulation-engineer`, `animation-systems-engineer`, `scripting-runtime-engineer`, `audio-engine-engineer`, `level-editor-engineer`, `editor-ui-framework-engineer`, `cinematics-sequencer-engineer`, `engine-technical-writer`. They are used only when `engine.name` is
`Custom`. This list is kept by hand (agent files carry no engine field to
derive it from): a new Custom-engine agent must be added here and in
`.claude/docs/agent-roster.md`'s Custom section.

Check each `.claude/agents/<name>.md` for a "Version Awareness" section that
reads `docs/engine-reference/custom/VERSION.md`. A file that is missing is
reported by name (`<name>: agent file not found — not checked`), never
skipped silently. Adding or fixing the section follows Section 9: ask first,
and point it at `docs/engine-reference/custom/VERSION.md`, the project's ADRs
in `docs/architecture/`, and the `NOT SOURCEABLE` rule for anything those do
not cover. Steps 3 and 4 of Section 9's list (breaking changes, web search)
apply only to the third-party toolchain and libraries, never to the engine's
own API.
