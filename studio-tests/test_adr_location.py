"""docs.adr_dir and docs.adr_glob: where the project keeps its ADRs.

Run: python -m unittest discover -s studio-tests -p test_adr_location.py -v

Each test builds a fixture project in the OS temp directory. The scripts run
with `--root <fixture>`; the hooks and the status line run inside a fixture
that holds a copy of `.claude/`. These test the scripts' and hooks'
observations, not a Claude session.
"""

from pathlib import Path
import fnmatch
import os
import re
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / ".claude" / "scripts"
GIT_BASH = Path("C:/Program Files/Git/bin/bash.exe")
BASH = str(GIT_BASH) if GIT_BASH.exists() else shutil.which("bash")
SCRIPT_ENV = {k: v for k, v in os.environ.items() if k != "CLAUDE_PROJECT_DIR"}
SCRIPT_TIMEOUT_S = 120
COMPACT_INPUT = '{"hook_event_name":"SessionStart","source":"compact"}\n'
COMPACTION_LOG = "production/session-logs/compaction-log.txt"

DECISIONS = "docs/architecture/decisions"
CONFIGURED = f"docs:\n  adr_dir: {DECISIONS}\n  adr_glob: ADR-*.md\n"
CUSTOM = 'engine:\n  name: "Custom"\nmodes:\n  workflow: standard\n'
GODOT = 'engine:\n  name: "Godot"\nmodes:\n  workflow: standard\n'


def adr(title, status=None, front=None, depends=None):
    """An ADR's text: optional YAML front matter, a title, a Status section."""
    text = f"---\n{front}---\n" if front else ""
    text += f"# {title}\n\n"
    if status is not None:
        text += f"## Status\n\n{status}\n\n"
    if depends is not None:
        text += f"## ADR Dependencies\n\n| Field | Value |\n|---|---|\n| **Depends On** | {depends} |\n"
    return text


# A project that keeps its ADRs in docs/architecture/decisions/ as ADR-*.md:
# a status with a full stop, a status from front matter only, a lower-case
# file name, a file that is not an ADR, and an ADR in the default folder that
# is outside the configured location.
CONFIGURED_FILES = {
    f"{DECISIONS}/ADR-0003-layered-modules.md": adr("ADR-0003: Layered modules", "Accepted."),
    f"{DECISIONS}/ADR-0004-job-system.md": adr("ADR-0004: Job system", front="status: proposed\n",
                                               depends="ADR-0003"),
    f"{DECISIONS}/adr-0005-memory.md": adr("ADR-0005: Memory", front='status: "Accepted"\n'),
    f"{DECISIONS}/README.md": "# Decisions\n",
    "docs/architecture/adr-0001-elsewhere.md": adr("ADR-0001: Elsewhere", "Accepted"),
}

INVALID = (
    ("absolute folder", "  adr_dir: /tmp/adrs\n", "docs.adr_dir: absolute path '/tmp/adrs'"),
    ("parent folder", "  adr_dir: ../outside\n", "docs.adr_dir: '..' not allowed in '../outside'"),
    ("missing folder", "  adr_dir: docs/missing\n", "docs.adr_dir: no folder 'docs/missing'"),
    ("pattern with a folder", "  adr_glob: decisions/ADR-*.md\n", "docs.adr_glob: a file-name pattern"),
    ("folder list", "  adr_dir: [docs/a, docs/b]\n", "docs.adr_dir: one folder path, not '[docs/a, docs/b]'"),
    ("folder placeholder", "  adr_dir: \"[TO BE CONFIGURED]\"\n",
     "docs.adr_dir: one folder path, not '[TO BE CONFIGURED]'"),
    ("pattern list", "  adr_glob: [ADR-*.md, x]\n", "docs.adr_glob: one file-name pattern, not '[ADR-*.md, x]'"),
    ("pattern mapping", "  adr_glob: {a: b}\n", "docs.adr_glob: one file-name pattern, not '{a: b}'"),
)
ANY_CASE_ADR = "[Aa][Dd][Rr]-*.[Mm][Dd]"
SKILLS = ROOT / ".claude" / "skills"
# Files held to the base release plus Custom units (test_engine_authoring,
# test_engine_support), each with the text in its skill that reaches the ADRs
# where docs.adr_dir keeps them.
ADR_PATH_MAPPING = ("Where a reference file names an existing ADR `docs/architecture/[adr-file].md`, "
                    "use its path on a `file` row instead.")
