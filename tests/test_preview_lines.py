#!/usr/bin/env python3
"""Tests for `ax preview --lines N` (issue #39)."""
import contextlib
import io
import json
import os
import shutil
import sys
import tempfile
import unittest

from test_ax import FIXTURES, load_ax
import ax_test_support  # noqa: F401  (scrubs HERMES_HOME for the test run)

FIRST_TURN = "Refactor the login form"
LAST_TURN = "Done. Validation errors now render inline."


class TestPreviewLines(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls._orig_home = os.environ.get("HOME")
        cls.tmp = tempfile.mkdtemp(prefix="ax_test_lines_")
        cls._orig_cwd = os.getcwd()
        os.chdir(cls.tmp)
        mapping = [
            ("claude", ".claude"),
            ("codex", ".codex"),
            ("gemini", ".gemini"),
            ("local", ".local"),
            ("aider", "aiderws"),
            ("omp", ".omp"),
            ("vibe", ".vibe"),
            ("hermes", ".hermes"),
        ]
        for src, dst in mapping:
            s = os.path.join(FIXTURES, src)
            d = os.path.join(cls.tmp, dst)
            if os.path.isdir(s):
                shutil.copytree(s, d)
        cls.mod = load_ax(cls.tmp)

    @classmethod
    def tearDownClass(cls):
        os.chdir(cls._orig_cwd)
        if cls._orig_home is None:
            os.environ.pop("HOME", None)
        else:
            os.environ["HOME"] = cls._orig_home
        shutil.rmtree(cls.tmp)

    def _run_preview(self, args):
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            rc = self.mod.cmd_preview(args)
        return rc, out.getvalue(), err.getvalue()

    def test_lines_one_shows_only_last_turn(self):
        rc, out, _ = self._run_preview(["claude", "sess-c1a2b3", "--lines", "1"])
        self.assertEqual(rc, None)
        self.assertIn(LAST_TURN, out)
        self.assertNotIn(FIRST_TURN, out)

    def test_lines_default_shows_all_turns(self):
        rc, out, _ = self._run_preview(["claude", "sess-c1a2b3"])
        self.assertEqual(rc, None)
        self.assertIn(FIRST_TURN, out)
        self.assertIn(LAST_TURN, out)

    def test_lines_json_reflects_override(self):
        rc, out, _ = self._run_preview(
            ["claude", "sess-c1a2b3", "--lines", "1", "--json"])
        self.assertEqual(rc, None)
        obj = json.loads(out)
        self.assertIn(LAST_TURN, obj["preview"])
        self.assertNotIn(FIRST_TURN, obj["preview"])

    def test_lines_zero_is_usage_error(self):
        rc, _, err = self._run_preview(["claude", "sess-c1a2b3", "--lines", "0"])
        self.assertEqual(rc, 1)
        self.assertIn("usage", err.lower())

    def test_lines_negative_is_usage_error(self):
        rc, _, err = self._run_preview(["claude", "sess-c1a2b3", "--lines", "-2"])
        self.assertEqual(rc, 1)
        self.assertIn("usage", err.lower())

    def test_lines_non_numeric_is_usage_error(self):
        rc, _, err = self._run_preview(["claude", "sess-c1a2b3", "--lines", "abc"])
        self.assertEqual(rc, 1)
        self.assertIn("usage", err.lower())

    def test_lines_missing_value_is_usage_error(self):
        rc, _, err = self._run_preview(["claude", "sess-c1a2b3", "--lines"])
        self.assertEqual(rc, 1)
        self.assertIn("usage", err.lower())

    def test_cli_overrides_config(self):
        self.mod.CONFIG["limits"]["preview_lines"] = 1
        try:
            _, full, _ = self._run_preview(["claude", "sess-c1a2b3"])
            self.assertNotIn(FIRST_TURN, full)
            _, out, _ = self._run_preview(
                ["claude", "sess-c1a2b3", "--lines", "10"])
            self.assertIn(FIRST_TURN, out)
        finally:
            self.mod.CONFIG["limits"]["preview_lines"] = None


if __name__ == "__main__":
    unittest.main()
