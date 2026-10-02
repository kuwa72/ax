#!/usr/bin/env python3
"""Unit tests for ax stats (cross-agent usage statistics)."""
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
        loader = machinery.SourceFileLoader("ax_stats_test_mod", AX_PATH)
        spec = importlib.util.spec_from_loader("ax_stats_test_mod", loader, origin=AX_PATH)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod
    finally:
        if old is None:
            os.environ.pop("HOME", None)
        else:
            os.environ["HOME"] = old


class TestStats(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls._orig_home = os.environ.get("HOME")
        cls.tmp = tempfile.mkdtemp(prefix="ax_stats_test_home_")
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
        # git checkout resets mtimes; pin them so epochs are
        # deterministic (the lister derives claude epochs from mtime)
        os.utime(os.path.join(cls.tmp, ".claude", "projects",
                              "webapp", "sess-c1a2b3.jsonl"),
                 (1700000000, 1700000000))
        os.utime(os.path.join(cls.tmp, ".claude", "projects",
                              "api", "sess-d4e5f6.jsonl"),
                 (1700000020, 1700000020))
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

    def test_stats_agents_summary_tsv(self):
        _, out = self._capture_stdout(self.mod.cmd_stats, [])
        lines = out.strip().splitlines()
        self.assertEqual(lines[0].split("\t"),
                         ["agent", "sessions", "first", "last"])
        claude = [l for l in lines if l.startswith("claude\t")]
        self.assertEqual(len(claude), 1)
        cols = claude[0].split("\t")
        # claude fixture: sess-c1a2b3 (mtime 1700000000),
        # sess-d4e5f6 (mtime 1700000020)
        self.assertEqual(cols[1], "2")
        self.assertEqual(cols[2], "1700000000")
        self.assertEqual(cols[3], "1700000020")

    def test_stats_tsv_sections(self):
        _, out = self._capture_stdout(self.mod.cmd_stats, [])
        self.assertIn("agent\tsessions\tfirst\tlast", out)
        self.assertIn("date\tsessions", out)
        self.assertIn("cwd\tsessions", out)

    def test_stats_daily_window(self):
        # --days N は直近 N 日分だけ出力 (fixture は 2023 年なので
        # カウントは 0、ウィンドウ長のみ検証)
        _, out = self._capture_stdout(self.mod.cmd_stats, ["--days", "3"])
        daily = (out.split("date\tsessions\n", 1)[1]
                 .split("cwd\tsessions")[0].strip().splitlines())
        self.assertEqual(len(daily), 3)

    def test_stats_json_shape(self):
        _, out = self._capture_stdout(self.mod.cmd_stats, ["--json"])
        obj = json.loads(out)
        self.assertEqual(set(obj), {"agents", "daily", "top_cwd"})
        claude = [a for a in obj["agents"] if a["agent"] == "claude"][0]
        self.assertEqual(claude["sessions"], 2)
        self.assertEqual(claude["first"], 1700000000)
        self.assertEqual(claude["last"], 1700000020)
        self.assertEqual(len(obj["daily"]), 14)

    def test_stats_json_top_cwd(self):
        _, out = self._capture_stdout(
            self.mod.cmd_stats, ["--json", "--top", "100"])
        obj = json.loads(out)
        cwds = {c["cwd"]: c["sessions"] for c in obj["top_cwd"]}
        self.assertEqual(cwds.get("/home/alice/projects/webapp"), 1)

    def test_stats_one_provider_failing(self):
        # 1 プロバイダが異常でも他は継続 (stderr 警告のみ)
        def _boom(**kwargs):
            raise Exception("boom")

        with mock.patch.dict(self.mod.LISTERS, {"claude": _boom}), \
                contextlib.redirect_stderr(io.StringIO()):
            _, out = self._capture_stdout(self.mod.cmd_stats, ["--json"])
        obj = json.loads(out)
        agents = {a["agent"] for a in obj["agents"]}
        self.assertNotIn("claude", agents)
        self.assertIn("codex", agents)

    def test_stats_unknown_cwd_excluded(self):
        # cwd 不明 ("?") のセッションは top_cwd に出ない
        rows = self.mod.collect(list(self.mod.AGENTS), 100000)
        self.assertTrue(any(r["cwd"] == "?" for r in rows))
        _, out = self._capture_stdout(
            self.mod.cmd_stats, ["--json", "--top", "100"])
        obj = json.loads(out)
        self.assertNotIn("?", [c["cwd"] for c in obj["top_cwd"]])


if __name__ == "__main__":
    unittest.main()
