"""验证跨客户端安装的实际目录、重试及已有项目文件的保留。"""

import importlib.util
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch


REPO = Path(__file__).resolve().parents[1]
SCRIPT = REPO / "scripts" / "install_skill.py"
spec = importlib.util.spec_from_file_location("install_skill", SCRIPT)
installer = importlib.util.module_from_spec(spec)
spec.loader.exec_module(installer)


class InstallSkillTests(unittest.TestCase):
    def test_install_from_new_working_directory_and_repeat(self):
        with tempfile.TemporaryDirectory(prefix="xp target ") as folder:
            def run(*args):
                return subprocess.run([sys.executable, str(SCRIPT), *args], cwd=folder,
                                      capture_output=True, text=True, check=True).stdout

            output = run("--agent", "codex", "cursor", "--agent", "claude-code")
            self.assertEqual(output.count("Installed: "), 2)
            shared = Path(folder) / ".agents" / "skills" / "gaia-xp-fit"
            reference = shared / "references" / "spectroscopy.md"
            self.assertEqual(reference.read_bytes(),
                             (installer.SOURCE / "references" / "spectroscopy.md").read_bytes())
            first_time = reference.stat().st_mtime_ns
            output = run("--project", folder, "--agent", "all")
            self.assertEqual(output.count("Already installed: "), 2)
            self.assertEqual(output.count("Installed: "), 2)
            self.assertEqual(reference.stat().st_mtime_ns, first_time)
            for root in (".agents", ".claude", ".github", ".windsurf"):
                self.assertTrue(installer.identical(installer.SOURCE,
                                                    Path(folder) / root / "skills" / "gaia-xp-fit"))

    def test_conflict_preserves_private_skill_and_creates_no_other_copy(self):
        with tempfile.TemporaryDirectory() as folder:
            project = Path(folder)
            owned = project / ".claude" / "skills" / "gaia-xp-fit"
            owned.mkdir(parents=True)
            content = b"Original project-specific science workflow."
            (owned / "SKILL.md").write_bytes(content)
            with self.assertRaisesRegex(FileExistsError, "gaia-xp-fit"):
                installer.install(project, ["codex", "claude-code"])
            self.assertEqual((owned / "SKILL.md").read_bytes(), content)
            self.assertFalse((project / ".agents").exists())

    def test_copy_failure_leaves_no_partial_skill_and_retry_succeeds(self):
        with tempfile.TemporaryDirectory() as folder:
            project = Path(folder)
            target = project / ".github" / "skills" / "gaia-xp-fit"

            def fail_copy(source, staged):
                staged.mkdir()
                (staged / "SKILL.md").write_text("partial", encoding="utf-8")
                raise OSError("disk full")

            with patch.object(installer.shutil, "copytree", side_effect=fail_copy):
                with self.assertRaisesRegex(OSError, "disk full"):
                    installer.install(project, ["github-copilot"])
            self.assertEqual(list(target.parent.iterdir()), [])
            installer.install(project, ["github-copilot"])
            self.assertTrue(installer.identical(installer.SOURCE, target))

    def test_existing_file_at_directory_path_is_preserved(self):
        with tempfile.TemporaryDirectory() as folder:
            project = Path(folder)
            collision = project / ".agents"
            collision.write_bytes(b"keep")
            with self.assertRaises(NotADirectoryError):
                installer.install(project, ["github-copilot", "gemini-cli"])
            self.assertEqual(collision.read_bytes(), b"keep")
            self.assertFalse((project / ".github").exists())