HELD_TO_BASE = {
    "architecture-decision/references/3-gather-context.md": ("architecture-decision/SKILL.md", ADR_PATH_MAPPING),
    "create-stories/SKILL.md": ("create-stories/SKILL.md", "bash .claude/scripts/adr-status.sh ADR-0001"),
}


def write(root, files):
    for rel, text in files.items():
        path = Path(root, rel)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8", newline="\n")


def rows(out, kind):
    """The TSV rows of one kind, without their first column."""
    return [line.split("\t")[1:] for line in out.splitlines() if line.split("\t")[0] == kind]


def counts(out):
    return {line.split("\t")[0]: line.split("\t")[1] for line in out.splitlines()
            if line.split("\t")[0] in ("adrs", "accepted", "proposed", "other", "no_status")}


@unittest.skipUnless(BASH, "bash not found")
class AdrScriptsTest(unittest.TestCase):
    """adr-files.sh, adr-status.sh, adr-dep-graph.sh, registry.sh, project-state.sh."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory(prefix="ccgs-adr-")
        self.root = Path(self._tmp.name).resolve()

    def tearDown(self):
        self._tmp.cleanup()

    def script(self, name, *args):
        result = subprocess.run([BASH, (SCRIPTS / name).as_posix(), *args], capture_output=True,
                                text=True, env=SCRIPT_ENV, timeout=SCRIPT_TIMEOUT_S)
        return result.returncode, result.stdout.replace("\r", ""), result.stderr

    def in_root(self, name, *args):
        return self.script(name, "--root", self.root.as_posix(), *args)

    def test_default_layout_is_found_as_before(self):
        write(self.root, {"docs/architecture/adr-0001-a.md": adr("ADR-0001: A", "Accepted"),
                          "docs/architecture/adr-0002-b.md": adr("ADR-0002: B", "Proposed"),
                          "docs/architecture/architecture.md": "# Architecture\n"})
        code, out, err = self.in_root("adr-files.sh", "list")
        self.assertEqual(code, 0, err)
        self.assertEqual(rows(out, "dir"), [["docs/architecture", "default"]])
        self.assertEqual(rows(out, "glob"), [["adr-*.md", "default"]])
        self.assertEqual(rows(out, "new"), [["docs/architecture/adr-NNNN-<slug>.md"]])
        self.assertEqual(rows(out, "file"), [["docs/architecture/adr-0001-a.md"],
                                             ["docs/architecture/adr-0002-b.md"]])
        code, out, err = self.in_root("adr-status.sh")
        self.assertEqual(code, 0, err)
        self.assertIn("adrs\t2\tdocs/architecture/adr-*.md", out)
        self.assertEqual(counts(out), {"adrs": "2", "accepted": "1", "proposed": "1",
                                       "other": "0", "no_status": "0"})

    def test_configured_location_is_read_by_adr_status(self):
        write(self.root, dict(CONFIGURED_FILES, **{"project.yaml": CONFIGURED}))
        code, out, err = self.in_root("adr-files.sh")
        self.assertEqual(code, 0, err)
        self.assertEqual(rows(out, "dir"), [[DECISIONS, "docs.adr_dir"]])
        self.assertEqual(rows(out, "glob"), [["ADR-*.md", "docs.adr_glob"]])
        self.assertEqual(rows(out, "new"), [[f"{DECISIONS}/ADR-NNNN-<slug>.md"]])
        self.assertEqual([r[0] for r in rows(out, "file")],
                         [f"{DECISIONS}/ADR-0003-layered-modules.md", f"{DECISIONS}/ADR-0004-job-system.md",
                          f"{DECISIONS}/adr-0005-memory.md"])
        code, out, err = self.in_root("adr-status.sh")
        self.assertEqual(code, 0, err)
        self.assertIn(f"adrs\t3\t{DECISIONS}/ADR-*.md", out)
        self.assertEqual(counts(out), {"adrs": "3", "accepted": "2", "proposed": "1",
                                       "other": "0", "no_status": "0"})
        status = {r[0]: r[2] for r in rows(out, "ADR")}
        self.assertEqual(status, {"adr-0003": "Accepted", "adr-0004": "Proposed", "adr-0005": "Accepted"})

    def test_a_status_section_wins_over_front_matter(self):
        write(self.root, {"docs/architecture/adr-0001-a.md": adr("ADR-0001: A", "Accepted",
                                                                  front="status: proposed\n")})
        code, out, err = self.in_root("adr-status.sh")
        self.assertEqual(code, 0, err)
        self.assertEqual(counts(out)["accepted"], "1")

    def test_ids_match_without_regard_to_case(self):
        write(self.root, dict(CONFIGURED_FILES, **{"project.yaml": CONFIGURED}))
        for given in ("ADR-0003", "adr-0003", "0003", "3"):
            with self.subTest(id=given):
                code, out, err = self.in_root("adr-status.sh", given)
                self.assertEqual(code, 0, err)
                self.assertEqual([r[1] for r in rows(out, "ADR")], [f"{DECISIONS}/ADR-0003-layered-modules.md"])
        code, out, err = self.in_root("adr-status.sh", "ADR-0005")
        self.assertEqual([r[1] for r in rows(out, "ADR")], [f"{DECISIONS}/adr-0005-memory.md"])
        code, out, err = self.in_root("adr-status.sh", "ADR-0001")
        self.assertEqual(code, 3)
        self.assertIn("NOT_FOUND\tADR-0001", out)

    def test_dependency_graph_reads_the_configured_location(self):
        write(self.root, dict(CONFIGURED_FILES, **{"project.yaml": CONFIGURED}))
        code, out, err = self.in_root("adr-dep-graph.sh")
        self.assertEqual(code, 0, err)
        self.assertIn("ADRS: 3", out)
        self.assertIn("adr-0004 -> adr-0003", out)
        self.assertNotIn("adr-0001", out)

    def test_dependency_graph_still_takes_a_folder(self):
        write(self.root, {"adr-2024/adr-0001-a.md": adr("ADR-0001: A", "Accepted", depends="None"),
                          "adr-2024/ADR-0002-b.md": adr("ADR-0002: B", "Accepted", depends="ADR-0001")})
        code, out, err = self.script("adr-dep-graph.sh", (self.root / "adr-2024").as_posix())
        self.assertEqual(code, 0, err)
        self.assertIn("ADRS: 2", out)
        self.assertIn("adr-0002 -> adr-0001", out)

    def test_next_adr_id_counts_the_configured_location(self):
        write(self.root, dict(CONFIGURED_FILES, **{"project.yaml": CONFIGURED}))
        code, out, err = self.in_root("registry.sh", "next-id", "adr")
        self.assertEqual(code, 0, err)
        self.assertEqual(out.split("\t")[:4], ["next", "adr", "-", "ADR-0006"])

    def test_project_state_counts_the_configured_location(self):
        write(self.root, dict(CONFIGURED_FILES, **{"project.yaml": CONFIGURED}))
        code, out, err = self.in_root("project-state.sh")
        self.assertEqual(code, 0, err)
        self.assertIn(f"adr\t3\t{DECISIONS}/ADR-*.md\n", out)
        self.assertIn("phase_inferred\ttechnical-setup\t", out)

    def test_an_unusable_value_is_not_assessed_with_its_reason(self):
        write(self.root, {"docs/architecture/adr-0001-a.md": adr("ADR-0001: A", "Accepted")})
        for name, lines, reason in INVALID:
            with self.subTest(value=name):
                write(self.root, {"project.yaml": "docs:\n" + lines})
                code, out, err = self.in_root("adr-files.sh", "list")
                self.assertEqual(code, 3, out + err)
                self.assertEqual(len(rows(out, "invalid")), 1, out)
                self.assertIn(reason, rows(out, "invalid")[0][0])
                self.assertEqual(rows(out, "file"), [])
                code, out, err = self.in_root("adr-status.sh")
                self.assertEqual(code, 4, out + err)
                self.assertIn(f"NOT_ASSESSED\t{reason}", out)
                self.assertNotIn("ADR\t", out)
                code, out, err = self.in_root("adr-dep-graph.sh")
                self.assertEqual(code, 3, out + err)
                self.assertIn(f"ADRS: NOT ASSESSED ({reason}", out)
                code, out, err = self.in_root("registry.sh", "next-id", "adr")
                self.assertEqual(code, 5, out + err)
                self.assertIn(f"NOT_ASSESSED\tadr\t{reason}", out)
                code, out, err = self.in_root("project-state.sh")
                self.assertEqual(code, 0, err)
                self.assertIn(f"adr\tunknown\tinvalid: {reason}", out)

    def test_a_quoted_character_class_is_a_pattern(self):
        write(self.root, {f"docs/architecture/{n}": adr("X", "Accepted")
                          for n in ("Adr-0001-a.md", "adr-0002-b.md", "0003-c.md", "notes.md")})
        cases = (('"[Aa]dr-*.md"', "[Aa]dr-*.md", "[Aa][Dd][Rr]-*.[Mm][Dd]", ["Adr-0001-a.md", "adr-0002-b.md"]),
                 ("'[0-9][0-9][0-9][0-9]-*.md'", "[0-9][0-9][0-9][0-9]-*.md",
                  "[0-9][0-9][0-9][0-9]-*.[Mm][Dd]", ["0003-c.md"]))
        for given, value, match, names in cases:
            with self.subTest(glob=given):
                write(self.root, {"project.yaml": f"docs:\n  adr_glob: {given}\n"})
                code, out, err = self.in_root("adr-files.sh", "list")
                self.assertEqual(code, 0, out + err)
                self.assertEqual(rows(out, "glob"), [[value, "docs.adr_glob"]])
                self.assertEqual(rows(out, "match"), [[f"docs/architecture/{match}"]])
                self.assertEqual([r[0] for r in rows(out, "file")], [f"docs/architecture/{n}" for n in names])

    def test_the_match_row_is_a_glob_for_exactly_the_listed_files(self):
        # Skills hand the `match` row to Grep's glob= and to bash, which match
        # case-sensitively: it spells the case-insensitive match out.
        extra = {f"{DECISIONS}/Adr-0006-mixed.md": adr("ADR-0006: Mixed", "Accepted"),
                 f"{DECISIONS}/notes-adr-0007.md": "# Not an ADR\n"}
        for yaml, folder in ((CONFIGURED, DECISIONS), ("", "docs/architecture")):
            with self.subTest(folder=folder):
                write(self.root, dict(CONFIGURED_FILES, **extra, **{"project.yaml": yaml}))
                code, out, err = self.in_root("adr-files.sh", "list")
                self.assertEqual(code, 0, out + err)
                match = rows(out, "match")
                self.assertEqual(match, [[f"{folder}/{ANY_CASE_ADR}"]])
                listed = [r[0] for r in rows(out, "file")]
                self.assertTrue(listed)
                on_disk = sorted(f"{folder}/{p.name}" for p in Path(self.root, folder).iterdir()
                                 if p.is_file() and fnmatch.fnmatchcase(p.name, ANY_CASE_ADR))
                self.assertEqual(listed, on_disk)
                result = subprocess.run([BASH, "-c", f'cd "{self.root.as_posix()}" && printf "%s\n" {match[0][0]}'],
                                        capture_output=True, text=True, env=SCRIPT_ENV, timeout=SCRIPT_TIMEOUT_S)
                self.assertEqual(result.stdout.split(), listed)

    def test_the_settings_are_refused_in_project_local_yaml(self):
        write(self.root, dict(CONFIGURED_FILES, **{
            "project.yaml": "engine:\n  name: Custom\n",
            "project.local.yaml": CONFIGURED}))
        helper = (ROOT / ".claude" / "hooks" / "yaml-helper.sh").as_posix()
        result = subprocess.run(
            [BASH, "-c", f'. "{helper}"; validate_local_scope project.local.yaml'],
            cwd=self.root, capture_output=True, text=True, env=SCRIPT_ENV, timeout=SCRIPT_TIMEOUT_S)
        self.assertEqual(result.returncode, 1, result.stderr)
        self.assertIn("`docs.adr_dir` is not locally overridable", result.stderr)
        self.assertIn("`docs.adr_glob` is not locally overridable", result.stderr)
        code, out, err = self.in_root("adr-files.sh", "where")
        self.assertEqual(code, 0, err)
        self.assertEqual(rows(out, "dir"), [["docs/architecture", "default"]])


@unittest.skipUnless(BASH, "bash not found")
class AdrHooksTest(unittest.TestCase):
    """session-start.sh, pre-compact.sh, detect-gaps.sh and statusline.sh, in a
    fixture holding a copy of `.claude/`."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory(prefix="ccgs-adr-hooks-")
        self.root = Path(self._tmp.name).resolve()
        shutil.copytree(ROOT / ".claude", self.root / ".claude",
                        ignore=shutil.ignore_patterns("__pycache__"))

    def tearDown(self):
        self._tmp.cleanup()

    def hook(self, rel, stdin=""):
        result = subprocess.run([BASH, rel], cwd=self.root, input=stdin, capture_output=True,
                                text=True, env=SCRIPT_ENV, timeout=SCRIPT_TIMEOUT_S)
        self.assertEqual(result.returncode, 0, result.stderr)
        return result.stdout.replace("\r", "")

    def compaction_log(self):
        log = self.root / COMPACTION_LOG
        return log.read_text(encoding="utf-8") if log.exists() else ""

    def test_engine_context_lists_the_accepted_adrs_of_the_configured_location(self):
        write(self.root, dict(CONFIGURED_FILES, **{"project.yaml": CUSTOM + CONFIGURED}))
        out = self.hook(".claude/hooks/session-start.sh", COMPACT_INPUT)
        self.assertIn("Accepted ADRs (2):", out)
        self.assertIn("ADR-0003: Layered modules", out)
        self.assertIn("ADR-0005: Memory", out)
        self.assertNotIn("ADR-0001: Elsewhere", out)
        self.hook(".claude/hooks/pre-compact.sh", COMPACT_INPUT)
        log = self.compaction_log()
        self.assertIn("accepted ADRs (2):", log)
        self.assertIn("ADR-0003: Layered modules", log)

    def test_engine_context_names_the_configured_location_when_it_has_none(self):
        write(self.root, {"project.yaml": CUSTOM + CONFIGURED, f"{DECISIONS}/README.md": "# Decisions\n"})
        out = self.hook(".claude/hooks/session-start.sh", COMPACT_INPUT)
        self.assertIn(f"Accepted ADRs: none (no {DECISIONS}/ADR-*.md)", out)
        self.hook(".claude/hooks/pre-compact.sh", COMPACT_INPUT)
        self.assertIn(f"accepted ADRs: none (no {DECISIONS}/ADR-*.md)", self.compaction_log())

    def test_engine_context_default_message_is_unchanged(self):
        write(self.root, {"project.yaml": CUSTOM})
        out = self.hook(".claude/hooks/session-start.sh", COMPACT_INPUT)
        self.assertIn("Accepted ADRs: none (no docs/architecture/adr-*.md)", out)

    def test_engine_context_is_not_assessed_for_an_unusable_value(self):
        for name, lines, reason in INVALID:
            with self.subTest(value=name):
                write(self.root, {"project.yaml": CUSTOM + "docs:\n" + lines, "docs/README.md": "# Docs\n"})
                out = self.hook(".claude/hooks/session-start.sh", COMPACT_INPUT)
                self.assertIn(f"Accepted ADRs: NOT ASSESSED ({reason}", out)
                self.hook(".claude/hooks/pre-compact.sh", COMPACT_INPUT)
                self.assertIn(f"accepted ADRs: NOT ASSESSED ({reason}", self.compaction_log())

    def test_detect_gaps_counts_the_configured_adrs(self):
        one = {f"{DECISIONS}/ADR-0003-layered-modules.md": adr("ADR-0003: Layered modules", "Accepted"),
               f"{DECISIONS}/README.md": "# Decisions\n",
               "docs/architecture/architecture.md": "# Architecture\n",
               "docs/architecture/frame-budget.md": "# Frame budget\n",
               "docs/architecture/memory-invariants.md": "# Memory invariants\n"}
        cases = (("Custom", CUSTOM, {"engine/core/src/a.cpp": "int a;\n"}),
                 ("Godot", GODOT, {"src/core/a.gd": "extends Node\n"}))
        for engine, yaml, code in cases:
            with self.subTest(engine=engine):
                write(self.root, dict(one, **code, **{"project.yaml": yaml + CONFIGURED}))
                out = self.hook(".claude/hooks/detect-gaps.sh")
                self.assertIn("Core systems exist but only 1 ADR(s) documented", out)
        write(self.root, {f"{DECISIONS}/ADR-000{n}-x.md": adr(f"ADR-000{n}: X", "Accepted") for n in (4, 5)})
        out = self.hook(".claude/hooks/detect-gaps.sh")
        self.assertNotIn("ADR(s) documented", out)

    def test_detect_gaps_does_not_count_for_an_unusable_value(self):
        write(self.root, {"project.yaml": CUSTOM + "docs:\n  adr_dir: docs/missing\n",
                          "docs/README.md": "# Docs\n", "engine/core/src/a.cpp": "int a;\n"})
        out = self.hook(".claude/hooks/detect-gaps.sh")
        self.assertNotIn("ADR(s) documented", out)
        self.assertIn("NOT CHECKED: the ADR location is invalid (docs.adr_dir: no folder 'docs/missing')", out)

    def test_artifact_check_reads_the_configured_adrs(self):
        engine_adr = "\n## Platform / Graphics-API Matrix\n"
        write(self.root, {f"{DECISIONS}/ADR-000{n}-x.md": adr(f"ADR-000{n}: X", "Accepted") + engine_adr
                          for n in (3, 4, 5)})
        write(self.root, {"project.yaml": CUSTOM + CONFIGURED, "docs/architecture/adr-0001-a.md": "# A\n"})
        out = self.hook(".claude/scripts/artifact-check.sh")
        steps = {line.split()[1]: line for line in out.splitlines() if line.strip().startswith("STEP:")}
        self.assertIn("status=PRESENT count=3 min=3", steps["architecture-decision"])
        self.assertIn("status=PRESENT count=3", steps["engine-adrs"])
        write(self.root, {"project.yaml": CUSTOM + "docs:\n  adr_dir: docs/missing\n"})
        out = self.hook(".claude/scripts/artifact-check.sh")
        steps = {line.split()[1]: line for line in out.splitlines() if line.strip().startswith("STEP:")}
        self.assertIn("status=UNKNOWN reason=docs.adr_dir: no folder 'docs/missing' why=adr-location-invalid",
                      steps["architecture-decision"])
        write(self.root, {"project.yaml": CUSTOM})
        out = self.hook(".claude/scripts/artifact-check.sh")
        steps = {line.split()[1]: line for line in out.splitlines() if line.strip().startswith("STEP:")}
        self.assertIn("status=SHORT", steps["architecture-decision"])
        self.assertIn("glob=docs/architecture/adr-*.md", steps["architecture-decision"])

    def test_status_line_infers_the_stage_from_the_configured_adrs(self):
        write(self.root, dict(CONFIGURED_FILES, **{"project.yaml": GODOT + CONFIGURED}))
        Path(self.root, "docs/architecture/adr-0001-elsewhere.md").unlink()
        payload = ('{"model": {"display_name": "M"}, "workspace": {"project_dir": "'
                   + self.root.as_posix() + '"}}')
        self.assertIn("Pre-Production", self.hook(".claude/statusline.sh", payload))
        write(self.root, {"project.yaml": GODOT})
        self.assertIn("Technical Setup", self.hook(".claude/statusline.sh", payload))

    def test_status_line_does_not_infer_a_stage_for_an_unusable_value(self):
        write(self.root, dict(CONFIGURED_FILES, **{"project.yaml": GODOT + "docs:\n  adr_dir: docs/missing\n"}))
        payload = ('{"model": {"display_name": "M"}, "workspace": {"project_dir": "'
                   + self.root.as_posix() + '"}}')
        out = self.hook(".claude/statusline.sh", payload)
        self.assertIn("Stage NOT ASSESSED (docs.adr_dir)", out)
        self.assertNotIn("Technical Setup", out)
        self.assertNotIn("Pre-Production", out)


