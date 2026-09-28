#!/usr/bin/env python3
"""Unit tests for ax --grep (cross-agent body search) using synthetic fixtures."""
import contextlib
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

import ax_test_support  # noqa: F401  (scrubs HERMES_HOME for the test run)

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
AX_PATH = os.path.join(REPO_ROOT, "ax")
FIXTURES = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fixtures")


def load_ax(home):
    old = os.environ.get("HOME")
    os.environ["HOME"] = home
    try:
        loader = machinery.SourceFileLoader("ax_grep_test_mod", AX_PATH)
        spec = importlib.util.spec_from_loader("ax_grep_test_mod", loader, origin=AX_PATH)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod
    finally:
        if old is None:
            os.environ.pop("HOME", None)
        else:
            os.environ["HOME"] = old


class TestGrep(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls._orig_home = os.environ.get("HOME")
        cls.tmp = tempfile.mkdtemp(prefix="ax_grep_test_home_")
        cls._orig_cwd = os.getcwd()
        os.chdir(cls.tmp)
        for src, dst in [("claude", ".claude"), ("codex", ".codex"),
                         ("gemini", ".gemini"), ("local", ".local"),
                         ("aider", "aiderws"), ("omp", ".omp"),
                         ("vibe", ".vibe"), ("hermes", ".hermes")]:
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
        os.chdir(cls._orig_cwd)
        shutil.rmtree(cls.tmp)

    def _capture_stdout(self, fn, *args, **kwargs):
        old = sys.stdout
        buf = io.StringIO()
        sys.stdout = buf
        try:
            result = fn(*args, **kwargs)
        finally:
            sys.stdout = old
        return result, buf.getvalue()

    def test_grep_hits_each_agent_body(self):
        cases = [
            ("claude", "framework", {"sess-c1a2b3"}),
            ("codex", "adding an index", {"codex-2"}),
            ("agy", "start with plan", {"agy-1"}),
            ("opencode", "explanation", {"oc-1"}),
            ("devin", "landing page", {"dev-1"}),
            ("aider", "lexer", set()),
            ("goose", "indexer", {"g-1"}),
            ("omp", "tokenizer", {"ompid1"}),
            ("vibe", "deploy", {"vb002"}),
            ("hermes", "gateway", {"h-1"}),
        ]
        aider_hit = {os.path.join(self.tmp, "aiderws", "proj-one",
                                  ".aider.chat.history.md")}
        for agent, q, expected in cases:
            if agent == "aider":
                expected = aider_hit
            rows = self.mod.grep_sessions(q, [agent], 50)
            ids = {r["id"] for r in rows}
            self.assertTrue(expected <= ids,
                            f"{agent}: {q!r} -> {ids}, want superset of {expected}")

    def test_grep_goose_legacy_jsonl(self):
        ids = {r["id"] for r in self.mod.grep_sessions("Legacy user", ["goose"], 50)}
        self.assertIn("20260101_1", ids)

    def test_grep_hermes_skips_inactive(self):
        self.assertEqual(
            self.mod.grep_sessions("old inactive message", ["hermes"], 50), [])
        ids = {r["id"] for r in
               self.mod.grep_sessions("Worker restarted", ["hermes"], 50)}
        self.assertIn("h-2", ids)

    def test_grep_cross_agent(self):
        rows = self.mod.grep_sessions("Refactor", list(self.mod.AGENTS), 50)
        agents = {r["agent"] for r in rows}
        self.assertIn("claude", agents)
        self.assertIn("devin", agents)
        ids = {r["id"] for r in rows}
        self.assertIn("sess-c1a2b3", ids)
        self.assertIn("dev-2", ids)

    def test_grep_no_hit(self):
        self.assertEqual(
            self.mod.grep_sessions("zzz-no-such-term-987", list(self.mod.AGENTS), 50), [])

    def test_grep_case_insensitive(self):
        ids = {r["id"] for r in self.mod.grep_sessions("LOGIN FORM", ["claude"], 50)}
        self.assertIn("sess-c1a2b3", ids)

    def test_grep_ignores_metadata(self):
        # "webapp" は claude fixture の cwd メタデータにのみ出現。本文検索なので非ヒット
        self.assertEqual(self.mod.grep_sessions("webapp", list(self.mod.AGENTS), 50), [])

    def test_grep_skips_devin_system_steps(self):
        self.assertEqual(
            self.mod.grep_sessions("should be ignored", ["devin"], 50), [])

    def test_grep_match_field_contains_snippet(self):
        rows = self.mod.grep_sessions("login", ["claude"], 50)
        self.assertTrue(rows)
        for r in rows:
            self.assertIn("match", r)
            self.assertNotIn("\t", r["match"])
            self.assertNotIn("\n", r["match"])
        self.assertTrue(any("login" in r["match"].lower() for r in rows))

    def test_cmd_list_grep_tsv_seven_columns(self):
        _, out = self._capture_stdout(self.mod.cmd_list, ["--grep", "Refactor"])
        lines = out.strip().splitlines()
        self.assertTrue(lines)
        for line in lines:
            self.assertEqual(len(line.split("\t")), 7, f"bad TSV line: {line!r}")
        self.assertIn("sess-c1a2b3", out)
        self.assertIn("dev-2", out)

    def test_cmd_list_grep_json(self):
        _, out = self._capture_stdout(
            self.mod.cmd_list, ["--json", "--grep", "migration"])
        rows = json.loads(out)
        self.assertTrue(rows)
        for r in rows:
            self.assertIn("match", r)
        self.assertIn("agy-1", {r["id"] for r in rows})

    def test_cmd_list_grep_agent_filter(self):
        _, out = self._capture_stdout(
            self.mod.cmd_list, ["--grep", "Refactor", "--agent", "devin"])
        for line in out.strip().splitlines():
            self.assertTrue(line.startswith("devin"), f"unexpected: {line!r}")

    def test_cmd_list_grep_no_hit_prints_nothing(self):
        _, out = self._capture_stdout(
            self.mod.cmd_list, ["--grep", "zzz-no-such-term-987"])
        self.assertEqual(out.strip(), "")

    def test_cmd_grep_agent_filter_and_limit(self):
        with mock.patch("shutil.which", return_value="/usr/bin/fzf"), \
                mock.patch.object(
                    self.mod, "grep_sessions", return_value=[]) as mgrep, \
                contextlib.redirect_stderr(io.StringIO()):
            rc = self.mod.cmd_grep(["Refactor", "--agent", "devin",
                                    "--limit", "5"])
        self.assertEqual(rc, 1)
        self.assertEqual(mgrep.call_args[0][0], "Refactor")
        self.assertEqual(mgrep.call_args[0][1], ["devin"])
        self.assertEqual(mgrep.call_args[0][2], 5)

    def test_cmd_grep_positional_only_is_query(self):
        with mock.patch("shutil.which", return_value="/usr/bin/fzf"), \
                mock.patch.object(
                    self.mod, "grep_sessions", return_value=[]) as mgrep, \
                contextlib.redirect_stderr(io.StringIO()):
            rc = self.mod.cmd_grep(["foo bar", "--agent", "codex"])
        self.assertEqual(rc, 1)
        self.assertEqual(mgrep.call_args[0][0], "foo bar")
        self.assertEqual(mgrep.call_args[0][1], ["codex"])

    def test_cmd_grep_unknown_agent_empty(self):
        with mock.patch("shutil.which", return_value="/usr/bin/fzf"), \
                mock.patch.object(
                    self.mod, "grep_sessions",
                    side_effect=AssertionError("must not be called")) as mgrep, \
                contextlib.redirect_stderr(io.StringIO()):
            rc = self.mod.cmd_grep(["Refactor", "--agent", "no-such-agent"])
        self.assertEqual(rc, 0)
        mgrep.assert_not_called()

    def test_cmd_grep_default_limit_400(self):
        with mock.patch("shutil.which", return_value="/usr/bin/fzf"), \
                mock.patch.object(
                    self.mod, "grep_sessions", return_value=[]) as mgrep, \
                contextlib.redirect_stderr(io.StringIO()):
            self.mod.cmd_grep(["Refactor"])
        self.assertEqual(mgrep.call_args[0][2], 400)

    def test_cmd_grep_multi_positional_joined(self):
        with mock.patch("shutil.which", return_value="/usr/bin/fzf"), \
                mock.patch.object(
                    self.mod, "grep_sessions", return_value=[]) as mgrep, \
                contextlib.redirect_stderr(io.StringIO()):
            self.mod.cmd_grep(["foo", "bar"])
        self.assertEqual(mgrep.call_args[0][0], "foo bar")

    def test_cmd_grep_usage_line(self):
        buf = io.StringIO()
        with mock.patch("shutil.which", return_value="/usr/bin/fzf"), \
                contextlib.redirect_stderr(buf):
            rc = self.mod.cmd_grep([])
        self.assertEqual(rc, 1)
        self.assertIn("usage: ax grep", buf.getvalue())

    def test_cmd_grep_fzf_binds_preserved(self):
        rows = [{"agent": "devin", "id": "dev-1", "epoch": 1, "cwd": "?",
                 "title": "t ▸ Refactor hit"}]
        seen = {}

        class _Proc:
            returncode = 0
            stdout = "devin\tdev-1\t1\tnow\t?\t?\tt ▸ Refactor hit\n"

        def _run(argv, **kwargs):
            seen["argv"] = argv
            return _Proc()

        resumed = {}
        with mock.patch("shutil.which", return_value="/usr/bin/fzf"), \
                mock.patch.object(
                    self.mod, "grep_sessions", return_value=rows), \
                mock.patch("subprocess.run", side_effect=_run), \
                mock.patch.object(
                    self.mod, "cmd_resume",
                    side_effect=lambda a: resumed.update(args=a) or 0):
            rc = self.mod.cmd_grep(["Refactor", "--agent", "devin"])
        self.assertEqual(rc, 0)
        self.assertEqual(resumed["args"], ["devin", "dev-1"])
        binds = [seen["argv"][i + 1]
                 for i, a in enumerate(seen["argv"][:-1]) if a == "--bind"]
        self.assertTrue(any(b.startswith("ctrl-g:become:") for b in binds))
        self.assertTrue(any(b.startswith("ctrl-a:become:") for b in binds))
        self.assertTrue(any(b.startswith("ctrl-d:become:") for b in binds))
        header = seen["argv"][seen["argv"].index("--header") + 1]
        for token in ("enter=resume", "ctrl-g=new search", "ctrl-a=all",
                      "ctrl-d=delete"):
            self.assertIn(token, header)


if __name__ == "__main__":
    unittest.main()
