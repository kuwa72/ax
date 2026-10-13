#!/usr/bin/env python3
"""Unit tests for ax qwen / droid / grok / kimi / copilot providers
using synthetic fixtures."""
import importlib.machinery as machinery
import importlib.util
import io
import os
import shutil
import sys
import tempfile
import unittest

import ax_test_support  # noqa: F401  (scrubs store-redirecting env vars)

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
AX_PATH = os.path.join(REPO_ROOT, "ax")
FIXTURES = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fixtures")


def load_ax(home):
    old = os.environ.get("HOME")
    os.environ["HOME"] = home
    try:
        loader = machinery.SourceFileLoader("ax_newprov_test_mod", AX_PATH)
        spec = importlib.util.spec_from_loader(
            "ax_newprov_test_mod", loader, origin=AX_PATH)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod
    finally:
        if old is None:
            os.environ.pop("HOME", None)
        else:
            os.environ["HOME"] = old


class TestNewProviders(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls._orig_home = os.environ.get("HOME")
        cls.tmp = tempfile.mkdtemp(prefix="ax_newprov_test_home_")
        cls._orig_cwd = os.getcwd()
        os.chdir(cls.tmp)
        for src, dst in [("qwen", ".qwen"),
                         ("factory", ".factory"),
                         ("grok", ".grok"),
                         ("kimi-code", ".kimi-code"),
                         ("copilot", ".copilot")]:
            s = os.path.join(FIXTURES, src)
            d = os.path.join(cls.tmp, dst)
            if os.path.isdir(s):
                shutil.copytree(s, d)
        # pin qwen session mtimes (epochs derive from mtime)
        p1 = os.path.join(
            cls.tmp, ".qwen", "projects", "home-alice-qwen-proj",
            "chats", "aaaa1111-0000-0000-0000-0000000000q1.jsonl")
        os.utime(p1, (1768471200, 1768471200))
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

    # ---------------- qwen ----------------
    def test_list_qwen(self):
        by_id = {r["id"]: r for r in self.mod.list_qwen(50)}
        self.assertEqual(set(by_id), {"qwen-1", "qwen-2"})
        self.assertEqual(by_id["qwen-1"]["agent"], "qwen")
        self.assertEqual(by_id["qwen-1"]["cwd"], "/home/alice/qwen-proj")
        self.assertEqual(by_id["qwen-1"]["title"],
                         "Refactor the qwen search")
        self.assertEqual(by_id["qwen-1"]["epoch"],
                         self.mod._epoch_from_ts(
                             "2026-01-15T10:00:00.000Z", utc=True))

    def test_preview_qwen(self):
        text = self.mod.preview_qwen("qwen-1")
        self.assertIn("--- qwen qwen-1", text)
        self.assertIn("Refactor the qwen search", text)
        self.assertIn("I'll refactor the qwen search", text)
        self.assertNotIn("should not leak", text)

    def test_preview_qwen_not_found(self):
        self.assertIn("not found", self.mod.preview_qwen("zzz"))

    def test_grep_qwen(self):
        rows = self.mod.grep_sessions("migration", ["qwen"], 50)
        self.assertEqual({r["id"] for r in rows}, {"qwen-2"})
        rows = self.mod.grep_sessions("should not leak", ["qwen"], 50)
        self.assertEqual(rows, [])

    def test_lookup_qwen(self):
        self.assertEqual(self.mod._lookup_qwen("qwen-1")["cwd"],
                         "/home/alice/qwen-proj")
        self.assertIsNone(self.mod._lookup_qwen("zzz"))

    def test_store_info_qwen(self):
        info = self.mod.store_info_qwen()
        self.assertTrue(info["ok"])
        self.assertEqual(info["count"], 2)

    # ---------------- droid ----------------
    def test_list_droid(self):
        by_id = {r["id"]: r for r in self.mod.list_droid(50)}
        self.assertEqual(set(by_id), {"droid-1", "droid-2"})
        self.assertEqual(by_id["droid-1"]["agent"], "droid")
        self.assertEqual(by_id["droid-1"]["cwd"], "/home/alice/droid-proj")
        self.assertEqual(by_id["droid-1"]["title"],
                         "Refactor the droid search")

    def test_preview_droid(self):
        text = self.mod.preview_droid("droid-1")
        self.assertIn("--- droid droid-1", text)
        self.assertIn("Refactor the droid search", text)
        self.assertIn("I'll refactor the droid search", text)
        # system-reminder content must not leak
        self.assertNotIn("should not leak", text)

    def test_preview_droid_not_found(self):
        self.assertIn("not found", self.mod.preview_droid("zzz"))

    def test_grep_droid(self):
        rows = self.mod.grep_sessions("migration", ["droid"], 50)
        self.assertEqual({r["id"] for r in rows}, {"droid-2"})
        rows = self.mod.grep_sessions("should not leak", ["droid"], 50)
        self.assertEqual(rows, [])

    def test_lookup_droid(self):
        self.assertEqual(self.mod._lookup_droid("droid-1")["cwd"],
                         "/home/alice/droid-proj")
        self.assertIsNone(self.mod._lookup_droid("zzz"))

    def test_store_info_droid(self):
        info = self.mod.store_info_droid()
        self.assertTrue(info["ok"])
        self.assertEqual(info["count"], 2)  # .settings.json not counted

    # ---------------- grok ----------------
    def test_list_grok(self):
        by_id = {r["id"]: r for r in self.mod.list_grok(50)}
        self.assertEqual(set(by_id), {"grok-1", "grok-2"})
        self.assertEqual(by_id["grok-1"]["agent"], "grok")
        self.assertEqual(by_id["grok-1"]["cwd"], "/home/alice/grok-proj")
        self.assertEqual(by_id["grok-1"]["title"],
                         "Refactor the grok search")

    def test_preview_grok(self):
        text = self.mod.preview_grok("grok-1")
        self.assertIn("--- grok grok-1", text)
        self.assertIn("Refactor the grok search", text)
        self.assertIn("I'll refactor the grok search", text)
        # system prompt / user_info / system-reminder must not leak
        self.assertNotIn("should not leak", text)
        self.assertNotIn("env noise", text)
        self.assertNotIn("reminder", text)

    def test_preview_grok_not_found(self):
        self.assertIn("not found", self.mod.preview_grok("zzz"))

    def test_grep_grok(self):
        rows = self.mod.grep_sessions("migration", ["grok"], 50)
        self.assertEqual({r["id"] for r in rows}, {"grok-2"})
        rows = self.mod.grep_sessions("should not leak", ["grok"], 50)
        self.assertEqual(rows, [])

    def test_lookup_grok(self):
        self.assertEqual(self.mod._lookup_grok("grok-1")["cwd"],
                         "/home/alice/grok-proj")
        self.assertIsNone(self.mod._lookup_grok("zzz"))

    def test_store_info_grok(self):
        info = self.mod.store_info_grok()
        self.assertTrue(info["ok"])
        self.assertEqual(info["count"], 2)

    # ---------------- kimi ----------------
    def test_list_kimi(self):
        by_id = {r["id"]: r for r in self.mod.list_kimi(50)}
        self.assertEqual(set(by_id), {"kimi-1", "kimi-2"})
        self.assertEqual(by_id["kimi-1"]["agent"], "kimi")
        self.assertEqual(by_id["kimi-1"]["cwd"], "/home/alice/kimi-proj")
        self.assertEqual(by_id["kimi-1"]["title"],
                         "Refactor the kimi search")
        self.assertEqual(by_id["kimi-1"]["epoch"], 1700000300)

    def test_preview_kimi(self):
        text = self.mod.preview_kimi("kimi-1")
        self.assertIn("--- kimi kimi-1", text)
        self.assertIn("Refactor the kimi search", text)
        self.assertIn("I'll refactor the kimi search", text)
        # injected messages must not leak
        self.assertNotIn("should not leak", text)

    def test_preview_kimi_not_found(self):
        self.assertIn("not found", self.mod.preview_kimi("zzz"))

    def test_grep_kimi(self):
        rows = self.mod.grep_sessions("migration", ["kimi"], 50)
        self.assertEqual({r["id"] for r in rows}, {"kimi-2"})
        rows = self.mod.grep_sessions("should not leak", ["kimi"], 50)
        self.assertEqual(rows, [])

    def test_lookup_kimi(self):
        self.assertEqual(self.mod._lookup_kimi("kimi-1")["cwd"],
                         "/home/alice/kimi-proj")
        self.assertIsNone(self.mod._lookup_kimi("zzz"))

    def test_store_info_kimi(self):
        info = self.mod.store_info_kimi()
        self.assertTrue(info["ok"])
        self.assertEqual(info["count"], 2)

    # ---------------- copilot ----------------
    def test_list_copilot(self):
        by_id = {r["id"]: r for r in self.mod.list_copilot(50)}
        self.assertEqual(set(by_id), {"copilot-1", "copilot-2"})
        self.assertEqual(by_id["copilot-1"]["agent"], "copilot")
        self.assertEqual(by_id["copilot-1"]["cwd"],
                         "/home/alice/copilot-proj")
        self.assertEqual(by_id["copilot-1"]["title"],
                         "Refactor the copilot search")

    def test_preview_copilot(self):
        text = self.mod.preview_copilot("copilot-1")
        self.assertIn("--- copilot copilot-1", text)
        self.assertIn("Refactor the copilot search", text)
        self.assertIn("I'll refactor the copilot search", text)
        # transformedContent and non-message events must not leak
        self.assertNotIn("current_datetime", text)
        self.assertNotIn("should not leak", text)

    def test_preview_copilot_not_found(self):
        self.assertIn("not found", self.mod.preview_copilot("zzz"))

    def test_grep_copilot(self):
        rows = self.mod.grep_sessions("migration", ["copilot"], 50)
        self.assertEqual({r["id"] for r in rows}, {"copilot-2"})
        rows = self.mod.grep_sessions("should not leak", ["copilot"], 50)
        self.assertEqual(rows, [])

    def test_lookup_copilot(self):
        self.assertEqual(self.mod._lookup_copilot("copilot-1")["cwd"],
                         "/home/alice/copilot-proj")
        self.assertIsNone(self.mod._lookup_copilot("zzz"))

    def test_store_info_copilot(self):
        info = self.mod.store_info_copilot()
        self.assertTrue(info["ok"])
        self.assertEqual(info["count"], 2)

    # ---------------- resume commands ----------------
    def test_resume_cmds_registered(self):
        self.assertEqual(self.mod.RESUME_CMD["qwen"]("qwen-1"),
                         ["qwen", "--resume", "qwen-1"])
        self.assertEqual(self.mod.RESUME_CMD["droid"]("droid-1"),
                         ["droid", "resume", "droid-1"])
        self.assertEqual(self.mod.RESUME_CMD["grok"]("grok-1"),
                         ["grok", "--resume", "grok-1"])
        self.assertEqual(self.mod.RESUME_CMD["kimi"]("session_x"),
                         ["kimi", "--session", "session_x"])
        self.assertEqual(self.mod.RESUME_CMD["copilot"]("copilot-1"),
                         ["copilot", "--resume", "copilot-1"])


if __name__ == "__main__":
    unittest.main()
