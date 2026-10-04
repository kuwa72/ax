#!/usr/bin/env python3
"""Unit tests for ax crush / pi providers using synthetic fixtures."""
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

PI_1 = os.path.join(FIXTURES, "pi", "agent", "sessions",
                    "--home-alice-pi-proj--",
                    "2026-01-15T10-00-00-000Z_pi-1.jsonl")
PI_2 = os.path.join(FIXTURES, "pi", "agent", "sessions",
                    "--home-alice-pi-proj2--",
                    "2026-01-14T09-00-00-000Z_pi-2.jsonl")
REPO_CRUSH = os.path.join(FIXTURES, "crush", "share", "crush")


def load_ax(home):
    old = os.environ.get("HOME")
    os.environ["HOME"] = home
    try:
        loader = machinery.SourceFileLoader("ax_crush_pi_test_mod", AX_PATH)
        spec = importlib.util.spec_from_loader(
            "ax_crush_pi_test_mod", loader, origin=AX_PATH)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod
    finally:
        if old is None:
            os.environ.pop("HOME", None)
        else:
            os.environ["HOME"] = old


class TestCrushPi(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls._orig_home = os.environ.get("HOME")
        cls.tmp = tempfile.mkdtemp(prefix="ax_crush_pi_test_home_")
        cls._orig_cwd = os.getcwd()
        os.chdir(cls.tmp)
        for src, dst in [("pi", ".pi"),
                         (os.path.join("crush", "share", "crush"),
                          os.path.join(".local", "share", "crush"))]:
            s = os.path.join(FIXTURES, src)
            d = os.path.join(cls.tmp, dst)
            if os.path.isdir(s):
                shutil.copytree(s, d)
        # pin pi session mtimes (epochs derive from mtime)
        os.utime(os.path.join(cls.tmp, ".pi", "agent", "sessions",
                                "--home-alice-pi-proj--",
                                "2026-01-15T10-00-00-000Z_pi-1.jsonl"),
                 (1700000000, 1700000000))
        os.utime(os.path.join(cls.tmp, ".pi", "agent", "sessions",
                                "--home-alice-pi-proj2--",
                                "2026-01-14T09-00-00-000Z_pi-2.jsonl"),
                 (1700000010, 1700000010))
        # rewrite crush projects.json data_dirs to the copied tree
        pj = os.path.join(cls.tmp, ".local", "share", "crush",
                          "projects.json")
        with open(pj, encoding="utf-8") as fh:
            d = json.load(fh)
        tmp_crush = os.path.join(cls.tmp, ".local", "share", "crush")
        for pr in d["projects"]:
            if isinstance(pr.get("data_dir"), str):
                pr["data_dir"] = pr["data_dir"].replace(
                    "CRUSH_FIXTURE_ROOT", tmp_crush)
        with open(pj, "w", encoding="utf-8") as fh:
            json.dump(d, fh)
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

    # ---------------- pi ----------------
    def test_list_pi(self):
        by_id = {r["id"]: r for r in self.mod.list_pi(50)}
        self.assertEqual(set(by_id), {"pi-1", "pi-2"})
        self.assertEqual(by_id["pi-1"]["cwd"], "/home/alice/pi-proj")
        self.assertEqual(by_id["pi-1"]["title"], "Refactor the pi search")
        self.assertEqual(by_id["pi-1"]["epoch"], 1700000000)
        self.assertEqual(by_id["pi-2"]["cwd"], "/home/alice/pi-proj2")

    def test_preview_pi(self):
        text = self.mod.preview_pi("pi-1")
        self.assertIn("--- pi pi-1", text)
        self.assertIn("Refactor the pi search", text)
        self.assertIn("I'll refactor the pi search", text)
        # thinking parts must not leak
        self.assertNotIn("internal thought", text)

    def test_preview_pi_not_found(self):
        self.assertIn("not found", self.mod.preview_pi("zzz"))

    def test_grep_pi(self):
        rows = self.mod.grep_sessions("migration", ["pi"], 50)
        self.assertEqual({r["id"] for r in rows}, {"pi-2"})

    def test_grep_pi_thinking_excluded(self):
        rows = self.mod.grep_sessions("internal thought", ["pi"], 50)
        self.assertEqual(rows, [])

    def test_lookup_pi(self):
        row = self.mod._lookup_pi("pi-1")
        self.assertEqual(row["cwd"], "/home/alice/pi-proj")
        self.assertIsNone(self.mod._lookup_pi("zzz"))

    def test_store_info_pi(self):
        info = self.mod.store_info_pi()
        self.assertTrue(info["ok"])
        self.assertEqual(info["count"], 2)

    # ---------------- crush ----------------
    def test_list_crush(self):
        by_id = {r["id"]: r for r in self.mod.list_crush(50)}
        # subagent session (parent_session_id set) is hidden
        self.assertEqual(set(by_id), {"crush-1", "crush-2"})
        self.assertEqual(by_id["crush-1"]["title"], "crush test one")
        self.assertEqual(by_id["crush-1"]["cwd"], "/home/alice/crush-proj")
        self.assertEqual(by_id["crush-1"]["epoch"], 1700000000)
        self.assertEqual(by_id["crush-2"]["cwd"],
                         "/home/alice/crush-proj2")

    def test_preview_crush(self):
        text = self.mod.preview_crush("crush-1")
        self.assertIn("--- crush crush-1", text)
        self.assertIn("Plan the migration", text)
        self.assertIn("I will plan the migration", text)

    def test_preview_crush_not_found(self):
        self.assertIn("not found", self.mod.preview_crush("zzz"))

    def test_grep_crush(self):
        rows = self.mod.grep_sessions("migration", ["crush"], 50)
        self.assertEqual({r["id"] for r in rows}, {"crush-1"})

    def test_grep_crush_child_excluded(self):
        rows = self.mod.grep_sessions("child only", ["crush"], 50)
        self.assertEqual(rows, [])

    def test_lookup_crush(self):
        row = self.mod._lookup_crush("crush-1")
        self.assertEqual(row["cwd"], "/home/alice/crush-proj")
        self.assertIsNone(self.mod._lookup_crush("zzz"))

    def test_store_info_crush(self):
        info = self.mod.store_info_crush()
        self.assertTrue(info["ok"])
        self.assertEqual(info["count"], 2)

    # ---------------- integration ----------------
    def test_collect_includes_both(self):
        rows = self.mod.collect(["pi", "crush"], 50)
        self.assertEqual({r["agent"] for r in rows}, {"pi", "crush"})

    def test_fmt_tsv_seven_columns(self):
        rows = self.mod.collect(["pi", "crush"], 50)
        for line in self.mod.fmt_tsv(rows).splitlines():
            self.assertEqual(len(line.split("\t")), 7, f"bad line: {line!r}")

    def test_cmd_list_both_agents(self):
        _, out = self._capture_stdout(
            self.mod.cmd_list, ["--agent", "pi"])
        self.assertIn("pi-1", out)
        _, out = self._capture_stdout(
            self.mod.cmd_list, ["--agent", "crush"])
        self.assertIn("crush-1", out)

    def test_crush_store_failing_pi_continues(self):
        # projects.json が壊れても pi は継続 (stderr 警告のみ)
        pj = os.path.join(self.tmp, ".local", "share", "crush",
                          "projects.json")
        with open(pj, "w", encoding="utf-8") as fh:
            fh.write("{broken")
        try:
            with contextlib.redirect_stderr(io.StringIO()):
                rows = self.mod.collect(["pi", "crush"], 50)
        finally:
            shutil.copy(os.path.join(REPO_CRUSH, "projects.json"), pj)
            with open(pj, encoding="utf-8") as fh:
                d = json.load(fh)
            tmp_crush = os.path.join(self.tmp, ".local", "share", "crush")
            for pr in d["projects"]:
                if isinstance(pr.get("data_dir"), str):
                    pr["data_dir"] = pr["data_dir"].replace(
                        "CRUSH_FIXTURE_ROOT", tmp_crush)
            with open(pj, "w", encoding="utf-8") as fh:
                json.dump(d, fh)
        agents = {r["agent"] for r in rows}
        self.assertIn("pi", agents)
        self.assertNotIn("crush", agents)

    def test_agents_status(self):
        _, out = self._capture_stdout(self.mod.cmd_agents)
        self.assertIn("pi: ok", out)
        self.assertIn("crush: ok", out)


if __name__ == "__main__":
    unittest.main()
