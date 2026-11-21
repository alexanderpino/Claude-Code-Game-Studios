"""Structural contracts added by fix plan Phase 9 (second score remediation).

Run: python -m unittest discover -s studio-tests -p test_engine_phase9.py -v
The fixes and their deductions (score report 2, N1-N5) are in
docs/research/aaa-engine-support-2026/fix-plan.md, section 11. Fix 9.1's tests
extend studio-tests/test_engine_phase8b.py. These check files on disk, not
Claude's behaviour in a session.
"""
from collections import Counter
import difflib
import fnmatch
from pathlib import Path
import re
import subprocess
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_engine_support import (  # noqa: E402
    BASE_RELEASE, CUSTOM_ROOTS, FRONTMATTER, RELEASE_NOTE_SECTIONS, ROOT, base_release_file,
    base_release_names, custom_only_glob_root, custom_only_rules, expand, frontmatter, ledger, read)
from test_engine_phase8 import (  # noqa: E402
    SETUP_CUSTOM, SHADER_CUSTOM_SECTION, SHADER_RULE, bullets, custom_agents, section_text)
from test_engine_scope import (  # noqa: E402
    BASH, NON_CUSTOM_ENGINES, SCRIPT_ENV, SCRIPT_TIMEOUT_S, SIDES, TwoFixtures)

# Fix 9.2 (N2). Rule-versus-agent and rule-versus-example consistency.
RHI_RULE = ".claude/rules/rhi-renderer-code.md"
RHI_AGENT = ".claude/agents/rhi-backend-engineer.md"
RHI_AGENT_SECTION = "All backends"
STREAMING_RULE = ".claude/rules/streaming-io-code.md"
CONCURRENCY_AGENT = ".claude/agents/concurrency-job-system-engineer.md"
FALSE_SHARING = "False sharing"
# Item 1: one device-loss policy. Both statements recreate the device and exit
# only when that fails too (Vulkan spec, Lost Device: logical device loss "may
# be recoverable"; DXGI: the app "must reinitialize the Direct3D device").
DEVICE_LOSS_BULLET = re.compile(r"[Dd]evice[- ]l(?:oss|ost)")
DEVICE_LOSS_POLICY = ("recreate", "only if")
# Item 2: a record callback runs at graph execution, after the function that
# added the pass returned, so a "Correct" example never captures it by default
# reference. A record callback is a lambda whose first parameter is the
# command list or pass context; these are the two forms in the tree.
RECORD_CALLBACK_DEFAULT_REF = re.compile(r"\[&\s*(?:,[^\]]*)?\]\s*\(\s*(?:command_list|PassContext)\s*&")
CORRECT_LABEL = re.compile(r"^\*\*Correct\b")
# Item 3: the Rust loader example checks what the rule's checksum bullet asks.
RUST_LOADER_TOKENS = ("payload_size", "checksum")
# Item 5: the Custom carve-out for the texture-loop bullet.
TEXTURE_LOOP_BULLET = "- No texture reads inside loops"

# Ledgered sections of fixes 9.2 (items 1 and 4) and 9.4: each has a claim
# record whose file and heading name it (fix plan Q9b, step 2). Enumerated
# because which section a phase sourced cannot be derived from the text
# (.claude/rules/skill-authoring.md:76-79).
PHASE9_LEDGERED = [
    (RHI_RULE, "RHI and Renderer Code Rules", "9.2 item 1, device loss"),
    (RHI_AGENT, RHI_AGENT_SECTION, "9.2 item 1, device loss"),
    (CONCURRENCY_AGENT, FALSE_SHARING, "9.2 item 4, cache-line padding"),
    (".claude/agents/editor-ui-framework-engineer.md", "Worked Example — property drawer", "9.4, borrows and label"),
    (".claude/agents/online-services-engineer.md", "API shape", "9.4, OnlineError"),
    (".claude/agents/engine-technical-writer.md", "Measure First", "9.4, rustdoc lints"),
    (".claude/skills/memory-audit/references/evidence.md", "2e. Layout evidence", "9.4, -Wpadded"),
]

# Fix 9.3 (N3). (b) The Must-not paths of the original brief: the Godot, Unity
# and Unreal agents, their specs, and the four shipped engine references.
MUST_NOT_PATHSPECS = (
    ".claude/agents/godot-*", ".claude/agents/unity-*", ".claude/agents/unreal-*", ".claude/agents/ue-*",
    "studio-tests/agents/engine/godot/", "studio-tests/agents/engine/unity/", "studio-tests/agents/engine/unreal/",
    "docs/engine-reference/godot/", "docs/engine-reference/unity/", "docs/engine-reference/unreal/",
    "docs/engine-reference/web/",
)
# Fix plan AM38(e), owner decision 2026-11-18: in a Must-not agent file only
# the frontmatter `model:` and `effort:` lines may differ from the base release,
# and in its spec only the Model-tier line; every other line stays the base
# release's, so each engine specialist's content and routing are unchanged.
SPEC_TIER_PREFIX = "- [ ] Model tier is "


def base_release_text(path):
    """A file's text at the base release, read as UTF-8 (the agents hold em dashes)."""
    return subprocess.run(["git", "-C", str(ROOT), "show", f"{BASE_RELEASE}:{path}"], capture_output=True,
                          encoding="utf-8").stdout


