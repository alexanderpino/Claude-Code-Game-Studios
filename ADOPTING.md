# Adopting Claude Code Game Studios

[README.md](README.md#setup) starts a new game by cloning this repository. This
guide puts the framework into a folder or a repository that already exists: a
game, an engine, a project with its own `AGENTS.md` or `CLAUDE.md`, a repository
nested inside another folder. It says what to copy, what to merge by hand, what
to create, what to leave out, how to check that it works and how to update it.

Two scripts do the copying, with the same behaviour: `scripts/adopt.sh` (bash,
including Git Bash on Windows) and `scripts/adopt.ps1` (PowerShell 7). They are
tooling of this repository, not part of the framework they copy.

---

## Table of Contents

- [Prerequisites](#prerequisites)
- [Quick start](#quick-start)
- [Where Claude Code looks](#where-claude-code-looks)
- [What the scripts do](#what-the-scripts-do)
- [A new project](#a-new-project)
- [An existing project](#an-existing-project)
- [A nested repository or a worktree](#a-nested-repository-or-a-worktree)
- [Windows](#windows)
- [What not to copy](#what-not-to-copy)
- [Check that it works](#check-that-it-works)
- [Updating](#updating)

---

## Prerequisites

- The tools of [README.md's Prerequisites](README.md#prerequisites): Git, Claude
  Code, Python 3 (reads `project.yaml` for every skill and hook) and Bash (runs
  every hook; on Windows it comes with Git for Windows).
  `.claude/docs/setup-requirements.md` has the detail.
- A clean clone of this repository at the commit you want to adopt. The
  scripts copy from the clone they sit in, so check out a release tag first if
  you want one (`git -C ccgs checkout v1.3.0`). They copy the files on disk,
  not the files of the commit, and run no git command: an untracked or ignored
  file under the copied folders (work in progress, `.DS_Store`, an editor's
  `*.swp`) goes into the project too. `git -C ccgs status --short --ignored
  .claude LICENSE CLAUDE.md` must print nothing.
- To run a script: bash (any version from 3.2), or PowerShell 7 (`pwsh`;
  Windows PowerShell 5.1 is not supported).

## Quick start

```bash
git clone https://github.com/Donchitos/Claude-Code-Game-Studios.git ccgs
bash ccgs/scripts/adopt.sh path/to/your-project --dry-run   # read what it would do
bash ccgs/scripts/adopt.sh path/to/your-project
```

```powershell
pwsh ccgs\scripts\adopt.ps1 -Target C:\src\your-project -DryRun
pwsh ccgs\scripts\adopt.ps1 -Target C:\src\your-project
```

Then do the hand merges the output names (`SKIP` lines), create `project.yaml`
([below](#projectyaml)), and [check that it works](#check-that-it-works). In a
git repository, commit or stash your own changes first, so that what the script
changed is one diff you can review.

## Where Claude Code looks

Where each file goes follows from where Claude Code reads it. Each line quotes
the Claude Code documentation (read 2026-11-21) or names the framework file.

| What | Read from | Source |
|------|-----------|--------|
| `.claude/settings.json`: hooks, permissions, status line | The folder you start Claude Code in only: "Claude Code reads the shared `.claude/settings.json` from the session's primary working directory, so to use a file committed at the repository root, start Claude Code there." | [settings](https://code.claude.com/docs/en/settings.md), "Where Claude Code keeps the local file in a git repository" |
| Skills, `.claude/skills/` | "in the directory where you start it and in every parent directory up to the repository root" | [skills](https://code.claude.com/docs/en/skills.md) |
| Subagents, `.claude/agents/` | "discovered by walking up from the current working directory, so every `.claude/agents/` between there and the repository root is scanned" | [sub-agents](https://code.claude.com/docs/en/sub-agents.md), "Choose the subagent scope" |
| `CLAUDE.md` | "from your current working directory and every directory above it", and "All discovered files are concatenated into context rather than overriding each other." | [memory](https://code.claude.com/docs/en/memory.md), "How CLAUDE.md files load" |
| `AGENTS.md` | Only "when you have no `CLAUDE.md` in your working directory or above it"; a `CLAUDE.md`, `.claude/CLAUDE.md` or `CLAUDE.local.md` there counts | [memory](https://code.claude.com/docs/en/memory.md), "When Claude Code reads AGENTS.md" |
| `project.yaml`, `project.local.yaml` | The working directory, else `$CLAUDE_PROJECT_DIR` (the folder Claude Code started in); never a parent folder | `.claude/hooks/yaml-helper.sh`, `_yaml_helper_set_root` and the comment above it |

So the framework's `.claude/`, `CLAUDE.md` and `project.yaml` go in the folder
you start Claude Code in, the root of the project. Two settings look like a way
round that and are not:

- `permissions.additionalDirectories` in `settings.json` "grants file access
  only and loads none of these" (skills, commands, agents)
  ([skills](https://code.claude.com/docs/en/skills.md)).
- `--add-dir` and `/add-dir` load an added directory's skills, commands and
  agents, but from its `.claude/settings.json` only the `enabledPlugins` and
  `extraKnownMarketplaces` keys, so none of its hooks or permissions
  ([permissions](https://code.claude.com/docs/en/permissions.md), "Additional
  directories grant file access, not configuration").

The framework's own `CLAUDE.md` says the same in its Collaboration Protocol:
hooks, deny rules and the ask-first mode load only when Claude Code starts in
its folder.

## What the scripts do

```
bash scripts/adopt.sh <target-dir> [--dry-run]
pwsh scripts/adopt.ps1 <target-dir> [--dry-run]     # or -Target <dir> -DryRun
```

| Path in the target | What the script does |
|--------------------|----------------------|
| `.claude/agents/`, `skills/`, `rules/`, `hooks/`, `scripts/`, `engines/`, `genres/`, `docs/` | Copied whole: adds and overwrites the framework's files, never deletes one, so a skill or agent of your own survives |
| `.claude/statusline.sh` | Copied, overwriting |
| `.claude/LICENSE` | This repository's `LICENSE`, copied, overwriting: the MIT notice that goes with the copy |
| `.claude/agent-models.yaml` | Copied when missing. Once the project's copy differs (its own `overrides:`, or an older release's table) it is kept, and the framework's copy is written beside it as `.claude/agent-models.ccgs.yaml`: take its `tiers:` and `agents:` lines into yours, keep your `overrides:`, then run `bash .claude/scripts/agent-models.sh sync`, as [UPGRADING.md](UPGRADING.md) says for this file |
| `.claude/docs/technical-preferences.md` | Copied when missing; once the project has one it is the project's own, as [UPGRADING.md](UPGRADING.md) treats it |
| `.claude/settings.json` | Copied when missing. Otherwise kept, and the framework's copy is written beside it as `.claude/settings.ccgs.json`, which Claude Code does not read, for you to [merge by hand](#settingsjson) |
| `CLAUDE.md` | Copied only when the project has no `CLAUDE.md`, `.claude/CLAUDE.md` or `AGENTS.md`; never overwritten. Otherwise [merge by hand](#instruction-files) |
| `project.yaml` | Never written: run `/start` or `/setup-engine`, or [write it by hand](#projectyaml) |
| `.gitignore` | Gains, once, `production/session-state/`, `production/session-logs/`, `project.local.yaml` and `.claude/worktrees/`; created when missing |
| `.gitattributes` | Gains, once, `.claude/**/*.sh`, `.claude/**/*.awk` and `.claude/**/*.tsv` with `text eol=lf` (the first covers `.claude/statusline.sh`); created when missing |

The lists sit at the top of each script, one place each, and
`studio-tests/test_adopt_scripts.py` checks that the two scripts agree.

Every action prints one line: `ADD`, `OVERWRITE`, `UNCHANGED`, `SKIP` with its
reason in brackets, or `APPEND` with the lines appended; a summary closes the
run. `--dry-run` prints the same lines and writes nothing. A second run from
the same files prints only `UNCHANGED` and `SKIP` and changes nothing. A line
is appended only when the file lacks it, in the file's own line endings.

The scripts check every path they would write before they write any. They
refuse, with exit code 1 and nothing written, when:

- the target does not exist, is not a directory, or is this repository or a
  folder inside it, also when reached through a symlink or junction;
- a path they would write, or a folder on the way to it, is a symlink or a
  junction (such as a `.claude` that links to a shared folder), a folder where
  a file goes, or a file where a folder goes. A link elsewhere, such as a
  `.claude/commands` of your own, is left alone;
- a file they would change is read-only. A Perforce workspace keeps files
  read-only until they are checked out: check out the files the message lists
  (or make them writable) and run again. A read-only file they would not change
  is fine.

A missing target or an unknown option is exit code 2. A write that fails after
the checks (a full disk, a folder's permissions) stops the run with exit code
1 and a `Copy failed:` line naming the file; run it again once the cause is
fixed. Exit code 0 means every line was carried out. The scripts use no network
and no git command, and write only inside the target: the link check keeps a
link from carrying a write outside it. Paths with spaces work.

## A new project

Clone this repository as [README.md](README.md#setup) says, or, to start from an
empty folder or a fresh `git init`, run the script on it. Its `CLAUDE.md` and
`settings.json` are then the framework's. A new project that uses the
template's layout (`design/`, `docs/`, `src/`) also takes by hand:

- `design/CLAUDE.md`, `docs/CLAUDE.md` and `src/CLAUDE.md`: the standards for
  those folders, which Claude Code loads when it works on a file there.
- `docs/engine-reference/README.md` and the folder of your engine only
  (`godot/`, `unity/`, `unreal/` or `web/`). A Custom engine has no shipped
  folder: `/setup-engine custom` writes `docs/engine-reference/custom/`
  (`docs/engine-reference/README.md`, "Structure").

Then open Claude Code in the project's root folder and type `/prototype` and an
idea, or run `/start`.

## An existing project

### settings.json

When the project has its own `.claude/settings.json`, merge
`.claude/settings.ccgs.json` into it, then delete `settings.ccgs.json`:

- `hooks`: every entry. Each command runs a script under
  `$CLAUDE_PROJECT_DIR/.claude/hooks/` in the one-line form that both bash and
  PowerShell read (`.claude/docs/setup-requirements.md`, Windows). A project
  with its own planning may leave out the `SessionStart` entry that runs
  `detect-gaps.sh`, which suggests `/start`, `/reverse-document` or
  `/project-stage-detect` when it finds code without design documents
  (`.claude/docs/hooks-reference.md`).
- `permissions.deny`: the safety rules (recursive `rm`, force push,
  `git reset --hard`, `git clean -f` and more). Keep them all.
- `permissions.allow`: the read-only helpers the skills run
  (`bash .claude/scripts/…`, `bash .claude/hooks/yaml-helper.sh …`).
- `statusLine` and `worktree`, if you want them.

Within one file you merge by hand; across settings files Claude Code merges list
keys such as `permissions.allow` itself ([settings](https://code.claude.com/docs/en/settings.md),
"Lists merge instead of overriding"). Never put the framework's hooks only in
`.claude/settings.local.json`: that file is personal and kept out of git.

### Instruction files

- **No `CLAUDE.md` or `AGENTS.md`:** the script copies the framework's
  `CLAUDE.md`. Fill in its Technology Stack lines.
- **Your own `CLAUDE.md`:** add the framework's sections to it by hand:
  `git diff --no-index ccgs/CLAUDE.md CLAUDE.md` shows them. They are the
  imports `@.claude/docs/coordination-rules.md` and
  `@.claude/docs/coding-standards.md`, the Collaboration Protocol, Technical
  Preferences (which points to `project.yaml`) and Context Management. Import
  `@.claude/docs/directory-structure.md` only if the project uses the
  template's layout; otherwise describe your own layout in your file.
- **Your own `AGENTS.md` and no `CLAUDE.md`:** do not add a bare `CLAUDE.md`.
  Claude Code reads `AGENTS.md` only while no `CLAUDE.md` exists in the working
  directory or above it ([memory](https://code.claude.com/docs/en/memory.md)),
  so a new `CLAUDE.md` would hide it. Either add the framework's sections to
  `AGENTS.md` (Claude Code expands `@path` imports inside it, same page), or
  create a `CLAUDE.md` whose first line is `@AGENTS.md`, followed by the
  framework's sections.
- **A `CLAUDE.md` in a folder above the project** (a workspace folder, a home
  folder) loads too, before the project's, and counts in the `AGENTS.md` rule
  above. To skip one, list it under `claudeMdExcludes` in
  `.claude/settings.local.json` ([memory](https://code.claude.com/docs/en/memory.md),
  "Exclude specific CLAUDE.md files").

### project.yaml

`project.yaml` sits at the project root beside `.claude/`. Three ways to create
it:

- `/start`: on a project without one it creates `project.yaml` and nothing else
  (`.claude/docs/effects-map.md`, "Creation and error handling"). Pick
  "existing work".
- `/setup-engine <engine>`: creates it when it does not exist
  (`.claude/skills/setup-engine/references/5.5-project-yaml.md`).
- By hand, for a layout the engine table does not expect. `/project-settings`
  never creates the file (`.claude/scripts/config-set.sh`), so write the first
  lines yourself:

  ```yaml
  schema_version: 1

  engine:
    name: Custom        # Godot | Unity | Unreal | Web | Custom, with the capital
    code_root: src      # only when the code is not in the engine's usual folder
    test_root: tests    # only when the tests are not in the engine's usual folder
  ```

  `engine.code_root` and `engine.test_root` are folders relative to the project
  root; a folder that does not exist makes the code root invalid, and the code
  checks then report NOT ASSESSED rather than scanning the wrong folder. Every
  `engine.*` key belongs in `project.yaml`, never `project.local.yaml`
  (`.claude/docs/effects-map.md`, `engine.code_root`, `engine.test_root`,
  `engine.name`).

A project whose own process approves agents' writes before they happen (a
reviewed plan that agents then build) can set `features.agent_write_guard: off`.
`validate-write.sh` then stops warning on each subagent write outside
`production/`, `docs/` and `tests/`, and runs its other rules
(`.claude/docs/effects-map.md`, `features.agent_write_guard`).

### .gitignore and .gitattributes

The hooks write `production/session-state/` (the session checkpoint) and
`production/session-logs/`, `project.local.yaml` holds one person's settings,
and `.claude/worktrees/` holds the checkouts of the `prototyper` agent
(`isolation: worktree`) and of `claude --worktree`, so the script keeps all
four out of git. Each worktree is a checkout of its own: staged with the rest,
it would be added as an embedded repository (this repository's `.gitignore`). It also adds the LF rules
of [Windows](#windows). A `.gitattributes` rule changes what git stores, not a
checkout that already exists: `git add --renormalize .claude` applies it to
files git already tracks (this repository's `.gitattributes` says the same).

## A nested repository or a worktree

A repository inside a folder that is not itself the project, for example
`workspace/game/` with its own `.git`:

- Put `.claude/`, `CLAUDE.md` and `project.yaml` in `game/`, and start Claude
  Code in `game/`.
- A `.claude/` in `workspace/` does not reach a session started in `game/`:
  its settings and hooks load only from the working directory, and skills and
  agents are searched only up to the repository root, which is `game/`.
- `workspace/CLAUDE.md` does reach it. See [Instruction files](#instruction-files)
  for `claudeMdExcludes`.
- If `workspace/` is a git repository too, `game/` is a nested repository or a
  submodule there: run the script on `game/`, and commit in `game/`.

In a linked git worktree, Claude Code "searches parent directories only up to
the worktree root" ([skills](https://code.claude.com/docs/en/skills.md)). When
the worktree has no `.claude/skills` at its root, it loads the main checkout's
skills instead (Claude Code v2.1.277 or later), and "the same read-through
covers `.claude/agents` and `.claude/commands`"
([worktrees](https://code.claude.com/docs/en/worktrees.md), "What worktrees
share with the main checkout"). Settings, hooks and `project.yaml` have no such
read-through: they come from the folder the session starts in (see [Where
Claude Code looks](#where-claude-code-looks)), so commit `.claude/` and
`project.yaml`, and every worktree has them. This repository's
`.worktreeinclude` lists the gitignored files Claude Code copies into worktrees
it creates (`project.local.yaml`, `CLAUDE.local.md`,
`.claude/settings.local.json`); copy it too if you use them.

## Windows

- Install Git for Windows. Without Git Bash every hook skips itself and session
  start says so; Claude Code finds Git at `C:\Program Files\Git`, or set
  `CLAUDE_CODE_GIT_BASH_PATH` (`.claude/docs/setup-requirements.md`).
- Shell scripts need LF line endings or Git Bash misreads them: a stray `\r`
  corrupts commands and string comparisons (this repository's
  `.gitattributes`). The clone's own `.gitattributes` checks its scripts out
  LF, so the copies are LF; the rules the script adds to the project's
  `.gitattributes` keep them LF in every later checkout, whatever
  `core.autocrlf` says.
- Run `adopt.sh` from Git Bash (`bash ccgs/scripts/adopt.sh C:/src/game`) or
  `adopt.ps1` from PowerShell 7. Quote a path with spaces.

## What not to copy

| Path in this repository | Why |
|-------------------------|-----|
| `studio-tests/` | Tests the framework's skills and agents, not your game (README.md, "Testing your customizations"). Take it only if you edit skills or agents and want `/skill-test spec`; nothing in `.claude/` needs it (`studio-tests/CLAUDE.md`, "This folder is deletable") |
| `README.md`, `CHANGELOG.md`, `UPGRADING.md`, `ADOPTING.md`, `CONTRIBUTING.md`, `SECURITY.md`, `.github/`, `scripts/` | This repository's own documents and tooling |
| `LICENSE` | Not as your project's licence. The MIT licence asks that its notice go with "all copies or substantial portions" (`LICENSE`), so the scripts copy it to `.claude/LICENSE`; copying by hand, do the same |
| `production/` | This repository's session logs and checkpoint; the hooks write your own |
| `design/registry/entities.yaml`, `docs/registry/architecture.yaml`, `docs/architecture/tr-registry.yaml` | Registries the skills fill from your design and ADRs, and write after asking: `/design-system` offers to create the entity registry (`references/5-post-design.md`), `/architecture-review` writes the TR registry (`references/8-write.md`) |
| `docs/engine-reference/<other engines>/` | Only your engine's folder applies |
| `docs/research/` and the other files under `docs/` | This repository's own records and guides; `docs/WORKFLOW-GUIDE.md` and `docs/COLLABORATIVE-DESIGN-PRINCIPLE.md` are worth reading, not needed by any hook |
| `design/CLAUDE.md`, `docs/CLAUDE.md`, `src/CLAUDE.md` | Only for a project with those folders and that use ([A new project](#a-new-project)) |
| `project.yaml` | The template's file; create the project's own ([project.yaml](#projectyaml)) |
| `.claude/settings.local.json`, `.claude/agent-memory/`, `.claude/worktrees/` | Personal or runtime files, gitignored here; the scripts never copy them |

## Check that it works

Start a new Claude Code session in the project's root folder.

1. Session start prints `=== Claude Code Game Studios — Session Context ===`:
   the hooks run. A line saying the hooks are off means Claude Code found no
   Git Bash ([Windows](#windows)).
2. Type `/` and look for the framework's skills (`/start`, `/next-step`,
   `/project-settings`), and run `/agents` for its agents (`producer`,
   `technical-director`).
3. `/project-settings` with no argument shows every setting with the file it
   came from. Check `engine.name` and, if you set them, `engine.code_root`,
   `engine.test_root` and `features.agent_write_guard`.
4. `/status` lists the settings files Claude Code loaded; the project settings
   must be among them ([settings](https://code.claude.com/docs/en/settings.md),
   "Confirm what loaded").

## Updating

- **With the script:** check out the new release in the clone
  (`git -C ccgs fetch --tags && git -C ccgs checkout <tag>`), run the script
  with `--dry-run`, then without. It overwrites the framework's files and keeps
  yours. It never deletes: a file the new release removed stays until you
  delete it (a release's section of [UPGRADING.md](UPGRADING.md) names what it
  removed). It writes the new `settings.json` to `.claude/settings.ccgs.json`
  and the new `agent-models.yaml` to `.claude/agent-models.ccgs.yaml` again for
  you to merge, and keeps yours. After merging `agent-models.yaml`, run
  `bash .claude/scripts/agent-models.sh sync`: the run overwrote the agent
  files with the new release's, so your `overrides:` are back in them only
  after the sync. If you edited another framework file, such as an agent's
  text, the run overwrites it: review the diff and restore what you keep, as
  UPGRADING.md's Strategy A2 says. Without git, keep a copy of such edits
  before you run it.
- **With git:** [UPGRADING.md](UPGRADING.md), "Strategy A2 — Selective
  checkout (no shared history)", takes the framework-owned paths from the new
  release with `git checkout template/main -- <paths>`; use the paths of
  [What the scripts do](#what-the-scripts-do) in place of `.claude`, so that
  your `settings.json` is not replaced.

Then read the release's section in [UPGRADING.md](UPGRADING.md) for anything to
run or merge after it.
