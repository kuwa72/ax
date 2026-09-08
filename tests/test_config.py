#!/usr/bin/env python3
"""Tests for ax configuration file support."""
import importlib.machinery as machinery
import importlib.util
import io
import os
import shutil
import sys
import tempfile
import unittest

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
AX_PATH = os.path.join(REPO_ROOT, "ax")
FIXTURES = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fixtures")


def load_ax(home, xdg=None):
    old_home = os.environ.get("HOME")
    old_xdg = os.environ.get("XDG_CONFIG_HOME")
    os.environ["HOME"] = home
    if xdg is not None:
        os.environ["XDG_CONFIG_HOME"] = xdg
    else:
        os.environ.pop("XDG_CONFIG_HOME", None)
    try:
        loader = machinery.SourceFileLoader("ax_test_mod_cfg", AX_PATH)
        spec = importlib.util.spec_from_loader(
            "ax_test_mod_cfg", loader, origin=AX_PATH
        )
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod
    finally:
        if old_home is None:
            os.environ.pop("HOME", None)
        else:
            os.environ["HOME"] = old_home
        if old_xdg is None:
            os.environ.pop("XDG_CONFIG_HOME", None)
        else:
            os.environ["XDG_CONFIG_HOME"] = old_xdg


def copy_fixtures(dst):
    mapping = [
        ("claude", ".claude"),
        ("codex", ".codex"),
        ("gemini", ".gemini"),
        ("local", ".local"),
    ]
    for src, dst_name in mapping:
        s = os.path.join(FIXTURES, src)
        d = os.path.join(dst, dst_name)
        if os.path.isdir(s):
            shutil.copytree(s, d)