def must_not_problems(path, base, work):
    """The differences between a Must-not file and the base release that AM38(e)
    does not admit, as a list (empty when only the admitted lines differ).

    Positional, not a filter: the work file must be the base file with its one
    frontmatter `model:` line replaced in place and at most one `effort:` line
    directly after it (an agent), or with its one Model-tier line replaced in
    place (a spec). Any other added, moved or changed line is a problem."""
    base_lines = base.replace("\r\n", "\n").split("\n")
    work_lines = work.replace("\r\n", "\n").split("\n")
    if path.startswith(".claude/agents/"):
        close = base_lines.index("---", 1) if base_lines[:1] == ["---"] and "---" in base_lines[1:] else 0
        at = [i for i in range(1, close) if base_lines[i].startswith("model:")]
        if len(at) != 1 or any(base_lines[i].startswith("effort:") for i in range(1, close)):
            return [f"{path}: the base frontmatter has no single model: line and no effort: line to replace"]
        i = at[0]
        head, tail = base_lines[:i], base_lines[i + 1:]
        if work_lines[:i] != head or len(work_lines) <= i or not work_lines[i].startswith("model:"):
            return [f"{path}: lines before the model: line, or the model: line itself, differ from the base release"]
        rest = work_lines[i + 1:]
        if rest[:1] and rest[0].startswith("effort:") and not (tail[:1] and tail[0].startswith("effort:")):
            rest = rest[1:]
        return [] if rest == tail else [f"{path}: a line after the model: and effort: lines differs from the base release"]
    if path.startswith("studio-tests/agents/engine/"):
        at = [i for i, line in enumerate(base_lines) if line.startswith(SPEC_TIER_PREFIX)]
        if len(at) != 1:
            return [f"{path}: the base spec has no single Model-tier line to replace"]
        i = at[0]
        if (len(work_lines) != len(base_lines) or work_lines[:i] != base_lines[:i]
                or not work_lines[i].startswith(SPEC_TIER_PREFIX) or work_lines[i + 1:] != base_lines[i + 1:]):
            return [f"{path}: a line other than the Model-tier line differs from the base release"]
        return []
    return [] if work_lines == base_lines else [f"{path}: differs from the base release"]
