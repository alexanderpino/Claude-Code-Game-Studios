"""scripts/adopt.sh and scripts/adopt.ps1: copy the framework into a project.

Run: python -m unittest discover -s studio-tests -p test_adopt_scripts.py -v

Each test builds a fixture project in the OS temp directory, runs a script on
it and reads the files it left. The bash script runs through Git Bash on
Windows (bash on PATH elsewhere); the PowerShell script runs through pwsh and
is skipped without it. A last class runs both on the same fixtures and needs
the same files, exit codes and action lines from each. ADOPTING.md states the
behaviour these tests check.

The scripts run from a snapshot of this repository (its `.claude/`, `CLAUDE.md`,
`LICENSE` and `scripts/`) in a temp folder whose name has a space, so an edit to
the working tree during the run cannot change what a test compares against.
They run in an empty working directory of their own, which must stay empty.
"""

from pathlib import Path
import os
import re
import shutil
import stat
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
GIT_BASH = Path("C:/Program Files/Git/bin/bash.exe")
BASH = str(GIT_BASH) if GIT_BASH.exists() else shutil.which("bash")
PWSH = shutil.which("pwsh")
GIT = shutil.which("git")
SCRIPT_ENV = {k: v for k, v in os.environ.items() if k != "CLAUDE_PROJECT_DIR"}
SCRIPT_TIMEOUT_S = 300

# The framework-owned paths, as ADOPTING.md lists them ("What the scripts do").
FRAMEWORK_DIRS = (".claude/agents", ".claude/skills", ".claude/rules", ".claude/hooks",
                  ".claude/scripts", ".claude/engines", ".claude/genres", ".claude/docs")
FRAMEWORK_FILES = (".claude/statusline.sh",)
LICENSE_COPY = ".claude/LICENSE"
PROJECT_OWNED = ".claude/docs/technical-preferences.md"
AGENT_MODELS = ".claude/agent-models.yaml"
AGENT_MODELS_SIDECAR = ".claude/agent-models.ccgs.yaml"
SETTINGS = ".claude/settings.json"
SETTINGS_SIDECAR = ".claude/settings.ccgs.json"
GITIGNORE_LINES = ("production/session-state/", "production/session-logs/", "project.local.yaml",
                   ".claude/worktrees/")
GITATTRIBUTES_LINES = (".claude/**/*.sh text eol=lf", ".claude/**/*.awk text eol=lf",
                       ".claude/**/*.tsv text eol=lf")
ACTION = re.compile(r"^(ADD|OVERWRITE|UNCHANGED|SKIP|APPEND) (\S.*?)(?: \((.*)\))?$")


_SNAPSHOT = {}


def setUpModule():
    tmp = tempfile.TemporaryDirectory()
    unittest.addModuleCleanup(tmp.cleanup)
    fork = Path(tmp.name, "ccgs fork")
    for rel in (".claude", "scripts"):
        shutil.copytree(ROOT / rel, fork / rel,
                        ignore=shutil.ignore_patterns("settings.local.json", "agent-memory", "worktrees"))
    for rel in ("CLAUDE.md", "LICENSE"):
        shutil.copy2(ROOT / rel, fork / rel)
    (fork / "docs").mkdir()
    cwd = Path(tmp.name, "cwd")
    cwd.mkdir()
    _SNAPSHOT["root"] = fork
    _SNAPSHOT["cwd"] = cwd
    _SNAPSHOT["fingerprint"] = fingerprint(fork)


def fork():
    """The snapshot the scripts run from: the framework they copy."""
    return _SNAPSHOT["root"]


def fingerprint(top):
    """Every file and folder under top, with its size and modification time."""
    top = Path(top)
    return {p.relative_to(top).as_posix(): (p.is_dir(), p.lstat().st_size, p.lstat().st_mtime_ns)
            for p in top.rglob("*")}


def framework_files():
    files = [rel for rel in FRAMEWORK_FILES + (AGENT_MODELS,) if (fork() / rel).is_file()]
    for top in FRAMEWORK_DIRS:
        for path in (fork() / top).rglob("*"):
            if path.is_file():
                files.append(path.relative_to(fork()).as_posix())
    return sorted(files)


