"""features.agent_write_guard: the subagent write rule of write-guard.sh.

Run: python -m unittest discover -s studio-tests -p test_write_guard_agent.py -v

Each test builds a fixture project in the OS temp directory and runs
`write-guard.sh --root <fixture> agent` on a subagent's write outside
production/, docs/ and tests/. These test the script's observations, not a
Claude session.
"""

from pathlib import Path
import os
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
GUARD = ROOT / ".claude" / "scripts" / "write-guard.sh"
GIT_BASH = Path("C:/Program Files/Git/bin/bash.exe")
BASH = str(GIT_BASH) if GIT_BASH.exists() else shutil.which("bash")
SCRIPT_ENV = {k: v for k, v in os.environ.items() if k != "CLAUDE_PROJECT_DIR"}
SCRIPT_TIMEOUT_S = 60
OUTSIDE = "src/feature.cs"


@unittest.skipUnless(BASH, "bash not found")
class AgentWriteGuardSettingTest(unittest.TestCase):

    def run_agent_rule(self, files):
        with tempfile.TemporaryDirectory() as tmp:
            for rel, text in files.items():
                path = Path(tmp, rel)
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(text, encoding="utf-8", newline="\n")
            result = subprocess.run(
                [BASH, GUARD.as_posix(), "--root", Path(tmp).as_posix(), "agent", OUTSIDE,
                 "--agent", "implementer"],
                capture_output=True, text=True, env=SCRIPT_ENV, timeout=SCRIPT_TIMEOUT_S)
        self.assertEqual(result.returncode, 0, result.stderr)
        return result.stdout

    def test_reports_a_write_outside_the_exception_by_default(self):
        out = self.run_agent_rule({"project.yaml": "engine:\n  name: Custom\n"})
        self.assertIn(f"AGENT_WRITE\t{OUTSIDE}\timplementer\toutside", out)

    def test_reports_it_when_the_setting_is_on(self):
        out = self.run_agent_rule({"project.yaml": "features:\n  agent_write_guard: on\n"})
        self.assertIn("AGENT_WRITE", out)

    def test_off_in_project_yaml_turns_the_rule_off(self):
        for value in ("off", "false"):
            with self.subTest(value=value):
                out = self.run_agent_rule({"project.yaml": f"features:\n  agent_write_guard: {value}\n"})
                self.assertNotIn("AGENT_WRITE", out)

    def test_project_local_yaml_wins_over_project_yaml(self):
        out = self.run_agent_rule({
            "project.yaml": "features:\n  agent_write_guard: off\n",
            "project.local.yaml": "features:\n  agent_write_guard: on\n"})
        self.assertIn("AGENT_WRITE", out)

    def test_a_value_that_is_not_on_or_off_keeps_the_default(self):
        out = self.run_agent_rule({"project.yaml": "features:\n  agent_write_guard: maybe\n"})
        self.assertIn("AGENT_WRITE", out)


@unittest.skipUnless(BASH, "bash not found")
class AgentWriteHookTest(unittest.TestCase):
    """validate-write.sh end to end, in a fixture holding a copy of `.claude/`."""

    PAYLOAD = ('{"tool_name": "Write", "agent_type": "implementer", "tool_input": '
               '{"file_path": "' + OUTSIDE + '", "content": "class Feature {}\\n"}}')

    def run_hook(self, project_yaml):
        with tempfile.TemporaryDirectory() as tmp:
            shutil.copytree(ROOT / ".claude", Path(tmp, ".claude"))
            Path(tmp, "project.yaml").write_text(project_yaml, encoding="utf-8", newline="\n")
            result = subprocess.run(
                [BASH, ".claude/hooks/validate-write.sh"], input=self.PAYLOAD, cwd=tmp,
                capture_output=True, text=True, env=SCRIPT_ENV, timeout=SCRIPT_TIMEOUT_S)
        self.assertEqual(result.returncode, 0, result.stderr)
        return result.stdout + result.stderr

    def test_warns_and_names_the_setting_when_on(self):
        out = self.run_hook("engine:\n  name: Custom\n")
        self.assertIn(f"A subagent (implementer) writes {OUTSIDE}", out)
        self.assertIn("features.agent_write_guard: off", out)

    def test_stays_silent_when_off(self):
        out = self.run_hook("features:\n  agent_write_guard: off\n")
        self.assertNotIn("A subagent (implementer)", out)


if __name__ == "__main__":
    unittest.main()