class TestConfig(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls._orig_home = os.environ.get("HOME")
        cls._orig_xdg = os.environ.get("XDG_CONFIG_HOME")

    @classmethod
    def tearDownClass(cls):
        if cls._orig_home is None:
            os.environ.pop("HOME", None)
        else:
            os.environ["HOME"] = cls._orig_home
        if cls._orig_xdg is None:
            os.environ.pop("XDG_CONFIG_HOME", None)
        else:
            os.environ["XDG_CONFIG_HOME"] = cls._orig_xdg

    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="ax_cfg_test_")
        copy_fixtures(self.tmp)

    def tearDown(self):
        shutil.rmtree(self.tmp)

    def _capture_stdout(self, fn, *args, **kwargs):
        old = sys.stdout
        buf = io.StringIO()
        sys.stdout = buf
        try:
            result = fn(*args, **kwargs)
        finally:
            sys.stdout = old
        return result, buf.getvalue()

    def _write_config(self, text, xdg=None):
        if xdg:
            cfg_dir = os.path.join(xdg, "ax")
        else:
            cfg_dir = os.path.join(self.tmp, ".config", "ax")
        os.makedirs(cfg_dir, exist_ok=True)
        with open(os.path.join(cfg_dir, "config.toml"), "w", encoding="utf-8") as f:
            f.write(text)

    def _load_with_stderr(self, xdg=None):
        old_err = sys.stderr
        err = io.StringIO()
        sys.stderr = err
        try:
            mod = load_ax(self.tmp, xdg=xdg)
        finally:
            sys.stderr = old_err
        return mod, err.getvalue()

    def test_no_config_uses_defaults(self):
        mod = load_ax(self.tmp)
        self.assertEqual(
            mod.ALL_AGENTS, ("claude", "codex", "agy", "opencode", "devin")
        )
        self.assertEqual(mod.AGENTS, mod.ALL_AGENTS)
        self.assertEqual(mod.CONFIG["limits"]["max_sessions"], 300)
        self.assertEqual(mod.CONFIG["limits"]["preview_lines"], None)
        self.assertEqual(mod.CONFIG["providers"]["disabled"], [])

        _, out = self._capture_stdout(mod.cmd_list, [])
        lines = out.strip().splitlines()
        self.assertEqual(len(lines), 10)
        for line in lines:
            cols = line.split("\t")
            self.assertEqual(len(cols), 7, f"bad TSV line: {line!r}")

    def test_disabled_provider_excluded(self):
        self._write_config('[providers]\ndisabled = ["agy"]\n')
        mod = load_ax(self.tmp)
        self.assertNotIn("agy", mod.AGENTS)
        self.assertEqual(
            set(mod.AGENTS), {"claude", "codex", "opencode", "devin"}
        )

        _, out = self._capture_stdout(mod.cmd_list, [])
        lines = out.strip().splitlines()
        self.assertEqual(len(lines), 8)
        for line in lines:
            cols = line.split("\t")
            self.assertEqual(len(cols), 7)
            self.assertNotEqual(cols[0], "agy")

    def test_max_sessions_limits_total(self):
        self._write_config('[limits]\nmax_sessions = 5\n')
        mod = load_ax(self.tmp)
        self.assertEqual(mod.CONFIG["limits"]["max_sessions"], 5)

        _, out = self._capture_stdout(mod.cmd_list, [])
        lines = out.strip().splitlines()
        self.assertEqual(len(lines), 5)
        for line in lines:
            cols = line.split("\t")
            self.assertEqual(len(cols), 7)

    def test_per_provider_max_sessions(self):
        self._write_config(
            """
[limits.max_sessions]
claude = 1
codex = 1
agy = 1
opencode = 1
devin = 1
"""
        )
        mod = load_ax(self.tmp)
        _, out = self._capture_stdout(mod.cmd_list, [])
        lines = out.strip().splitlines()
        self.assertEqual(len(lines), 5)
        agents = [l.split("\t")[0] for l in lines]
        self.assertEqual(sorted(agents), sorted(mod.ALL_AGENTS))

    def test_preview_lines_global(self):
        self._write_config('[limits]\npreview_lines = 1\n')
        mod = load_ax(self.tmp)

        _, out = self._capture_stdout(mod.cmd_preview, ["claude", "sess-c1a2b3"])
        self.assertIn("--- claude sess-c1a2b3", out)
        self.assertNotIn("Refactor the login form", out)
        self.assertIn("[ai]", out)

        _, out2 = self._capture_stdout(mod.cmd_preview, ["devin", "dev-1"])
        self.assertNotIn("Build a landing page", out2)
        self.assertIn("[ai]", out2)

    def test_preview_lines_per_provider(self):
        self._write_config(
            """
[limits.preview_lines]
devin = 1
"""
        )
        mod = load_ax(self.tmp)

        _, out = self._capture_stdout(mod.cmd_preview, ["devin", "dev-1"])
        self.assertNotIn("Build a landing page", out)
        self.assertIn("[ai]", out)

        _, out2 = self._capture_stdout(mod.cmd_preview, ["claude", "sess-c1a2b3"])
        self.assertIn("Refactor the login form", out2)
        self.assertIn("[user]", out2)
        self.assertIn("[ai]", out2)

    def test_cli_limit_overrides_config(self):
        self._write_config('[limits]\nmax_sessions = 2\n')
        mod = load_ax(self.tmp)
        _, out = self._capture_stdout(mod.cmd_list, ["--limit", "10"])
        lines = out.strip().splitlines()
        self.assertEqual(len(lines), 10)

    def test_xdg_config_home(self):
        xdg = tempfile.mkdtemp(prefix="ax_xdg_")
        try:
            self._write_config('[providers]\ndisabled = ["agy"]\n', xdg=xdg)
            mod = load_ax(self.tmp, xdg=xdg)
            self.assertNotIn("agy", mod.AGENTS)
            _, out = self._capture_stdout(mod.cmd_list, [])
            for line in out.strip().splitlines():
                self.assertNotEqual(line.split("\t")[0], "agy")
        finally:
            shutil.rmtree(xdg)

    def test_invalid_config_warns_and_defaults(self):
        self._write_config(
            """
[limits]
max_sessions = "not a number"
preview_lines = -5

[providers]
disabled = "agy"
"""
        )
        mod, err = self._load_with_stderr()
        warnings = err.lower()
        self.assertIn("max_sessions", warnings)
        self.assertIn("preview_lines", warnings)
        self.assertIn("disabled", warnings)
        self.assertEqual(mod.CONFIG["limits"]["max_sessions"], 300)
        self.assertEqual(mod.CONFIG["limits"]["preview_lines"], None)
        self.assertEqual(mod.CONFIG["providers"]["disabled"], [])

        _, out = self._capture_stdout(mod.cmd_list, [])
        self.assertEqual(len(out.strip().splitlines()), 10)

    def test_unknown_disabled_provider_warns(self):
        self._write_config('[providers]\ndisabled = ["unknown", "agy"]\n')
        mod, err = self._load_with_stderr()
        self.assertIn("unknown", err)
        self.assertEqual(mod.CONFIG["providers"]["disabled"], ["agy"])
        self.assertNotIn("agy", mod.AGENTS)

    def test_agents_command_shows_disabled(self):
        self._write_config('[providers]\ndisabled = ["agy"]\n')
        mod = load_ax(self.tmp)
        _, out = self._capture_stdout(mod.cmd_agents)
        by_prefix = {l.split(":", 1)[0]: l for l in out.strip().splitlines()}
        self.assertIn("agy", by_prefix)
        self.assertIn("disabled", by_prefix["agy"].lower())
        self.assertIn("ok", by_prefix["claude"])

    def test_fzf_extra_args_loaded(self):
        self._write_config(
            '[fzf]\nextra_args = ["--bind", "ctrl-a:toggle-preview"]\n'
        )
        mod = load_ax(self.tmp)
        self.assertEqual(
            mod.CONFIG["fzf"]["extra_args"],
            ["--bind", "ctrl-a:toggle-preview"],
        )

    def test_bad_toml_syntax_warns_and_defaults(self):
        self._write_config('max_sessions = [unclosed\n')
        mod, err = self._load_with_stderr()
        self.assertIn("config read failed", err)

        _, out = self._capture_stdout(mod.cmd_list, [])
        self.assertEqual(len(out.strip().splitlines()), 10)


if __name__ == "__main__":
    unittest.main()