def tree(top):
    top = Path(top)
    return {p.relative_to(top).as_posix(): p.read_bytes()
            for p in top.rglob("*") if p.is_file()}


def write_files(top, files):
    for rel, text in files.items():
        path = Path(top, rel)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(text if isinstance(text, bytes) else text.encode("utf-8"))


def make_read_only(test, path):
    os.chmod(path, stat.S_IREAD)

    def restore():
        if os.path.exists(path):
            os.chmod(path, stat.S_IREAD | stat.S_IWRITE)
    test.addCleanup(restore)


def make_dir_link(test, link, target):
    """A symlink to a folder or, on Windows without the right to make one, a junction."""
    link.parent.mkdir(parents=True, exist_ok=True)
    try:
        os.symlink(target, link, target_is_directory=True)
    except OSError:
        if sys.platform != "win32":
            test.skipTest("cannot create a symlink")
        import _winapi
        _winapi.CreateJunction(str(target), str(link))

    def remove():
        if os.path.lexists(link):
            os.rmdir(link) if sys.platform == "win32" else os.unlink(link)
    test.addCleanup(remove)


def actions(stdout):
    """{path: (action, reason)} for every action line of a run."""
    found = {}
    for line in stdout.splitlines():
        match = ACTION.match(line.rstrip("\r"))
        if match:
            found[match.group(2)] = (match.group(1), match.group(3))
    return found


def action_lines(stdout):
    return [line.rstrip("\r") for line in stdout.splitlines() if ACTION.match(line.rstrip("\r"))]


def run_sh(*args):
    return subprocess.run([BASH, (fork() / "scripts" / "adopt.sh").as_posix(), *args],
                          capture_output=True, text=True, encoding="utf-8", env=SCRIPT_ENV,
                          timeout=SCRIPT_TIMEOUT_S, cwd=_SNAPSHOT["cwd"])


def run_ps1(*args):
    return subprocess.run([PWSH, "-NoProfile", "-NonInteractive", "-File",
                           str(fork() / "scripts" / "adopt.ps1"), *args],
                          capture_output=True, text=True, encoding="utf-8", env=SCRIPT_ENV,
                          timeout=SCRIPT_TIMEOUT_S, cwd=_SNAPSHOT["cwd"])


