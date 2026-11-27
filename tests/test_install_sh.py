#!/usr/bin/env python3
"""Tests for install.sh / install.ps1 (curl|sh and irm|iex installers)."""
import os
import shutil
import stat
import subprocess
import tempfile
import unittest

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
INSTALL_SH = os.path.join(REPO_ROOT, "install.sh")
INSTALL_PS1 = os.path.join(REPO_ROOT, "install.ps1")


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
            env["AXS_BIN_DIR"] = tmp
            env["AXS_SRC"] = "file://" + os.path.join(REPO_ROOT, "axs")
            r = subprocess.run(["sh", INSTALL_SH],
                               capture_output=True, text=True, env=env)
            self.assertEqual(r.returncode, 0,
                             f"install.sh failed: {r.stderr}")
            target = os.path.join(tmp, "axs")
            self.assertTrue(os.path.isfile(target), "axs not installed")
            mode = os.stat(target).st_mode
            self.assertTrue(mode & stat.S_IXUSR, "axs is not executable")
            # installed file should run (prints agents status to stdout/stderr)
            r2 = subprocess.run([target, "agents"],
                                capture_output=True, text=True)
            self.assertEqual(r2.returncode, 0,
                             f"installed axs failed: {r2.stderr}")
            self.assertIn("claude", r2.stdout + r2.stderr)
        finally:
            shutil.rmtree(tmp)

    def test_install_ps1_exists_and_creates_cmd_shim(self):
        # Windows cannot run an extension-less Python script directly (no
        # shebang support), so install.ps1 must also write an axs.cmd shim.
        self.assertTrue(os.path.isfile(INSTALL_PS1), "install.ps1 not found")
        with open(INSTALL_PS1, encoding="utf-8") as fh:
            text = fh.read()
        self.assertIn('Join-Path $binDir "axs.cmd"', text)
        self.assertIn('python `"%~dp0axs`" %*', text)
        self.assertIn("AXS_BIN_DIR", text)
        self.assertIn("AXS_SRC", text)


if __name__ == "__main__":
    unittest.main()