# (c) The whole allowed-tools of each skill this change added, with the reason
# for each entry. Recorded, not derived: what a skill needs is a reading of its
# text (.claude/rules/skill-authoring.md:76-79). A change to a list is made
# here, with its reason, where review sees it. Git forms are also held to the
# read-only list in test_engine_phase8.py.
# AM21(a), P9 critic F8: a reason names a step of the skill's text that uses the
# permission; one with no such step is removed from the skill, not recorded.
READ = "reads the project's files"
FIND = "finds files by pattern"
SEARCH = "searches file contents"
ASK = "asks the user (automation-modes.md)"
CONFIG = "reads project.yaml through the helper's resolve_config"
WRITE_REPORT = "writes its report after the user says yes"
# AM40: the exact adr-files.sh commands the new skills run.
ADR_FILES_LIST = "Bash(bash .claude/scripts/adr-files.sh list)"
ADR_FILES_WHERE = "Bash(bash .claude/scripts/adr-files.sh where)"
NEW_SKILL_ALLOWED_TOOLS = {
    "api-review": {
        "Read": READ, "Glob": FIND, "Grep": SEARCH, "AskUserQuestion": ASK,
        "Write": "writes the API review and the migration note after a yes",
        "Agent": "spawns engine-technical-writer for the migration note",
        "Bash(git diff *)": "lists the changed files of the range",
        "Bash(git log *)": "finds the commit that added a deprecation (git log -S)",
        "Bash(git show *)": "reads files and lists folders at the range's head and base (surface.md 2a)",
        "Bash(git merge-base *)": "proposes the branch's range when no argument is given",
        "Bash(git rev-parse *)": "checks both ends of the range",
        "Bash(git tag --list*)": "lists engine release tags for the report",
        "Bash(git status *)": "lists untracked public files for --working-tree",
        'Bash(bash "*/.claude/skills/api-review/../../hooks/yaml-helper.sh" resolve_config *)': CONFIG,
        ADR_FILES_LIST: "lists the ADRs (SKILL.md, Phase 1)",
        ADR_FILES_WHERE: "Greps the ADRs on the `match` row (surface.md)",
    },
    "benchmark-report": {
        "Read": READ, "Glob": FIND, "Grep": SEARCH, "AskUserQuestion": ASK, "Write": WRITE_REPORT,
        "Bash(wc *)": "counts the frames of a capture (wc -l)",
        "Bash(bash .claude/scripts/frame-stats.sh *)":
            "computes N, the nearest-rank percentiles, max, mean and the over-budget count (statistics.md 3a; AM28 D3)",
        'Bash(bash "*/.claude/skills/benchmark-report/../../hooks/yaml-helper.sh" resolve_config *)': CONFIG,
        'Bash(bash "*/.claude/skills/benchmark-report/../../hooks/yaml-helper.sh" get_effective_yaml_key *)':
            "reads performance.enforce",
    },
    "engine-release": {
        "Read": READ, "Glob": FIND, "Grep": SEARCH, "AskUserQuestion": ASK,
        "Write": "writes the engine release record after a yes",
        "Agent": "spawns chief-engine-architect for the inventory review",
        "Bash(git log *)": "lists the release range's commits",
        "Bash(git rev-parse *)": "pins the candidate commit the tag is planned on",
        "Bash(git tag --list*)": "finds the previous engine tag and the tag scheme",
        "Bash(git branch --list *)": "checks the candidate is on the release branch (--contains)",
        "Bash(git status *)": "checks the candidate checkout and build inputs are clean",
        "Bash(bash .claude/scripts/test-run.sh custom)": "Phase 4 runs the integration test (test-run.sh custom)",
        'Bash(bash "*/.claude/skills/engine-release/../../hooks/yaml-helper.sh" resolve_config *)': CONFIG,
        ADR_FILES_LIST: "lists the ADRs whose changes inventory.md 2c reads",
        ADR_FILES_WHERE: "names the ADR folder for inventory.md 2c's git log",
    },
    "memory-audit": {
        "Read": READ, "Glob": FIND, "Grep": SEARCH, "AskUserQuestion": ASK, "Write": WRITE_REPORT,
        "Bash(git log *)": "binds a sanitizer log to the tested revision (git log -1)",
        "Bash(git status *)": "checks the audited sources are unmodified since the log",
        "Bash(git hash-object -- *)": "content receipt without -w: prints the id, writes no object",
        'Bash(bash "*/.claude/skills/memory-audit/../../hooks/yaml-helper.sh" resolve_config *)': CONFIG,
    },
    "perf-regression-triage": {
        "Read": READ, "Glob": FIND, "Grep": SEARCH, "AskUserQuestion": ASK,
        "Write": "writes a new bug file after a yes",
        "Edit": "updates an existing bug's triage or tracking entry after a yes",
        "Bash(git rev-parse *)": "checks the good and bad commits",
        "Bash(git rev-list *)": "counts the commits in the bisect range",
        "Bash(git log *)": "lists suspect commits over the affected paths",
        "Bash(git show *)": "lists a suspect commit's changed paths (--stat)",
        'Bash(bash "*/.claude/skills/perf-regression-triage/../../hooks/yaml-helper.sh" resolve_config *)': CONFIG,
    },
    "team-frame-pipeline": {
        "Read": READ, "Glob": FIND, "Grep": SEARCH, "AskUserQuestion": ASK,
        "Agent": "spawns the rendering agents and chief-engine-architect",
        "Skill": "runs /architecture-decision in engine mode",
        "Bash(bash .claude/scripts/test-run.sh custom)": "Phase 5 runs the Custom tests (references/pipeline.md)",
        'Bash(bash "*/.claude/skills/team-frame-pipeline/../../hooks/yaml-helper.sh" resolve_config *)': CONFIG,
    },
}
ALLOWED_TOOLS_LINE = re.compile(r"^allowed-tools:[ \t]*(.*)$", re.M)
TOOL_ENTRY = re.compile(r"\s*([^,(]+(?:\([^)]*\))?)\s*(?:,|$)")
# (a) A glob added to a base-release rule's paths: starts under a Custom-only
# root (CUSTOM_ROOTS: engine/, crates/, game/), at a folder boundary (fix plan
# AM21(b), P9 critic F4, F5). The layout's other rows (tests/, tools/,
# vendor/, the root build files) are shared by every engine, so they do not
# count; a glob whose first segment is a wildcard has no root and fails. The
# named exceptions, each with its reason (fix plan AM20); a new one is added
# here, where review sees it.
ADDED_GLOB_EXCEPTIONS = {
    ("shader-code", "**/*.slang"):
        "intentional (rules-reference.md, shader-code.md row and the overlaps note): a .slang file is a "
        "shader on any engine, and no base-release rule covered a .slang file outside assets/shaders/ "
        "and Shaders/",
}
RULE_PATH_ITEM = re.compile(r'^  - "([^"]+)"', re.M)
# AM20 (1): the release notes' Permissions passage names every --output deny
# rule that also refuses the display-only --output-indicator-* options.
OUTPUT_INDICATOR = "--output-indicator-*"
OUTPUT_INDICATOR_SUBCOMMANDS = ("diff", "log", "show")
# AM20 (2): the rules reference lists shader-code.md's globs as its
# frontmatter has them.
RULES_REFERENCE = ".claude/docs/rules-reference.md"
SHADER_RULE_NAME = "shader-code.md"
# (d) The Engine Specialists block setup writes into the project's
# preferences: its agent lines name every Custom agent.
ENGINE_SPECIALISTS_HEADING = "## Engine Specialists"
SPECIALIST_AGENT_LINES = ("Primary", "Language/Code Specialist", "Shader Specialist", "Additional Specialists")


# AM22 (score report 3, P1-P3). P1(a): the two hooks this change extended, run
# on the two-fixture setup of test_engine_scope.py after a compaction.
HOOKS = ("session-start.sh", "pre-compact.sh")
COMPACT_INPUT = b'{"hook_event_name":"SessionStart","source":"compact"}\n'
COMPACTION_LOG = "production/session-logs/compaction-log.txt"
LOG_DATE = re.compile(r"^(Context compaction occurred at ).*$", re.M)
CUSTOM_HOOK_BLOCK = {"session-start.sh": "=== ENGINE CONTEXT (Custom engine, restored after compact) ===",
                     "pre-compact.sh": "  Engine context (Custom):"}
UNSET_FRAME_BUDGET = r"target_framerate 60[ ,/].*frame_budget_ms NOT SET"
HOOK_FIXTURE_FILES = {
    "docs/architecture/memory-invariants.md": "# Memory invariants\n- per-frame arena reset at frame end\n",
    "production/session-state/active.md": "# Active\n<!-- STATUS -->\nEpic: fixture\n",
}