class AdoptBehaviour:
    """The behaviour both scripts share; a subclass names the runner."""

    runner = None
    dry_flag = "--dry-run"

    @classmethod
    def setUpClass(cls):
        cls.files = framework_files()

    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.tmp = Path(tmp.name)

    def target(self, files=None, name="game"):
        path = self.tmp / name
        path.mkdir(parents=True)
        write_files(path, files or {})
        return path

    def run_script(self, *args):
        result = type(self).runner(*args)
        self.assertEqual(list(_SNAPSHOT["cwd"].iterdir()), [], "the working directory stays empty")
        return result

    def adopt(self, target, *extra):
        result = self.run_script(Path(target).as_posix(), *extra)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        return result.stdout

    def assert_refused(self, target, *extra):
        result = self.run_script(Path(target).as_posix(), *extra)
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        self.assertFalse(action_lines(result.stdout), result.stdout)
        self.assertIn("Refused", result.stderr)
        return result.stderr

    def assert_framework_copied(self, target):
        for rel in self.files:
            self.assertEqual(Path(target, rel).read_bytes(), (fork() / rel).read_bytes(), rel)

    # --- an empty project -------------------------------------------------

    def test_empty_target_gets_the_framework_settings_and_claude_md(self):
        target = self.target()
        out = self.adopt(target)
        self.assert_framework_copied(target)
        self.assertEqual((target / SETTINGS).read_bytes(), (fork() / SETTINGS).read_bytes())
        self.assertEqual((target / "CLAUDE.md").read_bytes(), (fork() / "CLAUDE.md").read_bytes())
        self.assertFalse((target / SETTINGS_SIDECAR).exists())
        self.assertFalse((target / AGENT_MODELS_SIDECAR).exists())
        self.assertFalse((target / "project.yaml").exists())
        found = actions(out)
        self.assertEqual(found[SETTINGS][0], "ADD")
        self.assertEqual(found["CLAUDE.md"][0], "ADD")
        self.assertEqual(found["project.yaml"][0], "SKIP")
        self.assertIn("/start", found["project.yaml"][1])
        for rel in self.files:
            self.assertEqual(found[rel][0], "ADD", rel)

    def test_the_licence_notice_goes_with_the_copy(self):
        target = self.target()
        out = self.adopt(target)
        self.assertEqual((target / LICENSE_COPY).read_bytes(), (fork() / "LICENSE").read_bytes())
        self.assertEqual(actions(out)[LICENSE_COPY][0], "ADD")
        self.assertFalse((target / "LICENSE").exists(), "the project's own licence is not touched")

    def test_it_writes_nothing_else_and_nothing_outside_the_target(self):
        target = self.target()
        self.adopt(target)
        expected = set(self.files) | {SETTINGS, "CLAUDE.md", LICENSE_COPY, ".gitignore", ".gitattributes"}
        self.assertEqual(set(tree(target)), expected)
        self.assertEqual([p.name for p in self.tmp.iterdir()], ["game"])
        self.assertEqual(fingerprint(fork()), _SNAPSHOT["fingerprint"], "the framework copy is unchanged")

    def test_studio_tests_and_the_framework_docs_are_not_copied(self):
        target = self.target()
        self.adopt(target)
        for rel in ("studio-tests", "README.md", "CHANGELOG.md", "UPGRADING.md", "ADOPTING.md",
                    "production", "docs", "design", "src", "scripts", ".claude/settings.local.json"):
            self.assertFalse((target / rel).exists(), rel)

    def test_gitignore_and_gitattributes_are_created(self):
        target = self.target()
        self.adopt(target)
        ignore = (target / ".gitignore").read_text(encoding="utf-8").splitlines()
        attributes = (target / ".gitattributes").read_text(encoding="utf-8").splitlines()
        for line in GITIGNORE_LINES:
            self.assertEqual(ignore.count(line), 1, line)
        for line in GITATTRIBUTES_LINES:
            self.assertEqual(attributes.count(line), 1, line)

    @unittest.skipUnless(GIT, "git not found")
    def test_the_lf_rule_covers_the_hooks_and_the_statusline(self):
        target = self.target()
        self.adopt(target)
        subprocess.run([GIT, "init", "-q", str(target)], check=True, timeout=60)
        result = subprocess.run(
            [GIT, "-C", str(target), "check-attr", "eol", "--", ".claude/statusline.sh",
             ".claude/hooks/session-start.sh", ".claude/scripts/yaml-get.awk",
             ".claude/engines/engines.tsv"],
            capture_output=True, text=True, check=True, timeout=60)
        lines = result.stdout.splitlines()
        self.assertEqual(len(lines), 4, result.stdout)
        for line in lines:
            self.assertTrue(line.endswith("eol: lf"), line)

    @unittest.skipUnless(GIT, "git not found")
    def test_the_runtime_files_are_ignored(self):
        target = self.target()
        self.adopt(target)
        subprocess.run([GIT, "init", "-q", str(target)], check=True, timeout=60)
        paths = ["production/session-state/active.md", "production/session-logs/x.log",
                 "project.local.yaml", ".claude/worktrees/agent-1/README.md"]
        result = subprocess.run([GIT, "-C", str(target), "check-ignore", "--no-index", "--", *paths],
                                capture_output=True, text=True, timeout=60)
        self.assertEqual(sorted(result.stdout.split()), sorted(paths), result.stdout + result.stderr)

    # --- a project with files of its own --------------------------------

    def test_own_settings_json_is_kept_and_the_framework_copy_written_beside_it(self):
        own = '{\n  "permissions": {"allow": ["Bash(make *)"]}\n}\n'
        target = self.target({SETTINGS: own})
        out = self.adopt(target)
        self.assertEqual((target / SETTINGS).read_text(encoding="utf-8"), own)
        self.assertEqual((target / SETTINGS_SIDECAR).read_bytes(), (fork() / SETTINGS).read_bytes())
        found = actions(out)
        self.assertEqual(found[SETTINGS][0], "SKIP")
        self.assertIn(SETTINGS_SIDECAR, found[SETTINGS][1])
        self.assertEqual(found[SETTINGS_SIDECAR][0], "ADD")

    def test_own_agent_models_overrides_are_kept(self):
        own = "overrides:\n  producer: session\n"
        target = self.target({AGENT_MODELS: own})
        out = self.adopt(target)
        self.assertEqual((target / AGENT_MODELS).read_text(encoding="utf-8"), own)
        self.assertEqual((target / AGENT_MODELS_SIDECAR).read_bytes(), (fork() / AGENT_MODELS).read_bytes())
        found = actions(out)
        self.assertEqual(found[AGENT_MODELS][0], "SKIP")
        self.assertIn(AGENT_MODELS_SIDECAR, found[AGENT_MODELS][1])
        self.assertIn("agent-models.sh sync", found[AGENT_MODELS][1])
        self.assertEqual(found[AGENT_MODELS_SIDECAR][0], "ADD")

    def test_own_claude_md_is_kept(self):
        target = self.target({"CLAUDE.md": "# My game\n"})
        out = self.adopt(target)
        self.assertEqual((target / "CLAUDE.md").read_text(encoding="utf-8"), "# My game\n")
        self.assertEqual(actions(out)["CLAUDE.md"][0], "SKIP")

    def test_agents_md_alone_gets_no_claude_md(self):
        # A CLAUDE.md beside AGENTS.md would stop Claude Code reading AGENTS.md.
        for own in ("AGENTS.md", ".claude/CLAUDE.md"):
            with self.subTest(own=own):
                target = self.target({own: "# Rules\n"}, name=own.replace("/", "_"))
                out = self.adopt(target)
                self.assertFalse((target / "CLAUDE.md").exists())
                self.assertEqual((target / own).read_text(encoding="utf-8"), "# Rules\n")
                found = actions(out)["CLAUDE.md"]
                self.assertEqual(found[0], "SKIP")
                self.assertIn(own, found[1])

    def test_own_project_yaml_is_never_touched(self):
        target = self.target({"project.yaml": "engine:\n  name: Custom\n"})
        out = self.adopt(target)
        self.assertEqual((target / "project.yaml").read_text(encoding="utf-8"),
                         "engine:\n  name: Custom\n")
        self.assertEqual(actions(out)["project.yaml"][0], "SKIP")

    def test_own_files_inside_framework_folders_survive(self):
        mine = ".claude/skills/my-own-skill/SKILL.md"
        stale = ".claude/agents/producer.md"
        target = self.target({mine: "---\nname: my-own-skill\n---\n", stale: "old text\n",
                              ".claude/settings.local.json": "{}\n"})
        out = self.adopt(target)
        self.assertEqual((target / mine).read_text(encoding="utf-8"), "---\nname: my-own-skill\n---\n")
        self.assertEqual((target / ".claude/settings.local.json").read_text(encoding="utf-8"), "{}\n")
        self.assertEqual((target / stale).read_bytes(), (fork() / stale).read_bytes())
        found = actions(out)
        self.assertEqual(found[stale][0], "OVERWRITE")
        self.assertNotIn(mine, found)

    def test_technical_preferences_is_kept_once_the_project_has_it(self):
        target = self.target({PROJECT_OWNED: "# Mine\n"})
        out = self.adopt(target)
        self.assertEqual((target / PROJECT_OWNED).read_text(encoding="utf-8"), "# Mine\n")
        self.assertEqual(actions(out)[PROJECT_OWNED][0], "SKIP")

    def test_gitignore_lines_are_appended_once_and_existing_text_kept(self):
        target = self.target({".gitignore": "node_modules/\nproject.local.yaml",
                              ".gitattributes": "*.png binary\r\n"})
        out = self.adopt(target)
        ignore = (target / ".gitignore").read_text(encoding="utf-8")
        self.assertTrue(ignore.startswith("node_modules/\nproject.local.yaml\n"), ignore)
        for line in GITIGNORE_LINES:
            self.assertEqual(ignore.splitlines().count(line), 1, line)
        attributes = (target / ".gitattributes").read_bytes()
        self.assertTrue(attributes.startswith(b"*.png binary\r\n"), attributes)
        self.assertNotIn(b"\n", attributes.replace(b"\r\n", b""), "line endings kept CRLF")
        found = actions(out)
        self.assertEqual(found[".gitignore"][0], "APPEND")
        self.assertEqual(found[".gitattributes"][0], "APPEND")

    # --- files the run cannot or must not write -----------------------------

    def test_read_only_files_it_would_change_refuse_the_run_before_any_write(self):
        # A Perforce workspace keeps files read-only until they are checked out.
        skill = ".claude/skills/start/SKILL.md"
        target = self.target({skill: "old\n", ".claude/statusline.sh": "old\n"})
        for rel in (skill, ".claude/statusline.sh"):
            make_read_only(self, target / rel)
        before = tree(target)
        for extra in ((self.dry_flag,), ()):
            with self.subTest(extra=extra):
                err = self.assert_refused(target, *extra)
                self.assertEqual(tree(target), before)
                self.assertIn(skill, err)
                self.assertIn(".claude/statusline.sh", err)

    def test_read_only_files_it_would_not_change_are_fine(self):
        target = self.target()
        self.adopt(target)
        for rel in (".claude/skills/start/SKILL.md", SETTINGS, ".gitignore"):
            make_read_only(self, target / rel)
        out = self.adopt(target)
        self.assertLessEqual({kind for kind, _ in actions(out).values()}, {"UNCHANGED", "SKIP"}, out)

    def test_a_folder_where_a_file_goes_or_a_file_where_a_folder_goes_is_refused(self):
        cases = (("folder at a file path", lambda t: (t / ".claude/statusline.sh").mkdir(parents=True)),
                 ("folder at gitignore", lambda t: (t / ".gitignore").mkdir()),
                 ("file at a folder path", lambda t: write_files(t, {".claude/agents": "x"})))
        for label, make in cases:
            with self.subTest(label):
                target = self.target(name=label)
                make(target)
                before = fingerprint(target)
                self.assert_refused(target)
                self.assertEqual(fingerprint(target), before)

    def test_a_link_the_run_would_write_through_is_refused(self):
        for link in (".claude", ".claude/skills"):
            with self.subTest(link=link):
                name = link.replace("/", "_")
                outside = self.tmp / ("outside" + name)
                outside.mkdir()
                target = self.target(name="game" + name)
                make_dir_link(self, target / link, outside)
                err = self.assert_refused(target)
                self.assertIn(link, err)
                self.assertEqual(list(outside.iterdir()), [], "nothing written through the link")

    def test_a_link_the_run_does_not_write_through_is_left_alone(self):
        outside = self.tmp / "shared commands"
        outside.mkdir()
        target = self.target()
        make_dir_link(self, target / ".claude/commands", outside)
        self.adopt(target)
        self.assertEqual(list(outside.iterdir()), [])
        self.assert_framework_copied(target)

    # --- running it again, dry runs, refusals ------------------------------

    def test_a_second_run_changes_nothing(self):
        target = self.target({SETTINGS: "{}\n", "AGENTS.md": "# Rules\n", AGENT_MODELS: "overrides:\n"})
        self.adopt(target)
        before = tree(target)
        out = self.adopt(target)
        self.assertEqual(tree(target), before)
        kinds = {kind for kind, _ in actions(out).values()}
        self.assertLessEqual(kinds, {"UNCHANGED", "SKIP"}, out)

    def test_dry_run_writes_nothing_and_prints_the_real_runs_lines(self):
        own = {SETTINGS: "{}\n", "CLAUDE.md": "# Mine\n", ".gitignore": "build/\n",
               ".claude/agents/producer.md": "old\n", AGENT_MODELS: "overrides:\n"}
        dry = self.target(own, name="dry")
        real = self.target(own, name="real")
        before = tree(dry)
        dry_out = self.adopt(dry, self.dry_flag)
        self.assertEqual(tree(dry), before)
        self.assertEqual(action_lines(dry_out), action_lines(self.adopt(real)))
        self.assertTrue(action_lines(dry_out))

    def test_dry_run_on_an_empty_target_leaves_it_empty(self):
        target = self.target()
        self.adopt(target, self.dry_flag)
        self.assertEqual(list(target.iterdir()), [])

    def test_a_path_with_spaces_works(self):
        target = self.target(name="my games/first game")
        self.adopt(target)
        self.assert_framework_copied(target)
        self.assertTrue((target / ".gitignore").is_file())

    def test_refuses_a_bad_target(self):
        a_file = self.tmp / "a-file.txt"
        a_file.write_text("x", encoding="utf-8")
        for label, path in (("missing", self.tmp / "nope"), ("a file", a_file),
                            ("the framework itself", fork()),
                            ("inside the framework", fork() / "docs")):
            with self.subTest(label):
                result = self.run_script(path.as_posix(), self.dry_flag)
                self.assertNotEqual(result.returncode, 0, result.stdout)
                self.assertFalse(action_lines(result.stdout), result.stdout)
                self.assertTrue(result.stderr.strip(), "names the reason")

    def test_refuses_a_link_to_the_framework(self):
        for label, target in (("the framework", fork()), ("a folder inside it", fork() / "docs")):
            with self.subTest(label):
                link = self.tmp / ("link to " + label)
                make_dir_link(self, link, target)
                for extra in ((self.dry_flag,), ()):
                    result = self.run_script(link.as_posix(), *extra)
                    self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
                    self.assertFalse(action_lines(result.stdout), result.stdout)
                    self.assertIn("framework repository", result.stderr)
                self.assertEqual(fingerprint(fork()), _SNAPSHOT["fingerprint"])

    def test_refuses_no_target_and_an_unknown_option(self):
        target = self.target()
        for args in ((), (target.as_posix(), "--force")):
            with self.subTest(args=args):
                result = self.run_script(*args)
                self.assertNotEqual(result.returncode, 0)
                self.assertIn("Usage", result.stdout + result.stderr)
        self.assertEqual(list(target.iterdir()), [])