class AdrSkillTextTest(unittest.TestCase):
    """What the skills tell Claude about the ADR location."""

    def skill_texts(self):
        for skill in sorted(SKILLS.glob("*/SKILL.md")):
            texts = [skill] + sorted(skill.parent.rglob("references/**/*.md")) + sorted(
                p for p in skill.parent.glob("*.md") if p.name != "SKILL.md")
            yield skill, {p: p.read_text(encoding="utf-8") for p in texts}

    def test_skills_allow_adr_files_where_they_run_it(self):
        seen = 0
        for skill, texts in self.skill_texts():
            if not any("adr-files.sh" in t for t in texts.values()):
                continue
            seen += 1
            front = texts[skill].split("---", 2)[1]
            allowed = re.search(r"^allowed-tools: *(.*)$", front, re.M)
            patterns = re.findall(r"Bash\(([^)]*)\)", allowed[1]) if allowed else []
            for command in ("bash .claude/scripts/adr-files.sh list", "bash .claude/scripts/adr-files.sh where"):
                with self.subTest(skill=skill.parent.name, command=command):
                    self.assertTrue(any(re.fullmatch("".join(".*" if c == "*" else re.escape(c) for c in p),
                                                     command) for p in patterns),
                                    "no allowed-tools pattern lets the skill run this command")
        self.assertGreater(seen, 5, "no skill runs adr-files.sh: the scan is out of date")

    def test_no_skill_names_an_adr_path_in_the_default_folder(self):
        # A path built on docs/architecture/, or a check that counts ADRs
        # there, misses ADRs that docs.adr_dir keeps elsewhere.
        hard = re.compile(r"docs/architecture/\[adr|<docs\.adr_dir>"
                          r"|ADRs?\b[^\n`]{0,60}`docs/architecture/`|`docs/architecture/`[^\n`]{0,40}\bADR")
        found = [f"{p.relative_to(ROOT).as_posix()}:{n}: {line.strip()}"
                 for _, texts in self.skill_texts() for p, text in texts.items()
                 if p.relative_to(SKILLS).as_posix() not in HELD_TO_BASE
                 for n, line in enumerate(text.splitlines(), 1)
                 if hard.search(line) and "use its path on a `file` row" not in line]
        self.assertEqual(found, [])
        # A file that other tests hold to the base release keeps its text;
        # its skill reaches the configured location elsewhere.
        for rel, (where, mapping) in HELD_TO_BASE.items():
            with self.subTest(file=rel):
                self.assertIn(mapping, " ".join((SKILLS / where).read_text(encoding="utf-8").split()))


if __name__ == "__main__":
    unittest.main()
