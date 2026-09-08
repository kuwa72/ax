#!/usr/bin/env python3
"""Unit tests for `ax rm` / `ax rename`.

All tests run against a synthetic fixture HOME (copied into a temp dir) and
mock subprocess / input / shutil.which, so the real session stores and the
real `devin` / `codex` binaries are never touched.
"""
import importlib.machinery as machinery
import importlib.util
import io
import json
import os
import shutil
import sys
import tempfile
import unittest
from unittest import mock

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
AX_PATH = os.path.join(REPO_ROOT, "ax")
FIXTURES = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fixtures")


def load_ax(home):
    old = os.environ.get("HOME")
    os.environ["HOME"] = home
    try:
        loader = machinery.SourceFileLoader("ax_rm_test_mod", AX_PATH)
        spec = importlib.util.spec_from_loader("ax_rm_test_mod", loader,
                                               origin=AX_PATH)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod
    finally:
        if old is None:
            os.environ.pop("HOME", None)
        else:
            os.environ["HOME"] = old


class TestRmRename(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls._orig_home = os.environ.get("HOME")
        cls.tmp = tempfile.mkdtemp(prefix="ax_rm_test_home_")
        mapping = [
            ("claude", ".claude"),
            ("codex", ".codex"),
            ("gemini", ".gemini"),
            ("local", ".local"),
        ]
        for src, dst in mapping:
            s = os.path.join(FIXTURES, src)
            d = os.path.join(cls.tmp, dst)
            if os.path.isdir(s):
                shutil.copytree(s, d)
        cls.mod = load_ax(cls.tmp)

    @classmethod
    def tearDownClass(cls):
        if cls._orig_home is None:
            os.environ.pop("HOME", None)
        else:
            os.environ["HOME"] = cls._orig_home
        shutil.rmtree(cls.tmp)

    def setUp(self):
        # isolate the ax-local title store between tests
        if os.path.exists(self.mod.TITLES_PATH):
            os.remove(self.mod.TITLES_PATH)

    # ---------- helpers ----------
    def _capture(self, fn, *args, **kwargs):
        old_out, old_err = sys.stdout, sys.stderr
        out, err = io.StringIO(), io.StringIO()
        sys.stdout, sys.stderr = out, err
        try:
            rc = fn(*args, **kwargs)
        finally:
            sys.stdout, sys.stderr = old_out, old_err
        return rc, out.getvalue(), err.getvalue()

    def _run_ok(self):
        m = mock.Mock()
        m.returncode = 0
        return m

    # ---------- ax rm ----------
    def test_rm_devin_invokes_devin_rm_force(self):
        with mock.patch("subprocess.run", return_value=self._run_ok()) as mrun, \
                mock.patch("shutil.which", return_value="/bin/true"):
            rc, _, _ = self._capture(
                self.mod.cmd_rm, ["devin", "dev-1", "--yes"])
        self.assertEqual(rc, 0)
        argv = mrun.call_args[0][0]
        self.assertEqual(argv, ["devin", "rm", "--force", "dev-1"])

    def test_rm_codex_defaults_to_archive(self):
        with mock.patch("subprocess.run", return_value=self._run_ok()) as mrun, \
                mock.patch("shutil.which", return_value="/bin/true"):
            rc, _, _ = self._capture(
                self.mod.cmd_rm, ["codex", "codex-1", "--yes"])
        self.assertEqual(rc, 0)
        argv = mrun.call_args[0][0]
        self.assertEqual(argv, ["codex", "archive", "codex-1"])

    def test_rm_codex_hard_deletes(self):
        with mock.patch("subprocess.run", return_value=self._run_ok()) as mrun, \
                mock.patch("shutil.which", return_value="/bin/true"):
            rc, _, _ = self._capture(
                self.mod.cmd_rm, ["codex", "codex-1", "--yes", "--hard"])
        self.assertEqual(rc, 0)
        argv = mrun.call_args[0][0]
        self.assertEqual(argv, ["codex", "delete", "--force", "codex-1"])

    def test_rm_without_yes_prompts_and_y_confirms(self):
        with mock.patch("subprocess.run", return_value=self._run_ok()) as mrun, \
                mock.patch("shutil.which", return_value="/bin/true"), \
                mock.patch("builtins.input", return_value="y"):
            rc, _, err = self._capture(self.mod.cmd_rm, ["devin", "dev-1"])
        self.assertEqual(rc, 0)
        self.assertTrue(mrun.called)

    def test_rm_without_yes_and_no_answer_aborts(self):
        with mock.patch("subprocess.run") as mrun, \
                mock.patch("shutil.which", return_value="/bin/true"), \
                mock.patch("builtins.input", return_value="n"):
            rc, _, _ = self._capture(self.mod.cmd_rm, ["devin", "dev-1"])
        self.assertNotEqual(rc, 0)
        self.assertFalse(mrun.called)

    def test_rm_without_yes_and_eof_aborts(self):
        # non-interactive stdin (e.g. </dev/null) must never delete
        with mock.patch("subprocess.run") as mrun, \
                mock.patch("shutil.which", return_value="/bin/true"), \
                mock.patch("builtins.input", side_effect=EOFError):
            rc, _, _ = self._capture(self.mod.cmd_rm, ["devin", "dev-1"])
        self.assertNotEqual(rc, 0)
        self.assertFalse(mrun.called)

    def test_rm_unsupported_provider_exits_nonzero(self):
        for agent, sid in (("claude", "sess-c1a2b3"),
                           ("agy", "agy-1"),
                           ("opencode", "oc-1")):
            with mock.patch("subprocess.run") as mrun, \
                    mock.patch("shutil.which", return_value="/bin/true"):
                rc, _, err = self._capture(
                    self.mod.cmd_rm, [agent, sid, "--yes"])
            self.assertNotEqual(rc, 0, agent)
            self.assertIn("not supported", err)
            self.assertFalse(mrun.called, agent)

    def test_rm_unknown_agent(self):
        with mock.patch("subprocess.run") as mrun:
            rc, _, _ = self._capture(self.mod.cmd_rm, ["nope", "x", "--yes"])
        self.assertNotEqual(rc, 0)
        self.assertFalse(mrun.called)

    def test_rm_session_not_found(self):
        with mock.patch("subprocess.run") as mrun, \
                mock.patch("shutil.which", return_value="/bin/true"):
            rc, _, _ = self._capture(
                self.mod.cmd_rm, ["devin", "no-such-id", "--yes"])
        self.assertNotEqual(rc, 0)
        self.assertFalse(mrun.called)

    def test_rm_missing_cli_binary(self):
        with mock.patch("subprocess.run") as mrun, \
                mock.patch("shutil.which", return_value=None):
            rc, _, err = self._capture(
                self.mod.cmd_rm, ["devin", "dev-1", "--yes"])
        self.assertNotEqual(rc, 0)
        self.assertFalse(mrun.called)

    def test_rm_propagates_cli_failure(self):
        m = mock.Mock()
        m.returncode = 3
        with mock.patch("subprocess.run", return_value=m), \
                mock.patch("shutil.which", return_value="/bin/true"):
            rc, _, _ = self._capture(
                self.mod.cmd_rm, ["devin", "dev-1", "--yes"])
        self.assertEqual(rc, 3)

    def test_rm_usage_error(self):
        rc, _, _ = self._capture(self.mod.cmd_rm, ["devin"])
        self.assertNotEqual(rc, 0)

    # ---------- ax rename ----------
    def test_rename_sets_display_title(self):
        rc, _, _ = self._capture(
            self.mod.cmd_rename,
            ["claude", "sess-c1a2b3", "--name", "Renamed session"])
        self.assertEqual(rc, 0)
        rows = self.mod.collect(["claude"], 400, no_cache=True)
        by_id = {r["id"]: r for r in rows}
        self.assertEqual(by_id["sess-c1a2b3"]["title"], "Renamed session")
        # other sessions keep their original titles
        self.assertEqual(by_id["sess-d4e5f6"]["title"],
                         "Write tests for the new endpoint")

    def test_rename_store_lives_under_fixture_home(self):
        self._capture(self.mod.cmd_rename,
                      ["codex", "codex-1", "--name", "X"])
        self.assertTrue(os.path.exists(self.mod.TITLES_PATH))
        self.assertTrue(self.mod.TITLES_PATH.startswith(self.tmp))
        with open(self.mod.TITLES_PATH, encoding="utf-8") as fh:
            data = json.load(fh)
        self.assertEqual(data.get("codex:codex-1"), "X")

    def test_rename_shows_in_list_tsv(self):
        self._capture(self.mod.cmd_rename,
                      ["devin", "dev-1", "--name", "My devin title"])
        rc, out, _ = self._capture(self.mod.cmd_list, ["--agent", "devin"])
        line = next(l for l in out.splitlines() if l.split("\t")[1] == "dev-1")
        self.assertEqual(len(line.split("\t")), 7)
        self.assertTrue(line.endswith("\tMy devin title"))

    def test_rename_sanitizes_name_for_tsv(self):
        rc, _, _ = self._capture(
            self.mod.cmd_rename,
            ["claude", "sess-c1a2b3", "--name", "bad\ttab\nnewline"])
        self.assertEqual(rc, 0)
        _, out, _ = self._capture(self.mod.cmd_list, ["--agent", "claude"])
        for line in out.strip().splitlines():
            self.assertEqual(len(line.split("\t")), 7, f"bad TSV line: {line!r}")

    def test_rename_empty_name_clears_alias(self):
        self._capture(self.mod.cmd_rename,
                      ["claude", "sess-c1a2b3", "--name", "tmp name"])
        rc, _, _ = self._capture(
            self.mod.cmd_rename, ["claude", "sess-c1a2b3", "--name", ""])
        self.assertEqual(rc, 0)
        rows = self.mod.collect(["claude"], 400, no_cache=True)
        by_id = {r["id"]: r for r in rows}
        self.assertEqual(by_id["sess-c1a2b3"]["title"],
                         "Refactor the login form")

    def test_rename_requires_name(self):
        rc, _, _ = self._capture(self.mod.cmd_rename, ["claude", "sess-c1a2b3"])
        self.assertNotEqual(rc, 0)
        self.assertFalse(os.path.exists(self.mod.TITLES_PATH))

    def test_rename_unknown_session(self):
        rc, _, _ = self._capture(
            self.mod.cmd_rename, ["claude", "no-such", "--name", "X"])
        self.assertNotEqual(rc, 0)
        self.assertFalse(os.path.exists(self.mod.TITLES_PATH))

    def test_rename_unknown_agent(self):
        rc, _, _ = self._capture(
            self.mod.cmd_rename, ["nope", "x", "--name", "X"])
        self.assertNotEqual(rc, 0)

    def test_rename_does_not_touch_provider_store(self):
        target = os.path.join(self.tmp, ".claude", "projects", "webapp",
                              "sess-c1a2b3.jsonl")
        with open(target, "rb") as fh:
            before = fh.read()
        self._capture(self.mod.cmd_rename,
                      ["claude", "sess-c1a2b3", "--name", "Overlay title"])
        with open(target, "rb") as fh:
            after = fh.read()
        self.assertEqual(before, after)


if __name__ == "__main__":
    unittest.main()