@unittest.skipUnless(BASH, "bash not found")
class AdoptShTest(AdoptBehaviour, unittest.TestCase):
    runner = staticmethod(run_sh)


@unittest.skipUnless(PWSH, "pwsh not found")
class AdoptPs1Test(AdoptBehaviour, unittest.TestCase):
    runner = staticmethod(run_ps1)

    def test_accepts_the_named_parameters(self):
        target = self.target(name="named target")
        result = self.run_script("-Target", target.as_posix(), "-DryRun")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertTrue(action_lines(result.stdout))
        self.assertEqual(list(target.iterdir()), [])


@unittest.skipUnless(BASH and PWSH, "needs bash and pwsh")
class AdoptScriptsAgreeTest(unittest.TestCase):
    """Both scripts leave the same files and give the same exit codes and action lines."""

    # name: (files, read-only paths, exit code of each run)
    FIXTURES = {
        "empty": ({}, (), 0),
        "own files": ({SETTINGS: "{}\n", "AGENTS.md": "# Rules\n", ".gitignore": "out/",
                       ".claude/skills/mine/SKILL.md": "x\n", ".claude/agents/producer.md": "old\n",
                       PROJECT_OWNED: "# Mine\n", "project.yaml": "engine:\n  name: Godot\n",
                       AGENT_MODELS: "overrides:\n  producer: session\n"}, (), 0),
        "read-only": ({".claude/agents/producer.md": "old\n", ".claude/statusline.sh": "old\n"},
                      (".claude/agents/producer.md", ".claude/statusline.sh"), 1),
    }

    def test_same_tree_and_same_lines(self):
        for name, (files, read_only, code) in self.FIXTURES.items():
            with self.subTest(name), tempfile.TemporaryDirectory() as tmp:
                outputs, trees = [], []
                for side, runner in (("sh", run_sh), ("ps1", run_ps1)):
                    target = Path(tmp, side, "a game")
                    target.mkdir(parents=True)
                    write_files(target, files)
                    for rel in read_only:
                        make_read_only(self, target / rel)
                    runs = [runner(target.as_posix(), "--dry-run"), runner(target.as_posix()),
                            runner(target.as_posix())]
                    for result in runs:
                        self.assertEqual(result.returncode, code, side + ": " + result.stdout + result.stderr)
                    outputs.append([action_lines(r.stdout) for r in runs])
                    trees.append(tree(target))
                    self.assertEqual(list(_SNAPSHOT["cwd"].iterdir()), [])
                self.assertEqual(outputs[0], outputs[1])
                self.assertEqual(trees[0], trees[1])


if __name__ == "__main__":
    unittest.main()
