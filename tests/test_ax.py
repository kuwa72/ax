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
from unittest import mock

import ax_test_support  # noqa: F401  (scrubs HERMES_HOME for the test run)

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
        cls.aider_ids = {
            os.path.join(cls.tmp, "aiderws", "proj-one",
                         ".aider.chat.history.md"),
            os.path.join(cls.tmp, "aiderws", "proj-two",
                         ".aider.chat.history.md"),
        }

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

    def _run_ok(self):
        m = mock.Mock()
        m.returncode = 0
        return m

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
            "oc-v2-1",
            "oc-v2-parent",
            "oc-v2-null",
            "dev-1",
            "dev-2",
            "g-1",
            "g-2",
            "20260101_1",
            "ompid1",
            "ompid2",
            "vb001",
            "vb002",
            "h-1",
            "h-2",
        } | self.aider_ids
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
        by_id = {r["id"] for r in rows}
        # v1 (pre-migration) and v2 (post-migration) sessions both appear;
        # fork/subagent children (parent_id set) are hidden (#36)
        self.assertEqual(by_id, {"oc-1", "oc-2", "oc-v2-1", "oc-v2-parent",
                                "oc-v2-null"})
        rows = {r["id"]: r for r in self.mod.list_opencode(400)}
        self.assertEqual(rows["oc-1"]["title"], "open test one")
        self.assertEqual(rows["oc-2"]["title"], "open test two")
        self.assertEqual(rows["oc-v2-1"]["title"], "v2 session one")
        self.assertEqual(rows["oc-v2-1"]["cwd"], "/home/alice/opencode3")

    def test_preview_opencode_v2_session(self):
        text = self.mod.preview_opencode("oc-v2-1", 10)
        self.assertIn("--- opencode oc-v2-1", text)
        self.assertIn("[user]", text)
        self.assertIn("v2 user question", text)
        self.assertIn("[ai]", text)
        self.assertIn("v2 assistant answer", text)

    def test_grep_opencode_v2_session(self):
        rows = self.mod.grep_sessions("v2 assistant", ["opencode"], 50)
        ids = {r["id"] for r in rows}
        self.assertIn("oc-v2-1", ids)

    def _capture(self, fn, *args, **kwargs):
        old_out, old_err = sys.stdout, sys.stderr
        out, err = io.StringIO(), io.StringIO()
        sys.stdout, sys.stderr = out, err
        try:
            rc = fn(*args, **kwargs)
        finally:
            sys.stdout, sys.stderr = old_out, old_err
        return rc, out.getvalue(), err.getvalue()

    def test_rm_opencode_v2_session_accepted(self):
        # opencode rm goes through subprocess.run, not the tty runner;
        # existence check must also accept v2 sessions.
        with mock.patch("subprocess.run", return_value=self._run_ok()) as mrun, \
                mock.patch("shutil.which", return_value="/bin/true"):
            rc, _, _ = self._capture(
                self.mod.cmd_rm, ["opencode", "oc-v2-1", "--yes"])
        self.assertEqual(rc, 0)
        argv = mrun.call_args[0][0]
        self.assertEqual(argv, ["opencode", "session", "delete", "oc-v2-1"])

    def test_opencode_cache_creates_and_reuses(self):
        rows = self.mod.list_opencode(300)
        self.assertTrue(rows)
        cache_path = os.path.join(self.tmp, ".cache", "ax", "opencode.json")
        self.assertTrue(os.path.exists(cache_path))
        rows2 = self.mod.list_opencode(300)
        self.assertEqual(rows, rows2)

    def test_opencode_cache_no_cache_matches(self):
        rows1 = self.mod.list_opencode(300, no_cache=True)
        rows2 = self.mod.list_opencode(300, no_cache=False)
        self.assertEqual(rows1, rows2)

    def test_list_devin(self):
        rows = self.mod.list_devin(400)
        by_id = {r["id"]: r for r in rows}
        self.assertEqual(set(by_id), {"dev-1", "dev-2"})
        self.assertEqual(by_id["dev-1"]["title"], "devin test one")
        self.assertEqual(by_id["dev-2"]["title"], "devin test two")

    def test_list_aider(self):
        rows = self.mod.list_aider(400)
        by_id = {r["id"]: r for r in rows}
        self.assertEqual(set(by_id), self.aider_ids)
        p1 = os.path.join(self.tmp, "aiderws", "proj-one",
                          ".aider.chat.history.md")
        self.assertEqual(by_id[p1]["title"], "Fix the lexer bug")
        self.assertEqual(by_id[p1]["cwd"], os.path.dirname(p1))
        p2 = os.path.join(self.tmp, "aiderws", "proj-two",
                          ".aider.chat.history.md")
        self.assertEqual(by_id[p2]["title"], "Update the README")

    def test_list_goose(self):
        rows = self.mod.list_goose(400)
        by_id = {r["id"]: r for r in rows}
        self.assertEqual(set(by_id), {"g-1", "g-2", "20260101_1"})
        self.assertEqual(by_id["g-1"]["title"], "goose test one")
        self.assertEqual(by_id["g-1"]["cwd"], "/home/alice/gooseproj")
        self.assertEqual(by_id["20260101_1"]["title"], "legacy goose session")
        self.assertEqual(by_id["20260101_1"]["cwd"], "/home/alice/legacy")

    def test_list_omp(self):
        rows = self.mod.list_omp(400)
        by_id = {r["id"]: r for r in rows}
        self.assertEqual(set(by_id), {"ompid1", "ompid2"})
        self.assertEqual(by_id["ompid1"]["title"], "omp test one")
        self.assertEqual(by_id["ompid1"]["cwd"], "/home/alice/ws")
        # legacy header-first file has no title -> first user message
        self.assertEqual(by_id["ompid2"]["title"], "Second omp session")

    def test_list_vibe(self):
        rows = self.mod.list_vibe(400)
        by_id = {r["id"]: r for r in rows}
        self.assertEqual(set(by_id), {"vb001", "vb002"})
        self.assertEqual(by_id["vb001"]["title"], "vibe test one")
        self.assertEqual(by_id["vb001"]["cwd"], "/home/alice/vibeproj")
        self.assertEqual(by_id["vb002"]["title"], "Plan the deploy")

    def test_list_hermes(self):
        rows = self.mod.list_hermes(400)
        by_id = {r["id"]: r for r in rows}
        self.assertEqual(set(by_id), {"h-1", "h-2"})
        self.assertEqual(by_id["h-1"]["title"], "hermes test one")
        self.assertEqual(by_id["h-1"]["cwd"], "/home/alice/hproj")
        self.assertEqual(by_id["h-2"]["title"], "Restart the worker")

    def test_hermes_env_scrubbed_by_harness(self):
        # Issue #31: session runners (Hermes etc.) export HERMES_HOME
        # pointing at the real store. The harness support module must scrub
        # it on import so tests only ever see the fixture store.
        store = os.path.join(self.tmp, "empty_hermes_store")
        os.makedirs(store, exist_ok=True)
        os.environ["HERMES_HOME"] = store
        importlib.reload(ax_test_support)
        try:
            self.assertNotIn("HERMES_HOME", os.environ)
            rows = self.mod.list_hermes(400)
        finally:
            os.environ.pop("HERMES_HOME", None)
        self.assertEqual({r["id"] for r in rows}, {"h-1", "h-2"})

    def test_preview_claude(self):
        text = self.mod.preview_claude("sess-c1a2b3", 10)
        self.assertIn("--- claude sess-c1a2b3", text)
        self.assertIn("[user]", text)
        self.assertIn("Refactor the login form", text)
        self.assertIn("[ai]", text)
        self.assertIn("I'll help you refactor the login form.", text)

    def test_preview_codex(self):
        text = self.mod.preview_codex("codex-1", 10)
        self.assertIn("--- codex codex-1", text)
        self.assertIn("[user]", text)
        self.assertIn("Review this function", text)
        self.assertIn("[ai]", text)
        self.assertIn("The function looks okay.", text)

    def test_preview_agy(self):
        text = self.mod.preview_agy("agy-1", 10)
        self.assertIn("--- agy agy-1", text)
        self.assertIn("[user]", text)
        self.assertIn("Plan the migration", text)
        self.assertIn("[ai]", text)
        self.assertIn("Okay, let's start with plan the migration.", text)

    def test_preview_opencode(self):
        text = self.mod.preview_opencode("oc-1", 10)
        self.assertIn("--- opencode oc-1", text)
        self.assertIn("[user]", text)
        self.assertIn("Explain this code", text)
        self.assertIn("[ai]", text)
        self.assertIn("Here is an explanation", text)

    def test_preview_devin(self):
        text = self.mod.preview_devin("dev-1", 10)
        self.assertIn("--- devin dev-1", text)
        self.assertIn("[user]", text)
        self.assertIn("Build a landing page", text)
        self.assertIn("[ai]", text)
        self.assertIn("I will build a landing page", text)
        self.assertNotIn("this should be ignored", text)

    def test_preview_aider(self):
        sid = os.path.join(self.tmp, "aiderws", "proj-one",
                           ".aider.chat.history.md")
        text = self.mod.preview_aider(sid, 10)
        self.assertIn(f"--- aider {sid}", text)
        self.assertIn("[user]", text)
        self.assertIn("Fix the lexer bug", text)
        self.assertIn("[ai]", text)
        self.assertIn("Here is the fix for the lexer bug.", text)
        self.assertNotIn("Applied edit to parser.py", text)

    def test_preview_goose(self):
        text = self.mod.preview_goose("g-1", 10)
        self.assertIn("--- goose g-1", text)
        self.assertIn("Explain the indexer", text)
        self.assertIn("Here is how the indexer works", text)
        legacy = self.mod.preview_goose("20260101_1", 10)
        self.assertIn("Legacy user message", legacy)
        self.assertIn("Legacy reply", legacy)

    def test_preview_omp(self):
        text = self.mod.preview_omp("ompid1", 10)
        self.assertIn("--- omp ompid1", text)
        self.assertIn("[user]", text)
        self.assertIn("Fix the tokenizer", text)
        self.assertIn("[ai]", text)
        self.assertIn("I'll fix the tokenizer", text)
        self.assertNotIn("tool output ignored", text)

    def test_preview_vibe(self):
        text = self.mod.preview_vibe("vb001", 10)
        self.assertIn("--- vibe vb001", text)
        self.assertIn("Summarize the logs", text)
        self.assertIn("Reply to: Summarize the logs", text)
        self.assertNotIn("system prompt ignored", text)

    def test_preview_hermes(self):
        text = self.mod.preview_hermes("h-1", 10)
        self.assertIn("--- hermes h-1", text)
        self.assertIn("Check the gateway", text)
        self.assertIn("Gateway is running", text)
        self.assertNotIn("old inactive message", text)
        text2 = self.mod.preview_hermes("h-2", 10)
        self.assertIn("Worker restarted", text2)

    def test_cmd_list_json(self):
        _, out = self._capture_stdout(self.mod.cmd_list, ["--json"])
        rows = json.loads(out)
        ids = {r["id"] for r in rows}
        self.assertIn("dev-2", ids)
        self.assertEqual(len(rows), 24)

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

    def test_cmd_list_no_cache(self):
        _, out = self._capture_stdout(self.mod.cmd_list, ["--agent", "opencode", "--no-cache"])
        for line in out.strip().splitlines():
            cols = line.split("\t")
            self.assertEqual(len(cols), 7, f"bad TSV line: {line!r}")
        _, out2 = self._capture_stdout(self.mod.cmd_list, ["--agent", "opencode"])
        ids1 = [l.split("\t")[1] for l in out.strip().splitlines()]
        ids2 = [l.split("\t")[1] for l in out2.strip().splitlines()]
        self.assertEqual(ids1, ids2)

    def test_cmd_preview(self):
        _, out = self._capture_stdout(self.mod.cmd_preview, ["claude", "sess-c1a2b3"])
        self.assertIn("Refactor the login form", out)

    def test_cmd_agents(self):
        _, out = self._capture_stdout(self.mod.cmd_agents)
        for a in self.mod.AGENTS:
            line = next(l for l in out.strip().splitlines() if l.startswith(f"{a}:"))
            self.assertIn(f"{a}: ok", line)
            self.assertIn("sessions", line)


if __name__ == "__main__":
    unittest.main()