def hook_project_yaml(engine):
    return f'engine:\n  name: "{engine}"\nperformance:\n  target_framerate: 60\n'


SHARED_DIRS = (".claude/agents", ".claude/skills")
# P1(b) (shared agent and skill files change only by reviewed hunks) moved to
# test_engine_shared_guard.py: an approved-hunk manifest replaced the diff
# heuristic and its allowlist (fix plan AM27).

# P1(c): what the change added to a modified shared skill's allowed-tools, with
# the reason (the step that uses it). Base entries stay, in base order.
# AM28 D7 (R19, R34): each grant is the exact form the skill runs, so no
# grant reaches test-run.sh's --cmd, --root or --log.
TEST_RUN_CUSTOM = "Bash(bash .claude/scripts/test-run.sh custom)"
TEST_RUN_CUSTOM_NO_BUILD = "Bash(bash .claude/scripts/test-run.sh custom --no-build)"
TEST_SCAFFOLD_CUSTOM = "Bash(bash .claude/scripts/test-scaffold.sh custom*)"
TOOLCHAIN_VERSION = "setup-engine/references/custom.md: records the toolchain versions it detects"
# AM40: the skills that run the ADR location helpers (docs.adr_dir, docs.adr_glob).
ADR_FILES = "Bash(bash .claude/scripts/adr-files.sh *)"
ADR_STATUS = "Bash(bash .claude/scripts/adr-status.sh *)"
SHARED_SKILL_TOOL_ADDITIONS = {
    "dev-story": {TEST_RUN_CUSTOM: "Custom stories verify through test-run.sh custom (SKILL.md, Custom step)"},
    "smoke-check": {TEST_RUN_CUSTOM: "Phase 2 reads the Custom test rule row (references/2-run-tests.md)"},
    "test-setup": {TEST_SCAFFOLD_CUSTOM: "scaffolds the Custom test folders and CI workflow",
                   TEST_RUN_CUSTOM: "runs the scaffolded tests through the helper (references/3-directories.md, Custom)"},
    "setup-engine": {
        "Bash(cmake --version)": TOOLCHAIN_VERSION, "Bash(ctest --version)": TOOLCHAIN_VERSION,
        "Bash(cargo --version)": TOOLCHAIN_VERSION, "Bash(rustc --version)": TOOLCHAIN_VERSION,
        "Bash(clang++ --version)": TOOLCHAIN_VERSION, "Bash(g++ --version)": TOOLCHAIN_VERSION,
        TEST_RUN_CUSTOM_NO_BUILD: "Custom setup runs the tests after its build (references/custom.md, --no-build)",
        TEST_SCAFFOLD_CUSTOM: "Custom setup scaffolds the test folders (references/custom.md)",
        ADR_FILES: "references/custom.md names the first ADRs on adr-files.sh's `new` row",
    },
    "adopt": {ADR_FILES: "references/1-detect.md counts the ADRs adr-files.sh lists"},
    "architecture-decision": {ADR_FILES: "the next ADR number and the new ADR's path (SKILL.md, references/0-accept.md)"},
    "architecture-review": {ADR_FILES: "every phase uses adr-files.sh's `match` row (SKILL.md, Where the ADRs are)"},
    "create-architecture": {ADR_FILES: "references/0-load-context.md greps the ADRs on the `match` row"},
    "design-system": {ADR_FILES: "references/2-gather-context.md and 4-section-design.md read the ADRs it lists"},
    "gate-check": {TEST_RUN_CUSTOM: "the gate files' Custom engine additions run the engine tests",
                   ADR_FILES: "the gate files count and read the ADRs adr-files.sh lists"},
    "next-step": {ADR_FILES: "Step 2's ladder asks whether adr-files.sh lists an ADR"},
    "project-stage-detect": {ADR_FILES: "the Architecture Docs scan counts the ADRs adr-files.sh lists"},
    "code-review": {ADR_STATUS: "finds a referenced ADR's file wherever docs.adr_dir keeps it"},
}
# P3: the allocator agent pads with the concurrency agent's per-target constant.
ALLOCATOR_AGENT = ".claude/agents/memory-allocator-specialist.md"
ALLOCATOR_LAYOUT = "Layout and cache lines"
CACHE_LINE_CONSTANT = "engine::cache_line"
# AM24(f): the cache-line sizes the agents name (64; 128 for CachePadded on
# x86-64 and aarch64; 256 on s390x). SIMD alignments (16, 32) are not lines.
LITERAL_CACHE_LINE = re.compile(r"\b(?:alignas|align)\(\s*(?:64|128|256)\s*\)")


def rule_path_items(text):
    """The quoted paths: items of a rule's frontmatter, as written."""
    return RULE_PATH_ITEM.findall(text.replace("\r", "").split("---", 2)[1])


def allowed_tools(skill):
    line = ALLOWED_TOOLS_LINE.search(frontmatter(read(f".claude/skills/{skill}/SKILL.md")))
    return [entry.strip() for entry in TOOL_ENTRY.findall(line[1])] if line else []


def specialist_line_agents():
    """Agent names on the agent lines of the Engine Specialists block in
    setup-engine's Custom reference (the text setup writes)."""
    text = read(SETUP_CUSTOM).replace("\r", "")
    start = text.find(ENGINE_SPECIALISTS_HEADING)
    block = text[start:text.find("```", start)] if start >= 0 else ""
    names = []
    for label in SPECIALIST_AGENT_LINES:
        line = re.search(rf"^- \*\*{re.escape(label)}\*\*: (.*)$", block, re.M)
        # A parenthesis is a note on the agent before it ("core-systems-lead
        # (memory, jobs, platform; ...)"), not a list of names.
        items = re.sub(r"\([^)]*\)", "", line[1]).split(",") if line else []
        names += [re.match(r"[\w-]+", item.strip())[0] for item in items]
    return names


