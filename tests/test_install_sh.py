#!/usr/bin/env python3
"""Tests for install.sh (curl|sh installer, issue #26)."""
import os
import shutil
import stat
import subprocess
import tempfile
import unittest

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
INSTALL_SH = os.path.join(REPO_ROOT, "install.sh")


class TestInstallSh(unittest.TestCase):
    def test_install_sh_exists_and_syntax_ok(self):
        self.assertTrue(os.path.isfile(INSTALL_SH), "install.sh not found")
        r = subprocess.run(["sh", "-n", INSTALL_SH],
                           capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, f"sh -n failed: {r.stderr}")

    def test_install_sh_installs_executable(self):
        tmp = tempfile.mkdtemp(prefix="ax_install_")
        try:
            env = os.environ.copy()
            env["AX_BIN_DIR"] = tmp
            env["AX_SRC"] = "file://" + os.path.join(REPO_ROOT, "ax")
            r = subprocess.run(["sh", INSTALL_SH],
                               capture_output=True, text=True, env=env)
            self.assertEqual(r.returncode, 0,
                             f"install.sh failed: {r.stderr}")
            target = os.path.join(tmp, "ax")
            self.assertTrue(os.path.isfile(target), "ax not installed")
            mode = os.stat(target).st_mode
            self.assertTrue(mode & stat.S_IXUSR, "ax is not executable")
            # installed file should run (prints agents status to stdout/stderr)
            r2 = subprocess.run([target, "agents"],
                                capture_output=True, text=True)
            self.assertEqual(r2.returncode, 0,
                             f"installed ax failed: {r2.stderr}")
            self.assertIn("claude", r2.stdout + r2.stderr)
        finally:
            shutil.rmtree(tmp)


if __name__ == "__main__":
    unittest.main()
