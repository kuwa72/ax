#!/usr/bin/env python3
"""Unit tests for ax using synthetic fixtures."""
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
        loader = machinery.SourceFileLoader("ax_test_mod", AX_PATH)
        spec = importlib.util.spec_from_loader("ax_test_mod", loader, origin=AX_PATH)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod
    finally:
        if old is None:
            os.environ.pop("HOME", None)
        else:
            os.environ["HOME"] = old


class TestAx(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls._orig_home = os.environ.get("HOME")
        cls.tmp = tempfile.mkdtemp(prefix="ax_test_home_")
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

    def _capture_stdout(self, fn, *args, **kwargs):
        old = sys.stdout
        buf = io.StringIO()
        sys.stdout = buf
        try:
            result = fn(*args, **kwargs)
        finally:
            sys.stdout = old
        return result, buf.getvalue()

    def test_collect_returns_sessions_for_all_providers(self):
        rows = self.mod.collect(list(self.mod.AGENTS), 400)
        ids = {r["id"] for r in rows}
        expected = {
            "sess-c1a2b3",
            "sess-d4e5f6",
            "codex-1",
            "codex-2",
            "agy-1",
            "agy-2",
            "oc-1",
            "oc-2",
            "dev-1",
            "dev-2",
        }
        self.assertEqual(ids, expected)
        self.assertNotIn("dev-hidden", ids)

    def test_fmt_tsv_has_seven_columns(self):
        rows = self.mod.collect(list(self.mod.AGENTS), 400)
        tsv = self.mod.fmt_tsv(rows)
        self.assertTrue(tsv)
        for line in tsv.splitlines():
            cols = line.split("\t")
            self.assertEqual(len(cols), 7, f"bad TSV line: {line!r}")

    def test_list_claude(self):
        rows = self.mod.list_claude(400)
        by_id = {r["id"]: r for r in rows}
        self.assertEqual(set(by_id), {"sess-c1a2b3", "sess-d4e5f6"})
        self.assertEqual(by_id["sess-c1a2b3"]["title"], "Refactor the login form")
        self.assertEqual(by_id["sess-d4e5f6"]["title"], "Write tests for the new endpoint")

    def test_list_codex(self):
        rows = self.mod.list_codex(400)
        by_id = {r["id"]: r for r in rows}
        self.assertEqual(set(by_id), {"codex-1", "codex-2"})
        self.assertEqual(by_id["codex-1"]["title"], "Review this function")
        self.assertEqual(by_id["codex-2"]["title"], "Optimize the query")

    def test_list_agy(self):
        rows = self.mod.list_agy()
        by_id = {r["id"]: r for r in rows}
        self.assertEqual(set(by_id), {"agy-1", "agy-2"})
        self.assertEqual(by_id["agy-1"]["title"], "Plan the migration")
        self.assertEqual(by_id["agy-1"]["cwd"], "/home/alice/ws")
        self.assertEqual(by_id["agy-2"]["title"], "Optimize database")
        self.assertEqual(by_id["agy-2"]["cwd"], "/home/alice/ws2")

    def test_list_opencode(self):
        rows = self.mod.list_opencode(400)
        by_id = {r["id"]: r for r in rows}
        self.assertEqual(set(by_id), {"oc-1", "oc-2"})
        self.assertEqual(by_id["oc-1"]["title"], "open test one")
        self.assertEqual(by_id["oc-2"]["title"], "open test two")

    def test_list_devin(self):
        rows = self.mod.list_devin(400)
        by_id = {r["id"]: r for r in rows}
        self.assertEqual(set(by_id), {"dev-1", "dev-2"})
        self.assertEqual(by_id["dev-1"]["title"], "devin test one")
        self.assertEqual(by_id["dev-2"]["title"], "devin test two")

    def test_preview_claude(self):
        text = self.mod.preview_claude("sess-c1a2b3", 10)
        self.assertIn("--- claude sess-c1a2b3", text)
        self.assertIn("[user] Refactor the login form", text)
        self.assertIn("[ai] I'll help you refactor the login form.", text)

    def test_preview_codex(self):
        text = self.mod.preview_codex("codex-1", 10)
        self.assertIn("--- codex codex-1", text)
        self.assertIn("[user] Review this function", text)
        self.assertIn("[ai] The function looks okay.", text)

    def test_preview_agy(self):
        text = self.mod.preview_agy("agy-1", 10)
        self.assertIn("--- agy agy-1", text)
        self.assertIn("[user] Plan the migration", text)
        self.assertIn("[ai] Okay, let's start with plan the migration.", text)

    def test_preview_opencode(self):
        text = self.mod.preview_opencode("oc-1", 10)
        self.assertIn("--- opencode oc-1", text)
        self.assertIn("[msg] Explain this code", text)
        self.assertIn("[msg] Here is an explanation", text)

    def test_preview_devin(self):
        text = self.mod.preview_devin("dev-1", 10)
        self.assertIn("--- devin dev-1", text)
        self.assertIn("[user] Build a landing page", text)
        self.assertIn("[assistant] I will build a landing page", text)
        self.assertNotIn("this should be ignored", text)

    def test_cmd_list_json(self):
        _, out = self._capture_stdout(self.mod.cmd_list, ["--json"])
        rows = json.loads(out)
        ids = {r["id"] for r in rows}
        self.assertIn("dev-2", ids)
        self.assertEqual(len(rows), 10)

    def test_cmd_list_tsv(self):
        _, out = self._capture_stdout(self.mod.cmd_list, [])
        for line in out.strip().splitlines():
            cols = line.split("\t")
            self.assertEqual(len(cols), 7, f"bad TSV line: {line!r}")

    def test_cmd_list_agent_filter(self):
        _, out = self._capture_stdout(self.mod.cmd_list, ["--agent", "devin"])
        lines = out.strip().splitlines()
        self.assertTrue(lines)
        for line in lines:
            self.assertTrue(line.startswith("devin"))

    def test_cmd_preview(self):
        _, out = self._capture_stdout(self.mod.cmd_preview, ["claude", "sess-c1a2b3"])
        self.assertIn("Refactor the login form", out)

    def test_cmd_agents(self):
        _, out = self._capture_stdout(self.mod.cmd_agents)
        for a in self.mod.AGENTS:
            self.assertIn(f"{a}: ok", out)


if __name__ == "__main__":
    unittest.main()