def fenced_blocks(text):
    """(label line, code) for each fenced block, with the nearest non-blank line
    above the fence as its label."""
    lines, blocks, i = text.replace("\r", "").splitlines(), [], 0
    while i < len(lines):
        if lines[i].startswith("```"):
            label = next((lines[k] for k in range(i - 1, -1, -1) if lines[k].strip()), "")
            end = next((k for k in range(i + 1, len(lines)) if lines[k].startswith("```")), len(lines))
            blocks.append((label, "\n".join(lines[i + 1:end])))
            i = end
        i += 1
    return blocks


def git(*args):
    return subprocess.run(["git", "-C", str(ROOT), *args], capture_output=True, text=True)


def modified_shared_files():
    """Agent and skill files present in the base release that the change modified."""
    out = git("diff", "--name-status", BASE_RELEASE, "--", *SHARED_DIRS)
    return [line.split("\t")[-1] for line in out.stdout.splitlines() if line.startswith("M")]


def run_hook(fx, side, hook):
    """(exit code, stdout, stderr) of one hook in one fixture, fed COMPACT_INPUT."""
    result = subprocess.run([BASH, f".claude/hooks/{hook}"], cwd=fx.roots[side], env=SCRIPT_ENV,
                            input=COMPACT_INPUT, capture_output=True, timeout=SCRIPT_TIMEOUT_S)
    return (result.returncode, fx.normalise(side, result.stdout.decode("utf-8", "replace")),
            fx.normalise(side, result.stderr.decode("utf-8", "replace")))


def hook_observations(fx, side):
    """Both hooks' results in one fixture, and the compaction log without its date."""
    seen = {hook: run_hook(fx, side, hook) for hook in HOOKS}
    log = fx.roots[side] / COMPACTION_LOG
    seen["log"] = LOG_DATE.sub(r"\1<DATE>", log.read_text(encoding="utf-8")) if log.exists() else None
    return seen


