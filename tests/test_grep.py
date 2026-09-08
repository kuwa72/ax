#!/usr/bin/env python3
"""Unit tests for ax --grep (cross-agent body search) using synthetic fixtures."""
import importlib.machinery as machinery
import importlib.util
import io
import json
import os
import shutil
import sys
import tempfile
import unittest

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
        for src, dst in [("claude", ".claude"), ("codex", ".codex"),
                         ("gemini", ".gemini"), ("local", ".local")]:
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
        ]
        for agent, q, expected in cases:
            rows = self.mod.grep_sessions(q, [agent], 50)
            ids = {r["id"] for r in rows}
            self.assertTrue(expected <= ids,
                            f"{agent}: {q!r} -> {ids}, want superset of {expected}")

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


if __name__ == "__main__":
    unittest.main()