class Phase9(unittest.TestCase):
    def test_device_loss_policy_is_one_policy(self):
        # Fix 9.2 item 1: the rule that loads for engine/rhi/** and the agent
        # that writes the backends state the same device-loss policy.
        statements = {
            RHI_RULE: [b for b in bullets(FRONTMATTER.sub("", read(RHI_RULE), count=1))
                       if DEVICE_LOSS_BULLET.search(b)],
            RHI_AGENT: [b for b in bullets(section_text(read(RHI_AGENT), RHI_AGENT_SECTION) or "")
                        if DEVICE_LOSS_BULLET.search(b)],
        }
        for path, found in statements.items():
            with self.subTest(file=path):
                self.assertEqual(len(found), 1, "expected one device-loss bullet")
                flat = " ".join(found[0].split())
                for token in DEVICE_LOSS_POLICY:
                    self.assertIn(token, flat)

    def test_correct_record_callbacks_do_not_capture_by_reference(self):
        # Fix 9.2 item 2: a "Correct" example's record callback copies handles
        # and values; [&] would leave references to the adding function's frame.
        seen = 0
        for path in sorted((ROOT / ".claude").rglob("*.md")):
            for label, code in fenced_blocks(path.read_text(encoding="utf-8")):
                if not CORRECT_LABEL.match(label):
                    continue
                seen += len(re.findall(r"\(\s*(?:command_list|PassContext)\s*&", code))
                for hit in RECORD_CALLBACK_DEFAULT_REF.finditer(code):
                    with self.subTest(file=path.relative_to(ROOT).as_posix(), code=hit[0]):
                        self.fail("record callback captures by default reference")
        self.assertTrue(seen, "no record callback found: the forms are out of date")

    def test_rust_loader_example_checks_checksum_and_payload_size(self):
        # Fix 9.2 item 3: the rule asks for a checksum verified before decoding
        # and for every size checked; its Rust "Correct" example does both, as
        # the C++ one does.
        examples = section_text(read(STREAMING_RULE), "Examples") or ""
        rust = [code for label, code in fenced_blocks(examples) if label.startswith("Rust")]
        self.assertEqual(len(rust), 1, "the Rust loader example was not found")
        for token in RUST_LOADER_TOKENS:
            with self.subTest(token=token):
                self.assertIn(token, rust[0])

    def test_cache_line_padding_is_not_equated_with_crossbeam(self):
        # Fix 9.2 item 4: CachePadded's size is stated (128 on x86-64 and
        # aarch64), and the line size no public primary source gives is
        # marked NOT SOURCEABLE.
        section = " ".join((section_text(read(CONCURRENCY_AGENT), FALSE_SHARING) or "").split())
        self.assertTrue(section, f"no '{FALSE_SHARING}' section")
        self.assertRegex(section, r"CachePadded`[^.]*\b128\b[^.]*x86-64[^.]*aarch64")
        self.assertIn("NOT SOURCEABLE", section)
        # P9 critic F7: the old equation "`#[repr(align(64))]`
        # (`crossbeam_utils::CachePadded`)" (score report 2, N2 item 4).
        self.assertNotRegex(section, r"align\(64\)\)\]`?\s*\(`crossbeam_utils::CachePadded`\)")
        # P9 critic F1: the paired-line prefetcher is the x86-64 reason only;
        # aarch64's 128 has its own reason (crossbeam's cache_padded.rs: "big"
        # cores have 128-byte lines), and no claim ties aarch64 to Intel.
        self.assertNotRegex(section, r"aarch64\s*\([^)]*prefetch")
        self.assertRegex(section, r"x86-64 \([^)]*prefetch")
        self.assertRegex(section, r"aarch64 \([^)]*128-byte")
        for claim in ledger("claims"):
            if (claim.get("file"), claim.get("heading")) == (CONCURRENCY_AGENT, FALSE_SHARING):
                with self.subTest(claim=claim["claim_id"]):
                    self.assertNotRegex(claim["claim"], r"aarch64[^.;]*because[^.;]*Intel")

    def test_cache_line_examples_use_the_named_constant(self):
        # P9 critic F2: the text asks for one named constant per target, so no
        # example in the agent hard-codes the line size in an alignment.
        seen = 0
        for label, code in fenced_blocks(read(CONCURRENCY_AGENT)):
            seen += len(re.findall(r"\balignas\(|\brepr\(align\(|CachePadded", code))
            for hit in re.finditer(r"\balignas\(\s*\d+\s*\)|\brepr\(align\(\s*\d+\s*\)\)", code):
                with self.subTest(label=label, code=hit[0]):
                    self.fail("hard-coded cache-line size in an example")
        self.assertTrue(seen, "no padded example found: the forms are out of date")

    def test_texture_loop_bullet_has_a_custom_carve_out(self):
        # Fix 9.2 item 5: like the branching bullet, the other engines'
        # texture-loop bullet does not bind a Custom engine; base bullets stay
        # unchanged (test_shader_rule_keeps_the_other_engines_bullets).
        body = FRONTMATTER.sub("", read(SHADER_RULE), count=1).split(SHADER_CUSTOM_SECTION)
        items = bullets(body[0])
        self.assertIn(TEXTURE_LOOP_BULLET, items)
        self.assertTrue(any(item.startswith("- Custom engine") and "texture reads inside loops" in item
                            for item in items), "no Custom line for the texture-loop bullet")
        custom = " ".join(body[1].split()) if len(body) > 1 else ""
        self.assertRegex(custom, r"loop[^.]*sampl|sampl[^.]*loop", "the Custom section states no loop rule")

    def test_phase9_sourced_sections_are_ledgered(self):
        # Fixes 9.2 (items 1, 4) and 9.4: each sourced section has a claim
        # record naming it, and its evidence resolves. That each quote supports
        # its sentence is shown by the Phase 9 critic (fix plan Q9b step 4).
        claims = ledger("claims")
        evidence = {e["evidence_id"] for e in ledger("evidence")}
        for path, heading, item in PHASE9_LEDGERED:
            with self.subTest(section=f"{path} # {heading}", item=item):
                self.assertIsNotNone(section_text(read(path), heading), "heading not found")
                records = [c for c in claims if c.get("file") == path and c.get("heading") == heading]
                self.assertTrue(records, "no claim record names this section")
                for claim in records:
                    self.assertTrue(set(claim.get("evidence_ids", [])) <= evidence, claim["claim_id"])

    def test_globs_added_to_base_rules_are_custom_roots(self):
        # Fix 9.3 (a), with AM20: a shared rule that gains a glob outside the
        # Custom roots loads on another engine's paths (the form of original
        # F1). Every added glob starts under a Custom-only root or is a named
        # exception.
        checked = 0
        for path in sorted((ROOT / ".claude/rules").glob("*.md")):
            base = base_release_file(f".claude/rules/{path.name}")
            if base is None:
                continue
            added = ({g for item in rule_path_items(path.read_text(encoding="utf-8")) for g in expand(item)}
                     - {g for item in rule_path_items(base) for g in expand(item)})
            for glob in sorted(added):
                checked += 1
                if (path.stem, glob) in ADDED_GLOB_EXCEPTIONS:
                    continue
                # The literal root ends at a folder boundary ("engine/core/"),
                # so a prefix test cannot pass "engineering/" or a file root.
                root = custom_only_glob_root(glob)
                with self.subTest(rule=path.name, glob=glob):
                    self.assertTrue(root.startswith(CUSTOM_ROOTS), f"not under a Custom root (root {root!r})")
        if base_release_names(".claude/rules") is None:
            self.skipTest(f"base release {BASE_RELEASE} absent from this clone (O14)")
        self.assertTrue(checked, "no glob was added to a base rule: re-check this test")
        for rule, glob in ADDED_GLOB_EXCEPTIONS:
            with self.subTest(exception=(rule, glob)):
                self.assertIn(glob, rule_path_items(read(f".claude/rules/{rule}.md")), "stale exception")

    def test_release_notes_name_every_output_indicator_refusal(self):
        # AM20 (1): the diff and show deny rules refuse --output-indicator-*
        # as the log rule does; the notes' sentence about it names all three.
        for path, region in RELEASE_NOTE_SECTIONS.items():
            flat = " ".join(region.search(read(path))[0].split())
            sentence = next((s for s in re.split(r"(?<=[.;])\s", flat) if OUTPUT_INDICATOR in s), "")
            for subcommand in OUTPUT_INDICATOR_SUBCOMMANDS:
                with self.subTest(path=path, subcommand=subcommand):
                    self.assertTrue(sentence, f"no sentence names {OUTPUT_INDICATOR}")
                    self.assertRegex(sentence, rf"\b{subcommand}\b")

    def test_rules_reference_lists_every_shader_rule_glob(self):
        # AM20 (2): the shader-code.md row lists each paths: item of the rule.
        row = re.search(rf"^\| `{re.escape(SHADER_RULE_NAME)}` \| ([^|]*) \|", read(RULES_REFERENCE), re.M)
        self.assertIsNotNone(row, "no shader-code.md row")
        for item in rule_path_items(read(SHADER_RULE)):
            with self.subTest(glob=item):
                self.assertIn(f"`{item}`", row[1])

    def test_must_not_paths_equal_the_base_release(self):
        # Fix 9.3 (b): the other engines' agents, their specs and the shipped
        # engine references are byte-for-byte the base release's: no tracked
        # file changed, added or removed, and no untracked file added.
        if base_release_names(".claude/agents") is None:
            self.skipTest(f"base release {BASE_RELEASE} absent from this clone (O14)")
        # git ls-tree takes path prefixes, not wildcards: list the folders and
        # match each pathspec here (git diff below reads them as pathspecs).
        base_files = git("ls-tree", "-r", "--name-only", BASE_RELEASE, "--", ".claude/agents/",
                         "studio-tests/agents/engine/", "docs/engine-reference/").stdout.split()
        for spec in MUST_NOT_PATHSPECS:
            with self.subTest(pathspec=spec):
                pattern = spec + "*" if spec.endswith("/") else spec
                self.assertTrue(fnmatch.filter(base_files, pattern), "the pathspec matches no base file: out of date")
        changed = git("diff", "--name-status", BASE_RELEASE, "--", *MUST_NOT_PATHSPECS)
        self.assertEqual(changed.returncode, 0, changed.stderr)
        for line in changed.stdout.splitlines():
            status, path = line.split("\t", 1)
            with self.subTest(path=path):
                self.assertEqual(status, "M", "a Must-not file was added, removed or renamed")
                base = base_release_text(path)
                work = (ROOT / path).read_text(encoding="utf-8")
                self.assertEqual(must_not_problems(path, base, work), [])
        added = git("ls-files", "--others", "--exclude-standard", "--", *MUST_NOT_PATHSPECS)
        self.assertEqual(added.stdout.strip(), "", "untracked files under the Must-not paths")

    def test_must_not_exception_covers_only_model_and_effort(self):
        # AM38(e): the exception admits the agent's frontmatter `model:` and
        # `effort:` lines and the spec's Model-tier line, and nothing else.
        agent = ".claude/agents/unity-specialist.md"
        base = base_release_text(agent)
        work = (ROOT / agent).read_text(encoding="utf-8")
        self.assertEqual(must_not_problems(agent, base, work), [])
        lines = work.replace("\r\n", "\n").split("\n")
        close = lines.index("---", 1)
        model_at = next(i for i in range(1, close) if lines[i].startswith("model:"))
        effort_at = next(i for i in range(1, close) if lines[i].startswith("effort:"))

        def edited(fn):
            copy = list(lines)
            fn(copy)
            return "\n".join(copy)
        cases = {
            "a description edit": edited(lambda c: c.__setitem__(2, c[2].replace("Unity", "Unity Engine", 1))),
            "a tools edit": edited(lambda c: c.__setitem__(
                next(i for i in range(1, close) if c[i].startswith("tools:")), c[3] + ", Agent")),
            "a body line after the frontmatter": edited(lambda c: c.__setitem__(close + 2, c[close + 2] + " (edited)")),
            "a second effort line": edited(lambda c: c.insert(effort_at + 1, "effort: low")),
            "a second model line": edited(lambda c: c.insert(effort_at + 1, "model: haiku")),
            "model moved above name": edited(lambda c: c.insert(1, c.pop(model_at))),
            "effort moved away from model": edited(lambda c: c.insert(1, c.pop(effort_at))),
        }
        for label, text in cases.items():
            with self.subTest(edit=label):
                self.assertTrue(must_not_problems(agent, base, text), f"{label} passed the Must-not check")
        spec = "studio-tests/agents/engine/unity/unity-specialist.md"
        spec_base = base_release_text(spec)
        spec_work = (ROOT / spec).read_text(encoding="utf-8")
        self.assertEqual(must_not_problems(spec, spec_base, spec_work), [])
        tier_line = next(line for line in spec_work.splitlines() if line.startswith(SPEC_TIER_PREFIX))
        spec_cases = {
            "a heading edit": spec_work.replace("## ", "### ", 1),
            "a second Model-tier line": spec_work.replace(tier_line, tier_line + "\n" + tier_line, 1),
        }
        for label, text in spec_cases.items():
            with self.subTest(spec_edit=label):
                self.assertTrue(must_not_problems(spec, spec_base, text), f"{label} passed the Must-not check")

    def test_new_skills_allowed_tools_equal_the_recorded_lists(self):
        # Fix 9.3 (c): every allowed-tools entry of a skill this change added is
        # recorded above with its reason, and every recorded entry is present.
        base = base_release_names(".claude/skills")
        if base is None:
            self.skipTest(f"base release {BASE_RELEASE} absent from this clone (O14)")
        added = sorted(p.name for p in (ROOT / ".claude/skills").iterdir()
                       if (p / "SKILL.md").exists() and p.name not in base)
        self.assertEqual(added, sorted(NEW_SKILL_ALLOWED_TOOLS), "the set of added skills changed")
        for skill in added:
            tools = allowed_tools(skill)
            with self.subTest(skill=skill):
                self.assertEqual(len(tools), len(set(tools)), "an entry repeats")
                self.assertEqual(sorted(tools), sorted(NEW_SKILL_ALLOWED_TOOLS[skill]))
                for reason in NEW_SKILL_ALLOWED_TOOLS[skill].values():
                    self.assertTrue(reason.strip())

    def test_setup_specialist_lines_name_every_custom_agent(self):
        # Fix 9.3 (d): the Engine Specialists lines setup writes into the
        # project's preferences name the Custom agents, each once.
        names = specialist_line_agents()
        self.assertEqual(len(names), len(set(names)), "an agent is named twice")
        self.assertEqual(sorted(names), custom_agents())


    def test_compaction_hooks_match_base_on_non_custom(self):
        # AM22 P1(a): after a compaction, session-start.sh and pre-compact.sh
        # print and log exactly what the base release did on every other
        # engine, and on Custom print and log their engine block.
        for engine in NON_CUSTOM_ENGINES:
            files = dict(HOOK_FIXTURE_FILES, **{"project.yaml": hook_project_yaml(engine)})
            with TwoFixtures(self, files) as fx:
                base, work = (hook_observations(fx, side) for side in SIDES)
            for key in (*HOOKS, "log"):
                with self.subTest(engine=engine, output=key):
                    self.assertIsNotNone(work[key], "the hook wrote no compaction log")
                    self.assertEqual(work[key], base[key])
        files = dict(HOOK_FIXTURE_FILES, **{"project.yaml": hook_project_yaml("Custom")})
        with TwoFixtures(self, files) as fx:
            work = hook_observations(fx, "work")
        with self.subTest(engine="Custom", hook="session-start.sh"):
            self.assertIn(CUSTOM_HOOK_BLOCK["session-start.sh"], work["session-start.sh"][1])
        with self.subTest(engine="Custom", hook="pre-compact.sh"):
            self.assertIn(CUSTOM_HOOK_BLOCK["pre-compact.sh"], work["log"] or "")
        # The fixture sets target_framerate and no frame_budget_ms: both hooks
        # report the unset key as NOT SET, not as an empty value.
        for hook, text in (("session-start.sh", work["session-start.sh"][1]), ("pre-compact.sh", work["log"] or "")):
            with self.subTest(engine="Custom", hook=hook, key="frame_budget_ms"):
                self.assertRegex(text, UNSET_FRAME_BUDGET)


    def test_shared_skills_allowed_tools_are_base_plus_recorded_additions(self):
        # AM22 P1(c): a modified shared skill keeps base's allowed-tools in base
        # order and adds only the recorded entries.
        if base_release_names(".claude/skills") is None:
            self.skipTest(f"base release {BASE_RELEASE} absent from this clone (O14)")
        skills = sorted(Path(p).parent.name for p in modified_shared_files() if p.endswith("/SKILL.md")
                        and p.startswith(".claude/skills/"))
        self.assertTrue(skills, "no modified shared skill found: re-check this test")
        self.assertLessEqual(set(SHARED_SKILL_TOOL_ADDITIONS), set(skills), "a recorded skill is not modified")
        for skill in skills:
            base = ALLOWED_TOOLS_LINE.search(frontmatter(base_release_file(f".claude/skills/{skill}/SKILL.md")))
            base = [e.strip() for e in TOOL_ENTRY.findall(base[1])] if base else []
            work = allowed_tools(skill)
            added = SHARED_SKILL_TOOL_ADDITIONS.get(skill, {})
            with self.subTest(skill=skill):
                self.assertEqual([t for t in work if t not in added], base, "base entries changed")
                self.assertEqual(sorted(set(work) - set(base)), sorted(added))
                for reason in added.values():
                    self.assertTrue(reason.strip())

    def test_custom_examples_use_no_literal_cache_line_alignment(self):
        # AM23(d): a code example in a Custom agent or a Custom-only rule
        # aligns to a cache line only through the per-target constant; a line
        # with a literal 64-byte alignment must name it.
        files = [f".claude/agents/{agent}.md" for agent in custom_agents()]
        files += [f".claude/rules/{rule}.md" for rule in sorted(custom_only_rules())]
        self.assertTrue(files)
        for path in files:
            for label, code in fenced_blocks(read(path)):
                for line in code.splitlines():
                    if LITERAL_CACHE_LINE.search(line) and CACHE_LINE_CONSTANT not in line:
                        with self.subTest(file=path, line=line.strip()):
                            self.fail("literal cache-line alignment in an example")

    def test_allocator_agent_pads_with_the_per_target_constant(self):
        # AM22 P3: like concurrency-job-system-engineer (P9 F1, F2), the
        # allocator agent names the per-target constant, not a literal 64.
        text = read(ALLOCATOR_AGENT)
        layout = section_text(text, ALLOCATOR_LAYOUT) or ""
        self.assertTrue(layout, f"no '{ALLOCATOR_LAYOUT}' section")
        for where, body in (("description", frontmatter(text)), (ALLOCATOR_LAYOUT, layout)):
            with self.subTest(where=where):
                self.assertNotRegex(body, LITERAL_CACHE_LINE)
        self.assertIn(CACHE_LINE_CONSTANT, layout)
        self.assertIn("concurrency-job-system-engineer", layout)


if __name__ == "__main__":
    unittest.main()
